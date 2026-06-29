"""Step-by-step research pipeline for Vercel serverless (10s function limit)."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import select, update

from backend.config import settings
from backend.models.database import async_session_factory
from backend.models.report import Report, Citation, DataPoint, utcnow
from backend.models.schemas import ENTITY_LABELS
from backend.services.entity_classifier import classify_entity
from backend.services.search.duckduckgo import DuckDuckGoSearch
from backend.services.search.baidu import BaiduSearch
from backend.services.search.chinese_sources import ChineseOfficialSourceSearch
from backend.services.search.base import SearchManager, SearchResult
from backend.services.fetcher import fetch_pages
from backend.services.simple_extractor import extract_from_pages as extract_data_regex
from backend.services.extractor import extract_data_from_pages as extract_data_llm
from backend.services.verifier import verify_data_points
from backend.services.citation import build_citations, format_inline_citation
from backend.services.template_report import generate_template_report
from backend.services.orchestrator import TARGETED_QUERIES
from backend.utils.logger import orchestrator_logger

router = APIRouter()


def _build_search_manager() -> SearchManager:
    providers = []
    if settings.ENABLE_BAIDU:
        providers.append(BaiduSearch())
    providers.append(DuckDuckGoSearch())
    if settings.ENABLE_CHINESE_OFFICIAL:
        providers.append(ChineseOfficialSourceSearch())
    return SearchManager(providers)


async def _get_report(report_id: str) -> Report | None:
    async with async_session_factory() as session:
        r = await session.execute(select(Report).where(Report.id == report_id))
        return r.scalar_one_or_none()


async def _update_status(report_id: str, status: str, step_data: dict = None, error: str = None):
    async with async_session_factory() as session:
        vals = {"status": status}
        if step_data is not None:
            vals["step_data"] = step_data
        if error:
            vals["error_message"] = error
        await session.execute(update(Report).where(Report.id == report_id).values(**vals))
        await session.commit()


async def _save_report(report: Report):
    async with async_session_factory() as session:
        session.add(report)
        await session.commit()
        return report.id


# ── Status ───────────────────────────────────────────────────────

@router.get("/research/{report_id}/status")
async def get_status(report_id: str):
    """Get the current status of a research task."""
    report = await _get_report(report_id)
    if not report:
        raise HTTPException(404, "Task not found")
    return {
        "task_id": report.id,
        "status": report.status,
        "query": report.query,
        "entity_type": report.entity_type,
        "entity_name": report.entity_name,
        "error_message": report.error_message,
    }


# ── Step: Classify ───────────────────────────────────────────────

@router.post("/research/{report_id}/step-classify")
async def step_classify(report_id: str):
    report = await _get_report(report_id)
    if not report:
        raise HTTPException(404, "Task not found")

    query = report.step_data.get("query", report.query) if report.step_data else report.query
    try:
        classification = await classify_entity(query)
    except Exception as e:
        orchestrator_logger.warning(f"Classification failed: {e}")
        classification = {"entity_type": "agricultural_product", "entity_name": query,
                          "keywords": [query], "search_query_zh": query}

    step_data = dict(report.step_data or {})
    step_data.update(classification)

    async with async_session_factory() as session:
        await session.execute(
            update(Report).where(Report.id == report_id).values(
                status="classified",
                entity_type=classification["entity_type"],
                entity_name=classification.get("entity_name", query),
                step_data=step_data,
            )
        )
        await session.commit()

    return {"status": "classified", "entity_type": classification["entity_type"],
            "entity_name": classification.get("entity_name", query)}


# ── Step: Search ─────────────────────────────────────────────────

@router.post("/research/{report_id}/step-search")
async def step_search(report_id: str):
    import asyncio
    from backend.services.orchestrator import TARGETED_QUERIES

    report = await _get_report(report_id)
    if not report:
        raise HTTPException(404, "Task not found")

    sd = report.step_data or {}
    entity_type = report.entity_type
    entity_name = report.entity_name
    query = sd.get("search_query_zh", report.query)

    # Ensure query has agricultural context for better Chinese search results
    if entity_type == "agricultural_product":
        enhanced = f"{query} 农业 农产品"
    elif entity_type == "agricultural_region":
        enhanced = f"{query} 农业 经济"
    elif entity_type == "agricultural_enterprise":
        enhanced = f"{query} 企业"
    else:
        enhanced = query

    search_query = enhanced

    manager = _build_search_manager()
    all_results = []

    for provider in manager.providers:
        try:
            results = await asyncio.wait_for(
                provider.search(search_query, num=6), timeout=7.0
            )
            for r in results:
                url = r.url
                if url:
                    all_results.append(SearchResult(url=url, title=r.title, snippet=r.snippet))
            if len(all_results) >= 5:
                break
        except Exception as e:
            orchestrator_logger.warning(f"Provider {provider.name} failed: {e}")
            continue

    # Deduplicate
    seen = set()
    deduped = []
    for r in all_results:
        url = r.url
        if url and url not in seen:
            seen.add(url)
            deduped.append(r)
    all_results = deduped

    results_data = [{"title": r.title, "url": r.url, "snippet": r.snippet} for r in all_results]

    step_data = dict(sd)
    step_data["search_results"] = results_data

    async with async_session_factory() as session:
        await session.execute(
            update(Report).where(Report.id == report_id).values(
                status="searched", step_data=step_data
            )
        )
        await session.commit()

    return {"status": "searched", "count": len(results_data)}


# ── Step: Fetch ──────────────────────────────────────────────────

@router.post("/research/{report_id}/step-fetch")
async def step_fetch(report_id: str):
    report = await _get_report(report_id)
    if not report:
        raise HTTPException(404, "Task not found")

    sd = report.step_data or {}
    search_results = sd.get("search_results", [])

    urls = [r["url"] for r in search_results[:5] if r.get("url")]
    fetched_pages = await fetch_pages(urls, max_concurrent=3, timeout=8.0)

    success_count = sum(1 for p in fetched_pages if p["fetch_success"])

    # If no pages were fetched, use search snippets as fallback content
    if success_count == 0:
        fetched_pages = []
        for r in search_results:
            snippet = r.get("snippet", "")
            if snippet and len(snippet) > 30:
                fetched_pages.append({
                    "url": r.get("url", ""),
                    "title": r.get("title", ""),
                    "text_content": snippet,
                    "fetch_success": True,
                })

    pages_data = [{
        "url": p["url"], "title": p.get("title",""),
        "fetch_success": p.get("fetch_success", False),
        "text_length": len(p.get("text_content","")) if p.get("fetch_success") else 0,
        "text_preview": (p.get("text_content","") or "")[:200],
        "error": p.get("error_message", ""),
    } for p in fetched_pages]

    step_data = dict(sd)
    step_data["fetched_pages"] = pages_data
    success_count = sum(1 for p in fetched_pages if p["fetch_success"])

    async with async_session_factory() as session:
        await session.execute(
            update(Report).where(Report.id == report_id).values(
                status="fetched", step_data=step_data
            )
        )
        await session.commit()

    return {"status": "fetched", "success": success_count, "total": len(urls)}


# ── Step: Extract ────────────────────────────────────────────────

@router.post("/research/{report_id}/step-extract")
async def step_extract(report_id: str):
    report = await _get_report(report_id)
    if not report:
        raise HTTPException(404, "Task not found")

    sd = report.step_data or {}
    fetched_pages = sd.get("fetched_pages", [])
    entity_name = report.entity_name

    # Use instant regex extraction (no LLM call, works within 10s limit)
    try:
        data_points = extract_data_regex(fetched_pages)
        verified = await verify_data_points(data_points)
    except Exception as e:
        orchestrator_logger.warning(f"Regex extract failed: {e}")
        verified = []

    step_data = dict(sd)
    step_data["data_points"] = verified

    async with async_session_factory() as session:
        await session.execute(
            update(Report).where(Report.id == report_id).values(
                status="extracted", step_data=step_data,
                data_points_count=len(verified),
            )
        )
        await session.commit()

    return {"status": "extracted", "count": len(verified)}


# ── Step: Generate ───────────────────────────────────────────────

@router.post("/research/{report_id}/step-generate")
async def step_generate(report_id: str):
    import markdown as md_lib
    from backend.models.schemas import ENTITY_LABELS

    report = await _get_report(report_id)
    if not report:
        raise HTTPException(404, "Task not found")

    sd = report.step_data or {}
    search_results = sd.get("search_results", [])
    fetched_pages = sd.get("fetched_pages", [])
    data_points = sd.get("data_points", [])
    entity_name = report.entity_name
    entity_type = report.entity_type

    citations = build_citations(
        [type("obj", (object,), r) for r in search_results],
        fetched_pages
    )

    confidence_counts = {"high": 0, "medium": 0, "low": 0}
    for dp in data_points:
        conf = dp.get("confidence", "medium")
        confidence_counts[conf] = confidence_counts.get(conf, 0) + 1
    total = len(data_points) or 1
    confidence_score = (confidence_counts.get("high", 0) * 1.0 +
                        confidence_counts.get("medium", 0) * 0.5) / total

    # Use template generator (fast, no LLM call)
    type_label = ENTITY_LABELS.get(entity_type, entity_type)
    markdown = generate_template_report(
        entity_name=entity_name,
        entity_type=entity_type,
        entity_type_label=type_label,
        data_points=data_points,
        citations=citations,
    )

    html_content = md_lib.markdown(
        markdown,
        extensions=["tables", "fenced_code", "codehilite", "toc", "nl2br"],
    )

    now = utcnow()
    ttl_hours = settings.CACHE_TTL_HOURS
    expires_at = now.isoformat()

    async with async_session_factory() as session:
        # Delete stale
        await session.execute(
            update(Report).where(Report.id == report_id).values(
                status="complete",
                markdown_content=markdown,
                html_content=html_content,
                sources_count=len(citations),
                confidence_score=round(confidence_score, 2),
                step_data=None,
                created_at=now,
            )
        )
        # Save citations
        for c in citations:
            session.add(Citation(
                report_id=report_id,
                ref_number=c["ref_number"],
                title=c.get("title", ""),
                url=c["url"],
                snippet=c.get("snippet", ""),
                access_date=now,
            ))
        # Save data points
        for dp in data_points:
            session.add(DataPoint(
                report_id=report_id,
                indicator=dp.get("indicator", ""),
                value=dp.get("value"),
                value_text=dp.get("value_text", ""),
                unit=dp.get("unit", ""),
                year=dp.get("year", ""),
                source_url=dp.get("source_url", ""),
                source_sentence=dp.get("source_sentence", ""),
                confidence=dp.get("confidence", "medium"),
            ))
        await session.commit()

    return {"status": "complete", "report_id": report_id, "url": f"/report/{report_id}"}
