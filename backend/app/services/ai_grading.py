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
from app.services.ai_providers import get_llm_provider
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

    def __init__(self, db: Session):
        self.db = db

    async def _call_ai(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """
        Call the AI model using the user-defined provider and model from settings.
        All modules use the common LLM provider interface; provider/model args are ignored.
        """
        llm = get_llm_provider(self.db)
        config = get_resolved_ai_config(self.db)
        timeout = config.get("timeout", 300)
        timeout = max(300, int(timeout)) if timeout is not None else 300
        logger.info("Calling AI: provider=%s, model=%s", config.get("provider"), config.get("model"))
        return await llm.complete(
            prompt,
            system_prompt=system_prompt,
            timeout=timeout,
        )

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
        background = context.get("background", "") or ""
        instructions = context.get("instructions", "") or ""
        understanding = context.get("understanding", "")
        if isinstance(understanding, dict):
            understanding = json.dumps(understanding, indent=2)
        student_name = (context.get("student_name") or "").strip()
        if not student_name and getattr(assignment, "student_name", None):
            student_name = (assignment.student_name or "").strip()
        if not student_name and getattr(assignment, "student", None) and assignment.student:
            student_name = (assignment.student.name or "").strip()
        if not student_name:
            student_name = "Student"

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

    @staticmethod
    def _understanding_to_lines(understanding: Union[str, dict, None]) -> Optional[str]:
        """Format understanding as line-by-line text."""
        if understanding is None:
            return None
        if isinstance(understanding, str):
            return understanding.strip() or None
        if isinstance(understanding, dict):
            lines = []
            for k, v in understanding.items():
                if isinstance(v, (list, dict)):
                    lines.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
                else:
                    lines.append(f"{k}: {v}")
            return "\n".join(lines) if lines else None
        return str(understanding)

    async def grade_with_context(
        self,
        assignment: Assignment,
        context: GradingContext,
        question_types: Optional[List[QuestionType]] = None,
    ) -> GradingResult:
        """
        Grade using an existing GradingContext (title, background, instructions).
        Updates context with ai_understanding (line-by-line) and returns result.
        """
        if question_types is None:
            question_types = [QuestionType.ESSAY]

        # Stage 1: Build context dict (references + understanding)
        context_dict = await self.build_grading_context(
            background=context.background or "",
            instructions=context.instructions or "",
            db=self.db,
        )
        # Persist to ORM context
        context.extracted_references = context_dict.get("references")
        context.search_results = None
        context.cached_article_ids = context_dict.get("cached_article_ids")
        context.ai_understanding = self._understanding_to_lines(context_dict.get("understanding"))
        self.db.commit()

        # Pass background, instructions, student_name for grading prompt
        context_dict["background"] = context.background or ""
        context_dict["instructions"] = context.instructions or ""
        student_name = (assignment.student_name or "").strip() if getattr(assignment, "student_name", None) else ""
        if not student_name and getattr(assignment, "student", None) and assignment.student:
            student_name = (assignment.student.name or "").strip()
        context_dict["student_name"] = student_name

        # Stage 2: Grade
        return await self.grade_assignment(assignment, context_dict, question_types)

    async def grade(
        self,
        assignment: Assignment,
        question_types: Optional[List[QuestionType]] = None,
    ) -> GradingResult:
        """
        Legacy: full pipeline with background/instructions from assignment.
        Prefer grade_with_context when using GradingContext ORM.
        """
        if question_types is None:
            question_types = [QuestionType.ESSAY]
        background = getattr(assignment, "background", None) or ""
        instructions = getattr(assignment, "instructions", None) or ""
        context_dict = await self.understand_context(background=background, instructions=instructions, db=self.db)
        context_dict["background"] = background
        context_dict["instructions"] = instructions
        context_dict["student_name"] = (getattr(assignment, "student_name", None) or "").strip() or (
            (assignment.student.name if getattr(assignment, "student", None) and assignment.student else "Student")
        )
        return await self.grade_assignment(assignment, context_dict, question_types)


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
            logger.warning("Context prompt JSON parse failed, using raw as instruction: %s", e)
            data = {
                "extracted_references": {"books": [], "articles": [], "authors": []},
                "final_grading_instruction": text[:8000],
            }
        refs = data.get("extracted_references") or {}
        if not isinstance(refs, dict):
            refs = {"books": [], "articles": [], "authors": []}
        final_instruction = (data.get("final_grading_instruction") or "").strip() or "Grade the assignment fairly with constructive feedback."
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
        self.db.commit()
        return {"extracted_references": refs, "final_grading_instruction": final_instruction}

    async def run_grading_prompt_phase(
        self,
        assignment: Assignment,
        context: GradingContext,
        student_name: str,
    ) -> str:
        """
        Run the grading prompt using context.ai_understanding as final instruction and assignment.extracted_text.
        Returns HTML grading result.
        """
        final_instruction = (context.ai_understanding or "").strip() or "Grade the assignment with constructive feedback. Output HTML with <del> for errors and <span class=\"correction\"> for corrections."
        homework = (assignment.extracted_text or "").strip() or "(No content)"
        student_name_display = (student_name or "").strip()
        if student_name_display:
            salutation_rule = "In the Teacher's Comments section, address the student with 'Dear " + student_name_display + ",' (use this exact salutation)."
        else:
            salutation_rule = "In the Teacher's Comments section, use 'Dear,' only (no name after it). Do not use 'Dear Student' or any other default name."
        prompt = GRADING_PROMPT.format(
            student_name=student_name_display or "(no name provided)",
            student_salutation_rule=salutation_rule,
            final_grading_instruction=final_instruction,
            student_homework=homework,
        )
        response = await self._call_ai(
            prompt=prompt,
            system_prompt="You are an expert English teacher. Output only the required HTML fragment.",
        )
        if not response:
            raise ValueError("Grading prompt returned empty response")
        html = response.strip()
        if html.startswith("```"):
            first = html.find("\n")
            if first != -1:
                html = html[first + 1 :]
            if html.endswith("```"):
                html = html[:-3].strip()
        return html


def get_ai_grading_service(db: Session) -> AIGradingService:
    """Get an AI grading service instance."""
    return AIGradingService(db)
