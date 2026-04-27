import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.database import create_all_tables
from api.routers import auth, users, tasks, marketplace, admin, content

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 API starting up...")
    await create_all_tables()
    await _seed_pricing()
    logger.info("✅ API ready")
    yield
    logger.info("⏹ API shutting down")


async def _seed_pricing():
    """Insert default pricing rows if table is empty."""
    from api.database import AsyncSessionLocal
    from api.models.user import Pricing
    from sqlalchemy import select, insert

    defaults = [
        ("slide_basic", 1000.0, "Oddiy slayd (1 ta)"),
        ("slide_pro", 2000.0, "Professional slayd (1 ta)"),
        ("page_basic", 500.0, "Mustaqil ish (1 sahifa)"),
    ]
    async with AsyncSessionLocal() as db:
        for service_type, price, desc in defaults:
            existing = await db.execute(
                select(Pricing).where(Pricing.service_type == service_type)
            )
            if existing.scalar_one_or_none() is None:
                db.add(Pricing(service_type=service_type, price=price, description=desc))
        await db.commit()


app = FastAPI(
    title="AISlidEbot API",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ─── Legacy compatibility shims (old aiohttp API paths) ───────────────────────
# Frontend calls /api/submit-presentation, /api/task-status, etc.
# These are proxied through Next.js; bot also calls them directly.

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(marketplace.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(content.router, prefix="/api/v1")


# ─── Legacy flat routes (keep backward compat with current Next.js proxies) ───

@app.post("/api/submit-presentation")
async def legacy_submit(request: Request):
    from api.routers.tasks import submit_task, SubmitRequest
    from api.database import AsyncSessionLocal
    from api.deps import require_api_secret
    auth_header = request.headers.get("Authorization", "")
    from api.services.auth import verify_api_secret
    if not verify_api_secret(auth_header):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    body = await request.json()
    async with AsyncSessionLocal() as db:
        try:
            result = await submit_task(SubmitRequest(**body), None, db)
            return JSONResponse({"ok": True, "task_uuid": result.task_uuid,
                                 "amount_charged": result.amount_charged, "is_free": result.is_free})
        except Exception as e:
            status_code = 402 if "insufficient_balance" in str(e) else 500
            return JSONResponse(status_code=status_code, content={"error": str(e)})


@app.get("/api/task-status/{uuid}")
async def legacy_task_status(uuid: str, request: Request):
    from api.routers.tasks import get_task_status
    from api.database import AsyncSessionLocal
    from api.services.auth import verify_api_secret
    if not verify_api_secret(request.headers.get("Authorization", "")):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    async with AsyncSessionLocal() as db:
        try:
            r = await get_task_status(uuid, None, db)
            return JSONResponse({"ok": True, "task_uuid": r.task_uuid, "status": r.status,
                                 "progress": r.progress, "presentation_type": r.presentation_type})
        except Exception as e:
            return JSONResponse(status_code=404, content={"error": str(e)})


@app.get("/api/user-info")
async def legacy_user_info(telegram_id: int, request: Request):
    from api.routers.users import get_user_info_by_id
    from api.database import AsyncSessionLocal
    from api.services.auth import verify_api_secret
    if not verify_api_secret(request.headers.get("Authorization", "")):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    async with AsyncSessionLocal() as db:
        try:
            r = await get_user_info_by_id(telegram_id, None, db)
            return JSONResponse({"ok": True, **r.model_dump()})
        except Exception as e:
            return JSONResponse(status_code=404, content={"error": str(e)})


@app.post("/api/resend-task")
async def legacy_resend_task(request: Request):
    """Re-send a completed task's file to the user via Telegram by file_id."""
    from api.database import AsyncSessionLocal
    from api.services.auth import verify_api_secret
    from api.services.notification import send_document
    from api.models.task import PresentationTask
    from api.models.user import User
    from sqlalchemy import select
    if not verify_api_secret(request.headers.get("Authorization", "")):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    body = await request.json()
    task_uuid = body.get("task_uuid")
    telegram_id = body.get("telegram_id")
    if not task_uuid or not telegram_id:
        return JSONResponse(status_code=400, content={"error": "task_uuid and telegram_id required"})
    async with AsyncSessionLocal() as db:
        u = (await db.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
        if not u:
            return JSONResponse(status_code=404, content={"error": "User not found"})
        t = (await db.execute(
            select(PresentationTask).where(
                PresentationTask.task_uuid == task_uuid,
                PresentationTask.user_id == u.id,
            )
        )).scalar_one_or_none()
        if not t or not t.result_file_id:
            return JSONResponse(status_code=404, content={"error": "File not found"})
        ok = await send_document(telegram_id, t.result_file_id, "📎 Sizning faylingiz")
        return JSONResponse({"ok": bool(ok)})


@app.get("/api/user-tasks")
async def legacy_user_tasks(telegram_id: int, request: Request, limit: int = 20):
    from api.database import AsyncSessionLocal
    from api.services.auth import verify_api_secret
    from api.models.task import PresentationTask
    from api.models.user import User
    from sqlalchemy import select, desc
    if not verify_api_secret(request.headers.get("Authorization", "")):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    async with AsyncSessionLocal() as db:
        u = (await db.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
        if not u:
            return JSONResponse({"ok": True, "tasks": []})
        rows = (await db.execute(
            select(PresentationTask)
            .where(PresentationTask.user_id == u.id)
            .order_by(desc(PresentationTask.created_at))
            .limit(limit)
        )).scalars().all()
        return JSONResponse({"ok": True, "tasks": [
            {
                "task_uuid": t.task_uuid,
                "type": t.presentation_type,
                "slide_count": t.slide_count,
                "status": t.status,
                "progress": t.progress or 0,
                "amount_charged": float(t.amount_charged or 0),
                "result_file_id": t.result_file_id,
                "error_message": t.error_message,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            } for t in rows
        ]})


@app.get("/api/user-transactions")
async def legacy_user_transactions(telegram_id: int, request: Request, limit: int = 20):
    from api.database import AsyncSessionLocal
    from api.services.auth import verify_api_secret
    from api.models.user import User, Transaction
    from sqlalchemy import select, desc
    if not verify_api_secret(request.headers.get("Authorization", "")):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    async with AsyncSessionLocal() as db:
        u = (await db.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
        if not u:
            return JSONResponse({"ok": True, "transactions": []})
        rows = (await db.execute(
            select(Transaction)
            .where(Transaction.user_id == u.id)
            .order_by(desc(Transaction.created_at))
            .limit(limit)
        )).scalars().all()
        return JSONResponse({"ok": True, "transactions": [
            {
                "id": t.id,
                "type": t.transaction_type,
                "amount": float(t.amount),
                "description": t.description or "",
                "status": t.status,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            } for t in rows
        ]})


@app.get("/api/templates")
async def legacy_templates(request: Request, category: str = ""):
    from api.routers.marketplace import list_templates
    from api.schemas.marketplace import TemplateOut
    from api.database import AsyncSessionLocal
    from api.services.auth import verify_api_secret
    if not verify_api_secret(request.headers.get("Authorization", "")):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    async with AsyncSessionLocal() as db:
        rows = await list_templates(category, None, db)
        return JSONResponse({"ok": True, "templates": [TemplateOut.model_validate(r).model_dump() for r in rows]})


@app.get("/api/templates/{template_id}")
async def legacy_template_detail(template_id: int, request: Request):
    from api.routers.marketplace import get_template
    from api.schemas.marketplace import TemplateDetail
    from api.database import AsyncSessionLocal
    from api.services.auth import verify_api_secret
    if not verify_api_secret(request.headers.get("Authorization", "")):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    async with AsyncSessionLocal() as db:
        try:
            r = await get_template(template_id, None, db)
            from api.services import pptx_preview
            slides_text = pptx_preview.get_slides_data(template_id)
            previews = pptx_preview.list_preview_files(template_id)
            return JSONResponse({
                "ok": True,
                "template": TemplateDetail.model_validate(r).model_dump(mode="json"),
                "slides_text": slides_text,
                "preview_count": len(previews),
            })
        except Exception as e:
            return JSONResponse(status_code=404, content={"error": str(e)})


@app.get("/api/templates/{template_id}/preview/{slide_num}")
async def template_preview_image(template_id: int, slide_num: int):
    """Public: serve a slide preview PNG. No auth — these are intended for marketplace browsing."""
    from fastapi.responses import FileResponse
    from api.services import pptx_preview
    p = pptx_preview.get_preview_path(template_id, slide_num)
    if not p:
        return JSONResponse(status_code=404, content={"error": "Preview not found"})
    return FileResponse(str(p), media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


@app.post("/api/admin/upload-template")
async def legacy_admin_upload_template(request: Request):
    """Admin uploads a PPTX template. Auth: API_SECRET + admin telegram_id check.

    Multipart form fields:
      file   — required (.pptx)
      name, category, price, colors — metadata
      telegram_id — admin's Telegram ID (must be in ADMINS env)
    """
    from api.services.auth import verify_api_secret
    from api.config import get_settings
    from api.database import AsyncSessionLocal
    from api.services import pptx_preview
    from api.models.marketplace import Template
    from api.deps import require_api_secret  # noqa
    if not verify_api_secret(request.headers.get("Authorization", "")):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    form = await request.form()
    telegram_id = int(form.get("telegram_id") or 0)
    settings = get_settings()
    if telegram_id not in settings.admin_ids:
        return JSONResponse(status_code=403, content={"error": "Not an admin"})

    upload = form.get("file")
    if not upload or not hasattr(upload, "filename"):
        return JSONResponse(status_code=400, content={"error": "file is required"})
    if not upload.filename.lower().endswith(".pptx"):
        return JSONResponse(status_code=400, content={"error": "Only .pptx files allowed"})

    file_bytes = await upload.read()
    if len(file_bytes) > 50 * 1024 * 1024:
        return JSONResponse(status_code=400, content={"error": "File too large (>50MB)"})

    name = (form.get("name") or upload.filename).strip()
    category = (form.get("category") or "general").strip()
    price = float(form.get("price") or 0)
    colors = (form.get("colors") or "linear-gradient(135deg,#ff6b35,#f7931e)").strip()

    async with AsyncSessionLocal() as db:
        t = Template(
            name=name, category=category, slide_count=0,
            price=price, colors=colors, file_id="local",
            is_premium=price > 0,
        )
        db.add(t)
        await db.flush()
        template_id = t.id

        try:
            pptx_path = pptx_preview.save_pptx(template_id, file_bytes)
            previews = pptx_preview.generate_previews(template_id)
            slides_text = pptx_preview.extract_slides_text(template_id)
        except Exception as e:
            t.is_active = False
            await db.commit()
            return JSONResponse(status_code=500, content={"error": f"Preview failed: {e}"})

        t.slide_count = len(previews) or len(slides_text) or 0
        t.file_id = str(pptx_path)
        t.preview_url = f"/api/templates/{template_id}/preview/1"
        await db.commit()

    return JSONResponse({
        "ok": True,
        "template_id": template_id,
        "slide_count": len(previews),
        "previews": previews,
    })


@app.delete("/api/admin/templates/{template_id}")
async def legacy_admin_delete_template(template_id: int, telegram_id: int, request: Request):
    from api.services.auth import verify_api_secret
    from api.config import get_settings
    from api.database import AsyncSessionLocal
    from api.services import pptx_preview
    from api.models.marketplace import Template
    from sqlalchemy import update
    if not verify_api_secret(request.headers.get("Authorization", "")):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    if telegram_id not in get_settings().admin_ids:
        return JSONResponse(status_code=403, content={"error": "Not an admin"})
    async with AsyncSessionLocal() as db:
        await db.execute(update(Template).where(Template.id == template_id).values(is_active=False))
        await db.commit()
    try:
        pptx_preview.delete_template_files(template_id)
    except Exception:
        pass
    return JSONResponse({"ok": True})


@app.post("/api/admin/upload-work")
async def legacy_admin_upload_work(request: Request):
    """Admin uploads a ready work (DOCX/PDF). Generates first-page preview."""
    from api.services.auth import verify_api_secret
    from api.config import get_settings
    from api.database import AsyncSessionLocal
    from api.services import work_preview
    from api.models.marketplace import ReadyWork
    if not verify_api_secret(request.headers.get("Authorization", "")):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    form = await request.form()
    telegram_id = int(form.get("telegram_id") or 0)
    if telegram_id not in get_settings().admin_ids:
        return JSONResponse(status_code=403, content={"error": "Not an admin"})

    upload = form.get("file")
    if not upload or not hasattr(upload, "filename"):
        return JSONResponse(status_code=400, content={"error": "file is required"})

    fname = upload.filename.lower()
    if not (fname.endswith(".docx") or fname.endswith(".pdf") or fname.endswith(".pptx")):
        return JSONResponse(status_code=400, content={"error": "Only .docx, .pdf or .pptx files"})

    file_bytes = await upload.read()
    if len(file_bytes) > 50 * 1024 * 1024:
        return JSONResponse(status_code=400, content={"error": "File too large (>50MB)"})

    title = (form.get("title") or upload.filename).strip()
    subject = (form.get("subject") or "").strip()
    work_type = (form.get("work_type") or "mustaqil_ish").strip()
    page_count = int(form.get("page_count") or 10)
    price = float(form.get("price") or 0)
    language = (form.get("language") or "uz").strip()
    description = (form.get("description") or "").strip()

    if fname.endswith(".docx"):
        ext = "docx"
    elif fname.endswith(".pptx"):
        ext = "pptx"
    else:
        ext = "pdf"

    async with AsyncSessionLocal() as db:
        w = ReadyWork(
            title=title, subject=subject, work_type=work_type,
            page_count=page_count, price=price, language=language,
            description=description, file_id="local",
            preview_available=False,
        )
        db.add(w)
        await db.flush()
        work_id = w.id

        try:
            file_path = work_preview.save_file(work_id, file_bytes, ext)
            page_count = work_preview.generate_preview(work_id)
        except Exception as e:
            w.is_active = False
            await db.commit()
            return JSONResponse(status_code=500, content={"error": f"Preview failed: {e}"})

        w.file_id = str(file_path)
        w.preview_available = page_count > 0
        await db.commit()

    return JSONResponse({
        "ok": True,
        "work_id": work_id,
        "preview_pages": page_count,
    })


@app.delete("/api/admin/works/{work_id}")
async def legacy_admin_delete_work(work_id: int, telegram_id: int, request: Request):
    from api.services.auth import verify_api_secret
    from api.config import get_settings
    from api.database import AsyncSessionLocal
    from api.services import work_preview
    from api.models.marketplace import ReadyWork
    from sqlalchemy import update
    if not verify_api_secret(request.headers.get("Authorization", "")):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    if telegram_id not in get_settings().admin_ids:
        return JSONResponse(status_code=403, content={"error": "Not an admin"})
    async with AsyncSessionLocal() as db:
        await db.execute(update(ReadyWork).where(ReadyWork.id == work_id).values(is_active=False))
        await db.commit()
    try:
        work_preview.delete_work_files(work_id)
    except Exception:
        pass
    return JSONResponse({"ok": True})


@app.get("/api/works/{work_id}/preview")
async def work_preview_image(work_id: int):
    """Public: serve first-page preview PNG."""
    from fastapi.responses import FileResponse
    from api.services import work_preview
    p = work_preview.get_preview_path(work_id)
    if not p:
        return JSONResponse(status_code=404, content={"error": "Preview not found"})
    return FileResponse(str(p), media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


@app.get("/api/works/{work_id}/page/{page_num}")
async def work_page_image(work_id: int, page_num: int):
    """Public: serve a specific page PNG (1-based)."""
    from fastapi.responses import FileResponse
    from api.services import work_preview
    p = work_preview.get_page_path(work_id, page_num)
    if not p:
        return JSONResponse(status_code=404, content={"error": "Page not found"})
    return FileResponse(str(p), media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})


@app.post("/api/admin/works/{work_id}/regenerate-preview")
async def legacy_admin_regenerate_work_preview(work_id: int, telegram_id: int, request: Request):
    """Re-generate per-page previews for an existing work. Useful after upgrading
    the preview pipeline (e.g. single-page → multi-page)."""
    from api.services.auth import verify_api_secret
    from api.config import get_settings
    from api.services import work_preview
    if not verify_api_secret(request.headers.get("Authorization", "")):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    if telegram_id not in get_settings().admin_ids:
        return JSONResponse(status_code=403, content={"error": "Not an admin"})
    count = work_preview.generate_preview(work_id)
    return JSONResponse({"ok": True, "page_count": count})


@app.get("/api/ready-works")
async def legacy_works(request: Request, q: str = "", type: str = ""):
    from api.routers.marketplace import list_works
    from api.schemas.marketplace import ReadyWorkOut
    from api.database import AsyncSessionLocal
    from api.services.auth import verify_api_secret
    if not verify_api_secret(request.headers.get("Authorization", "")):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    async with AsyncSessionLocal() as db:
        rows = await list_works(q, type, None, db)
        return JSONResponse({"ok": True, "works": [ReadyWorkOut.model_validate(r).model_dump() for r in rows]})


@app.get("/api/ready-works/{work_id}")
async def legacy_work_detail(work_id: int, request: Request):
    from api.routers.marketplace import get_work
    from api.schemas.marketplace import ReadyWorkDetail
    from api.database import AsyncSessionLocal
    from api.services.auth import verify_api_secret
    from api.services import work_preview
    if not verify_api_secret(request.headers.get("Authorization", "")):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    async with AsyncSessionLocal() as db:
        try:
            r = await get_work(work_id, None, db)
            pages = work_preview.list_page_files(work_id)
            return JSONResponse({
                "ok": True,
                "work": ReadyWorkDetail.model_validate(r).model_dump(mode="json"),
                "preview_count": len(pages),
            })
        except Exception as e:
            return JSONResponse(status_code=404, content={"error": str(e)})


@app.post("/api/generate-outline")
async def legacy_generate_outline(request: Request):
    from api.routers.content import generate_outline, OutlineRequest
    from api.services.auth import verify_api_secret
    if not verify_api_secret(request.headers.get("Authorization", "")):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    body = await request.json()
    return await generate_outline(OutlineRequest(**body), None)


@app.post("/api/generate-slide")
async def legacy_generate_slide(request: Request):
    from api.routers.content import generate_slide, SlideRequest
    from api.services.auth import verify_api_secret
    if not verify_api_secret(request.headers.get("Authorization", "")):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    body = await request.json()
    return await generate_slide(SlideRequest(**body), None)


@app.post("/api/fetch-image")
async def legacy_fetch_image(request: Request):
    from api.routers.content import fetch_image, FetchImageRequest
    from api.services.auth import verify_api_secret
    if not verify_api_secret(request.headers.get("Authorization", "")):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    body = await request.json()
    return await fetch_image(FetchImageRequest(**body), None)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "aislidebot-api", "version": "2.0.0"}
