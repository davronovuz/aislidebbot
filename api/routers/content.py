"""
AI content generation endpoints.
Called directly from Next.js frontend (proxied through Vercel Functions).
"""
import logging
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from openai import AsyncOpenAI

from api.config import get_settings
from api.deps import require_api_secret

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/content", tags=["content"])
settings = get_settings()


def _openai_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.openai_api_key)


# ─── Schemas ──────────────────────────────────────────────────────────────────

class OutlineRequest(BaseModel):
    topic: str
    details: str = ""
    slide_count: int = 10
    language: str = "uz"


class SlideRequest(BaseModel):
    topic: str
    slide_title: str
    slide_number: int
    total_slides: int
    language: str = "uz"
    details: str = ""


class FetchImageRequest(BaseModel):
    keywords: list[str]


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/generate-outline")
async def generate_outline(
    body: OutlineRequest,
    _: None = Depends(require_api_secret),
):
    """Generate slide outline (title + subtitle per slide) for a topic."""
    lang_map = {"uz": "O'zbek tilida", "ru": "На русском языке", "en": "In English"}
    lang_instruction = lang_map.get(body.language, "O'zbek tilida")

    prompt = f"""Prezentatsiya uchun slayd strukturasini yarating.

Mavzu: {body.topic}
{f"Qo'shimcha ma'lumot: {body.details}" if body.details else ""}
Slaydlar soni: {body.slide_count}
Til: {lang_instruction}

JSON formatda qaytaring:
{{
  "title": "Prezentatsiya asosiy sarlavhasi",
  "subtitle": "Kichik sarlavha yoki tavsif",
  "slides": [
    {{"number": 1, "title": "Slayd sarlavhasi", "description": "Slayd haqida qisqa tavsif"}},
    ...
  ]
}}

Birinchi slayd kirish (introduction), oxirgi slayd xulosa (conclusion) bo'lsin."""

    try:
        client = _openai_client()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Siz professional prezentatsiya mutaxassisisiz. Faqat JSON qaytaring."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=2000,
            temperature=0.7,
        )
        import json
        content = json.loads(response.choices[0].message.content)
        return {"ok": True, **content}
    except Exception as e:
        logger.error(f"generate-outline error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-slide")
async def generate_slide(
    body: SlideRequest,
    _: None = Depends(require_api_secret),
):
    """Generate full content for a single slide."""
    lang_map = {"uz": "O'zbek tilida", "ru": "На русском языке", "en": "In English"}
    lang_instruction = lang_map.get(body.language, "O'zbek tilida")

    system_prompts = {
        "uz": "Siz professional prezentatsiya mutaxassisisiz. Batafsil, mazmunli kontent yarating. Faqat JSON qaytaring.",
        "ru": "Вы профессиональный эксперт по презентациям. Создайте подробный, содержательный контент. Возвращайте только JSON.",
        "en": "You are a professional presentation expert. Create detailed, meaningful content. Return only JSON.",
    }

    prompt = f"""Slayd uchun kontent yarating:

Umumiy mavzu: {body.topic}
{f"Qo'shimcha: {body.details}" if body.details else ""}
Slayd sarlavhasi: {body.slide_title}
Slayd raqami: {body.slide_number}/{body.total_slides}
Til: {lang_instruction}

JSON formatda qaytaring:
{{
  "title": "{body.slide_title}",
  "content": "3-5 ta to'liq jumla, batafsil asosiy kontent",
  "bullet_points": ["Birinchi muhim nuqta (1-2 jumla)", "Ikkinchi nuqta", "Uchinchi nuqta", "To'rtinchi nuqta", "Beshinchi nuqta"],
  "image_keywords": ["keyword1", "keyword2", "keyword3"],
  "layout": "standard"
}}

bullet_points 4-6 ta bo'lsin, har biri 1-2 jumladan iborat bo'lsin.
image_keywords ingliz tilida bo'lsin."""

    try:
        client = _openai_client()
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompts.get(body.language, system_prompts["uz"])},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=1000,
            temperature=0.7,
        )
        import json
        content = json.loads(response.choices[0].message.content)
        return {"ok": True, **content}
    except Exception as e:
        logger.error(f"generate-slide error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fetch-image")
async def fetch_image(
    body: FetchImageRequest,
    _: None = Depends(require_api_secret),
):
    """Search Pixabay for a relevant image, return URL."""
    if not settings.pixabay_api_key:
        return {"ok": True, "image_url": None}

    query = " ".join(body.keywords[:3])
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(
                "https://pixabay.com/api/",
                params={
                    "key": settings.pixabay_api_key,
                    "q": query,
                    "image_type": "photo",
                    "orientation": "horizontal",
                    "category": "business",
                    "min_width": 800,
                    "safesearch": "true",
                    "per_page": 5,
                },
            )
            data = r.json()
            hits = data.get("hits", [])
            if hits:
                return {"ok": True, "image_url": hits[0].get("webformatURL")}
            return {"ok": True, "image_url": None}
        except Exception as e:
            logger.error(f"fetch-image error: {e}")
            return {"ok": True, "image_url": None}
