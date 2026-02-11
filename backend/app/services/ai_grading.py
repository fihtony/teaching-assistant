"""
AI grading service for intelligent assignment grading.
"""

import json
from datetime import datetime
from typing import List, Dict, Optional, Any
import re

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.security import decrypt_api_key
from app.core.settings_db import ensure_settings_config
from app.models import (
    Assignment,
    Settings,
    GradingContext,
    CachedArticle,
)
from app.schemas.assignment import (
    QuestionType,
    GradingResult,
    GradingItemResult,
    SectionScore,
)
from app.services.search_service import get_search_service

logger = get_logger()

# Encouragement words for sections with all correct answers
ENCOURAGEMENT_WORDS = [
    "Bravo!",
    "Excellent!",
    "Perfect!",
    "Outstanding!",
    "Wonderful!",
    "Fantastic!",
    "Superb!",
    "Amazing!",
    "Great job!",
    "Well done!",
]


class AIGradingService:
    """
    Service for AI-powered assignment grading.

    Uses LiteLLM to support multiple AI providers.
    Implements two-stage grading: understanding context, then grading.
    """

    def __init__(self, db: Session):
        self.db = db
        self._litellm = None

    def _get_litellm(self):
        """Lazy load litellm module."""
        if self._litellm is None:
            import litellm

            self._litellm = litellm
        return self._litellm

    def _get_ai_config(self) -> Optional[Settings]:
        """Get the AI configuration from database."""
        return self.db.query(Settings).filter(Settings.type == "ai-config").first()

    def _get_api_key(self, provider: str) -> Optional[str]:
        """Get the API key for a provider (from Settings type=ai-config)."""
        ai_config = self._get_ai_config()
        if not ai_config or not ai_config.config:
            return None

        api_key = ai_config.config.get("api_key")
        if api_key:
            try:
                return decrypt_api_key(api_key) if isinstance(api_key, str) else api_key
            except Exception as e:
                logger.error(f"Error decrypting API key for {provider}: {str(e)}")
                return None

        return None

    @staticmethod
    def _normalize_zhipu_model(model: str) -> str:
        """
        Normalize ZhipuAI model name to capitalized form (API is case-sensitive).
        e.g. glm-4.7 -> GLM-4.7, glm-4-flash -> GLM-4-flash.
        """
        if not model:
            return model
        lower = model.strip().lower()
        if lower.startswith("glm-"):
            return "GLM-" + lower[4:]  # GLM-4.7, GLM-4-flash, etc.
        return model

    def _build_litellm_model_and_base(
        self, provider: str, model: str
    ) -> tuple[str, Optional[str], Optional[str]]:
        """
        Build LiteLLM model string (provider/model) and optional api_base from
        database config (Settings type=ai-config). Returns (litellm_model, api_base, api_key).
        """
        ai_config = self._get_ai_config()
        config = (ai_config.config or {}) if ai_config else {}
        api_key = self._get_api_key(provider)

        # ZhipuAI: use OpenAI-compatible endpoint with model name in capitalized form (e.g. GLM-4.7)
        provider_lower = (provider or "").strip().lower()
        if provider_lower in ("zhipuai", "zhipu"):
            normalized = self._normalize_zhipu_model(model)
            logger.debug("ZhipuAI model normalized to capitalized form: %s -> %s", model, normalized)
            api_base = (
                config.get("baseUrl")
                or config.get("api_base")
                or "https://open.bigmodel.cn/api/coding/paas/v4"
            )
            litellm_model = f"openai/{normalized}"
            return litellm_model, api_base, api_key
        if provider_lower == "openai":
            return f"openai/{model}", None, api_key
        if provider_lower == "anthropic":
            return f"anthropic/{model}", None, api_key
        if provider_lower in ("google", "gemini"):
            return f"gemini/{model}", None, api_key
        # Fallback: try openai/ with optional custom base from config
        api_base = config.get("baseUrl") or config.get("api_base")
        return f"openai/{model}", api_base, api_key

    async def _call_ai(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        Call the AI model with the given prompt.

        Args:
            prompt: User prompt.
            system_prompt: Optional system prompt.
            provider: AI provider (openai, anthropic, google, copilot).
            model: Model name.

        Returns:
            AI response text.
        """
        ai_config = self._get_ai_config()
        defaults = ensure_settings_config(self.db).config or {}

        if provider is None:
            ai_config_data = ai_config.config if ai_config else {}
            provider = ai_config_data.get("provider") or defaults.get("provider", "openai")
        if model is None:
            ai_config_data = ai_config.config if ai_config else {}
            model = ai_config_data.get("model") or defaults.get("model", "gpt-4o")

        logger.info(f"Calling AI: provider={provider}, model={model}")

        # Handle copilot provider with Copilot Bridge
        if provider == "copilot":
            return await self._call_copilot_bridge(prompt, system_prompt, model)

        # For other providers, use litellm
        return await self._call_litellm(prompt, system_prompt, provider, model)

    async def build_grading_context(
        self, background: str, instructions: str, db: Session
    ) -> Dict[str, Any]:
        """
        Stage 1: Build understanding for grading

        Args:
            background: Teacher-provided background.
            instructions: Custom grading instructions.
            db: Database session.

        Returns:
            Context dictionary with understanding and references.
        """
        search_service = get_search_service(db)

        # Extract references from background
        references = search_service.extract_book_references(background)

        # Fetch article content for each book reference
        fetched_articles = []
        cached_article_ids = []

        for book in references.get("books", []):
            article_data = search_service.fetch_article_content(book)
            if article_data:
                fetched_articles.append(
                    {
                        "title": book,
                        "summary": article_data.get("summary", ""),
                        "quotes": article_data.get("quotes", [])[:5],
                        "author": article_data.get("author"),
                    }
                )
                if "cached_article_id" in article_data:
                    cached_article_ids.append(article_data["cached_article_id"])

        # Build context understanding prompt (background already includes any referenced articles)
        context_prompt = f"""
You are an expert English teacher grading student assignments.

Background Information:
{background}

Teacher's Grading Instructions:
{instructions}

Summarize briefly the assignment context and key grading criteria.
"""

        try:
            response = await self._call_ai(
                prompt=context_prompt,
                system_prompt="You are an expert English teacher. Analyze grading context carefully.",
            )
            # Use raw response as understanding (no JSON)
            understanding = response.strip() if response else ""

        except Exception as e:
            logger.error(f"Context understanding error: {str(e)}")
            understanding = f"Error: {str(e)}"

        return {
            "references": references,
            "fetched_articles": fetched_articles,
            "cached_article_ids": cached_article_ids,
            "understanding": understanding,
        }

    async def understand_context(
        self, background: str, instructions: str, db: Session
    ) -> Dict[str, Any]:
        """
        Alias for build_grading_context for backward compatibility.

        Args:
            background: Teacher-provided background.
            instructions: Custom grading instructions.
            db: Database session.

        Returns:
            Context dictionary with understanding and references.
        """
        return await self.build_grading_context(background, instructions, db)

    async def grade_assignment(
        self,
        assignment: Assignment,
        context: Dict[str, Any],
        question_types: List[QuestionType],
    ) -> GradingResult:
        """
        Stage 2: Grade the assignment.

        Args:
            assignment: Assignment to grade.
            context: Context from understand_context().
            question_types: Types of questions in the assignment.

        Returns:
            GradingResult with detailed grading.
        """
        extracted_text = assignment.extracted_text or ""
        background = assignment.background or ""
        instructions = assignment.instructions or ""
        understanding = context.get("understanding", "")
        if isinstance(understanding, dict):
            understanding = json.dumps(understanding, indent=2)
        student_name = (assignment.title or "").strip() or "Student"

        # Build grading prompt (output as HTML, no JSON)
        grading_prompt = f"""
You are an expert English teacher grading an English assignment. Here's the context:

STUDENT NAME: {student_name}

ASSIGNMENT BACKGROUND:
{background}

GRADING INSTRUCTIONS:
{instructions}

CONTEXT UNDERSTANDING:
{understanding}

STUDENT'S WORK:
{extracted_text}

QUESTION TYPES TO GRADE: {[qt.value for qt in question_types]}

Grade this assignment following these rules:
1. For each question/section, determine if the answer is correct
2. Provide specific, helpful comments for wrong answers
3. Be encouraging but accurate
4. For essays and writing, show corrections inline like a teacher's red pen

HTML format requirements (you MUST follow these so corrections are visible):
- Student's wrong text (to be deleted): wrap in <del>wrong text</del>. It will display as black text with a red strikethrough (student's original stays black; only the teacher's correction is red).
- Your correction or added text: wrap in <span class="correction">corrected text</span> or <span style="color: #b91c1c;">corrected text</span> (red text for teacher's feedback).
- Use <p> for paragraphs. For section titles you MUST use <h2> with inline bold so they stand out, e.g. <h2 style="font-weight: bold;">Revised Essay</h2>, <h2 style="font-weight: bold;">Detailed Corrections</h2>, <h2 style="font-weight: bold;">Teacher's Comments</h2>. Leave a blank line before each <h2> so sections are clearly separated.
- Keep student's correct text in normal black; only mark errors with <del> and your corrections in red.
- Example: "Many people have <del>an answer about</del><span class=\"correction\">different opinions on</span> the topic."

Respond with your grading as HTML only. Structure your output with these sections (each as <h2> with content below): (1) Revised Essay — student's work with strikethrough and red corrections inline; (2) Detailed Corrections — list of corrections with explanations; (3) Teacher's Comments — use <ul><li> for each point under "What You Did Well" and "Areas for Improvement" so each point has a bullet, and put the closing sentence (e.g. "Keep up the great work!") in a separate <p> after the lists so there is clear spacing before it. Example: <h2>Teacher's Comments</h2><h3>What You Did Well</h3><ul><li>First point.</li><li>Second point.</li></ul><h3>Areas for Improvement</h3><ul><li>First point.</li></ul><p>Keep up the great work!</p> Output only the HTML document fragment, no JSON and no markdown code fences.
"""

        try:
            response = await self._call_ai(
                prompt=grading_prompt,
                system_prompt="You are an expert English teacher. Grade fairly and provide constructive feedback. Output as HTML only. Use <del> for student's wrong text (it will show as black with red strikethrough) and <span class=\"correction\"> or red span for your corrections (red text). Student original text is always black; only teacher corrections are red.",
            )

            if not response:
                raise ValueError("AI grading service returned empty response")

            # Treat response as HTML (strip optional markdown code fence if present)
            html_content = response.strip()
            if html_content.startswith("```"):
                # Remove opening ```html or ```
                first_newline = html_content.find("\n")
                if first_newline != -1:
                    html_content = html_content[first_newline + 1 :]
                if html_content.endswith("```"):
                    html_content = html_content[:-3].strip()

            return GradingResult(
                items=[],
                section_scores={},
                overall_comment=None,
                html_content=html_content,
            )

        except Exception as e:
            logger.error(f"Grading error: {str(e)}")
            raise

    async def _call_copilot_bridge(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        Call Copilot Bridge API directly.

        Args:
            prompt: User prompt.
            system_prompt: Optional system prompt.
            model: Optional model ID.

        Returns:
            AI response text.
        """
        try:
            from app.services.copilot_bridge_client import CopilotBridgeClient
            import asyncio

            # Create Copilot Bridge client with session management
            client = CopilotBridgeClient(host="localhost", port=1287)

            # Create a new session for each request to avoid connection issues
            session_id = client.create_session()
            if not session_id:
                logger.warning(
                    "Failed to create Copilot session, continuing without session"
                )

            # Combine system and user prompts
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"

            # Call Copilot Bridge in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.query(
                    full_prompt,
                    context=None,
                    timeout=60,  # Increase to 60 seconds for longer prompts
                    model_id=model,
                ),
            )

            # Clean up session
            try:
                client.close_session()
            except Exception as e:
                logger.warning(f"Failed to close session: {str(e)}")

            if not response:
                logger.error(
                    "Copilot returned empty response, retrying with fallback..."
                )
                # Try once more without a session
                client2 = CopilotBridgeClient(host="localhost", port=1287)
                response = await loop.run_in_executor(
                    None,
                    lambda: client2.query(
                        full_prompt, context=None, timeout=60, model_id=model
                    ),
                )

            if not response:
                raise ValueError("Copilot returned empty response")

            return response
        except Exception as e:
            logger.error(f"Copilot Bridge call error: {str(e)}")
            raise

    async def _call_litellm(
        self,
        prompt: str,
        system_prompt: Optional[str],
        provider: str,
        model: str,
    ) -> str:
        """
        Call litellm for non-Copilot providers. Config (provider, model, baseUrl, api_key)
        is read from database Settings table (type=ai-config). For ZhipuAI, model is
        normalized to capitalized form (e.g. GLM-4.7).
        """
        litellm_model, api_base, api_key = self._build_litellm_model_and_base(
            provider, model
        )
        if not api_key and (provider or "").lower() in ("zhipuai", "zhipu", "openai", "anthropic"):
            raise ValueError(f"No API key configured for provider: {provider}")

        litellm = self._get_litellm()
        if (provider or "").lower() == "openai" and api_key:
            litellm.openai_key = api_key
        elif (provider or "").lower() == "anthropic" and api_key:
            litellm.anthropic_key = api_key

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        logger.debug(
            "AI request: system_prompt_len=%s, user_prompt_len=%s",
            len(system_prompt) if system_prompt else 0,
            len(prompt),
        )
        if system_prompt:
            logger.debug("AI request system_prompt: %s", system_prompt)
        logger.debug("AI request user prompt: %s", prompt)

        ai_config = self._get_ai_config()
        # Default 300s for grading (long prompts); config can override.
        raw_timeout = (ai_config.config or {}).get("timeout", 300) if ai_config else 300
        timeout = max(300, int(raw_timeout)) if raw_timeout is not None else 300

        kwargs = {
            "model": litellm_model,
            "messages": messages,
            "timeout": timeout,
        }
        if api_base:
            kwargs["api_base"] = api_base
        if api_key:
            kwargs["api_key"] = api_key
            # When using custom api_base (e.g. ZhipuAI), set openai_key so the client sends Authorization
            litellm.openai_key = api_key

        response = await litellm.acompletion(**kwargs)
        return response.choices[0].message.content

    async def grade(
        self,
        assignment: Assignment,
        question_types: Optional[List[QuestionType]] = None,
    ) -> GradingResult:
        """
        Full grading pipeline: understand context, then grade.

        Args:
            assignment: Assignment to grade.
            question_types: Types of questions (optional, will detect if not provided).

        Returns:
            GradingResult.
        """
        if question_types is None:
            question_types = [QuestionType.ESSAY]  # Default to essay

        # Stage 1: Understand context
        context = await self.understand_context(
            background=assignment.background or "",
            instructions=assignment.instructions or "",
            db=self.db,
        )

        # Save or update grading context (get-or-create to avoid UNIQUE on assignment_id on retry)
        grading_context = (
            self.db.query(GradingContext)
            .filter(GradingContext.assignment_id == assignment.id)
            .first()
        )
        if grading_context:
            grading_context.raw_background = assignment.background
            grading_context.extracted_references = context.get("references")
            grading_context.search_results = None
            grading_context.cached_article_ids = context.get("cached_article_ids")
            grading_context.ai_understanding = json.dumps(context.get("understanding"))
        else:
            grading_context = GradingContext(
                assignment_id=assignment.id,
                raw_background=assignment.background,
                extracted_references=context.get("references"),
                search_results=None,
                cached_article_ids=context.get("cached_article_ids"),
                ai_understanding=json.dumps(context.get("understanding")),
            )
            self.db.add(grading_context)
        self.db.commit()

        # Stage 2: Grade
        result = await self.grade_assignment(assignment, context, question_types)

        return result


def get_ai_grading_service(db: Session) -> AIGradingService:
    """Get an AI grading service instance."""
    return AIGradingService(db)
