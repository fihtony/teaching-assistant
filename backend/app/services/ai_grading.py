"""
AI grading service for intelligent assignment grading.
"""

import json
from datetime import datetime
from typing import List, Dict, Optional, Any, Union
import re

from sqlalchemy.orm import Session

from app.core.ai_config import get_resolved_ai_config
from app.core.logging import get_logger
from app.models import (
    Assignment,
    GradingContext,
    CachedArticle,
)
from app.services.ai_providers import get_llm_provider, get_llm_provider_for_config
from app.schemas.assignment import (
    QuestionType,
    GradingResult,
    GradingItemResult,
    SectionScore,
)
from app.services.search_service import get_search_service
from app.services.ai_prompts import GRADING_CONTEXT_PROMPT, GRADING_PROMPT

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

    def __init__(
        self,
        db: Session,
        ai_model_override: Optional[str] = None,
        ai_provider_override: Optional[str] = None,
    ):
        self.db = db
        self.ai_model_override = ai_model_override
        self.ai_provider_override = ai_provider_override

    async def _call_ai(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        Call the AI model using the user-defined provider and model from settings,
        or using overrides if provided (e.g., for preview grading with custom model selection).
        """
        # Use overrides from initialization if available (for preview grading), else use settings
        if self.ai_model_override or self.ai_provider_override:
            config = get_resolved_ai_config(self.db)
            if self.ai_provider_override:
                config["provider"] = self.ai_provider_override
            if self.ai_model_override:
                config["model"] = self.ai_model_override
            from app.services.ai_providers import get_llm_provider_for_config

            llm = get_llm_provider_for_config(config)
        else:
            llm = get_llm_provider(self.db)

        config = get_resolved_ai_config(self.db)
        timeout = config.get("timeout", 300)
        timeout = max(300, int(timeout)) if timeout is not None else 300

        # Log debug info about the AI prompt invocation
        ai_model = self.ai_model_override or config.get("model")
        ai_provider = self.ai_provider_override or config.get("provider")
        logger.debug(
            "AI prompt invocation: provider=%s, model=%s, prompt_length=%d, system_prompt_length=%d, timeout=%d",
            ai_provider,
            ai_model,
            len(prompt),
            len(system_prompt) if system_prompt else 0,
            timeout,
        )
        logger.debug("Prompt content:\n%s", prompt)
        if system_prompt:
            logger.debug("System prompt content:\n%s", system_prompt)

        logger.info("Calling AI: provider=%s, model=%s", ai_provider, ai_model)
        return await llm.complete(
            prompt,
            system_prompt=system_prompt,
            timeout=timeout,
        )

    async def run_context_prompt_phase(
        self,
        assignment: Assignment,
        context: GradingContext,
        template_instruction: str,
        custom_instruction: str,
        student_info: str,
    ) -> Dict[str, Any]:
        """
        Run the grading context prompt; parse JSON output and optionally search for books/articles.
        Saves extracted_references and final_grading_instruction (into ai_understanding) to context.
        Returns dict with keys: extracted_references, final_grading_instruction.
        """
        background = (context.background or "").strip()
        prompt = GRADING_CONTEXT_PROMPT.format(
            student_info=student_info or "Not provided.",
            background=background or "Not provided.",
            template_instruction=template_instruction or "None.",
            custom_instruction=custom_instruction or "None.",
        )
        response = await self._call_ai(
            prompt=prompt,
            system_prompt="You are an expert English teacher. Output only valid JSON.",
        )
        if not response:
            raise ValueError("Context prompt returned empty response")
        text = response.strip()
        if text.startswith("```"):
            first = text.find("\n")
            if first != -1:
                text = text[first + 1 :]
            if text.endswith("```"):
                text = text[:-3].strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(
                "Context prompt JSON parse failed, using raw as instruction: %s", e
            )
            data = {
                "extracted_references": {"books": [], "articles": [], "authors": []},
                "final_grading_instruction": text[:8000],
            }
        refs = data.get("extracted_references") or {}
        if not isinstance(refs, dict):
            refs = {"books": [], "articles": [], "authors": []}

        final_instruction = (
            data.get("final_grading_instruction") or ""
        ).strip() or "Grade the assignment fairly with constructive feedback."
        output_requirements = (data.get("output_requirements") or "").strip() or ""

        search_service = get_search_service(self.db)
        books = refs.get("books") or []
        cached_article_ids = []
        for book in books[:10]:
            article_data = search_service.fetch_article_content(book)
            if article_data and "cached_article_id" in article_data:
                cached_article_ids.append(article_data["cached_article_id"])
        context.extracted_references = refs
        context.cached_article_ids = cached_article_ids if cached_article_ids else None
        context.ai_understanding = final_instruction
        context.output_requirements = (
            output_requirements if output_requirements else None
        )
        self.db.commit()
        return {
            "extracted_references": refs,
            "final_grading_instruction": final_instruction,
            "output_requirements": output_requirements,
        }

    async def run_grading_prompt_phase(
        self,
        assignment: Assignment,
        context: GradingContext,
        student_name: str,
    ) -> str:
        """
        Run the grading prompt using context.ai_understanding as grading criteria.
        Returns markdown output with special markup for corrections.
        The markdown will be converted to HTML/PDF/Word by the frontend or export service.
        """
        final_instruction = (
            context.ai_understanding or ""
        ).strip() or "Grade the assignment with constructive feedback."
        output_reqs = (context.output_requirements or "").strip() or ""
        homework = (assignment.extracted_text or "").strip() or "(No content)"
        student_name_display = (student_name or "").strip()
        assignment_title = (context.title or "").strip() or "(No title provided)"

        # Escape braces in output_reqs so they survive .format() call
        # ({{ in format string becomes { in output, so we need to double them)
        output_reqs_escaped = output_reqs.replace("{", "{{").replace("}", "}}")

        prompt = GRADING_PROMPT.format(
            assignment_title=assignment_title,
            student_name=student_name_display or "(no name provided)",
            final_grading_instruction=final_instruction,
            output_requirements=output_reqs_escaped,
            student_homework=homework,
        )
        response = await self._call_ai(
            prompt=prompt,
            system_prompt="You are an expert English teacher. Output only the markdown format specified. Do not include JSON or code fences.",
        )
        if not response:
            raise ValueError("Grading prompt returned empty response")

        markdown = response.strip()

        # Remove markdown code fences if present
        if markdown.startswith("```"):
            first = markdown.find("\n")
            if first != -1:
                markdown = markdown[first + 1 :]
            if markdown.endswith("```"):
                markdown = markdown[:-3].strip()

        return markdown


def get_ai_grading_service(
    db: Session,
    ai_model_override: Optional[str] = None,
    ai_provider_override: Optional[str] = None,
) -> AIGradingService:
    """Get an AI grading service instance.

    Args:
        db: Database session
        ai_model_override: Optional AI model to use instead of the one from settings (useful for preview grading)
        ai_provider_override: Optional AI provider to use instead of the one from settings
    """
    return AIGradingService(
        db,
        ai_model_override=ai_model_override,
        ai_provider_override=ai_provider_override,
    )
