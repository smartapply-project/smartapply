from __future__ import annotations

import base64
import json
import os
import re
from datetime import date, datetime
from typing import Any

import httpx

from .extraction import extract_text
from .validation import SLOT_LABELS, validate_file


EXPECTED_LABELS = {"id": "ID proof", "marksheet": "Marksheet", "income": "Income certificate"}


def _field(value: str | None, confidence: float, source: str) -> dict[str, Any]:
    return {"value": value, "confidence": round(max(0, min(confidence, 1)), 2), "source": source}


def _first(patterns: list[str], text: str) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return " ".join(match.group(1).strip().split())
    return None


def extract_fields(text: str, source: str) -> dict[str, dict[str, Any]]:
    compact = " ".join(text.split())
    name = _first([
        r"(?:applicant|candidate|student|beneficiary)\s*(?:name)?\s*[:\-]\s*([A-Za-z][A-Za-z .'-]{2,})",
        r"(?:full\s+name|name)\s*[:\-]\s*([A-Za-z][A-Za-z .'-]{2,})",
        r"(?:certify that|certifies that)\s+([A-Za-z][A-Za-z .'-]{2,}?)(?:,|\s+son\b|\s+daughter\b)",
    ], text)
    dob = _first([
        r"(?:date\s+of\s+birth|dob|birth\s+date)\s*[:\-]\s*([0-9]{1,2}[\-/][0-9]{1,2}[\-/][0-9]{2,4})",
    ], text)
    percentage = _first([
        r"(?:percentage|percent|marks\s*%)\s*[:\-]?\s*([0-9]{1,3}(?:\.[0-9]+)?\s*%)",
        r"([0-9]{1,3}(?:\.[0-9]+)?\s*%)\s*(?:marks|overall|aggregate)",
    ], compact)
    if not percentage:
        percentage_match = re.search(r"(?:total|aggregate|final result).*?([0-9]{1,3}(?:\.[0-9]+)?\s*%)", compact, flags=re.IGNORECASE)
        percentage = percentage_match.group(1).strip() if percentage_match else None
    income = _first([
        r"(?:annual\s+income|family\s+income|income)\s*[:\-]?\s*(?:rs\.?|inr|₹)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
        r"(?:annual\s+family\s+income|family\s+income)\s+(?:is|of)\s*(?:rs\.?|inr|₹)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
    ], compact)
    issue_date = _first([
        r"(?:issue\s+date|date\s+of\s+issue|issued\s+on)\s*[:\-]\s*([0-9]{1,2}[\-/][0-9]{1,2}[\-/][0-9]{2,4})",
    ], text)
    authority = _first([
        r"(?:issued\s+by|issuing\s+authority|authority)\s*[:\-]\s*([A-Za-z][A-Za-z .,'()&-]{2,})",
    ], text)
    identifier = _first([
        r"(?:id\s*(?:no|number)?|certificate\s*(?:no|number)?|registration\s*(?:no|number)?)\s*[:\-]\s*([A-Z0-9][A-Z0-9\-/]{4,})",
    ], text)
    lower = compact.lower()
    return {
        "name": _field(name, 0.9 if name else 0, source),
        "date_of_birth": _field(dob, 0.92 if dob else 0, source),
        "marks_percentage": _field(percentage, 0.9 if percentage else 0, source),
        "family_income": _field(income, 0.86 if income else 0, source),
        "issue_date": _field(issue_date, 0.88 if issue_date else 0, source),
        "issuing_authority": _field(authority, 0.8 if authority else 0, source),
        "id_number": _field(identifier, 0.82 if identifier else 0, source),
        "signature_or_seal": _field("present" if any(k in lower for k in ("signature", "signed", "seal", "stamp", "issuing authority", "controller of examinations")) else "not detected", 0.9 if any(k in lower for k in ("signature", "signed", "seal", "stamp", "issuing authority", "controller of examinations")) else 0.65, source),
    }


def classify(text: str) -> tuple[str | None, float]:
    lower = text.lower()
    scores = {
        "id": sum(token in lower for token in ("aadhaar", "passport", "identity card", "identity", "identification", "driver license", "uid", "id number")),
        "marksheet": sum(token in lower for token in ("marksheet", "mark sheet", "marks memo", "percentage", "total marks", "semester", "grade", "obtained")),
        "income": sum(token in lower for token in ("income certificate", "annual income", "family income", "tahsildar", "revenue department", "issuing authority")),
    }
    detected, score = max(scores.items(), key=lambda item: item[1])
    if score == 0:
        return None, 0
    # Confidence reflects converging document evidence, not a single keyword.
    # Clear multi-signal samples should be high confidence; sparse evidence stays reviewable.
    confidence = {1: 0.78, 2: 0.88, 3: 0.94}.get(min(score, 3), 0.97)
    return detected, confidence


async def _vision_extract(filename: str, mime_type: str, data: bytes) -> tuple[str, dict[str, Any] | None]:
    api_url = os.getenv("MANUS_API_URL") or ("https://api.openai.com" if os.getenv("OPENAI_API_KEY") else "")
    api_key = os.getenv("MANUS_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_url or not api_key or mime_type not in {"image/jpeg", "image/png"}:
        return "", None
    endpoint = api_url.rstrip("/") + "/v1/chat/completions"
    data_url = f"data:{mime_type};base64,{base64.b64encode(data).decode('ascii')}"
    prompt = (
        "Read this uploaded application document. Return JSON only with keys "
        "document_type (id, marksheet, income, or unknown), confidence (0..1), "
        "fields (object with name, date_of_birth, marks_percentage, family_income, "
        "issue_date, issuing_authority, id_number, signature_or_seal; each value is a string or null), "
        "and reason. Do not infer missing values."
    )
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(endpoint, headers=headers, json={
                "model": os.getenv("DOCUMENT_MODEL", "gpt-4o-mini"),
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url, "detail": "auto"}},
                ]}],
                "response_format": {"type": "json_object"},
            })
        if response.status_code >= 400:
            return "", None
        content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        parsed = json.loads(content) if content else None
        if not isinstance(parsed, dict):
            return "", None
        return str(parsed.get("document_type", "unknown")), parsed
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
        return "", None


async def analyze_document(slot: str, filename: str, mime_type: str, data: bytes) -> dict[str, Any]:
    validation = validate_file(filename, mime_type, data)
    if not validation.ok:
        return {"ok": False, "status": "Rejected", "reason": validation.reason, "sha256": validation.sha256}

    text, source = await extract_text(filename, mime_type, data)
    vision_type, vision_payload = ("", None)
    if not text:
        vision_type, vision_payload = await _vision_extract(filename, mime_type, data)
        if vision_payload:
            text = json.dumps(vision_payload)
            source = "vision-model"

    if not text.strip():
        return {
            "ok": False,
            "status": "Manual Review",
            "reason": "We could not read text from this document. Upload a sharper scan or send it for manual review.",
            "sha256": validation.sha256,
            "detected_type": None,
            "confidence": 0,
            "fields": {},
        }

    detected, confidence = classify(text)
    fields = extract_fields(text, source)
    if vision_payload:
        detected = vision_payload.get("document_type") if vision_payload.get("document_type") in EXPECTED_LABELS else detected
        confidence = float(vision_payload.get("confidence") or confidence)
        for key, value in (vision_payload.get("fields") or {}).items():
            if key in fields and value:
                fields[key] = _field(str(value), max(0.7, confidence), source)

    expected = slot
    if detected and detected != expected:
        return {
            "ok": False,
            "status": "Rejected",
            "reason": f"This looks like a {EXPECTED_LABELS.get(detected, 'different document')}, not an {EXPECTED_LABELS[expected].lower()}.",
            "sha256": validation.sha256,
            "detected_type": detected,
            "confidence": confidence,
            "fields": fields,
        }
    if not detected or confidence < 0.6:
        return {
            "ok": False,
            "status": "Manual Review",
            "reason": "The document type could not be classified with enough confidence. A reviewer should verify it.",
            "sha256": validation.sha256,
            "detected_type": detected,
            "confidence": confidence,
            "fields": fields,
        }
    required_fields = ["name", "date_of_birth"] if slot in {"id", "marksheet"} else ["name"]
    missing_core = [key for key in required_fields if not fields.get(key, {}).get("value")]
    if slot == "marksheet" and not fields.get("marks_percentage", {}).get("value"):
        missing_core.append("marks percentage")
    if slot == "income" and not fields.get("family_income", {}).get("value"):
        missing_core.append("family income")
    status = "Verified" if not missing_core else "Manual Review"
    reason = None if not missing_core else f"The document is classified as {EXPECTED_LABELS[slot]}, but these fields were not readable: {', '.join(missing_core)}."
    return {
        "ok": True,
        "status": status,
        "reason": reason,
        "sha256": validation.sha256,
        "detected_type": detected,
        "confidence": confidence,
        "fields": fields,
    }


def _norm(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def _similar(left: str | None, right: str | None) -> bool:
    a, b = _norm(left), _norm(right)
    if not a or not b:
        return False
    date_pattern = re.compile(r"^(\d{4})(\d{2})(\d{2})$")
    if date_pattern.match(a) and len(b) == 8:
        if b[4:] == a[:4]:
            b = b[4:] + b[2:4] + b[:2]
    if a == b or a in b or b in a:
        return True
    return abs(len(a) - len(b)) <= 1 and sum(x != y for x, y in zip(a, b)) <= 1


def _issue(code: str, message: str, suggestion: str, source: str | None = None, severity: str = "error") -> dict[str, Any]:
    return {"code": code, "message": message, "suggestion": suggestion, "source": source, "severity": severity}


def cross_check(form: dict[str, str], documents: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, str]:
    issues: list[dict[str, Any]] = []
    checks = [{"key": "required-documents", "label": "Required documents", "status": "pass", "detail": "All required document slots are present."}]
    slots = {doc["slot"]: doc for doc in documents}
    if not documents:
        return [_issue("no_documents", "Application rejected: no documents were uploaded. Please upload the required documents.", "Upload the required ID proof, marksheet, and income certificate before processing.", severity="rejected")], [{"key": "required-documents", "label": "Required documents", "status": "fail", "detail": "No documents were uploaded."}], 0, "Rejected"
    missing = [EXPECTED_LABELS[key] for key in EXPECTED_LABELS if key not in slots]
    if missing:
        issues.append(_issue("missing_documents", f"Missing required documents: {', '.join(missing)}.", f"Upload: {', '.join(missing)}.", severity="rejected"))
        checks[0] = {"key": "required-documents", "label": "Required documents", "status": "fail", "detail": f"Missing: {', '.join(missing)}."}

    for doc in documents:
        for key, value in (doc.get("fields") or {}).items():
            value = value.get("value") if isinstance(value, dict) else value
            if key == "name" and value and not _similar(form.get("name"), value):
                issues.append(_issue("name_mismatch", f"The {EXPECTED_LABELS[doc['slot']].lower()} shows \"{value}\", but the form says \"{form['name']}\".", f"Correct the form or upload the right {EXPECTED_LABELS[doc['slot']].lower()}.", doc["slot"]))
            elif key == "date_of_birth" and value and not _similar(form.get("date_of_birth"), value):
                issues.append(_issue("dob_mismatch", f"The {EXPECTED_LABELS[doc['slot']].lower()} shows DOB {value}, which does not match the form.", "Correct the date of birth or upload the right document.", doc["slot"]))
            elif key == "marks_percentage" and value and _norm(value).replace("percent", "") != _norm(form.get("marks_percentage")):
                issues.append(_issue("percentage_mismatch", f"You entered {form['marks_percentage']} but the marksheet shows {value}.", "Correct the form or upload the right marksheet.", "marksheet"))
            elif key == "family_income" and value and _norm(value) != _norm(form.get("family_income")):
                issues.append(_issue("income_mismatch", f"You entered {form['family_income']} but the income certificate shows {value}.", "Correct the family income or upload the right income certificate.", "income"))
        if doc.get("status") == "Rejected":
            issues.append(_issue("document_rejected", doc.get("reason") or "This document was rejected.", "Choose another file for this upload slot.", doc["slot"], severity="rejected"))
        if doc.get("status") == "Manual Review":
            issues.append(_issue("low_confidence", doc.get("reason") or "This document needs manual review.", "Upload a clearer file or ask a reviewer to verify this document.", doc["slot"], severity="review"))
        signature = (doc.get("fields") or {}).get("signature_or_seal", {}).get("value")
        if signature == "not detected":
            issues.append(_issue("missing_signature", f"No signature or seal was detected on the {EXPECTED_LABELS[doc['slot']].lower()}.", "Upload a signed/sealed copy or send this document for manual review.", doc["slot"], severity="review"))

    for field_key, label in (("name", "name"), ("date_of_birth", "date of birth")):
        values = [doc.get("fields", {}).get(field_key, {}).get("value") for doc in documents]
        values = [v for v in values if v]
        if len(values) > 1 and any(not _similar(values[0], value) for value in values[1:]):
            issues.append(_issue("cross_document_mismatch", f"The documents do not agree on the applicant {label}.", "Upload matching documents or send the application for manual review.", severity="review"))

    marksheet = slots.get("marksheet")
    income_doc = slots.get("income")
    if marksheet and not marksheet.get("fields", {}).get("marks_percentage", {}).get("value"):
        checks.append({"key": "marks", "label": "Marks cross-check", "status": "review", "detail": "Marks percentage was not readable."})
    else:
        checks.append({"key": "marks", "label": "Marks cross-check", "status": "pass", "detail": "Marks were compared with the form."})
    if income_doc and income_doc.get("fields", {}).get("issue_date", {}).get("value"):
        checks.append({"key": "freshness", "label": "Document freshness", "status": "pass", "detail": "Issue date was found; policy review is available to the reviewer."})

    rejected = any(issue["severity"] == "rejected" for issue in issues)
    review = any(issue["severity"] == "review" for issue in issues)
    status = "Rejected" if rejected else "Manual Review" if review else "Needs Correction" if issues else "Approved"
    base = min(100, int(len(documents) / 3 * 55 + sum((doc.get("confidence") or 0) for doc in documents) / 3 * 45))
    health = max(0, base - min(45, len(issues) * 8))
    return issues, checks, health, status
