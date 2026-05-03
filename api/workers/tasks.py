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

    # IDEMPOTENCY — agar task allaqachon bajarilgan yoki boshqa worker
    # tomonidan oxirgi 60 sekund ichida olingan bo'lsa, takror ishlamaymiz
    status = task.get("status")
    if status == "completed":
        logger.info(f"[Worker] Task {task_uuid} allaqachon completed — skip")
        return
    if status == "failed":
        logger.info(f"[Worker] Task {task_uuid} allaqachon failed — skip")
        return
    if status == "processing":
        # Boshqa worker hozir ishlayotgan bo'lishi mumkin.
        # started_at oxirgi 60s ichida bo'lsa — duplicate; eski bo'lsa — abandoned, davom etamiz
        from datetime import datetime, timezone, timedelta
        started_at = task.get("started_at")
        if started_at:
            now = datetime.now(timezone.utc)
            if isinstance(started_at, datetime):
                if (now - started_at) < timedelta(seconds=60):
                    logger.warning(
                        f"[Worker] Task {task_uuid} hozir boshqa worker'da "
                        f"ishlayapti (started_at={started_at}) — duplicate, skip"
                    )
                    return
                logger.info(
                    f"[Worker] Task {task_uuid} eski processing'da "
                    f"(started_at={started_at}) — abandoned, davom etamiz"
                )

    telegram_id = task["telegram_id"]
    amount_charged = float(task.get("amount_charged") or 0)

    try:
        _update_task_status(task_uuid, "processing", 10)
        content_data = json.loads(task["answers"] or "{}")
        presentation_type = task["presentation_type"]
        work_type = (content_data.get("work_type") or "").lower()

        # Maxsus oqimlar (work_type bo'yicha aniqlanadi)
        if work_type == "tezis":
            _process_tezis(task_uuid, telegram_id, content_data, amount_charged)
        elif work_type == "krossvord":
            _process_krossvord(task_uuid, telegram_id, content_data, amount_charged)
        elif presentation_type == "course_work":
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

    eta_str = f"{max(1, slide_count // 5)}-{max(2, slide_count // 3)} daqiqa"

    progress_msg_id = _run(_send_progress_msg(
        telegram_id,
        _progress_text("Prezentatsiya", 5, f"Mavzu: <b>{topic[:60]}</b>\n📑 {slide_count} slayd", eta_str),
    ))

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
        if progress_msg_id:
            _run(_edit_progress_msg(telegram_id, progress_msg_id,
                _progress_text("Prezentatsiya", 25, "Slayd matnlari yaratilmoqda...", eta_str)))
        content = _run(_generate_presentation_content(topic, details, slide_count, language))
        logger.info(f"[Worker] Content generated for {task_uuid}")

    _update_task_status(task_uuid, "processing", 60)
    if progress_msg_id:
        _run(_edit_progress_msg(telegram_id, progress_msg_id,
            _progress_text("Prezentatsiya", 60, "Rasmlar va dizayn tayyorlanmoqda...", eta_str)))

    # PPTX generation
    pptx_bytes = _generate_pptx(content, theme_id, slide_count)
    _update_task_status(task_uuid, "processing", 85)
    if progress_msg_id:
        _run(_edit_progress_msg(telegram_id, progress_msg_id,
            _progress_text("Prezentatsiya", 95, "Telegram'ga yuborilmoqda...", "")))

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

    if progress_msg_id:
        _run(_delete_progress_msg(telegram_id, progress_msg_id))

    _update_task_status(task_uuid, "completed", 100, file_id=file_id, r2_key=r2_key)
    logger.info(f"[Worker] Task {task_uuid} completed ✓")


def _process_course_work(task_uuid: str, telegram_id: int, data: dict, amount_charged: float):
    import tempfile, os, subprocess
    from utils.course_work_generator import CourseWorkGenerator
    from utils.docx_generator import DocxGenerator

    work_type = data.get("work_type", "mustaqil_ish")
    work_name = data.get("work_name", "Mustaqil ish")
    topic = data.get("topic", "Mavzusiz")
    subject = data.get("subject", data.get("subject_name", topic.split()[0] if topic.split() else "Umumiy"))
    details = data.get("details", "")
    page_count = int(data.get("page_count", 10))
    language = data.get("language", "uz")
    file_format = data.get("file_format", "docx")

    # Hujjat hajmi bo'yicha taxminiy vaqt
    eta_minutes = max(2, round(page_count * 0.25))  # ~15s/sahifa
    eta_str = f"{eta_minutes}-{eta_minutes + 2} daqiqa"

    # Boshlang'ich progress message
    progress_msg_id = _run(_send_progress_msg(
        telegram_id,
        _progress_text(work_name, 5, f"Mavzu: <b>{topic[:60]}</b>\n📑 {page_count} sahifa", eta_str),
    ))

    _update_task_status(task_uuid, "processing", 20)
    if progress_msg_id:
        _run(_edit_progress_msg(telegram_id, progress_msg_id,
            _progress_text(work_name, 20, "Reja (outline) tuzilmoqda...", eta_str)))

    generator = CourseWorkGenerator(settings.openai_api_key)

    # Progress callback — har bir bo'lim tugaganda chaqiriladi
    total_steps = max(1, page_count // 2)  # taxminiy bo'limlar soni
    step_counter = {"done": 0}

    async def on_step(step_name: str):
        step_counter["done"] += 1
        # 20%–80% oraliqda taqsim qilamiz
        pct = min(80, 20 + int(60 * step_counter["done"] / max(total_steps, 1)))
        if progress_msg_id:
            await _edit_progress_msg(telegram_id, progress_msg_id,
                _progress_text(work_name, pct, step_name, eta_str))

    # CourseWorkGenerator progress_callback ni qo'llab-quvvatlasa, uzatiladi
    try:
        content = _run(generator.generate_course_work_content(
            work_type=work_type,
            topic=topic,
            subject=subject,
            details=details,
            page_count=page_count,
            language=language,
            progress_callback=on_step,
        ))
    except TypeError:
        # Eski signature — callback ishlatilmaydi
        content = _run(generator.generate_course_work_content(
            work_type=work_type,
            topic=topic,
            subject=subject,
            details=details,
            page_count=page_count,
            language=language,
        ))

    if not content:
        raise Exception("Content yaratilmadi")
    _update_task_status(task_uuid, "processing", 60)
    if progress_msg_id:
        _run(_edit_progress_msg(telegram_id, progress_msg_id,
            _progress_text(work_name, 80, "Matn tayyor. DOCX hujjat yaratilmoqda...", eta_str)))

    docx_gen = DocxGenerator()

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        docx_path = f.name

    try:
        ok = docx_gen.create_course_work(content, docx_path, work_type)
        if not ok:
            raise Exception("DOCX yaratilmadi")

        if file_format == "pdf":
            pdf_path = docx_path.replace(".docx", ".pdf")
            try:
                subprocess.run(
                    ["soffice", "--headless", "--convert-to", "pdf", "--outdir",
                     os.path.dirname(docx_path), docx_path],
                    timeout=60, check=True, capture_output=True
                )
                with open(pdf_path, "rb") as f:
                    file_bytes = f.read()
                ext = "pdf"
            except Exception:
                with open(docx_path, "rb") as f:
                    file_bytes = f.read()
                ext = "docx"
            finally:
                if os.path.exists(pdf_path):
                    os.unlink(pdf_path)
        else:
            with open(docx_path, "rb") as f:
                file_bytes = f.read()
            ext = "docx"
    finally:
        if os.path.exists(docx_path):
            os.unlink(docx_path)

    _update_task_status(task_uuid, "processing", 85)
    if progress_msg_id:
        _run(_edit_progress_msg(telegram_id, progress_msg_id,
            _progress_text(work_name, 95, "Telegram'ga yuborilmoqda...", "")))

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

    # Progress xabarini o'chirish (foydalanuvchi faqat yakuniy faylni ko'rsin)
    if progress_msg_id:
        _run(_delete_progress_msg(telegram_id, progress_msg_id))

    _update_task_status(task_uuid, "completed", 100, file_id=file_id, r2_key=r2_key)
    logger.info(f"[Worker] Course work task {task_uuid} completed ✓")


# ─── TEZIS ────────────────────────────────────────────────────────────────

def _process_tezis(task_uuid: str, telegram_id: int, data: dict, amount_charged: float):
    """Konferensiya tezisi (1-2 bet, 1.0 spacing, ramkasiz)."""
    import tempfile, os
    from utils.thesis_generator import ThesisGenerator

    topic = data.get("topic", "Mavzusiz")
    subject = data.get("subject_name") or data.get("subject", "")
    language = data.get("language", "uz")
    details = data.get("details", "")

    student_name = data.get("student_name", "")
    teacher_name = data.get("teacher_name", "")
    teacher_rank = data.get("teacher_rank", "")
    institution = data.get("university", "")
    email = data.get("email", "")  # ixtiyoriy

    progress_msg_id = _run(_send_progress_msg(
        telegram_id,
        _progress_text("Tezis", 5, f"Mavzu: <b>{topic[:60]}</b>", "1-2 daqiqa"),
    ))

    _update_task_status(task_uuid, "processing", 25)
    if progress_msg_id:
        _run(_edit_progress_msg(telegram_id, progress_msg_id,
            _progress_text("Tezis", 25, "AI matn yozmoqda...", "1-2 daqiqa")))

    # AI'ga tezis matnini yozdiramiz (qisqa, IMRaD)
    content_data = _run(_generate_tezis_content(topic, subject, details, language))

    _update_task_status(task_uuid, "processing", 70)
    if progress_msg_id:
        _run(_edit_progress_msg(telegram_id, progress_msg_id,
            _progress_text("Tezis", 80, "DOCX hujjat yaratilmoqda...", "")))

    # Authors blokini to'ldiramiz
    authors = []
    if student_name or teacher_name:
        author_entry = {
            'name': student_name or teacher_name,
            'rank': teacher_rank,
            'institution': institution,
            'city': "Toshkent",
            'country': "O'zbekiston",
        }
        authors.append({k: v for k, v in author_entry.items() if v})

    thesis_doc_content = {
        'title': content_data.get('title', topic),
        'authors': authors,
        'email': email,
        'keywords': content_data.get('keywords', []),
        'body': content_data.get('body', ''),
        'references': content_data.get('references', []),
    }

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        path = f.name
    try:
        ok = ThesisGenerator().create_thesis(thesis_doc_content, path)
        if not ok:
            raise Exception("Tezis DOCX yaratilmadi")
        with open(path, "rb") as f:
            file_bytes = f.read()
    finally:
        if os.path.exists(path):
            os.unlink(path)

    _update_task_status(task_uuid, "processing", 90)

    from api.services import storage
    r2_key = storage.upload_bytes(file_bytes, f"documents/{task_uuid}.docx")

    new_balance = _get_user_balance(telegram_id)
    caption = (
        f"✅ <b>Tezis tayyor!</b>\n\n"
        f"📋 Mavzu: {topic}\n"
        f"💳 Balans: {new_balance:,.0f} so'm"
    )
    file_id = _run(_send_pptx_to_telegram(telegram_id, file_bytes, f"{topic[:30]}.docx", caption))

    if progress_msg_id:
        _run(_delete_progress_msg(telegram_id, progress_msg_id))

    _update_task_status(task_uuid, "completed", 100, file_id=file_id, r2_key=r2_key)
    logger.info(f"[Worker] Tezis task {task_uuid} completed ✓")


async def _generate_tezis_content(topic: str, subject: str, details: str, language: str) -> dict:
    """OpenAI orqali tezis matnini yozish (qisqa, IMRaD format).
    Agar JSON parse xato bo'lsa yoki bo'limlar yetishmasa, sodda fallback."""
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    lang_label = {'uz': "O'zbek tilida", 'ru': "На русском", 'en': "In English"}.get(language, "O'zbek tilida")
    subject_part = f"\nFan: {subject}" if subject else ""
    details_part = f"\nQo'shimcha: {details}" if details else ""

    prompt = f"""Sen ilmiy konferensiya tezisi yozish bo'yicha mutaxassissan.

Mavzu: {topic}{subject_part}{details_part}
Til: {lang_label}

TEZIS TALABLARI:
- Hajmi: 700-1200 so'z (1-2 bet)
- IMRaD struktura: muammo qo'yilishi -> mavjud yondashuvlar -> muallif fikri -> xulosa
- Aniq, sodda, ilmiy uslub
- Adabiyotlar matnda [1], [2] ko'rinishida iqtibos qilinadi
- Kalit so'zlar: 5-7 ta

Faqat JSON qaytar:
{{
  "title": "Tezis nomi (BOSH HARFLAR shart emas, generator UPPER qiladi)",
  "keywords": ["soz1", "soz2", "soz3", "soz4", "soz5"],
  "body": "Asosiy matn... Bir necha paragraf, paragraflar orasi BO'SH QATOR bilan ajratilgan. Iqtiboslar [1], [2] ko'rinishida.",
  "references": [
    "Familiya I.O. Asar nomi. — Toshkent: Nashriyot, 2024. — 250 b.",
    "Author A.B. Article title // Journal Name. — 2023. — Vol. 15, No. 3. — P. 45-52."
  ]
}}"""

    try:
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        data = json.loads(resp.choices[0].message.content)
    except Exception as e:
        logger.error(f"Tezis AI/JSON xato: {e}")
        data = {}

    # Fallback — qiymat bo'lmasa, default
    body = (data.get("body") or "").strip()
    if not body or len(body) < 200:
        # Fallback minimal tezis matn
        body = (
            f"{topic} mavzusi hozirgi kunda dolzarb masalalardan biri hisoblanadi. "
            f"Ushbu yo'nalishda olib borilgan tadqiqotlar muhim natijalar bermoqda [1].\n\n"
            f"Mavjud yondashuvlar tahlili shuni ko'rsatadiki, mavzu turli aspektlardan "
            f"o'rganilgan, ammo ko'plab masalalar hali ham muhokama talab qiladi.\n\n"
            f"Ushbu tezisda muammoning yangi yondashuvlari taklif qilinadi va ularning "
            f"amaliy ahamiyati muhokama qilinadi [2].\n\n"
            f"Xulosa qilib aytganda, {topic.lower()} bo'yicha keyingi tadqiqotlar zarur "
            f"va tavsiya etiladi."
        )

    return {
        "title": data.get("title") or topic,
        "keywords": data.get("keywords") or [topic.split()[0] if topic.split() else "tadqiqot"],
        "body": body,
        "references": data.get("references") or [
            f"Karimov A.B. Zamonaviy tadqiqotlar. — Toshkent: Fan, 2024. — 200 b.",
            f"Smith J. Modern Approaches // Research Journal. — 2023. — Vol. 12. — P. 15-28.",
        ],
    }


# ─── KROSSVORD ────────────────────────────────────────────────────────────

def _process_krossvord(task_uuid: str, telegram_id: int, data: dict, amount_charged: float):
    """Krossvord — AI dan so'z+ta'rif olib, grid'ga joylab DOCX chiqaradi."""
    import tempfile, os
    from utils.crossword_generator import generate_crossword

    topic = data.get("topic", "Mavzusiz")
    language = data.get("language", "uz")
    word_count = int(data.get("word_count") or data.get("page_count") or 18)
    word_count = max(10, min(30, word_count))

    progress_msg_id = _run(_send_progress_msg(
        telegram_id,
        _progress_text("Krossvord", 5, f"Mavzu: <b>{topic[:60]}</b>\n🔤 ~{word_count} ta so'z", "1-2 daqiqa"),
    ))

    _update_task_status(task_uuid, "processing", 30)
    if progress_msg_id:
        _run(_edit_progress_msg(telegram_id, progress_msg_id,
            _progress_text("Krossvord", 30, "AI so'z va savollar tayyorlamoqda...", "1-2 daqiqa")))

    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        path = f.name
    try:
        ok = _run(generate_crossword(topic, settings.openai_api_key, path, word_count, language))
        if not ok:
            raise Exception("Krossvord yaratilmadi (so'zlarni joylashtirib bo'lmadi)")

        if progress_msg_id:
            _run(_edit_progress_msg(telegram_id, progress_msg_id,
                _progress_text("Krossvord", 90, "DOCX hujjat tayyorlanmoqda...", "")))

        with open(path, "rb") as f:
            file_bytes = f.read()
    finally:
        if os.path.exists(path):
            os.unlink(path)

    from api.services import storage
    r2_key = storage.upload_bytes(file_bytes, f"documents/{task_uuid}.docx")

    new_balance = _get_user_balance(telegram_id)
    caption = (
        f"✅ <b>Krossvord tayyor!</b>\n\n"
        f"🔤 Mavzu: {topic}\n"
        f"📋 1-bet: krossvord\n"
        f"📋 2-bet: savollar\n"
        f"📋 3-bet: javoblar\n"
        f"💳 Balans: {new_balance:,.0f} so'm"
    )
    file_id = _run(_send_pptx_to_telegram(telegram_id, file_bytes, f"krossvord_{topic[:25]}.docx", caption))

    if progress_msg_id:
        _run(_delete_progress_msg(telegram_id, progress_msg_id))

    _update_task_status(task_uuid, "completed", 100, file_id=file_id, r2_key=r2_key)
    logger.info(f"[Worker] Krossvord task {task_uuid} completed ✓")


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


async def _send_progress_msg(telegram_id: int, text: str) -> int | None:
    from api.services.notification import send_message_id
    return await send_message_id(telegram_id, text)


async def _edit_progress_msg(telegram_id: int, message_id: int, text: str) -> bool:
    from api.services.notification import edit_message
    return await edit_message(telegram_id, message_id, text)


async def _delete_progress_msg(telegram_id: int, message_id: int) -> bool:
    from api.services.notification import delete_message
    return await delete_message(telegram_id, message_id)


def _progress_text(work_name: str, percent: int, current_step: str, eta: str = "") -> str:
    """Chiroyli progress message (HTML)."""
    bars = int(percent / 5)  # 0..20 bloka
    bar = "█" * bars + "░" * (20 - bars)
    eta_line = f"\n⏱ <i>Taxminiy: {eta}</i>" if eta else ""
    return (
        f"⚙️ <b>{work_name} yaratilmoqda</b>\n\n"
        f"<code>{bar}</code> {percent}%\n\n"
        f"📍 {current_step}{eta_line}"
    )
