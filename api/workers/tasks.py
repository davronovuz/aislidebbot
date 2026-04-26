"""
Dramatiq task definitions.
Each task pulls data from DB, processes, updates status, notifies user.
"""
import asyncio
import json
import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone

import dramatiq
from sqlalchemy import select, update

from api.workers.broker import broker  # noqa — must be imported before dramatiq.actor
from api.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _run(coro):
    """Run async code from sync Dramatiq task."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# ─── Sync DB helpers (psycopg2) for worker process ───────────────────────────

def _get_pg_conn():
    import psycopg2
    import psycopg2.extras
    return psycopg2.connect(settings.database_url_sync, cursor_factory=psycopg2.extras.RealDictCursor)


def _get_task(task_uuid: str) -> dict | None:
    with _get_pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pt.*, u.telegram_id FROM presentation_tasks pt "
                "JOIN users u ON u.id = pt.user_id "
                "WHERE pt.task_uuid = %s",
                (task_uuid,)
            )
            return cur.fetchone()


def _update_task_status(task_uuid: str, status: str, progress: int = 0,
                        error: str | None = None, file_id: str | None = None,
                        r2_key: str | None = None):
    with _get_pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE presentation_tasks SET
                    status=%s, progress=%s, error_message=%s,
                    result_file_id=%s, result_r2_key=%s,
                    started_at=CASE WHEN started_at IS NULL THEN NOW() ELSE started_at END,
                    completed_at=CASE WHEN %s IN ('completed','failed') THEN NOW() ELSE NULL END
                WHERE task_uuid=%s""",
                (status, progress, error, file_id, r2_key, status, task_uuid)
            )
        conn.commit()


def _refund_user(telegram_id: int, amount: float):
    if amount <= 0:
        return
    with _get_pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET balance = balance + %s WHERE telegram_id = %s",
                (amount, telegram_id)
            )
        conn.commit()


def _get_pricing(service_type: str, default: float = 500.0) -> float:
    with _get_pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT price FROM pricing WHERE service_type=%s AND is_active=TRUE", (service_type,))
            row = cur.fetchone()
            return float(row["price"]) if row else default


# ─── Presentation task ────────────────────────────────────────────────────────

@dramatiq.actor(queue_name="presentations", max_retries=2, time_limit=600_000)
def process_presentation_task(task_uuid: str):
    logger.info(f"[Worker] Starting task {task_uuid}")

    task = _get_task(task_uuid)
    if not task:
        logger.error(f"[Worker] Task {task_uuid} not found in DB")
        return

    telegram_id = task["telegram_id"]
    amount_charged = float(task.get("amount_charged") or 0)

    try:
        _update_task_status(task_uuid, "processing", 10)
        content_data = json.loads(task["answers"] or "{}")
        presentation_type = task["presentation_type"]

        if presentation_type == "course_work":
            _process_course_work(task_uuid, telegram_id, content_data, amount_charged)
        else:
            _process_presentation(task_uuid, telegram_id, content_data, amount_charged)

    except Exception as e:
        logger.error(f"[Worker] Task {task_uuid} failed: {e}", exc_info=True)
        _update_task_status(task_uuid, "failed", 0, error=str(e))
        _refund_user(telegram_id, amount_charged)
        _run(_notify_failure(telegram_id, str(e)))


def _process_presentation(task_uuid: str, telegram_id: int, data: dict, amount_charged: float):
    topic = data.get("topic", "Mavzusiz")
    slide_count = int(data.get("slide_count", 10))
    theme_id = data.get("theme_id", "chisel")
    language = data.get("language", "uz")
    details = data.get("details", "")

    # Content generation
    if data.get("pre_generated") and data.get("slides"):
        content = {
            "title": data.get("title", topic),
            "subtitle": data.get("subtitle", ""),
            "slides": data["slides"],
        }
        logger.info(f"[Worker] Using pre-generated content for {task_uuid}")
    else:
        _update_task_status(task_uuid, "processing", 25)
        content = _run(_generate_presentation_content(topic, details, slide_count, language))
        logger.info(f"[Worker] Content generated for {task_uuid}")

    _update_task_status(task_uuid, "processing", 60)

    # PPTX generation
    pptx_bytes = _generate_pptx(content, theme_id, slide_count)
    _update_task_status(task_uuid, "processing", 85)

    # Store to R2
    r2_key = None
    from api.services import storage
    r2_key = storage.upload_bytes(
        pptx_bytes,
        f"presentations/{task_uuid}.pptx",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )

    # Deliver to Telegram
    filename = f"{topic[:30]}.pptx"
    new_balance = _get_user_balance(telegram_id)
    caption = (
        f"✅ <b>Prezentatsiya tayyor!</b>\n\n"
        f"📊 Mavzu: {topic}\n📑 Slaydlar: {slide_count} ta\n"
        f"💳 Balans: {new_balance:,.0f} so'm"
    )
    file_id = _run(
        _send_pptx_to_telegram(telegram_id, pptx_bytes, filename, caption)
    )

    _update_task_status(task_uuid, "completed", 100, file_id=file_id, r2_key=r2_key)
    logger.info(f"[Worker] Task {task_uuid} completed ✓")


def _process_course_work(task_uuid: str, telegram_id: int, data: dict, amount_charged: float):
    from utils.course_work_generator import CourseWorkGenerator
    from utils.docx_generator import DocxGenerator

    work_type = data.get("work_type", "mustaqil_ish")
    work_name = data.get("work_name", "Mustaqil ish")
    topic = data.get("topic", "Mavzusiz")
    page_count = int(data.get("page_count", 10))

    _update_task_status(task_uuid, "processing", 20)

    generator = CourseWorkGenerator(settings.openai_api_key)
    content = _run(generator.generate(data))
    _update_task_status(task_uuid, "processing", 60)

    docx_gen = DocxGenerator()
    file_format = data.get("file_format", "docx")
    file_bytes, ext = docx_gen.generate(content, data, file_format)
    _update_task_status(task_uuid, "processing", 85)

    # R2 storage
    from api.services import storage
    r2_key = storage.upload_bytes(
        file_bytes,
        f"documents/{task_uuid}.{ext}",
    )

    filename = f"{topic[:30]}.{ext}"
    new_balance = _get_user_balance(telegram_id)
    caption = (
        f"✅ <b>{work_name} tayyor!</b>\n\n"
        f"📚 Mavzu: {topic}\n📄 Sahifalar: {page_count} ta\n"
        f"💳 Balans: {new_balance:,.0f} so'm"
    )
    file_id = _run(
        _send_pptx_to_telegram(telegram_id, file_bytes, filename, caption)
    )

    _update_task_status(task_uuid, "completed", 100, file_id=file_id, r2_key=r2_key)
    logger.info(f"[Worker] Course work task {task_uuid} completed ✓")


def _get_user_balance(telegram_id: int) -> float:
    with _get_pg_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT balance FROM users WHERE telegram_id=%s", (telegram_id,))
            row = cur.fetchone()
            return float(row["balance"]) if row else 0.0


async def _generate_presentation_content(
    topic: str, details: str, slide_count: int, language: str
) -> dict:
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from utils.content_generator import ContentGenerator
    gen = ContentGenerator(settings.openai_api_key)
    return await gen.generate_presentation_content(topic, details, slide_count, language=language)


async def _generate_pptx_async(content: dict, theme_id: str) -> bytes:
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from utils.pptx_generator import ProPPTXGenerator

    gen = ProPPTXGenerator(theme_id=theme_id)
    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
        tmp_path = f.name

    try:
        await gen.generate(content, tmp_path)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _generate_pptx(content: dict, theme_id: str, slide_count: int) -> bytes:
    return _run(_generate_pptx_async(content, theme_id))


async def _send_pptx_to_telegram(
    telegram_id: int, file_bytes: bytes, filename: str, caption: str
) -> str | None:
    from api.services.notification import send_file_bytes
    return await send_file_bytes(telegram_id, file_bytes, filename, caption)


async def _notify_failure(telegram_id: int, error: str):
    from api.services.notification import send_message
    await send_message(
        telegram_id,
        f"❌ <b>Xatolik yuz berdi!</b>\n\nIltimos, qayta urinib ko'ring.\n"
        f"Pul balansingizga qaytarildi.\n\nXato: {error[:200]}"
    )
