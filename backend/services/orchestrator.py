"""Central research orchestrator — coordinates the full pipeline."""

import asyncio
from datetime import datetime, timezone

from backend.config import settings
from backend.models.schemas import ENTITY_LABELS
from backend.services.search.duckduckgo import DuckDuckGoSearch
from backend.services.search.bing import BingSearch
from backend.services.search.serpapi import SerpAPISearch
from backend.services.search.base import SearchManager
from backend.services.fetcher import fetch_pages
from backend.services.entity_classifier import classify_entity
from backend.services.extractor import extract_data_from_pages
from backend.services.verifier import verify_data_points
from backend.services.report_generator import generate_report_markdown
from backend.services.citation import build_citations
from backend.services.progress import ProgressEmitter
from backend.services.cache import (
    get_cached_report,
    save_report_to_cache,
    get_cached_search,
    save_search_cache,
)
from backend.utils.logger import orchestrator_logger


# ── Targeted Search Queries by Entity Type ──────────────────────

TARGETED_QUERIES = {
    "agricultural_product": [
        "{entity} 产量 种植面积 统计数据",
        "{entity} 市场价格 走势 行情",
        "{entity} 进出口 贸易 数据",
        "{entity} 主产区 产业分析 报告",
        "{entity} 政策 补贴 农业",
        "site:moa.gov.cn {entity} 产量",
        "site:stats.gov.cn {entity} 数据",
        "site:baike.baidu.com {entity}",
    ],
    "agricultural_enterprise": [
        "{entity} 企业 营收 财务 数据",
        "{entity} 市场份额 竞争 格局",
        "{entity} 发展 新闻 动态",
        "{entity} 主营业务 产品",
        "site:baike.baidu.com {entity}",
        "{entity} 财报 业绩 公告",
    ],
    "agricultural_equipment": [
        "{entity} 技术参数 价格",
        "{entity} 品牌 生产企业",
        "{entity} 补贴 购置 农机",
        "{entity} 市场 占有率 规模",
        "site:baike.baidu.com {entity}",
        "{entity} 评测 对比 推荐",
    ],
    "agricultural_region": [
        "{entity} 农业 产值 经济 数据",
        "{entity} 特色产业 种植 养殖",
        "{entity} 人口 面积 地理位置",
        "{entity} 乡村旅游 发展",
        "{entity} 乡村振兴 政策",
        "site:stats.gov.cn {entity} 数据",
        "site:moa.gov.cn {entity} 农业",
        "site:baike.baidu.com {entity}",
    ],
}


# ── Build Search Manager ─────────────────────────────────────────

def _build_search_manager() -> SearchManager:
    """Create search manager with available providers ordered by priority."""
    providers = []

    # Always include DuckDuckGo (free)
    providers.append(DuckDuckGoSearch())

    # Chinese official sources (uses DuckDuckGo internally with site: queries)
    if settings.ENABLE_CHINESE_OFFICIAL:
        from backend.services.search.chinese_sources import ChineseOfficialSourceSearch
        providers.append(ChineseOfficialSourceSearch())

    # Baidu search (no API key needed)
    if settings.ENABLE_BAIDU:
        from backend.services.search.baidu import BaiduSearch
        providers.append(BaiduSearch())

    # Add paid providers if configured
    if settings.SERPAPI_API_KEY:
        providers.append(SerpAPISearch())

    if settings.BING_API_KEY:
        providers.append(BingSearch())

    return SearchManager(providers)


# ── Main Orchestrator ────────────────────────────────────────────

class ResearchOrchestrator:
    """Coordinates the full research pipeline from query to report."""

    def __init__(self):
        self.search_manager = _build_search_manager()

    async def execute(
        self,
        query: str,
        progress: ProgressEmitter,
        force_refresh: bool = False,
    ) -> dict:
        """Execute the full research pipeline.

        Args:
            query: User's search query.
            progress: ProgressEmitter for SSE streaming.
            force_refresh: Skip cache if True.

        Returns:
            Complete report dict ready for rendering.
        """
        start_time = datetime.now(timezone.utc)

        # ── Step 0: Check Cache ──────────────────────────────────
        if not force_refresh:
            progress.emit("classifying", "正在查询缓存...", percent=3)
            cached = await get_cached_report(query)
            if cached:
                progress.complete(cached["id"], f"/report/{cached['id']}")
                orchestrator_logger.info(f"Returning cached report for: {query}")
                return cached

        # ── Step 1: Classify Entity ──────────────────────────────
        progress.emit("classifying", "正在分析查询类型...", percent=8)
        try:
            classification = await asyncio.wait_for(
                classify_entity(query), timeout=15.0
            )
        except Exception as e:
            orchestrator_logger.warning(f"Entity classification failed ({e}), defaulting to product")
            classification = {
                "entity_type": "agricultural_product",
                "entity_name": query,
                "keywords": [query],
                "search_query_zh": query,
            }

        entity_type = classification["entity_type"]
        entity_name = classification.get("entity_name", query)
        keywords = classification.get("keywords", [query])

        orchestrator_logger.info(
            f"Classified: type={entity_type}, name={entity_name}, keywords={keywords}"
        )

        # ── Step 2: Search ───────────────────────────────────────
        progress.emit("searching", "正在搜索相关信息...", percent=15)

        # Build targeted queries
        templates = TARGETED_QUERIES.get(entity_type, TARGETED_QUERIES["agricultural_product"])
        search_queries = [tpl.format(entity=entity_name) for tpl in templates]
        # Add the original search query
        search_queries.insert(0, classification.get("search_query_zh", query))

        # Check search cache first
        all_search_results = None
        if not force_refresh:
            cached_search = await get_cached_search(query)
            if cached_search:
                from backend.services.search.base import SearchResult
                all_search_results = [
                    SearchResult(**r) if isinstance(r, dict) else r
                    for r in cached_search
                ]

        if not all_search_results:
            try:
                all_search_results = await asyncio.wait_for(
                    self.search_manager.multisearch(
                        search_queries,
                        num=settings.SEARCH_MAX_RESULTS // len(search_queries) + 2,
                    ),
                    timeout=45.0,
                )
                # Cache search results
                await save_search_cache(
                    query,
                    [{"title": r.title, "url": r.url, "snippet": r.snippet}
                     for r in all_search_results],
                )
            except asyncio.TimeoutError:
                orchestrator_logger.warning("Search timed out, continuing with partial results")
                all_search_results = all_search_results or []

        if not all_search_results:
            progress.error("未找到任何相关信息，请尝试其他查询词")
            # Return a minimal error report
            return await self._generate_fallback_report(query, entity_type, entity_name, progress)

        orchestrator_logger.info(f"Search complete: {len(all_search_results)} total results")

        # ── Step 3: Fetch Pages ──────────────────────────────────
        progress.emit("fetching", f"正在获取网页内容 (共{len(all_search_results[:10])}个来源)...", percent=25)

        urls = [r.url for r in all_search_results[:10]]
        fetched_pages = await fetch_pages(urls, max_concurrent=5)

        success_count = sum(1 for p in fetched_pages if p["fetch_success"])
        if success_count == 0:
            progress.error("所有网页获取失败，请检查网络连接")
            return await self._generate_fallback_report(query, entity_type, entity_name, progress)

        progress.emit("fetching", f"网页获取完成 ({success_count}/{len(urls)} 成功)", percent=45)

        # ── Step 4: Extract Data ─────────────────────────────────
        progress.emit("extracting", "正在提取关键数据...", percent=50)

        data_points = await extract_data_from_pages(fetched_pages, entity_name)

        progress.emit("extracting", f"数据提取完成 (共{len(data_points)}项)", percent=60)

        # ── Step 5: Verify ───────────────────────────────────────
        progress.emit("verifying", "正在交叉验证数据...", percent=65)

        verified_data = await verify_data_points(data_points)

        # Calculate confidence score
        confidence_counts = {"high": 0, "medium": 0, "low": 0}
        for dp in verified_data:
            conf = dp.get("confidence", "medium")
            confidence_counts[conf] = confidence_counts.get(conf, 0) + 1

        total = len(verified_data) or 1
        confidence_score = (
            confidence_counts.get("high", 0) * 1.0 +
            confidence_counts.get("medium", 0) * 0.5
        ) / total

        progress.emit("verifying",
            f"验证完成 (高{confidence_counts.get('high',0)} 中{confidence_counts.get('medium',0)} 低{confidence_counts.get('low',0)})",
            percent=75)

        # ── Step 6: Build Citations ─────────────────────────────
        citations = build_citations(all_search_results, fetched_pages)

        # ── Step 7: Generate Report ──────────────────────────────
        progress.emit("generating", "正在生成研究报告... (预计30-60秒)", percent=80)

        try:
            markdown = await asyncio.wait_for(
                generate_report_markdown(
                    entity_name=entity_name,
                    entity_type=entity_type,
                    data_points=verified_data,
                    fetched_pages=fetched_pages,
                    citations=citations,
                ),
                timeout=120.0,
            )
        except asyncio.TimeoutError:
            progress.error("报告生成超时")
            return await self._generate_fallback_report(query, entity_type, entity_name, progress)

        # ── Step 8: Convert Markdown to HTML ────────────────────
        import markdown as md_lib
        html_content = md_lib.markdown(
            markdown,
            extensions=["tables", "fenced_code", "codehilite", "toc", "nl2br"],
        )

        # ── Step 9: Save to Cache ───────────────────────────────
        report_id = await save_report_to_cache(
            query=query,
            entity_type=entity_type,
            entity_name=entity_name,
            markdown_content=markdown,
            html_content=html_content,
            citations=citations,
            data_points=verified_data,
            confidence_score=round(confidence_score, 2),
        )

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        orchestrator_logger.info(f"Report {report_id} generated in {elapsed:.1f}s")

        # Build response
        result = {
            "id": report_id,
            "query": query,
            "entity_type": entity_type,
            "entity_type_label": ENTITY_LABELS.get(entity_type, entity_type),
            "entity_name": entity_name,
            "markdown_content": markdown,
            "html_content": html_content,
            "sources_count": len(citations),
            "data_points_count": len(verified_data),
            "confidence_score": round(confidence_score, 2),
            "created_at": start_time.strftime("%Y-%m-%d %H:%M"),
            "citations": citations,
            "data_points": verified_data,
        }

        progress.complete(report_id, f"/report/{report_id}")
        return result

    async def _generate_fallback_report(
        self,
        query: str,
        entity_type: str,
        entity_name: str,
        progress: ProgressEmitter,
    ) -> dict:
        """Generate a minimal report when data collection fails."""
        now = datetime.now(timezone.utc)
        report_id = "fallback_" + now.strftime("%Y%m%d%H%M%S")

        entity_label = ENTITY_LABELS.get(entity_type, entity_type)

        markdown = f"""# {entity_name} 研究报告

## 报告摘要
> 由于数据获取受限，未能收集到足够的网络信息来生成完整报告。以下为基于现有信息的简要分析。

## 说明
本次查询未能获取足够的网络数据。可能的原因：
1. 关键词未匹配到相关信息
2. 搜索服务暂时不可用
3. 目标信息在公开网络上较少

## 建议
- 尝试更具体的查询词，如加上年份或省份限定
- 检查网络连接和API配置
- 稍后重试

## 信息来源
数据获取失败，无有效引用来源。

## 免责声明
本报告基于公开来源数据自动生成，仅供参考。本次查询未能获取足够数据。
"""
        html = f"<h1>{entity_name} 研究报告</h1><p>数据获取失败，未能生成完整报告。</p>"

        result = {
            "id": report_id,
            "query": query,
            "entity_type": entity_type,
            "entity_type_label": entity_label,
            "entity_name": entity_name,
            "markdown_content": markdown,
            "html_content": html,
            "sources_count": 0,
            "data_points_count": 0,
            "confidence_score": 0.0,
            "created_at": now.strftime("%Y-%m-%d %H:%M"),
            "citations": [],
            "data_points": [],
        }

        progress.complete(report_id, f"/report/{report_id}")
        return result
