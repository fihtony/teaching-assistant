"""
Web search service for fetching article content.
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import re

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.core.config import get_config
from app.core.logging import get_logger
from app.models import CachedArticle

logger = get_logger()


class SearchResult:
    """Represents a single search result."""

    def __init__(
        self,
        title: str,
        url: str,
        snippet: str,
        source_type: str = "web",
    ):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.source_type = source_type


class SearchService:
    """
    Service for web searching and article fetching.

    Supports multiple search engines (DuckDuckGo, Google).
    Implements caching to avoid repeated searches.
    """

    # Known article sources for classic literature
    GUTENBERG_BASE = "https://www.gutenberg.org"
    KNOWN_CLASSICS = {
        "alice's adventures in wonderland": "https://www.gutenberg.org/files/11/11-h/11-h.htm",
        "alice in wonderland": "https://www.gutenberg.org/files/11/11-h/11-h.htm",
        "pride and prejudice": "https://www.gutenberg.org/files/1342/1342-h/1342-h.htm",
        "the great gatsby": None,  # Not in public domain
        "romeo and juliet": "https://www.gutenberg.org/files/1112/1112-h/1112-h.htm",
        "hamlet": "https://www.gutenberg.org/files/1524/1524-h/1524-h.htm",
        "a tale of two cities": "https://www.gutenberg.org/files/98/98-h/98-h.htm",
        "the adventures of sherlock holmes": "https://www.gutenberg.org/files/1661/1661-h/1661-h.htm",
    }

    def __init__(self, db: Session):
        self.db = db
        self.config = get_config()

    def search(
        self,
        query: str,
        max_results: int = 10,
    ) -> List[SearchResult]:
        """
        Search for articles using the configured search engine.

        Args:
            query: Search query.
            max_results: Maximum number of results.

        Returns:
            List of search results.
        """
        engine = self.config.search.engine.lower()

        if engine == "duckduckgo":
            return self._search_duckduckgo(query, max_results)
        elif engine == "google":
            return self._search_google(query, max_results)
        else:
            logger.warning(
                f"Unknown search engine: {engine}, falling back to DuckDuckGo"
            )
            return self._search_duckduckgo(query, max_results)

    def _search_duckduckgo(
        self,
        query: str,
        max_results: int,
    ) -> List[SearchResult]:
        """Search using DuckDuckGo."""
        try:
            from duckduckgo_search import DDGS

            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))

            search_results = []
            for r in results:
                search_results.append(
                    SearchResult(
                        title=r.get("title", ""),
                        url=r.get("href", r.get("link", "")),
                        snippet=r.get("body", r.get("snippet", "")),
                        source_type="duckduckgo",
                    )
                )

            logger.info(
                f"DuckDuckGo search for '{query}' returned {len(search_results)} results"
            )
            return search_results

        except Exception as e:
            logger.error(f"DuckDuckGo search error: {str(e)}")
            return []

    def _search_google(
        self,
        query: str,
        max_results: int,
    ) -> List[SearchResult]:
        """Search using Google Custom Search API."""
        # This requires API key configuration
        logger.warning("Google search not fully implemented, using DuckDuckGo")
        return self._search_duckduckgo(query, max_results)

    def extract_book_references(self, text: str) -> Dict[str, List[str]]:
        """
        Extract book and article references from teacher's background text.

        Args:
            text: Teacher's background/instructions text.

        Returns:
            Dictionary with 'books', 'articles', 'authors' lists.
        """
        references = {
            "books": [],
            "articles": [],
            "authors": [],
        }

        if not text:
            return references

        # Pattern for quoted titles
        quoted_pattern = r'["\u201c\u201d\u300a\u300b]([^"\u201c\u201d\u300a\u300b]+)["\u201c\u201d\u300a\u300b]'
        quoted_matches = re.findall(quoted_pattern, text)

        for match in quoted_matches:
            # Determine if it's likely a book or article
            if len(match) > 50:
                references["articles"].append(match)
            else:
                references["books"].append(match)

        # Check for known classics
        text_lower = text.lower()
        for classic_name in self.KNOWN_CLASSICS.keys():
            if classic_name in text_lower:
                if classic_name not in [b.lower() for b in references["books"]]:
                    references["books"].append(classic_name.title())

        # Pattern for "by [Author Name]"
        author_pattern = r"by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)"
        author_matches = re.findall(author_pattern, text)
        references["authors"].extend(author_matches)

        return references

    def get_cached_article(self, title: str) -> Optional[CachedArticle]:
        """
        Get a cached article by title.

        Args:
            title: Article title to search for.

        Returns:
            CachedArticle if found and valid, None otherwise.
        """
        title_lower = title.lower()
        article = (
            self.db.query(CachedArticle)
            .filter(CachedArticle.title.ilike(f"%{title_lower}%"))
            .first()
        )

        if article and article.is_cache_valid():
            # Update access count
            article.access_count = str(int(article.access_count) + 1)
            article.last_accessed = datetime.utcnow()
            self.db.commit()
            return article

        return None

    def fetch_article_content(
        self,
        title: str,
        url: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch article content from the web.

        Args:
            title: Article title.
            url: Optional URL to fetch from.

        Returns:
            Dictionary with 'content', 'summary', 'quotes', 'author', 'source_url'.
        """
        # Check cache first
        cached = self.get_cached_article(title)
        if cached:
            logger.info(f"Using cached article: {title}")
            return {
                "content": cached.full_content,
                "summary": cached.summary,
                "quotes": (
                    json.loads(cached.notable_quotes) if cached.notable_quotes else []
                ),
                "author": cached.author,
                "source_url": cached.source_url,
                "cached_article_id": cached.id,
            }

        # Check known classics
        title_lower = title.lower()
        for classic_name, classic_url in self.KNOWN_CLASSICS.items():
            if classic_name in title_lower and classic_url:
                url = classic_url
                break

        # If no URL, search for it
        if not url:
            results = self.search(f"{title} full text", max_results=5)
            if results:
                # Prefer Gutenberg URLs
                for r in results:
                    if "gutenberg" in r.url.lower():
                        url = r.url
                        break
                if not url:
                    url = results[0].url

        if not url:
            logger.warning(f"Could not find URL for article: {title}")
            return None

        # Fetch content
        try:
            response = requests.get(
                url,
                timeout=30,
                headers={"User-Agent": "Mozilla/5.0 (compatible; TeachingApp/1.0)"},
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text content
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            content = "\n".join(chunk for chunk in chunks if chunk)

            # Extract notable quotes (sentences with quotes)
            quotes = self._extract_notable_quotes(content)

            # Generate summary (first 500 chars)
            summary = content[:500] + "..." if len(content) > 500 else content

            # Try to find author
            author = self._extract_author(soup, content)

            # Cache the article
            self._cache_article(title, content, summary, quotes, author, url)

            return {
                "content": content,
                "summary": summary,
                "quotes": quotes,
                "author": author,
                "source_url": url,
            }

        except Exception as e:
            logger.error(f"Error fetching article '{title}': {str(e)}")
            return None

    def _extract_notable_quotes(self, content: str) -> List[str]:
        """Extract notable quotes from content."""
        quotes = []

        # Find sentences with quotation marks
        quote_pattern = r'["\u201c]([^"\u201d]{20,200})["\u201d]'
        matches = re.findall(quote_pattern, content)
        quotes.extend(matches[:10])  # Limit to 10 quotes

        return quotes

    def _extract_author(self, soup: BeautifulSoup, content: str) -> Optional[str]:
        """Extract author name from page."""
        # Check meta tags
        author_meta = soup.find("meta", {"name": "author"})
        if author_meta and author_meta.get("content"):
            return author_meta["content"]

        # Check for "by [Author]" pattern in first 500 chars
        pattern = r"by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)"
        match = re.search(pattern, content[:500])
        if match:
            return match.group(1)

        return None

    def _cache_article(
        self,
        title: str,
        content: str,
        summary: str,
        quotes: List[str],
        author: Optional[str],
        source_url: str,
    ) -> CachedArticle:
        """Cache an article in the database."""
        cache_days = self.config.article_cache.cache_days

        article = CachedArticle(
            title=title,
            author=author,
            source_url=source_url,
            source_type="gutenberg" if "gutenberg" in source_url.lower() else "web",
            full_content=content[:100000],  # Limit content size
            summary=summary,
            notable_quotes=json.dumps(quotes),
            expires_at=datetime.utcnow() + timedelta(days=cache_days),
        )

        self.db.add(article)
        self.db.commit()
        self.db.refresh(article)

        logger.info(f"Cached article: {title}")
        return article


def get_search_service(db: Session) -> SearchService:
    """Get a search service instance."""
    return SearchService(db)
