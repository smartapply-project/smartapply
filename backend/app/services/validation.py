from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass


ALLOWED_MIME = {"application/pdf", "image/jpeg", "image/png"}
ALLOWED_EXT = {".pdf", ".jpg", ".jpeg", ".png"}
SLOT_LABELS = {"id": "ID proof", "marksheet": "Marksheet", "income": "Income certificate"}


@dataclass
class ValidationResult:
    ok: bool
    reason: str | None
    sha256: str


def validate_file(filename: str, content_type: str, data: bytes) -> ValidationResult:
    max_bytes = int(float(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024)
    digest = hashlib.sha256(data).hexdigest()
    suffix = os.path.splitext(filename.lower())[1]
    if suffix not in ALLOWED_EXT or content_type not in ALLOWED_MIME:
        return ValidationResult(False, "Unsupported file type. Upload a PDF, JPG, or PNG document.", digest)
    if not data:
        return ValidationResult(False, "This file is empty and cannot be analyzed.", digest)
    if len(data) > max_bytes:
        return ValidationResult(False, f"This file is larger than the {max_bytes // (1024 * 1024)} MB limit.", digest)
    if suffix == ".pdf" and not data.startswith(b"%PDF"):
        return ValidationResult(False, "This file is not a readable PDF. Choose the original document or export it again.", digest)
    if suffix in {".jpg", ".jpeg"} and not data.startswith(b"\xff\xd8\xff"):
        return ValidationResult(False, "This file is not a readable JPEG image.", digest)
    if suffix == ".png" and not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ValidationResult(False, "This file is not a readable PNG image.", digest)
    return ValidationResult(True, None, digest)
