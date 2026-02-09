"""
Database-backed settings and default values.

All feature config (AI, search, OCR, greeting, cache) is stored in the Settings
table. Default values are defined in the ensure_* functions below and used when
no record exists.

Default value locations in code:
- AI config (type=ai-config): ensure_settings_config() in this file
- Search (type=search): ensure_search_engine_config(), engine, max_results, cache_days
- OCR (type=ocr): ensure_ocr_config(), engine, languages, gpu
- Greeting (type=greeting): ensure_greeting_config(), lookback_days, no_repeat_hours
- Cache (type=cache): ensure_cache_config(), cache_days, max_articles
- Database path: config.yaml 'database.path' or app.core.config.DatabaseConfig.path
  (default 'data/teaching.db'); used by get_database_path() in config.py.
"""

from sqlalchemy.orm import Session

from app.models import Settings


def ensure_settings_config(db: Session) -> Settings:
    """Ensure AI settings exist (type=ai-config). Defaults: provider=openai, model=gpt-4o, etc."""
    config = db.query(Settings).filter(Settings.type == "ai-config").first()
    if not config:
        config = Settings(
            type="ai-config",
            config={
                "provider": "openai",
                "baseUrl": "https://api.openai.com/v1",
                "model": "gpt-4o",
                "max_token": 4096,
                "temperature": 0.3,
                "timeout": 60,
                "max_retries": 3,
            },
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def ensure_search_engine_config(db: Session) -> Settings:
    """Ensure search config exists (type=search). Defaults: engine=duckduckgo, max_results=10, cache_days=7."""
    config = db.query(Settings).filter(Settings.type == "search").first()
    if not config:
        config = Settings(
            type="search",
            config={
                "engine": "duckduckgo",
                "max_results": 10,
                "cache_days": 7,
            },
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def ensure_ocr_config(db: Session) -> Settings:
    """Ensure OCR config exists (type=ocr). Defaults: engine=easyocr, languages=[en, ch_sim], gpu=false."""
    config = db.query(Settings).filter(Settings.type == "ocr").first()
    if not config:
        config = Settings(
            type="ocr",
            config={
                "engine": "easyocr",
                "languages": ["en", "ch_sim"],
                "gpu": False,
            },
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def ensure_greeting_config(db: Session) -> Settings:
    """Ensure greeting config exists (type=greeting). Defaults: lookback_days=30, no_repeat_hours=24."""
    config = db.query(Settings).filter(Settings.type == "greeting").first()
    if not config:
        config = Settings(
            type="greeting",
            config={
                "lookback_days": 30,
                "no_repeat_hours": 24,
            },
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def ensure_cache_config(db: Session) -> Settings:
    """Ensure article cache config exists (type=cache). Defaults: cache_days=30, max_articles=1000."""
    config = db.query(Settings).filter(Settings.type == "cache").first()
    if not config:
        config = Settings(
            type="cache",
            config={
                "cache_days": 30,
                "max_articles": 1000,
            },
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config
