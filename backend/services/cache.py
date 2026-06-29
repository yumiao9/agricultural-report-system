"""Caching layer using SQLite for reports and search results."""

import hashlib
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, delete

from backend.config import settings
from backend.models.database import async_session_factory
from backend.models.report import Report, SearchCache, DataPoint, Citation
from backend.utils.logger import orchestrator_logger


def _hash_query(query: str) -> str:
    """Hash a query string for cache lookup."""
    return hashlib.sha256(query.strip().lower().encode()).hexdigest()


async def get_cached_report(query: str) -> dict | None:
    """Look up a cached report by query. Returns None if not found or expired."""
    query_hash = _hash_query(query)
    now = datetime.now(timezone.utc)

    async with async_session_factory() as session:
        result = await session.execute(
            select(Report).where(
                Report.query_hash == query_hash,
                Report.expires_at > now,
            ).order_by(Report.created_at.desc()).limit(1)
        )
        report = result.scalar_one_or_none()

        if report:
            orchestrator_logger.info(f"Cache HIT for: {query[:50]}")
            # Load citations
            citations_result = await session.execute(
                select(Citation).where(Citation.report_id == report.id)
            )
            citations = citations_result.scalars().all()

            # Load data points
            dp_result = await session.execute(
                select(DataPoint).where(DataPoint.report_id == report.id)
            )
            data_points = dp_result.scalars().all()

            from backend.models.schemas import ENTITY_LABELS

            return {
                "id": report.id,
                "query": report.query,
                "entity_type": report.entity_type,
                "entity_type_label": ENTITY_LABELS.get(report.entity_type, report.entity_type),
                "entity_name": report.entity_name,
                "markdown_content": report.markdown_content,
                "html_content": report.html_content,
                "sources_count": report.sources_count,
                "data_points_count": report.data_points_count,
                "confidence_score": report.confidence_score,
                "created_at": report.created_at.isoformat(),
                "citations": [
                    {
                        "ref_number": c.ref_number,
                        "title": c.title,
                        "url": c.url,
                        "snippet": c.snippet,
                        "access_date": c.access_date.strftime("%Y-%m-%d") if c.access_date else "",
                    }
                    for c in citations
                ],
                "data_points": [
                    {
                        "indicator": dp.indicator,
                        "value": dp.value,
                        "value_text": dp.value_text,
                        "unit": dp.unit,
                        "year": dp.year,
                        "source_url": dp.source_url,
                        "source_sentence": dp.source_sentence,
                        "confidence": dp.confidence,
                    }
                    for dp in data_points
                ],
            }

    orchestrator_logger.info(f"Cache MISS for: {query[:50]}")
    return None


async def save_report_to_cache(
    query: str,
    entity_type: str,
    entity_name: str,
    markdown_content: str,
    html_content: str,
    citations: list[dict],
    data_points: list[dict],
    confidence_score: float,
) -> str:
    """Save a generated report to the cache. Returns the report ID."""
    import uuid

    query_hash = _hash_query(query)
    now = datetime.now(timezone.utc)
    ttl_hours = settings.CACHE_TTL_HOURS
    expires_at = now + timedelta(hours=ttl_hours)
    report_id = uuid.uuid4().hex[:12]

    async with async_session_factory() as session:
        # Delete old cache for same query
        await session.execute(
            delete(Report).where(Report.query_hash == query_hash)
        )

        # Create report
        report = Report(
            id=report_id,
            query=query,
            query_hash=query_hash,
            entity_type=entity_type,
            entity_name=entity_name,
            markdown_content=markdown_content,
            html_content=html_content,
            sources_count=len(citations),
            data_points_count=len(data_points),
            confidence_score=confidence_score,
            expires_at=expires_at,
        )
        session.add(report)

        # Add citations
        for c in citations:
            session.add(Citation(
                report_id=report_id,
                ref_number=c["ref_number"],
                title=c.get("title", ""),
                url=c["url"],
                snippet=c.get("snippet", ""),
                access_date=now,
            ))

        # Add data points
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

    orchestrator_logger.info(f"Report saved to cache: {report_id} (expires in {ttl_hours}h)")
    return report_id


async def get_cached_search(query: str) -> list | None:
    """Look up cached search results."""
    query_hash = _hash_query(query)
    now = datetime.now(timezone.utc)

    async with async_session_factory() as session:
        result = await session.execute(
            select(SearchCache).where(
                SearchCache.query_hash == query_hash,
                SearchCache.expires_at > now,
            ).limit(1)
        )
        cache = result.scalar_one_or_none()
        if cache:
            return json.loads(cache.search_results) if isinstance(cache.search_results, str) else cache.search_results
    return None


async def save_search_cache(query: str, results: list[dict]):
    """Save search results to cache (24 hours)."""
    query_hash = _hash_query(query)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=24)

    async with async_session_factory() as session:
        # Delete old
        await session.execute(
            delete(SearchCache).where(SearchCache.query_hash == query_hash)
        )
        # Insert
        session.add(SearchCache(
            query_hash=query_hash,
            search_results=json.dumps(results, ensure_ascii=False),
            expires_at=expires_at,
        ))
        await session.commit()


async def get_report_history(limit: int = 20, offset: int = 0) -> list[dict]:
    """Get list of past reports."""
    from backend.models.schemas import ENTITY_LABELS

    async with async_session_factory() as session:
        result = await session.execute(
            select(Report)
            .order_by(Report.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        reports = result.scalars().all()

        return [
            {
                "id": r.id,
                "query": r.query,
                "entity_type": r.entity_type,
                "entity_type_label": ENTITY_LABELS.get(r.entity_type, r.entity_type),
                "sources_count": r.sources_count,
                "data_points_count": r.data_points_count,
                "confidence_score": r.confidence_score,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            }
            for r in reports
        ]


async def get_report_by_id(report_id: str) -> dict | None:
    """Get a specific report by ID."""
    from backend.models.schemas import ENTITY_LABELS

    async with async_session_factory() as session:
        result = await session.execute(
            select(Report).where(Report.id == report_id)
        )
        report = result.scalar_one_or_none()
        if not report:
            return None

        citations_result = await session.execute(
            select(Citation).where(Citation.report_id == report_id)
        )
        citations = citations_result.scalars().all()

        dp_result = await session.execute(
            select(DataPoint).where(DataPoint.report_id == report_id)
        )
        data_points = dp_result.scalars().all()

        return {
            "id": report.id,
            "query": report.query,
            "entity_type": report.entity_type,
            "entity_type_label": ENTITY_LABELS.get(report.entity_type, report.entity_type),
            "entity_name": report.entity_name,
            "markdown_content": report.markdown_content,
            "html_content": report.html_content,
            "sources_count": report.sources_count,
            "data_points_count": report.data_points_count,
            "confidence_score": report.confidence_score,
            "created_at": report.created_at.strftime("%Y-%m-%d %H:%M"),
            "citations": [
                {
                    "ref_number": c.ref_number,
                    "title": c.title,
                    "url": c.url,
                    "snippet": c.snippet,
                    "access_date": c.access_date.strftime("%Y-%m-%d") if c.access_date else "",
                }
                for c in citations
            ],
            "data_points": [
                {
                    "indicator": dp.indicator,
                    "value": dp.value,
                    "value_text": dp.value_text,
                    "unit": dp.unit,
                    "year": dp.year,
                    "source_url": dp.source_url,
                    "source_sentence": dp.source_sentence,
                    "confidence": dp.confidence,
                }
                for dp in data_points
            ],
        }
