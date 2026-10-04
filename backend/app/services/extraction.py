from __future__ import annotations

import io
import shutil
import subprocess
import tempfile
from pathlib import Path

from pypdf import PdfReader


async def extract_text(filename: str, mime_type: str, data: bytes) -> tuple[str, str]:
    suffix = Path(filename).suffix.lower()
    if mime_type == "application/pdf" or suffix == ".pdf":
        try:
            reader = PdfReader(io.BytesIO(data))
            pages = [(page.extract_text() or "") for page in reader.pages]
            text = "\n".join(pages).strip()
            if text:
                return text, "pdf-text"
            return "", "pdf-scanned"
        except Exception as exc:
            return "", f"pdf-error:{type(exc).__name__}"

    if shutil.which("tesseract"):
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / suffix.lstrip(".")
            image_path.write_bytes(data)
            try:
                result = subprocess.run(
                    ["tesseract", str(image_path), "stdout", "--psm", "6"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip(), "tesseract-ocr"
            except (OSError, subprocess.TimeoutExpired):
                pass
    return "", "image-no-text"
