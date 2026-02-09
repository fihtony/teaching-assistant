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
        """Get the API key for a provider."""
        ai_config = self._get_ai_config()
        if not ai_config or not ai_config.config:
            return None

        # API key would be stored in config if needed
        api_key = ai_config.config.get("api_key")
        if api_key:
            try:
                return decrypt_api_key(api_key) if isinstance(api_key, str) else api_key
            except Exception as e:
                logger.error(f"Error decrypting API key for {provider}: {str(e)}")
                return None

        return None

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

        # Build context understanding prompt
        context_prompt = f"""
You are an English teaching assistant helping a teacher grade assignments.

Teacher's Background Information:
{background}

Teacher's Grading Instructions:
{instructions}

Referenced Articles/Books Found:
{json.dumps(fetched_articles, indent=2) if fetched_articles else "No specific articles found"}

Please analyze this context and provide:
1. A summary of what the assignment is about
2. Key themes or concepts the teacher wants to assess
3. Specific grading criteria based on the instructions
4. Any relevant quotes or passages from the referenced material that might be useful

Respond in JSON format:
{{
    "assignment_summary": "...",
    "key_themes": ["theme1", "theme2"],
    "grading_criteria": ["criteria1", "criteria2"],
    "relevant_quotes": ["quote1", "quote2"]
}}
"""

        try:
            response = await self._call_ai(
                prompt=context_prompt,
                system_prompt="You are an expert English teacher assistant. Analyze grading context carefully.",
            )

            # Parse JSON response
            # Find JSON in response
            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                understanding = json.loads(json_match.group())
            else:
                understanding = {"raw_response": response}

        except Exception as e:
            logger.error(f"Context understanding error: {str(e)}")
            understanding = {"error": str(e)}

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

        # Build context understanding prompt
        context_prompt = f"""
You are an English teaching assistant helping a teacher grade assignments.

Teacher's Background Information:
{background}

Teacher's Grading Instructions:
{instructions}

Referenced Articles/Books Found:
{json.dumps(fetched_articles, indent=2) if fetched_articles else "No specific articles found"}

Please analyze this context and provide:
1. A summary of what the assignment is about
2. Key themes or concepts the teacher wants to assess
3. Specific grading criteria based on the instructions
4. Any relevant quotes or passages from the referenced material that might be useful

Respond in JSON format:
{{
    "assignment_summary": "...",
    "key_themes": ["theme1", "theme2"],
    "grading_criteria": ["criteria1", "criteria2"],
    "relevant_quotes": ["quote1", "quote2"]
}}
"""

        try:
            response = await self._call_ai(
                prompt=context_prompt,
                system_prompt="You are an expert English teacher assistant. Analyze grading context carefully.",
            )

            # Parse JSON response
            # Find JSON in response
            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                understanding = json.loads(json_match.group())
            else:
                understanding = {"raw_response": response}

        except Exception as e:
            logger.error(f"Context understanding error: {str(e)}")
            understanding = {"error": str(e)}

        return {
            "references": references,
            "fetched_articles": fetched_articles,
            "cached_article_ids": cached_article_ids,
            "understanding": understanding,
        }

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
        understanding = context.get("understanding", {})

        # Build grading prompt
        grading_prompt = f"""
You are grading an English assignment. Here's the context:

ASSIGNMENT BACKGROUND:
{background}

GRADING INSTRUCTIONS:
{instructions}

CONTEXT UNDERSTANDING:
{json.dumps(understanding, indent=2)}

STUDENT'S WORK:
{extracted_text}

QUESTION TYPES TO GRADE: {[qt.value for qt in question_types]}

Please grade this assignment following these rules:
1. For each question/section, determine if the answer is correct
2. Provide specific, helpful comments for wrong answers
3. Be encouraging but accurate
4. For essays, evaluate content, grammar, and understanding

Respond in JSON format:
{{
    "items": [
        {{
            "question_number": 1,
            "question_type": "mcq|true_false|fill_blank|qa|reading|picture|essay",
            "student_answer": "what the student wrote",
            "correct_answer": "the correct answer (if applicable)",
            "is_correct": true/false,
            "comment": "feedback for the student"
        }}
    ],
    "section_scores": {{
        "mcq": {{"correct": 3, "total": 5}},
        "essay": {{"correct": 1, "total": 1}}
    }},
    "overall_comment": "general feedback for the student"
}}
"""

        try:
            response = await self._call_ai(
                prompt=grading_prompt,
                system_prompt="You are an expert English teacher. Grade fairly and provide constructive feedback.",
            )

            # Handle None response
            if not response:
                raise ValueError("AI grading service returned empty response")

            # Parse JSON response
            json_match = re.search(r"\{[\s\S]*\}", response)
            if json_match:
                grading_data = json.loads(json_match.group())
            else:
                raise ValueError("Could not parse grading response")

            # Add encouragement words for perfect sections
            section_scores = {}
            for section_name, scores in grading_data.get("section_scores", {}).items():
                encouragement = None
                if (
                    scores.get("correct") == scores.get("total")
                    and scores.get("total", 0) > 0
                ):
                    import random

                    encouragement = random.choice(ENCOURAGEMENT_WORDS)

                section_scores[section_name] = SectionScore(
                    correct=scores.get("correct", 0),
                    total=scores.get("total", 0),
                    encouragement=encouragement,
                )

            # Build result
            items = []
            for item_data in grading_data.get("items", []):
                # Handle student_answer and correct_answer that might be dicts
                student_answer = item_data.get("student_answer", "")
                correct_answer = item_data.get("correct_answer")

                # Convert dict answers to string representation
                if isinstance(student_answer, dict):
                    student_answer = json.dumps(student_answer)
                if isinstance(correct_answer, dict):
                    correct_answer = json.dumps(correct_answer)

                items.append(
                    GradingItemResult(
                        question_number=item_data.get("question_number", 0),
                        question_type=QuestionType(
                            item_data.get("question_type", "qa")
                        ),
                        student_answer=str(student_answer) if student_answer else "",
                        correct_answer=str(correct_answer) if correct_answer else None,
                        is_correct=item_data.get("is_correct", False),
                        comment=item_data.get("comment", ""),
                    )
                )

            return GradingResult(
                items=items,
                section_scores=section_scores,
                overall_comment=grading_data.get("overall_comment"),
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
        Call litellm for non-Copilot providers.

        Args:
            prompt: User prompt.
            system_prompt: Optional system prompt.
            provider: AI provider.
            model: Model name.

        Returns:
            AI response text.
        """
        api_key = self._get_api_key(provider)
        if not api_key:
            raise ValueError(f"No API key configured for provider: {provider}")

        litellm = self._get_litellm()

        # Set API key
        if provider == "openai":
            litellm.openai_key = api_key
        elif provider == "anthropic":
            litellm.anthropic_key = api_key

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        ai_config = self._get_ai_config()
        timeout = (ai_config.config or {}).get("timeout", 60) if ai_config else 60
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            timeout=timeout,
        )
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

        # Save grading context
        grading_context = GradingContext(
            assignment_id=assignment.id,
            raw_background=assignment.background,
            extracted_references=context.get("references"),
            search_results=None,  # Could store search results here
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
