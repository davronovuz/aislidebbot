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


@app.get("/api/templates")
async def legacy_templates(request: Request, category: str = ""):
    from api.routers.marketplace import list_templates
    from api.database import AsyncSessionLocal
    from api.services.auth import verify_api_secret
    if not verify_api_secret(request.headers.get("Authorization", "")):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    async with AsyncSessionLocal() as db:
        rows = await list_templates(category, None, db)
        return JSONResponse({"ok": True, "templates": [r.model_dump() for r in rows]})


@app.get("/api/templates/{template_id}")
async def legacy_template_detail(template_id: int, request: Request):
    from api.routers.marketplace import get_template
    from api.database import AsyncSessionLocal
    from api.services.auth import verify_api_secret
    if not verify_api_secret(request.headers.get("Authorization", "")):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    async with AsyncSessionLocal() as db:
        try:
            r = await get_template(template_id, None, db)
            return JSONResponse({"ok": True, "template": r.model_dump()})
        except Exception as e:
            return JSONResponse(status_code=404, content={"error": str(e)})


@app.get("/api/ready-works")
async def legacy_works(request: Request, q: str = "", type: str = ""):
    from api.routers.marketplace import list_works
    from api.database import AsyncSessionLocal
    from api.services.auth import verify_api_secret
    if not verify_api_secret(request.headers.get("Authorization", "")):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    async with AsyncSessionLocal() as db:
        rows = await list_works(q, type, None, db)
        return JSONResponse({"ok": True, "works": [r.model_dump() for r in rows]})


@app.get("/api/ready-works/{work_id}")
async def legacy_work_detail(work_id: int, request: Request):
    from api.routers.marketplace import get_work
    from api.database import AsyncSessionLocal
    from api.services.auth import verify_api_secret
    if not verify_api_secret(request.headers.get("Authorization", "")):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    async with AsyncSessionLocal() as db:
        try:
            r = await get_work(work_id, None, db)
            return JSONResponse({"ok": True, "work": r.model_dump()})
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
