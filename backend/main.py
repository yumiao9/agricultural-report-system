"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.models.database import init_db, close_db
from backend.routers import research, reports, pages


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    await init_db()
    yield
    # Shutdown
    await close_db()


app = FastAPI(
    title="农业报告产出系统",
    description="Agricultural Research Report Generation System",
    version="1.0.0",
    lifespan=lifespan,
)

# Static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
try:
    app.mount("/static", StaticFiles(directory=str(static_dir.resolve())), name="static")
except Exception:
    pass  # Fallback: routes will handle static via API

# Routers
app.include_router(pages.router)
app.include_router(research.router, prefix="/api")
app.include_router(reports.router, prefix="/api")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "configured": settings.is_configured,
        "llm_provider": settings.llm_config["provider"],
    }
