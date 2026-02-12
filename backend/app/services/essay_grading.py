"""
Essay grading service with multi-provider support.
Replaces the old ai_grading.py with HTML-based grading.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from types import SimpleNamespace

from app.core.config import get_storage_path
from app.core.logging import get_logger
from app.models import (
    GradingTemplate,
    DEFAULT_TEACHER_ID,
)
from app.services.ai_providers import get_llm_provider
from app.services.essay_prompts import build_essay_prompt
from app.services.file_handler import read_essay
from app.services.html_generator import HTMLGenerator, parse_ai_response
from app.services.template_loader import TemplateLoader

logger = get_logger()


class EssayGradingService:
    """
    Essay grading service with multi-provider support.

    Supports:
    - Multiple AI providers (ZhipuAI, Gemini, etc.)
    - HTML output with red-ink annotations
    - Template-based grading instructions
    - File upload (txt, docx, pdf)
    - Grading history
    """

    def __init__(self, db: Session):
        """
        Initialize the grading service.

        Args:
            db: Database session
        """
        self.db = db
        self.html_generator = HTMLGenerator()
        self.template_loader = TemplateLoader()

    async def grade_essay(
        self,
        teacher_id: int = DEFAULT_TEACHER_ID,
        student_name: str = "Student",
        student_level: str = "Grade 4",
        recent_activity: str = "",
        essay_text: Optional[str] = None,
        file_path: Optional[str] = None,
        template_id: str = "persuasive_essay_grade4.html",
        additional_instructions: Optional[str] = None,
    ):
        """
        Grade a student essay.
        Returns a result object (id, html_result, student_name, student_level, created_at).
        Result is not persisted; use assignment grading + ai_grading for persistent history.
        """
        # 1. Get template content
        requirements = self._get_requirements(template_id, additional_instructions)

        # 2. Read essay (from text or file)
        essay = essay_text or read_essay(file_path or "")

        if not essay:
            raise ValueError("No essay content provided")

        # 3. Build prompt and call generic LLM provider (same config as other AI flows)
        prompt = build_essay_prompt(
            essay=essay,
            requirements=requirements,
            student_name=student_name,
            student_level=student_level,
            recent_activity=recent_activity,
        )
        llm = get_llm_provider(self.db)
        logger.info("Grading essay for %s using configured AI provider", student_name)
        result = await llm.complete(prompt)

        # 4. Parse and generate HTML
        essay_html, corrections_html, comments_html = parse_ai_response(result)

        # 7. Generate complete HTML file
        html_path = self._get_html_path(student_name)
        self.html_generator.generate(
            essay_html,
            corrections_html,
            comments_html,
            html_path,
            student_name,
        )

        # 8. Read HTML result
        with open(html_path, 'r', encoding='utf-8') as f:
            html_result = f.read()

        # 9. Save to database
        # Result not persisted (grading_history removed). Return in-memory result.
        import uuid
        grading_record = SimpleNamespace(
            id=str(uuid.uuid4()),
            html_result=html_result,
            student_name=student_name,
            student_level=student_level,
            created_at=datetime.utcnow(),
        )
        logger.info(f"Essay grading completed: {grading_record.id}")
        return grading_record

    def _get_requirements(self, template_id: str, additional: Optional[str]) -> str:
        """
        Build full requirements from template + additional instructions.

        Args:
            template_id: Template ID (integer ID or string identifier)
            additional: Additional instructions

        Returns:
            Full requirements string
        """
        requirements = ""

        # Try to load from database (by ID or name)
        try:
            # Try as integer ID first
            template_id_int = int(template_id)
            template = (
                self.db.query(GradingTemplate)
                .filter(GradingTemplate.id == template_id_int)
                .first()
            )
            if template:
                requirements = template.instructions
        except ValueError:
            # Not an integer, try as name
            template = (
                self.db.query(GradingTemplate)
                .filter(GradingTemplate.name == template_id)
                .first()
            )
            if template:
                requirements = template.instructions

        # If not found in database, try file-based template
        if not requirements:
            try:
                # Try loading from instructions/ folder
                requirements = self.template_loader.load_template(template_id)
            except Exception:
                # Use default template
                logger.warning(f"Template {template_id} not found, using default")
                requirements = self._get_default_requirements()

        if additional:
            requirements += f"\n\n## Additional Instructions\n{additional}"

        return requirements

    def _get_default_requirements(self) -> str:
        """Get default grading requirements."""
        return """
## Grading Focus Areas

### 1. Essay Structure (Highest Priority)
- **5-Paragraph Structure:**
  - Introduction with clear thesis/opinion
  - Body Paragraph 1: First argument with examples
  - Body Paragraph 2: Second argument with examples
  - Body Paragraph 3: Third argument with examples
  - Conclusion restating main points
- Clear topic sentences that stay focused
- Proper paragraph organization

### 2. Content & Logic
- Clear argument or opinion stated
- Logical explanations supporting the argument
- Relevant examples provided
- Cause and effect relationships
- Ideas stay focused on the topic

### 3. Grammar & Mechanics
- Basic spelling accuracy
- Simple sentences mastered
- Compound sentences developing
- Basic time tenses (present, past, future)
- Introduction to complex sentences

### 4. Word Choice
- Avoid repetition of vocabulary
- Choose specific, precise words
- Appropriate word level for grade
- Use transition words for flow

---

## Student Level Considerations

**Vocabulary Source:** Grade-appropriate vocabulary

**Grammar Scope:**
- Covered: Simple sentences, Compound sentences, Basic time tenses
- Not Fully Covered: Perfect tense
"""

    def _get_html_path(self, student_name: str) -> str:
        """
        Generate path for HTML output.

        Args:
            student_name: Student name

        Returns:
            Path to HTML file
        """
        output_dir = get_storage_path("graded")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = student_name.replace(" ", "_").replace("/", "_")
        filename = f"{safe_name}_{timestamp}_graded.html"
        return str(output_dir / filename)

    def get_grading_history(self, teacher_id: int = DEFAULT_TEACHER_ID, limit: int = 50, offset: int = 0):
        """Grading history is now from ai_grading/assignments; returns empty list."""
        return []

    def get_grading_result(self, grading_id: str):
        """Grading results are now under assignments; returns None."""
        return None
