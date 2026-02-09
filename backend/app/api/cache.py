"""
Cache management API routes.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.logging import get_logger
from app.models import CachedArticle
from app.schemas import CachedArticleResponse, CachedArticleListResponse

logger = get_logger()

router = APIRouter(prefix="/cache", tags=["Cache"])


@router.get("/articles", response_model=CachedArticleListResponse)
async def list_cached_articles(db: Session = Depends(get_db)):
    """
    List all cached articles.
    """
    articles = (
        db.query(CachedArticle).order_by(CachedArticle.last_accessed.desc()).all()
    )

    items = [
        CachedArticleResponse(
            id=a.id,
            title=a.title,
            author=a.author,
            source_url=a.source_url,
            source_type=a.source_type,
            cached_at=a.cached_at,
            expires_at=a.expires_at,
            access_count=a.access_count,
        )
        for a in articles
    ]

    return CachedArticleListResponse(items=items, total=len(items))


@router.get("/articles/{article_id}", response_model=CachedArticleResponse)
async def get_cached_article(
    article_id: str,
    db: Session = Depends(get_db),
):
    """
    Get a specific cached article.
    """
    article = db.query(CachedArticle).filter(CachedArticle.id == article_id).first()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    return CachedArticleResponse(
        id=article.id,
        title=article.title,
        author=article.author,
        source_url=article.source_url,
        source_type=article.source_type,
        cached_at=article.cached_at,
        expires_at=article.expires_at,
        access_count=article.access_count,
    )


@router.delete("/articles/{article_id}")
async def delete_cached_article(
    article_id: str,
    db: Session = Depends(get_db),
):
    """
    Delete a cached article.
    """
    article = db.query(CachedArticle).filter(CachedArticle.id == article_id).first()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    db.delete(article)
    db.commit()

    logger.info(f"Deleted cached article: {article_id}")

    return {"message": "Article deleted"}


@router.delete("/articles")
async def clear_cache(db: Session = Depends(get_db)):
    """
    Clear all cached articles.
    """
    count = db.query(CachedArticle).delete()
    db.commit()

    logger.info(f"Cleared {count} cached articles")

    return {"message": f"Cleared {count} cached articles"}
