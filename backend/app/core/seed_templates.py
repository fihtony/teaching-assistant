"""
Seed grading_templates from backend/instructions/ files during DB init.
Each file is imported as a template with question_type "essay".
"""

from pathlib import Path

from app.core.logging import get_logger
from app.models import GradingTemplate, Teacher, DEFAULT_TEACHER_ID

logger = get_logger()

# backend/instructions/ relative to this file: app/core/seed_templates.py -> backend = parent.parent.parent
INSTRUCTIONS_DIR = Path(__file__).resolve().parent.parent.parent / "instructions"

FORMAT_BY_EXT = {
    ".md": "markdown",
    ".html": "html",
    ".json": "json",
}
DEFAULT_FORMAT = "text"


def _format_from_filename(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in FORMAT_BY_EXT:
        return FORMAT_BY_EXT[suffix]
    # e.g. .html.md -> treat as markdown
    if ".md" in path.suffixes:
        return "markdown"
    return DEFAULT_FORMAT


def seed_templates_from_instructions(engine):
    """
    Import all files under backend/instructions/ into grading_templates.
    Uses default teacher; only inserts if no template with same name exists.
    """
    if not INSTRUCTIONS_DIR.exists():
        logger.debug("Instructions dir not found: %s", INSTRUCTIONS_DIR)
        return

    from sqlalchemy.orm import sessionmaker
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()

    try:
        teacher = db.query(Teacher).filter(Teacher.id == DEFAULT_TEACHER_ID).first()
        if not teacher:
            teacher = Teacher(id=DEFAULT_TEACHER_ID, name="Teacher")
            db.add(teacher)
            db.commit()
            db.refresh(teacher)

        existing_names = {t.name for t in db.query(GradingTemplate).filter(GradingTemplate.teacher_id == teacher.id).all()}

        files = list(INSTRUCTIONS_DIR.iterdir())
        for path in sorted(files):
            if not path.is_file():
                continue
            name = path.stem
            if name in existing_names:
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="replace").strip()
            except Exception as e:
                logger.warning("Skip %s: %s", path.name, e)
                continue
            if not content:
                continue
            instruction_format = _format_from_filename(path)
            default_encouragement = ["Bravo!", "Excellent!", "Perfect!", "Well done!", "Outstanding!"]
            default_question_types = [
                {"type": "essay", "name": "Essay", "weight": 10, "enabled": True},
            ]
            template = GradingTemplate(
                teacher_id=teacher.id,
                name=name,
                description=f"Imported from {path.name}",
                instructions=content,
                instruction_format=instruction_format,
                encouragement_words=default_encouragement,
                question_types=default_question_types,
            )
            db.add(template)
            existing_names.add(name)
            logger.info("Seeded template from %s (format=%s)", path.name, instruction_format)
        db.commit()
    finally:
        db.close()
