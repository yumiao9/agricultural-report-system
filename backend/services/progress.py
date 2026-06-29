"""SSE progress event emitter for real-time research status updates."""

import asyncio
import json
from typing import AsyncGenerator


class ProgressEmitter:
    """Emits SSE progress events throughout the research pipeline."""

    def __init__(self):
        self._queue = asyncio.Queue()

    def emit(self, stage: str, message: str, detail: str = None, percent: int = 0):
        """Push a progress event to the queue."""
        event = {
            "stage": stage,
            "message": message,
            "detail": detail,
            "percent": percent,
        }
        self._queue.put_nowait(event)

    async def stream(self) -> AsyncGenerator[str, None]:
        """Async generator yielding SSE-formatted strings."""
        while True:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=0.1)
                data = json.dumps(event, ensure_ascii=False)
                yield f"event: progress\ndata: {data}\n\n"

                if event["stage"] in ("complete", "error"):
                    break
            except asyncio.TimeoutError:
                # Send a keepalive comment
                yield ": keepalive\n\n"

    def complete(self, report_id: str, url: str):
        """Emit completion event."""
        event = {
            "stage": "complete",
            "message": "报告生成完成",
            "detail": None,
            "percent": 100,
            "report_id": report_id,
            "url": url,
        }
        self._queue.put_nowait(event)

    def error(self, message: str):
        """Emit error event."""
        event = {
            "stage": "error",
            "message": message,
            "detail": None,
            "percent": 0,
        }
        self._queue.put_nowait(event)


# Progress stage presets
PROGRESS_STAGES = [
    ("classifying", "正在分析查询类型...", 5),
    ("searching", "正在搜索相关信息...", 15),
    ("fetching", "正在获取网页内容...", 30),
    ("extracting", "正在提取关键数据...", 50),
    ("verifying", "正在交叉验证数据...", 65),
    ("generating", "正在生成研究报告...", 80),
    ("complete", "报告生成完成", 100),
]
