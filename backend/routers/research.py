"""Research endpoint with SSE progress streaming."""

import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from backend.models.schemas import ResearchRequest
from backend.services.orchestrator import ResearchOrchestrator
from backend.services.progress import ProgressEmitter
from backend.utils.logger import orchestrator_logger

router = APIRouter()

# Singleton orchestrator
_orchestrator = ResearchOrchestrator()


@router.post("/research")
async def start_research(request: ResearchRequest):
    """Start a research task, stream progress via SSE.

    The client receives progress events during research, and a
    'complete' event with report_id when the report is ready.
    """
    orchestrator_logger.info(f"Research request: {request.query} (force_refresh={request.force_refresh})")

    progress = ProgressEmitter()

    # Launch research in background
    async def run_research():
        try:
            result = await _orchestrator.execute(
                query=request.query,
                progress=progress,
                force_refresh=request.force_refresh,
            )
            return result
        except Exception as e:
            orchestrator_logger.error(f"Research failed: {e}")
            progress.error(f"研究过程出错: {str(e)[:200]}")
            return None

    # Start research task
    task = asyncio.create_task(run_research())

    async def sse_generator():
        """SSE stream that sends progress events until complete."""
        async for event in progress.stream():
            yield event

        # Ensure task completes
        await task

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
