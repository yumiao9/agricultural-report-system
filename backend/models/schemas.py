"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────

ENTITY_TYPES = ["agricultural_product", "agricultural_enterprise", "agricultural_equipment", "agricultural_region"]

ENTITY_LABELS = {
    "agricultural_product": "农产品",
    "agricultural_enterprise": "农业企业",
    "agricultural_equipment": "农机设备",
    "agricultural_region": "产地/乡村",
}


# ── Request ──────────────────────────────────────────────────────

class ResearchRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="搜索内容，如：黑龙江大豆、中粮集团、大型收割机",
        examples=["黑龙江大豆", "中粮集团", "大型收割机"],
    )
    force_refresh: bool = Field(
        default=False,
        description="是否强制刷新，忽略缓存",
    )


# ── Response ─────────────────────────────────────────────────────

class CitationResponse(BaseModel):
    ref_number: int
    title: Optional[str] = None
    url: str
    snippet: Optional[str] = None
    access_date: Optional[str] = None


class DataPointResponse(BaseModel):
    indicator: str
    value: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    year: Optional[str] = None
    source_url: Optional[str] = None
    source_sentence: Optional[str] = None
    confidence: str = "medium"


class ReportSummary(BaseModel):
    """Lightweight summary for history list."""
    id: str
    query: str
    entity_type: str
    entity_type_label: str
    sources_count: int
    data_points_count: int
    confidence_score: float
    created_at: str


class ReportDetail(BaseModel):
    """Full report detail."""
    id: str
    query: str
    entity_type: str
    entity_type_label: str
    entity_name: str
    markdown_content: Optional[str] = None
    html_content: Optional[str] = None
    sources_count: int
    data_points_count: int
    confidence_score: float
    created_at: str
    citations: list[CitationResponse] = []
    data_points: list[DataPointResponse] = []


class ReportListResponse(BaseModel):
    reports: list[ReportSummary]
    total: int


# ── SSE Progress ──────────────────────────────────────────────────

class ProgressEvent(BaseModel):
    stage: str           # e.g. "classifying", "searching", "fetching", "extracting", "verifying", "generating", "complete", "error"
    message: str         # Human-readable Chinese message
    detail: Optional[str] = None   # Extra detail (e.g. "3/8 pages fetched")
    percent: int = 0     # 0-100


class ResearchComplete(BaseModel):
    report_id: str
    url: str


# ── Search Result ─────────────────────────────────────────────────

class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str


class FetchedPage(BaseModel):
    url: str
    title: str
    text_content: str
    fetch_success: bool
    error_message: Optional[str] = None


# ── Entity Classification ────────────────────────────────────────

class EntityClassification(BaseModel):
    entity_type: str  # agricultural_product / agricultural_enterprise / agricultural_equipment
    entity_name: str
    keywords: list[str]
    search_query_zh: str
