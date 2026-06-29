"""Research endpoint — creates task and returns immediately."""

import uuid

from fastapi import APIRouter
from sqlalchemy import update

from backend.models.database import async_session_factory
from backend.models.report import Report
from backend.models.schemas import ResearchRequest
from backend.utils.logger import orchestrator_logger

router = APIRouter()


@router.post("/research")
async def start_research(request: ResearchRequest):
    """Create a research task and return immediately.

    The client then polls /api/research/{task_id}/status and calls
    step endpoints sequentially.
    """
    orchestrator_logger.info(f"Research request: {request.query} (force_refresh={request.force_refresh})")

    report_id = uuid.uuid4().hex[:12]
    report = Report(
        id=report_id,
        query=request.query,
        query_hash="pending",
        entity_type="pending",
        entity_name=request.query,
        status="pending",
        step_data={"query": request.query},
    )

    async with async_session_factory() as session:
        session.add(report)
        await session.commit()

    return {
        "task_id": report_id,
        "status": "pending",
        "url": f"/research/{report_id}",
    }
