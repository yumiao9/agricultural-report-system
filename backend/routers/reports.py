"""Report CRUD API endpoints."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, Response

from backend.services.cache import get_report_history, get_report_by_id

router = APIRouter()


@router.get("/reports")
async def list_reports(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List past reports."""
    reports = await get_report_history(limit=limit, offset=offset)
    return {"reports": reports, "total": len(reports)}


@router.get("/reports/{report_id}")
async def get_report(report_id: str):
    """Get a specific report by ID."""
    report = await get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/reports/{report_id}/pdf")
async def download_report_pdf(report_id: str):
    """Download a report as PDF."""
    report = await get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if not report.get("html_content"):
        raise HTTPException(status_code=400, detail="Report has no content")

    try:
        from weasyprint import HTML

        full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: "SimSun", "Microsoft YaHei", serif; font-size: 12pt; line-height: 1.8; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
  h1 {{ font-size: 20pt; text-align: center; margin-bottom: 20px; }}
  h2 {{ font-size: 16pt; margin-top: 24px; border-bottom: 1px solid #ddd; padding-bottom: 6px; }}
  h3 {{ font-size: 14pt; margin-top: 18px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 10pt; }}
  th, td {{ border: 1px solid #ccc; padding: 6px 10px; text-align: left; }}
  th {{ background-color: #f5f5f5; }}
  blockquote {{ border-left: 4px solid #4CAF50; padding-left: 12px; color: #555; margin: 12px 0; }}
  p {{ margin: 8px 0; }}
</style>
</head>
<body>
{report['html_content']}
</body>
</html>"""

        pdf_bytes = HTML(string=full_html).write_pdf()

        filename = f"{report.get('entity_name', 'report')}_研究报告.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            },
        )
    except ImportError:
        # WeasyPrint not available (e.g., on Vercel), return HTML as fallback
        filename = f"{report.get('entity_name', 'report')}_研究报告.html"
        return Response(
            content=report.get("html_content", ""),
            media_type="text/html",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")
