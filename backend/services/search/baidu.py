"""Baidu search provider — targets Chinese web content."""

from backend.services.search.base import SearchProvider, SearchResult
from backend.utils.logger import search_logger


class BaiduSearch(SearchProvider):
    """Baidu web search via public interface."""

    name = "baidu"

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

                for item in soup.select(".result, .c-container"):
                    title_el = item.select_one("h3 a, .t a")
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    href = title_el.get("href", "")
                    snippet_el = item.select_one(".c-abstract, .content-right_8Zs40, .c-span-last")
                    snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                    if href and title:
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
