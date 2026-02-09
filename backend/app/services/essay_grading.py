"""
Essay grading service with multi-provider support.
Replaces the old ai_grading.py with HTML-based grading.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.security import encrypt_api_key, decrypt_api_key
from app.models import (
    GradingHistory,
    GradingTemplate,
    AIProviderConfig,
    Teacher,
    DEFAULT_TEACHER_ID,
)
from app.services.ai_providers.factory import get_provider
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
    ) -> GradingHistory:
        """
        Grade a student essay.

        Args:
            teacher_id: Teacher ID
            student_name: Student name
            student_level: Student grade level
            recent_activity: Recent activity context
            essay_text: Essay text (if pasting)
            file_path: Path to uploaded file (if uploading)
            template_id: Template ID to use
            additional_instructions: Additional grading instructions

        Returns:
            GradingHistory record with HTML result
        """
        # 1. Get AI provider config for teacher
        ai_config = self._get_ai_config(teacher_id)

        # 2. Get template content
        requirements = self._get_requirements(template_id, additional_instructions)

        # 3. Read essay (from text or file)
        essay = essay_text or read_essay(file_path or "")

        if not essay:
            raise ValueError("No essay content provided")

        # 4. Get provider and grade
        provider = get_provider(
            ai_config.provider,
            decrypt_api_key(ai_config.api_key_encrypted),
            ai_config.model,
        )

        logger.info(f"Grading essay for {student_name} using {ai_config.provider}")

        # 5. Call AI with context
        result = await provider.grade_essay(
            essay=essay,
            requirements=requirements,
            student_name=student_name,
            student_level=student_level,
            recent_activity=recent_activity,
        )

        # 6. Parse and generate HTML
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
        grading_record = GradingHistory(
            teacher_id=teacher_id,
            student_name=student_name,
            student_level=student_level,
            recent_activity=recent_activity,
            template_id=template_id,
            additional_instructions=additional_instructions,
            essay_text=essay,
            html_result=html_result,
            file_path=file_path,
        )
        self.db.add(grading_record)
        self.db.commit()
        self.db.refresh(grading_record)

        logger.info(f"Grading completed: {grading_record.id}")
        return grading_record

    def _get_ai_config(self, teacher_id: int) -> AIProviderConfig:
        """
        Get teacher's AI config (default provider).

        Args:
            teacher_id: Teacher ID

        Returns:
            AIProviderConfig

        Raises:
            ValueError: If no AI config found
        """
        config = (
            self.db.query(AIProviderConfig)
            .filter(
                AIProviderConfig.teacher_id == teacher_id,
                AIProviderConfig.is_default == True,
            )
            .first()
        )

        if not config:
            # Try to get any config for this teacher
            config = (
                self.db.query(AIProviderConfig)
                .filter(AIProviderConfig.teacher_id == teacher_id)
                .first()
            )

        if not config:
            raise ValueError(
                f"No AI configuration found for teacher {teacher_id}. "
                "Please configure an AI provider first."
            )

        return config

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
        output_dir = Path("data/graded")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = student_name.replace(" ", "_").replace("/", "_")
        filename = f"{safe_name}_{timestamp}_graded.html"

        return str(output_dir / filename)

    def get_grading_history(
        self,
        teacher_id: int = DEFAULT_TEACHER_ID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[GradingHistory]:
        """
        Get grading history for a teacher.

        Args:
            teacher_id: Teacher ID
            limit: Maximum number of records
            offset: Offset for pagination

        Returns:
            List of GradingHistory records
        """
        return (
            self.db.query(GradingHistory)
            .filter(GradingHistory.teacher_id == teacher_id)
            .order_by(GradingHistory.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def get_grading_result(self, grading_id: str) -> Optional[GradingHistory]:
        """
        Get a specific grading result.

        Args:
            grading_id: Grading record ID

        Returns:
            GradingHistory record or None
        """
        return (
            self.db.query(GradingHistory)
            .filter(GradingHistory.id == grading_id)
            .first()
        )
