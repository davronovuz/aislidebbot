"""Local storage and preview generation for ready works (DOCX/PDF)."""
from __future__ import annotations
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_ROOT = Path("/app/data/works")


def work_dir(work_id: int) -> Path:
    d = DATA_ROOT / str(work_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_file(work_id: int, file_bytes: bytes, ext: str) -> Path:
    d = work_dir(work_id)
    p = d / f"work.{ext.lower()}"
    p.write_bytes(file_bytes)
    return p


def _run(cmd: list[str], timeout: int = 180) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr


def generate_preview(work_id: int) -> str | None:
    """Make a first-page PNG preview. Works with DOCX, PDF or PPTX.
    Returns the preview filename or None on failure.
    """
    d = work_dir(work_id)

    # Find original file
    candidates = list(d.glob("work.*"))
    candidates = [p for p in candidates if p.suffix.lower() in (".docx", ".pdf", ".pptx", ".doc")]
    if not candidates:
        return None
    src = candidates[0]

    # Clean previous preview
    for old in d.glob("preview.png"):
        old.unlink()
    for old in d.glob("work.pdf"):
        if old != src:
            old.unlink()

    # Get a PDF: convert DOCX/PPTX → PDF if needed
    if src.suffix.lower() == ".pdf":
        pdf_path = src
    else:
        rc, _, err = _run(
            ["soffice", "--headless", "--convert-to", "pdf",
             "--outdir", str(d), str(src)],
            timeout=180,
        )
        if rc != 0:
            logger.error(f"soffice (work {work_id}) failed: {err}")
            return None
        pdf_path = d / "work.pdf"
        if not pdf_path.exists():
            return None

    # PDF page 1 → PNG
    rc, _, err = _run(
        ["pdftoppm", "-png", "-r", "120", "-f", "1", "-l", "1",
         str(pdf_path), str(d / "preview")],
        timeout=60,
    )
    if rc != 0:
        logger.error(f"pdftoppm (work {work_id}) failed: {err}")
        return None

    # pdftoppm produces preview-1.png — rename
    cand = d / "preview-1.png"
    target = d / "preview.png"
    if cand.exists():
        cand.rename(target)

    # Cleanup intermediate PDF if we created one
    if src.suffix.lower() != ".pdf" and pdf_path.exists():
        pdf_path.unlink(missing_ok=True)

    return target.name if target.exists() else None


def get_preview_path(work_id: int) -> Path | None:
    p = work_dir(work_id) / "preview.png"
    return p if p.exists() else None


def get_file_path(work_id: int) -> Path | None:
    d = work_dir(work_id)
    for ext in ("docx", "pdf", "pptx", "doc"):
        p = d / f"work.{ext}"
        if p.exists():
            return p
    return None


def delete_work_files(work_id: int) -> None:
    d = work_dir(work_id)
    if d.exists():
        shutil.rmtree(d)
