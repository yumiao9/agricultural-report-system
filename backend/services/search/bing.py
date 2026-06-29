"""Bing Search API provider (free tier: 1000 queries/month via Azure)."""

from backend.services.search.base import SearchProvider, SearchResult
from backend.config import settings
from backend.utils.logger import search_logger


class BingSearch(SearchProvider):
    """Bing Web Search API provider."""

    name = "bing"

    async def search(self, query: str, num: int = 10) -> list[SearchResult]:
        """Search Bing for the given query."""
        import httpx

        # Bing Web Search API v7 endpoint
        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": settings.BING_API_KEY or ""}

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(
                    url,
                    headers=headers,
                    params={"q": query, "count": min(num, 50), "mkt": "zh-CN"},
                )
                resp.raise_for_status()
                data = resp.json()

                results = []
                for item in data.get("webPages", {}).get("value", []):
                    results.append(SearchResult(
                        title=item.get("name", ""),
                        url=item.get("url", ""),
                        snippet=item.get("snippet", ""),
                    ))
                return results
            except Exception as e:
                search_logger.error(f"Bing search error: {e}")
                return []

    async def is_available(self) -> bool:
        """Bing is only available if an API key is configured."""
        return bool(settings.BING_API_KEY)
