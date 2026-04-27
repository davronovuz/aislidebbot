"""Helper to download a Telegram file_id to local storage and generate previews.
Used by the bot's admin upload flow so works/templates uploaded via Telegram
get the same multi-page preview treatment as web admin uploads.
"""
from __future__ import annotations
import logging
import os
import subprocess
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)

WORKS_ROOT = Path("/app/data/works")
TEMPLATES_ROOT = Path("/app/data/templates")


def _ext_from_filename(fname: str) -> str:
    fname = (fname or "").lower()
    for ext in ("pptx", "docx", "pdf", "doc"):
        if fname.endswith("." + ext):
            return ext
    return "bin"


async def _download_file(bot, file_id: str, target: Path) -> bool:
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        await bot.download_file_by_id(file_id, str(target))
        return target.exists() and target.stat().st_size > 0
    except Exception as e:
        logger.error(f"Telegram download failed for {file_id}: {e}")
        return False


def _run(cmd: list[str], timeout: int = 240) -> int:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            logger.error(f"cmd failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stderr[:200]}")
        return proc.returncode
    except Exception as e:
        logger.error(f"cmd exception: {e}")
        return -1


def _generate_pages(work_dir: Path, src: Path, max_pages: int = 30) -> int:
    """PDF/DOCX/PPTX → page_1.png, page_2.png, ..."""
    # Clean previous
    for p in work_dir.glob("page_*.png"):
        p.unlink()
    for p in work_dir.glob("preview.png"):
        p.unlink()

    # Get PDF
    if src.suffix.lower() == ".pdf":
        pdf_path = src
        cleanup_pdf = False
    else:
        # Remove old work.pdf
        old = work_dir / "work.pdf"
        if old.exists() and old != src:
            old.unlink()
        rc = _run(["soffice", "--headless", "--convert-to", "pdf",
                   "--outdir", str(work_dir), str(src)], timeout=240)
        if rc != 0:
            return 0
        pdf_path = work_dir / "work.pdf"
        if not pdf_path.exists():
            return 0
        cleanup_pdf = True

    # PDF → pages
    rc = _run(["pdftoppm", "-png", "-r", "100",
               "-f", "1", "-l", str(max_pages),
               str(pdf_path), str(work_dir / "tmp")], timeout=180)
    if rc != 0:
        if cleanup_pdf:
            pdf_path.unlink(missing_ok=True)
        return 0

    pngs = sorted(work_dir.glob("tmp-*.png"),
                  key=lambda p: int(p.stem.split("-")[-1]))
    count = 0
    for i, p in enumerate(pngs, 1):
        p.rename(work_dir / f"page_{i}.png")
        count += 1

    # Legacy alias
    if count > 0:
        try:
            (work_dir / "preview.png").write_bytes((work_dir / "page_1.png").read_bytes())
        except Exception:
            pass

    if cleanup_pdf and pdf_path.exists():
        pdf_path.unlink(missing_ok=True)
    return count


async def download_to_local_and_make_preview(
    bot, work_id: int, file_id: str, orig_filename: str,
) -> Tuple[str | None, int]:
    """Download Telegram file → save to /app/data/works/{id}/work.{ext} →
    generate per-page previews.
    Returns (local_path, page_count) or (None, 0) on failure.
    """
    ext = _ext_from_filename(orig_filename)
    work_dir = WORKS_ROOT / str(work_id)
    work_dir.mkdir(parents=True, exist_ok=True)
    target = work_dir / f"work.{ext}"

    ok = await _download_file(bot, file_id, target)
    if not ok:
        return None, 0

    count = _generate_pages(work_dir, target)
    return str(target), count


async def download_template_to_local_and_make_preview(
    bot, template_id: int, file_id: str,
) -> Tuple[str | None, int]:
    """Same as above but for /app/data/templates/{id}/template.pptx."""
    tdir = TEMPLATES_ROOT / str(template_id)
    tdir.mkdir(parents=True, exist_ok=True)
    target = tdir / "template.pptx"
    ok = await _download_file(bot, file_id, target)
    if not ok:
        return None, 0
    count = _generate_pages(tdir, target)
    # Rename page_*.png → slide_*.png to match templates convention
    for i in range(1, count + 1):
        src = tdir / f"page_{i}.png"
        dst = tdir / f"slide_{i}.png"
        if src.exists():
            src.rename(dst)
    # Cleanup legacy preview.png (templates use slide_1.png)
    return str(target), count
