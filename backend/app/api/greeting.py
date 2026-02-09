"""
Greeting API routes.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.schemas import GreetingResponse, GreetingSource
from app.services import get_greeting_service

logger = get_logger()

router = APIRouter(prefix="/greeting", tags=["Greeting"])


@router.get("", response_model=GreetingResponse)
async def get_greeting(db: Session = Depends(get_db)):
    """
    Get a personalized greeting for the teacher.

    Generates a fresh greeting each time, using quotes from
    articles referenced in recent grading sessions.
    """
    greeting_service = get_greeting_service(db)

    greeting_text, source_info = await greeting_service.generate_greeting()

    source = None
    if source_info:
        source = GreetingSource(
            title=source_info.get("title", ""),
            author=source_info.get("author"),
        )

    return GreetingResponse(
        greeting=greeting_text,
        source=source,
    )
