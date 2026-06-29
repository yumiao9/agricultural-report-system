"""Chinese official data source searcher — targets gov.cn, stats.gov.cn, moa.gov.cn etc."""

from backend.services.search.base import SearchProvider, SearchResult
from backend.utils.logger import search_logger


CHINESE_AGRI_SOURCES = [
    "site:moa.gov.cn",            # 农业农村部
    "site:stats.gov.cn",          # 国家统计局
    "site:baike.baidu.com",       # 百度百科
    "site:agri.cn",               # 中国农业信息网
    "site:cnki.net",              # 中国知网
    "site:cnagri.com",           # 中国农业网
    "site:foodmate.net",          # 食品伙伴网（农业相关）
    "site:xinhuanet.com fortune",  # 新华网财经
    "site:people.com.cn",         # 人民网
    "site:gov.cn",                # 中国政府网
]


class ChineseOfficialSourceSearch(SearchProvider):
    """Searches Chinese official/government websites using DuckDuckGo site: syntax.

    This provider sends multiple site-specific queries and aggregates results.
    It is designed to find authoritative Chinese government and academic data.
    """

    name = "chinese_official"

    def __init__(self, fallback_search=None):
        """
        Args:
            fallback_search: A SearchProvider instance used to execute the actual
                            site: queries. Defaults to DuckDuckGo.
        """
        self.fallback_search = fallback_search

    async def search(self, query: str, num: int = 10) -> list[SearchResult]:
        """Search Chinese official sources.

        For each configured source domain, creates a 'site:domain query' search
        and aggregates results.
        """
        from backend.services.search.duckduckgo import DuckDuckGoSearch

        searcher = self.fallback_search or DuckDuckGoSearch()
        all_results = []
        seen_urls = set()

        # Use top sources first
        top_sources = CHINESE_AGRI_SOURCES[:4]
        for site_query in top_sources:
            full_query = f"{site_query} {query}"
            try:
                results = await searcher.search(full_query, num=3)
                for r in results:
                    if r.url not in seen_urls:
                        seen_urls.add(r.url)
                        # Tag the source type in snippet
                        tag = site_query.replace("site:", "").split(".")[0]
                        r.snippet = f"[{tag}] {r.snippet}" if r.snippet else f"[{tag}]"
                        all_results.append(r)
            except Exception as e:
                search_logger.warning(f"Chinese source search failed for {site_query}: {e}")

        # Fill remaining with broad search
        if len(all_results) < num:
            broad_query = f"农业 {query} 数据 统计 2024"
            try:
                results = await searcher.search(broad_query, num=num - len(all_results))
                for r in results:
                    if r.url not in seen_urls:
                        seen_urls.add(r.url)
                        all_results.append(r)
            except Exception as e:
                search_logger.warning(f"Broad Chinese search failed: {e}")

        search_logger.info(f"ChineseOfficialSourceSearch: {len(all_results)} results for '{query}'")
        return all_results[:num]

    async def is_available(self) -> bool:
        """Always available."""
        return True
