"""ORM models for reports, search cache, and citations."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, DateTime, Integer, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship

from backend.models.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def generate_id():
    return uuid.uuid4().hex[:12]


class Report(Base):
    __tablename__ = "reports"

    id = Column(String(12), primary_key=True, default=generate_id)
    query = Column(String(500), nullable=False, index=True)
    query_hash = Column(String(64), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)
    entity_name = Column(String(200), nullable=False)

    # Report content
    markdown_content = Column(Text, nullable=True)
    html_content = Column(Text, nullable=True)
    report_json = Column(JSON, nullable=True)  # Structured data

    # Metadata
    sources_count = Column(Integer, default=0)
    data_points_count = Column(Integer, default=0)
    confidence_score = Column(Float, default=0.0)

    # Timestamps
    created_at = Column(DateTime, default=utcnow)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    citations = relationship("Citation", back_populates="report", cascade="all, delete-orphan")
    data_points = relationship("DataPoint", back_populates="report", cascade="all, delete-orphan")


class Citation(Base):
    __tablename__ = "citations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String(12), ForeignKey("reports.id"), nullable=False)
    ref_number = Column(Integer, nullable=False)
    title = Column(String(500), nullable=True)
    url = Column(String(2000), nullable=False)
    snippet = Column(Text, nullable=True)
    access_date = Column(DateTime, default=utcnow)

    report = relationship("Report", back_populates="citations")


class DataPoint(Base):
    __tablename__ = "data_points"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String(12), ForeignKey("reports.id"), nullable=False)

    indicator = Column(String(200), nullable=False)       # e.g. "年产量"
    value = Column(Float, nullable=True)
    value_text = Column(String(200), nullable=True)       # Original text if not numeric
    unit = Column(String(50), nullable=True)
    year = Column(String(20), nullable=True)
    source_url = Column(String(2000), nullable=True)
    source_sentence = Column(Text, nullable=True)
    confidence = Column(String(20), default="medium")    # high / medium / low

    report = relationship("Report", back_populates="data_points")


class SearchCache(Base):
    __tablename__ = "search_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    query_hash = Column(String(64), nullable=False, index=True)
    search_results = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    expires_at = Column(DateTime, nullable=False)
