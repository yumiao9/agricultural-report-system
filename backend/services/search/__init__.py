"""Search provider abstractions and manager."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from backend.utils.logger import search_logger


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class SearchProvider(ABC):
    """Abstract base class for search providers."""

    name: str = "base"

    @abstractmethod
    async def search(self, query: str, num: int = 10) -> list[SearchResult]:
        """Execute a search and return results."""
        ...

    async def is_available(self) -> bool:
        """Check if this provider is available."""
        return True


class SearchManager:
    """Manages multiple search providers with fallback."""

    def __init__(self, providers: list[SearchProvider]):
        self.providers = providers

    async def search(
        self, query: str, num: int = 10, timeout: float = 30.0
    ) -> list[SearchResult]:
        """Search using providers in priority order, falling back on failure."""
        import asyncio

        for provider in self.providers:
            if not await provider.is_available():
                search_logger.info(f"Provider {provider.name} not available, skipping")
                continue

            try:
                search_logger.info(f"Searching via {provider.name}: {query[:80]}")
                results = await asyncio.wait_for(
                    provider.search(query, num=num), timeout=timeout
                )
                if results:
                    search_logger.info(f"{provider.name} returned {len(results)} results")
                    return results
                search_logger.warning(f"{provider.name} returned 0 results")
            except asyncio.TimeoutError:
                search_logger.warning(f"{provider.name} timed out")
            except Exception as e:
                search_logger.error(f"{provider.name} error: {e}")

        # All providers failed
        search_logger.error("All search providers failed")
        return []

    async def multisearch(
        self, queries: list[str], num: int = 5, timeout: float = 30.0
    ) -> list[SearchResult]:
        """Search multiple queries in parallel, deduplicate by URL."""
        import asyncio

        async def search_one(q: str) -> list[SearchResult]:
            return await self.search(q, num=num, timeout=timeout)

        all_results = await asyncio.gather(*[search_one(q) for q in queries])

        # Deduplicate by URL, preferring Chinese official sources
        seen_urls = set()
        deduped = []
        priority_domains = [
            "moa.gov.cn", "stats.gov.cn", "baike.baidu.com",
            "gov.cn", "agri.cn", "cnagri.com", "people.com.cn",
            "xinhuanet.com", "cnki.net",
        ]

        def domain_priority(url: str) -> int:
            for i, domain in enumerate(priority_domains):
                if domain in url:
                    return i
            return len(priority_domains)  # Lowest priority

        # Collect all results
        all_items = []
        for results in all_results:
            for r in results:
                if r.url not in seen_urls:
                    seen_urls.add(r.url)
                    all_items.append(r)

        # Sort by domain priority
        all_items.sort(key=lambda r: domain_priority(r.url))

        search_logger.info(
            f"Multisearch: {len(all_results)} queries -> {len(all_items)} unique results"
        )
        return all_items
