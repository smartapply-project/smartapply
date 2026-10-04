from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(180))
    email: Mapped[str] = mapped_column(String(240))
    date_of_birth: Mapped[str] = mapped_column(String(30))
    application_type: Mapped[str] = mapped_column(String(30))
    marks_percentage: Mapped[str] = mapped_column(String(30))
    family_income: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(40), default="Draft")
    health: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    documents: Mapped[list[DocumentRecord]] = relationship(back_populates="application", cascade="all, delete-orphan")
    checks: Mapped[list[CheckRecord]] = relationship(back_populates="application", cascade="all, delete-orphan")
    issues: Mapped[list[AnalysisIssue]] = relationship(back_populates="application", cascade="all, delete-orphan")


class DocumentRecord(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"))
    slot: Mapped[str] = mapped_column(String(40))
    filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(120))
    sha256: Mapped[str] = mapped_column(String(64))
    storage_key: Mapped[str] = mapped_column(String(300))
    detected_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    extracted_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(40), default="Processing")
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    application: Mapped[Application] = relationship(back_populates="documents")


class CheckRecord(Base):
    __tablename__ = "checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"))
    key: Mapped[str] = mapped_column(String(60))
    label: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(30))
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    application: Mapped[Application] = relationship(back_populates="checks")


class AnalysisIssue(Base):
    __tablename__ = "analysis_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"))
    severity: Mapped[str] = mapped_column(String(30))
    code: Mapped[str] = mapped_column(String(80))
    message: Mapped[str] = mapped_column(Text)
    suggestion: Mapped[str] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    application: Mapped[Application] = relationship(back_populates="issues")
