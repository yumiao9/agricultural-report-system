"""HTML page routes — server-side rendered via Jinja2."""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse

from backend.config import settings
from backend.services.cache import get_report_history, get_report_by_id

router = APIRouter()

# Jinja2 templates
from jinja2 import Environment, FileSystemLoader, select_autoescape

templates = Environment(
    loader=FileSystemLoader(str(settings.TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """Home page with search form."""
    template = templates.get_template("index.html")
    return template.render(
        configured=settings.is_configured,
        llm_provider=settings.llm_config["provider"],
    )


@router.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    """Past reports page."""
    reports = await get_report_history(limit=50)
    template = templates.get_template("history.html")
    return template.render(reports=reports)


@router.get("/report/{report_id}", response_class=HTMLResponse)
async def report_page(request: Request, report_id: str):
    """View a specific report."""
    report = await get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告未找到")

    template = templates.get_template("report.html")
    return template.render(
        report=report,
        configured=settings.is_configured,
    )
