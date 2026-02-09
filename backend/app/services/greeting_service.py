"""
Greeting service for generating personalized greetings.
"""

import json
import random
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.settings_db import ensure_greeting_config
from app.core.security import decrypt_api_key
from app.models import (
    CachedArticle,
    GradingContext,
    GreetingHistory,
    Settings,
)

logger = get_logger()


# Fallback greetings when no articles are available
FALLBACK_GREETINGS = [
    ("Good morning, Teacher! Ready to inspire young minds today?", None),
    ("Welcome back! Every correction is a step towards excellence.", None),
    ("Hello, Teacher! Your dedication shapes the future.", None),
    ("Greetings! Remember, great teachers make learning an adventure.", None),
    ("Welcome! As they say, 'Education is the passport to the future.'", None),
]


class GreetingService:
    """
    Service for generating personalized greetings.

    Uses quotes from articles referenced in recent grading sessions
    to create fresh, relevant greetings.
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

    def _get_recent_articles(self) -> List[CachedArticle]:
        """
        Get articles from recent grading sessions.

        Returns:
            List of cached articles from recent sessions.
        """
        rec = ensure_greeting_config(self.db)
        lookback_days = (rec.config or {}).get("lookback_days", 30)
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

        # Get grading contexts from recent period
        recent_contexts = (
            self.db.query(GradingContext)
            .filter(GradingContext.created_at >= cutoff_date)
            .order_by(GradingContext.created_at.desc())
            .limit(20)
            .all()
        )

        # Collect article IDs
        article_ids = []
        for ctx in recent_contexts:
            if ctx.cached_article_ids:
                article_ids.extend(ctx.cached_article_ids)

        if not article_ids:
            return []

        # Get unique articles
        articles = (
            self.db.query(CachedArticle)
            .filter(CachedArticle.id.in_(list(set(article_ids))))
            .all()
        )

        return articles

    def _get_recent_greetings(self) -> List[str]:
        """
        Get recent greetings to avoid repetition.

        Returns:
            List of recent greeting texts.
        """
        rec = ensure_greeting_config(self.db)
        no_repeat_hours = (rec.config or {}).get("no_repeat_hours", 24)
        cutoff_time = datetime.utcnow() - timedelta(hours=no_repeat_hours)

        recent = (
            self.db.query(GreetingHistory)
            .filter(GreetingHistory.generated_at >= cutoff_time)
            .all()
        )

        return [g.greeting_text for g in recent]

    def _select_quote(
        self,
        articles: List[CachedArticle],
        used_greetings: List[str],
    ) -> Optional[Tuple[str, CachedArticle]]:
        """
        Select a quote from available articles.

        Args:
            articles: Available cached articles.
            used_greetings: Recently used greetings to avoid.

        Returns:
            Tuple of (quote, article) or None.
        """
        # Shuffle articles for variety
        shuffled = articles.copy()
        random.shuffle(shuffled)

        for article in shuffled:
            if not article.notable_quotes:
                continue

            try:
                quotes = json.loads(article.notable_quotes)
            except (json.JSONDecodeError, TypeError):
                continue

            if not quotes:
                continue

            # Shuffle quotes
            random.shuffle(quotes)

            for quote in quotes:
                # Check if quote was recently used
                if not any(quote in greeting for greeting in used_greetings):
                    return (quote, article)

        return None

    async def _generate_greeting_with_ai(
        self,
        quote: str,
        article: CachedArticle,
    ) -> str:
        """
        Use AI to generate a creative greeting incorporating the quote.

        Args:
            quote: The quote to incorporate.
            article: Source article.

        Returns:
            Generated greeting.
        """
        try:
            ai_config = (
                self.db.query(Settings).filter(Settings.type == "ai-config").first()
            )

            if not ai_config or not ai_config.config:
                # Fallback to template-based greeting
                return self._template_greeting(quote, article)

            config_data = ai_config.config or {}
            if not config_data.get("api_key"):
                return self._template_greeting(quote, article)

            litellm = self._get_litellm()
            api_key = (
                decrypt_api_key(config_data["api_key"])
                if config_data.get("api_key")
                else None
            )
            if api_key:
                litellm.openai_key = api_key

            prompt = f"""
Create a brief, warm greeting for a teacher starting their day grading assignments.
Incorporate this quote from "{article.title}" by {article.author or 'Unknown'}:

"{quote}"

The greeting should:
1. Be warm and encouraging
2. Naturally reference the quote or its meaning
3. Be concise (1-2 sentences)
4. Feel fresh and inspiring

Just provide the greeting, nothing else.
"""

            response = await litellm.acompletion(
                model=config_data.get("model") or "gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                timeout=30,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"AI greeting generation error: {str(e)}")
            return self._template_greeting(quote, article)

    def _template_greeting(self, quote: str, article: CachedArticle) -> str:
        """
        Generate a template-based greeting.

        Args:
            quote: The quote to use.
            article: Source article.

        Returns:
            Template greeting.
        """
        templates = [
            f'Good morning! As "{article.title}" reminds us: "{quote[:100]}..."',
            f'Welcome back, Teacher! Here\'s some wisdom from {article.author or "a great work"}: "{quote[:100]}..."',
            f'Ready for another day? Remember from "{article.title}": "{quote[:100]}..."',
            f'Greetings! {article.author or "A wise author"} once wrote: "{quote[:100]}..."',
        ]

        return random.choice(templates)

    async def generate_greeting(self) -> Tuple[str, Optional[dict]]:
        """
        Generate a personalized greeting.

        Returns:
            Tuple of (greeting text, source info or None).
        """
        # Get recent articles
        articles = self._get_recent_articles()
        used_greetings = self._get_recent_greetings()

        if not articles:
            # Use fallback greeting
            greeting, source = random.choice(FALLBACK_GREETINGS)
            return greeting, source

        # Try to find an unused quote
        quote_result = self._select_quote(articles, used_greetings)

        if quote_result is None:
            # All quotes used, pick random fallback
            greeting, source = random.choice(FALLBACK_GREETINGS)
            return greeting, source

        quote, article = quote_result

        # Generate greeting
        greeting = await self._generate_greeting_with_ai(quote, article)

        # Save to history
        history = GreetingHistory(
            greeting_text=greeting,
            source_article_id=article.id,
            source_title=article.title,
            source_author=article.author,
            source_quote=quote,
        )
        self.db.add(history)
        self.db.commit()

        source = {
            "title": article.title,
            "author": article.author,
        }

        logger.info(f"Generated greeting from article: {article.title}")

        return greeting, source


def get_greeting_service(db: Session) -> GreetingService:
    """Get a greeting service instance."""
    return GreetingService(db)
