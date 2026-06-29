"""SerpAPI provider (paid, 100 searches/month free)."""

from backend.services.search.base import SearchProvider, SearchResult
from backend.config import settings
from backend.utils.logger import search_logger


class SerpAPISearch(SearchProvider):
    """SerpAPI Google Search provider."""

    name = "serpapi"

    async def search(self, query: str, num: int = 10) -> list[SearchResult]:
        """Search via SerpAPI."""
        import httpx

        url = "https://serpapi.com/search"

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(url, params={
                    "q": query,
                    "api_key": settings.SERPAPI_API_KEY,
                    "num": min(num, 20),
                    "hl": "zh-CN",
                    "gl": "cn",
                    "engine": "google",
                })
                resp.raise_for_status()
                data = resp.json()

                results = []
                for item in data.get("organic_results", []):
                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                    ))
                return results
            except Exception as e:
                search_logger.error(f"SerpAPI error: {e}")
                return []

    async def is_available(self) -> bool:
        """SerpAPI is only available if an API key is configured."""
        return bool(settings.SERPAPI_API_KEY)
