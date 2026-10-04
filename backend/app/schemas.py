from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ApplicationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    email: str = Field(min_length=5, max_length=240)
    date_of_birth: str = Field(min_length=4, max_length=30)
    application_type: Literal["Scholarship", "Admission", "Loan"]
    marks_percentage: str = Field(min_length=1, max_length=30)
    family_income: str = Field(min_length=1, max_length=60)


class ExtractedField(BaseModel):
    value: str | None = None
    confidence: float = 0
    source: str = "document text"


class DocumentResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slot: str
    filename: str
    detected_type: str | None = None
    confidence: float | None = None
    extracted_fields: dict[str, ExtractedField] = {}
    status: str
    rejection_reason: str | None = None


class CheckResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    key: str
    label: str
    status: str
    detail: str


class IssueResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    severity: str
    code: str
    message: str
    suggestion: str
    source: str | None = None


class ApplicationResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    date_of_birth: str
    application_type: str
    marks_percentage: str
    family_income: str
    status: str
    health: int
    created_at: datetime
    updated_at: datetime
    documents: list[DocumentResult]
    checks: list[CheckResult]
    issues: list[IssueResult]


class AdminRow(BaseModel):
    id: int
    name: str
    application_type: str
    status: str
    health: int
    document_count: int
    updated_at: datetime
