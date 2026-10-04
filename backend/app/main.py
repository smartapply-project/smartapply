from __future__ import annotations

import json
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .db import get_session, init_db
from .models import AnalysisIssue, Application, CheckRecord, DocumentRecord
from .schemas import ApplicationCreate
from .services.analysis import EXPECTED_LABELS, analyze_document, cross_check

BASE_DIR = Path(__file__).resolve().parents[2]
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
FRONTEND_DIR = BASE_DIR / "frontend" / "dist"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Smart Application Processing", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _json_fields(raw: str) -> dict:
    try:
        return json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}


def _payload(application: Application) -> dict:
    return {
        "id": application.id,
        "name": application.name,
        "email": application.email,
        "date_of_birth": application.date_of_birth,
        "application_type": application.application_type,
        "marks_percentage": application.marks_percentage,
        "family_income": application.family_income,
        "status": application.status,
        "health": application.health,
        "created_at": application.created_at.isoformat(),
        "updated_at": application.updated_at.isoformat(),
        "documents": [{"id": doc.id, "slot": doc.slot, "filename": doc.filename, "detected_type": doc.detected_type, "confidence": doc.confidence, "extracted_fields": _json_fields(doc.extracted_json), "status": doc.status, "rejection_reason": doc.rejection_reason} for doc in application.documents],
        "checks": [{"key": check.key, "label": check.label, "status": check.status, "detail": check.detail} for check in application.checks],
        "issues": [{"severity": issue.severity, "code": issue.code, "message": issue.message, "suggestion": issue.suggestion, "source": issue.source} for issue in application.issues],
    }


async def _load(session: AsyncSession, application_id: int) -> Application:
    result = await session.execute(select(Application).where(Application.id == application_id).options(selectinload(Application.documents), selectinload(Application.checks), selectinload(Application.issues)))
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(404, "Application not found")
    return application


async def _recompute(session: AsyncSession, application: Application) -> None:
    document_data = [{"slot": d.slot, "status": d.status, "confidence": d.confidence, "fields": _json_fields(d.extracted_json), "reason": d.rejection_reason} for d in application.documents]
    form = {"name": application.name, "date_of_birth": application.date_of_birth, "marks_percentage": application.marks_percentage, "family_income": application.family_income}
    issues, checks, health, status = cross_check(form, document_data)
    await session.execute(delete(AnalysisIssue).where(AnalysisIssue.application_id == application.id))
    await session.execute(delete(CheckRecord).where(CheckRecord.application_id == application.id))
    for issue in issues:
        session.add(AnalysisIssue(application_id=application.id, severity=issue["severity"], code=issue["code"], message=issue["message"], suggestion=issue["suggestion"], source=issue.get("source")))
    for check in checks:
        session.add(CheckRecord(application_id=application.id, key=check["key"], label=check["label"], status=check["status"], detail=check["detail"]))
    application.health = health
    application.status = status
    await session.commit()
    session.expire_all()


@app.on_event("startup")
async def startup() -> None:
    await init_db()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "smart-application-processing"}


@app.post("/api/applications")
async def create_application(payload: ApplicationCreate, session: AsyncSession = Depends(get_session)) -> dict:
    application = Application(**payload.model_dump(), status="Draft", health=0)
    session.add(application)
    await session.commit()
    await session.refresh(application)
    return {"id": application.id, "status": application.status}


@app.post("/api/applications/{application_id}/documents")
async def upload_document(application_id: int, slot: str = Form(...), file: UploadFile = File(...), session: AsyncSession = Depends(get_session)) -> dict:
    if slot not in EXPECTED_LABELS:
        raise HTTPException(400, "Unknown document slot")
    application = await _load(session, application_id)
    data = await file.read()
    result = await analyze_document(slot, file.filename or "upload", file.content_type or "application/octet-stream", data)
    if any(doc.sha256 == result["sha256"] for doc in application.documents):
        raise HTTPException(409, "This file was already uploaded for this application.")
    suffix = Path(file.filename or "upload").suffix.lower() or ".bin"
    storage_key = f"{application_id}/{slot}-{result['sha256']}{suffix}"
    if result.get("ok") or result.get("status") == "Manual Review":
        (UPLOAD_DIR / f"{application_id}_{slot}_{result['sha256']}{suffix}").write_bytes(data)
    previous = next((doc for doc in application.documents if doc.slot == slot), None)
    if previous:
        for path in UPLOAD_DIR.glob(f"{application_id}_{slot}_{previous.sha256}*"):
            path.unlink(missing_ok=True)
        await session.delete(previous)
        await session.flush()
    session.add(DocumentRecord(application_id=application_id, slot=slot, filename=file.filename or "upload", mime_type=file.content_type or "application/octet-stream", sha256=result["sha256"], storage_key=storage_key, detected_type=result.get("detected_type"), confidence=result.get("confidence"), extracted_json=json.dumps(result.get("fields", {})), status=result.get("status", "Rejected"), rejection_reason=result.get("reason")))
    await session.commit()
    application = await _load(session, application_id)
    await _recompute(session, application)
    return _payload(await _load(session, application_id))


@app.post("/api/applications/{application_id}/analyze")
async def analyze_application(application_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    application = await _load(session, application_id)
    await _recompute(session, application)
    return _payload(await _load(session, application_id))


@app.get("/api/applications/{application_id}")
async def get_application(application_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    return _payload(await _load(session, application_id))


@app.post("/api/applications/{application_id}/resubmit")
async def resubmit_application(application_id: int, payload: ApplicationCreate, session: AsyncSession = Depends(get_session)) -> dict:
    application = await _load(session, application_id)
    for key, value in payload.model_dump().items():
        setattr(application, key, value)
    application.status = "Draft"
    application.health = 0
    await session.commit()
    return _payload(await _load(session, application_id))


@app.delete("/api/applications/{application_id}")
async def delete_application(application_id: int, session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    application = await _load(session, application_id)
    for path in UPLOAD_DIR.glob(f"{application_id}_*"):
        path.unlink(missing_ok=True)
    await session.delete(application)
    await session.commit()
    return {"status": "deleted"}


@app.get("/api/admin/applications")
async def admin_applications(status: str | None = None, session: AsyncSession = Depends(get_session)) -> list[dict]:
    query = select(Application).options(selectinload(Application.documents)).order_by(Application.updated_at.desc())
    if status and status != "All statuses":
        query = query.where(Application.status == status)
    result = await session.execute(query)
    return [{"id": item.id, "name": item.name, "application_type": item.application_type, "status": item.status, "health": item.health, "document_count": len(item.documents), "updated_at": item.updated_at.isoformat()} for item in result.scalars().all()]


if FRONTEND_DIR.exists() and (FRONTEND_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")


@app.get("/{full_path:path}")
async def spa(full_path: str):
    if full_path == "manus-routes.json":
        return FileResponse(BASE_DIR / "public" / "manus-routes.json", media_type="application/json")
    index = FRONTEND_DIR / "index.html"
    if index.exists() and not full_path.startswith("api/"):
        return FileResponse(index)
    return JSONResponse({"detail": "Frontend is not built yet. Run pnpm --dir frontend build."}, status_code=503)
