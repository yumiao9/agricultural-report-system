"""Baidu search provider — targets Chinese web content."""

import re

from backend.services.search.base import SearchProvider, SearchResult
from backend.utils.logger import search_logger


class BaiduSearch(SearchProvider):
    """Baidu web search via public interface."""

    name = "baidu"

    async def _resolve_url(self, client, baidu_url: str) -> str:
        """Resolve a Baidu redirect URL to the actual destination."""
        if "baidu.com/link" not in baidu_url and "baidu.com/s" not in baidu_url:
            return baidu_url
        try:
            resp = await client.head(baidu_url, follow_redirects=True, timeout=5.0)
            if resp.url:
                final = str(resp.url)
                if "baidu.com" not in final:
                    return final
        except Exception:
            pass
        return baidu_url

    async def search(self, query: str, num: int = 10) -> list[SearchResult]:
        """Search Baidu for the given query."""
        import httpx
        from bs4 import BeautifulSoup

        url = "https://www.baidu.com/s"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                search_logger.info(f"Baidu search: {query[:80]}")
                resp = await client.get(url, params={"wd": query, "rn": min(num, 50)}, headers=headers)
                resp.raise_for_status()

                soup = BeautifulSoup(resp.text, "lxml")
                results = []

                for item in soup.select(".result, .c-container, .c-result"):
                    title_el = item.select_one("h3 a, .t a")
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    href = title_el.get("href", "")
                    if not href or not title:
                        continue

                    snippet_el = item.select_one(".c-abstract, .content-right_8Zs40, .c-span-last, .c-color-gray")
                    snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                    # Use URL directly, fetcher will follow redirects
                    results.append(SearchResult(
                        title=title,
                        url=href,
                        snippet=snippet,
                    ))

                search_logger.info(f"Baidu returned {len(results)} results")
                return results

            except Exception as e:
                search_logger.error(f"Baidu search error: {e}")
                return []

    async def is_available(self) -> bool:
        """Baidu is always available (no API key needed)."""
        return True
