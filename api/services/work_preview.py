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


def generate_preview(work_id: int, max_pages: int = 30) -> int:
    """Generate per-page PNG previews. Works with DOCX, PDF or PPTX.
    Returns the number of preview pages generated (0 on failure).
    Files saved as page_1.png, page_2.png, ... in the work dir.
    Also keeps preview.png as alias of page_1.png for legacy callers.
    """
    d = work_dir(work_id)

    candidates = list(d.glob("work.*"))
    candidates = [p for p in candidates if p.suffix.lower() in (".docx", ".pdf", ".pptx", ".doc")]
    if not candidates:
        return 0
    src = candidates[0]

    # Clean previous previews
    for old in d.glob("page_*.png"):
        old.unlink()
    for old in d.glob("preview.png"):
        old.unlink()

    # Get a PDF: convert DOCX/PPTX → PDF if needed
    if src.suffix.lower() == ".pdf":
        pdf_path = src
        cleanup_pdf = False
    else:
        # Remove any leftover work.pdf
        existing_pdf = d / "work.pdf"
        if existing_pdf.exists() and existing_pdf != src:
            existing_pdf.unlink()
        rc, _, err = _run(
            ["soffice", "--headless", "--convert-to", "pdf",
             "--outdir", str(d), str(src)],
            timeout=240,
        )
        if rc != 0:
            logger.error(f"soffice (work {work_id}) failed: {err}")
            return 0
        pdf_path = d / "work.pdf"
        if not pdf_path.exists():
            return 0
        cleanup_pdf = True

    # PDF → all pages as PNGs (cap at max_pages)
    rc, _, err = _run(
        ["pdftoppm", "-png", "-r", "100",
         "-f", "1", "-l", str(max_pages),
         str(pdf_path), str(d / "tmp")],
        timeout=180,
    )
    if rc != 0:
        logger.error(f"pdftoppm (work {work_id}) failed: {err}")
        if cleanup_pdf:
            pdf_path.unlink(missing_ok=True)
        return 0

    # pdftoppm produces tmp-1.png, tmp-2.png — rename to page_N.png
    pngs = sorted(d.glob("tmp-*.png"),
                  key=lambda p: int(p.stem.split("-")[-1]))
    count = 0
    for i, p in enumerate(pngs, 1):
        target = d / f"page_{i}.png"
        p.rename(target)
        count += 1

    # Legacy preview.png alias for backward compat
    if count > 0:
        try:
            (d / "preview.png").write_bytes((d / "page_1.png").read_bytes())
        except Exception:
            pass

    if cleanup_pdf and pdf_path.exists():
        pdf_path.unlink(missing_ok=True)

    return count


def get_preview_path(work_id: int) -> Path | None:
    """Legacy: return first page preview."""
    return get_page_path(work_id, 1)


def get_page_path(work_id: int, page_num: int) -> Path | None:
    d = work_dir(work_id)
    p = d / f"page_{page_num}.png"
    if p.exists():
        return p
    if page_num == 1:
        leg = d / "preview.png"
        if leg.exists():
            return leg
    return None


def list_page_files(work_id: int) -> list[str]:
    d = work_dir(work_id)
    return sorted(
        [p.name for p in d.glob("page_*.png")],
        key=lambda n: int(n.replace("page_", "").replace(".png", "")),
    )


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
