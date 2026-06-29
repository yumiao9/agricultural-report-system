"""DuckDuckGo search provider (free, no API key)."""

from duckduckgo_search import DDGS

from backend.services.search.base import SearchProvider, SearchResult
from backend.utils.logger import search_logger


class DuckDuckGoSearch(SearchProvider):
    """DuckDuckGo web search."""

    name = "duckduckgo"

    async def search(self, query: str, num: int = 10) -> list[SearchResult]:
        """Search DuckDuckGo for the given query."""
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=num))
        except Exception as e:
            search_logger.error(f"DuckDuckGo search error: {e}")
            return []

        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("href", ""),
                snippet=r.get("body", ""),
            )
            for r in results
            if r.get("href")
        ]

    async def is_available(self) -> bool:
        """DuckDuckGo is always 'available' (no API key needed)."""
        return True
