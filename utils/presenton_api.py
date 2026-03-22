# utils/presenton_api.py
# Presenton API client - Gamma API o'rniga bepul, open-source alternativa
# Self-hosted Docker konteyner orqali ishlaydi
# API V1 endpoint'lar ishlatiladi

import aiohttp
import asyncio
import logging
import os
import json
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class PresentonAPI:
    """
    Presenton API client - self-hosted prezentatsiya generator

    Base URL: http://presenton:80 (Docker network ichida)
    Hech qanday API key talab qilmaydi (self-hosted)

    V1 Endpoints:
    - POST /api/v1/ppt/presentation/generate       - sinxron yaratish
    - POST /api/v1/ppt/presentation/generate/async  - asinxron yaratish
    - GET  /api/v1/ppt/presentation/status/{id}     - status tekshirish
    - POST /api/v1/ppt/presentation/export/pptx     - PPTX eksport
    - POST /api/v1/ppt/presentation/export          - umumiy eksport
    """

    # Gamma theme -> Presenton template mapping
    TEMPLATE_MAPPING = {
        "chisel": "standard",
        "coal": "modern",
        "blues": "standard",
        "elysia": "modern",
        "breeze": "swift",
        "aurora": "modern",
        "coral-glow": "general",
        "gamma": "swift",
        "creme": "standard",
        "gamma-dark": "modern",
    }

    def __init__(self, base_url: str = None):
        self.base_url = (base_url or os.getenv("PRESENTON_URL", "http://presenton:80")).rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=600)

    def _get_template(self, gamma_theme_id: str) -> str:
        """Gamma theme ID ni Presenton template ga mapping"""
        if gamma_theme_id and gamma_theme_id.lower() in self.TEMPLATE_MAPPING:
            return self.TEMPLATE_MAPPING[gamma_theme_id.lower()]
        return "general"

    async def create_presentation_from_text(
            self,
            text_content: str,
            title: str = "Prezentatsiya",
            num_cards: int = 10,
            text_mode: str = "generate",
            theme_id: str = None,
            _retry_without_theme: bool = False
    ) -> Optional[Dict]:
        """
        Presenton orqali prezentatsiya yaratish (async)

        Returns:
            {'generationId': 'task-xxx', 'status': 'processing'}
        """
        template = self._get_template(theme_id if not _retry_without_theme else None)

        payload = {
            "content": text_content,
            "n_slides": num_cards,
            "tone": "professional",
            "verbosity": "standard",
            "language": "Uzbek",
            "template": template,
            "include_title_slide": True,
            "include_table_of_contents": True,
            "export_as": "pptx",
        }

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                url = f"{self.base_url}/api/v1/ppt/presentation/generate/async"
                logger.info(f"Presenton API: POST {url}")
                logger.info(f"Cards: {num_cards}, Template: {template}")

                async with session.post(url, json=payload) as response:
                    response_text = await response.text()
                    logger.info(f"Response status: {response.status}")
                    logger.info(f"Response: {response_text[:500]}")

                    if response.status in [200, 201]:
                        result = json.loads(response_text) if response_text else {}

                        # Async endpoint task_id yoki id qaytaradi
                        task_id = result.get("id") or result.get("task_id") or result.get("presentation_id")
                        if task_id:
                            logger.info(f"Task ID: {task_id}")
                            return {
                                "generationId": task_id,
                                "status": "processing",
                            }
                        else:
                            logger.error(f"Task ID yo'q: {result}")
                            return None
                    else:
                        logger.error(f"Presenton API XATO ({response.status}): {response_text[:300]}")

                        if theme_id and not _retry_without_theme and response.status in [400, 422, 500]:
                            logger.warning(f"Template '{template}' bilan xato! Default bilan qayta urinib ko'ramiz...")
                            return await self.create_presentation_from_text(
                                text_content=text_content,
                                title=title,
                                num_cards=num_cards,
                                text_mode=text_mode,
                                theme_id=None,
                                _retry_without_theme=True,
                            )
                        return None

        except asyncio.TimeoutError:
            logger.error("Timeout")
            return None
        except Exception as e:
            logger.error(f"Xato: {e}")
            if theme_id and not _retry_without_theme:
                return await self.create_presentation_from_text(
                    text_content=text_content, title=title, num_cards=num_cards,
                    text_mode=text_mode, theme_id=None, _retry_without_theme=True,
                )
            return None

    async def check_status(self, generation_id: str) -> Optional[Dict]:
        """
        Async task status tekshirish

        Endpoint: GET /api/v1/ppt/presentation/status/{id}
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                url = f"{self.base_url}/api/v1/ppt/presentation/status/{generation_id}"

                async with session.get(url) as response:
                    response_text = await response.text()

                    if response.status == 200:
                        result = json.loads(response_text)
                        logger.info(f"Status: {str(result)[:500]}")

                        status = result.get("status", "unknown")

                        # Status mapping
                        status_map = {
                            "pending": "processing",
                            "processing": "processing",
                            "in_progress": "processing",
                            "completed": "completed",
                            "done": "completed",
                            "error": "failed",
                            "failed": "failed",
                        }
                        mapped_status = status_map.get(status, status)

                        # PPTX URL olish
                        pptx_url = ""
                        presentation_id = ""

                        data = result.get("data") or result
                        if isinstance(data, dict):
                            pptx_url = data.get("path", "") or data.get("pptx_url", "") or data.get("export_url", "")
                            presentation_id = data.get("presentation_id", "") or data.get("id", "")

                        return {
                            "status": mapped_status,
                            "pptxUrl": pptx_url,
                            "gammaUrl": "",
                            "pdfUrl": "",
                            "files": [],
                            "exports": {},
                            "result": result,
                            "presentation_id": presentation_id,
                        }
                    else:
                        logger.error(f"Status xato ({response.status}): {response_text[:300]}")
                        return None

        except Exception as e:
            logger.error(f"Status xato: {e}")
            return None

    async def download_file(self, file_url: str, output_path: str) -> bool:
        """Faylni URL dan yuklab olish"""
        try:
            # Nisbiy URL bo'lsa base_url qo'shish
            if file_url.startswith("/"):
                file_url = f"{self.base_url}{file_url}"
            elif not file_url.startswith("http"):
                file_url = f"{self.base_url}/{file_url}"

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                logger.info(f"Download: {file_url[:100]}...")

                async with session.get(file_url) as response:
                    if response.status == 200:
                        content = await response.read()
                        with open(output_path, "wb") as f:
                            f.write(content)

                        file_size = os.path.getsize(output_path)
                        logger.info(f"Saqlandi: {output_path} ({file_size} bytes)")
                        return file_size > 0
                    else:
                        logger.error(f"Download xato: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"Download xato: {e}")
            return False

    async def download_pptx(self, generation_id: str, output_path: str) -> bool:
        """PPTX faylni yuklab olish"""
        try:
            logger.info(f"PPTX yuklab olish: {generation_id}")

            status_info = await self.check_status(generation_id)
            if not status_info:
                logger.error("Status olish xato")
                return False

            status = status_info.get("status", "")
            if status != "completed":
                logger.error(f"Hali tayyor emas (status: {status})")
                return False

            # 1. pptxUrl dan yuklab olish
            pptx_url = status_info.get("pptxUrl", "")
            if pptx_url:
                logger.info(f"PPTX URL topildi: {pptx_url[:80]}")
                return await self.download_file(pptx_url, output_path)

            # 2. presentation_id orqali eksport
            presentation_id = status_info.get("presentation_id", "")
            if presentation_id:
                logger.info(f"Export orqali PPTX olish: {presentation_id}")
                # Avval prezentatsiya ma'lumotlarini olish
                pres_data = await self._get_presentation(presentation_id)
                if pres_data:
                    return await self._export_pptx(pres_data, output_path)

            logger.error("Na pptxUrl, na presentation_id topilmadi")
            return False

        except Exception as e:
            logger.error(f"PPTX xato: {e}")
            return False

    async def _get_presentation(self, presentation_id: str) -> Optional[Dict]:
        """Prezentatsiya ma'lumotlarini olish"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                url = f"{self.base_url}/api/v1/ppt/presentation/{presentation_id}"
                async with session.get(url) as response:
                    if response.status == 200:
                        return json.loads(await response.text())
                    logger.error(f"Presentation olish xato: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Presentation olish xato: {e}")
            return None

    async def _export_pptx(self, presentation_data: Dict, output_path: str) -> bool:
        """Prezentatsiyani PPTX ga eksport qilish"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                url = f"{self.base_url}/api/v1/ppt/presentation/export/pptx"
                logger.info(f"Export PPTX: {url}")

                async with session.post(url, json=presentation_data) as response:
                    if response.status == 200:
                        content_type = response.headers.get("content-type", "")

                        if "application/json" in content_type:
                            result = json.loads(await response.text())
                            file_url = result.get("path", "") or result.get("url", "")
                            if file_url:
                                return await self.download_file(file_url, output_path)
                        else:
                            # To'g'ridan-to'g'ri fayl qaytarilgan
                            content = await response.read()
                            with open(output_path, "wb") as f:
                                f.write(content)
                            file_size = os.path.getsize(output_path)
                            logger.info(f"PPTX saqlandi: {output_path} ({file_size} bytes)")
                            return file_size > 0

                    logger.error(f"Export xato: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Export xato: {e}")
            return False

    async def wait_for_completion(
            self,
            generation_id: str,
            timeout_seconds: int = 600,
            check_interval: int = 10,
            wait_for_pptx: bool = True,
    ) -> bool:
        """Generation tayyor bo'lishini kutish"""
        elapsed = 0
        logger.info(f"Kutish: max {timeout_seconds}s, interval {check_interval}s")

        while elapsed < timeout_seconds:
            status_info = await self.check_status(generation_id)

            if not status_info:
                logger.warning("Status xato, qayta...")
                await asyncio.sleep(check_interval)
                elapsed += check_interval
                continue

            status = status_info.get("status", "")

            if status in ("failed", "error"):
                error_data = status_info.get("result", {})
                error_msg = error_data.get("error", "Noma'lum xato")
                logger.error(f"Generation failed! Error: {error_msg}")
                return False

            if status == "completed":
                if wait_for_pptx:
                    pptx_url = status_info.get("pptxUrl", "")
                    presentation_id = status_info.get("presentation_id", "")
                    if pptx_url or presentation_id:
                        logger.info("Tayyor! PPTX mavjud!")
                        return True
                    else:
                        logger.info("Completed, lekin PPTX hali yo'q...")
                else:
                    logger.info("Tayyor!")
                    return True

            logger.info(f"{elapsed}s / {timeout_seconds}s (status: {status})")
            await asyncio.sleep(check_interval)
            elapsed += check_interval

        logger.error(f"Timeout: {timeout_seconds}s")
        return False

    def format_content_for_gamma(self, content: Dict, content_type: str) -> str:
        """Content'ni Presenton uchun formatlash (Gamma interface saqlanadi)"""
        if content_type == "pitch_deck":
            return self._format_pitch_deck(content)
        else:
            return self._format_presentation(content)

    def _format_pitch_deck(self, content: Dict) -> str:
        """Pitch deck - strukturali matn"""
        project_name = content.get("project_name", "Startup")
        tagline = content.get("tagline", "")
        author = content.get("author", "")

        problem = content.get("problem", "")
        solution = content.get("solution", "")
        market = content.get("market", "")
        business_model = content.get("business_model", "")
        competition = content.get("competition", "")
        advantage = content.get("advantage", "")
        financials = content.get("financials", "")
        team = content.get("team", "")
        milestones = content.get("milestones", "")
        cta = content.get("cta", "")

        text = f"""
{project_name}

{tagline}

Muallif: {author}

MUAMMO:
{problem}

YECHIM:
{solution}

BOZOR VA IMKONIYATLAR:
{market}

BIZNES MODEL:
{business_model}

RAQOBAT TAHLILI:
{competition}

BIZNING USTUNLIKLARIMIZ:
{advantage}

MOLIYAVIY REJALAR:
{financials}

JAMOA:
{team}

YO'L XARITASI:
{milestones}

TAKLIF:
{cta}
"""
        return text.strip()

    def _format_presentation(self, content: Dict) -> str:
        """Professional prezentatsiya formatlash — Presenton uchun optimallashtirilgan"""
        title = content.get("title", "Prezentatsiya")
        subtitle = content.get("subtitle", "")
        slides = content.get("slides", [])

        text = f"# {title}\n{subtitle}\n\n"

        for slide in slides:
            slide_title = slide.get("title", "")
            slide_content = slide.get("content", "")
            bullet_points = slide.get("bullet_points", [])

            # 3-bosqichli rasm kalit so'zlarini olish
            image_keyword = self._get_best_image_keyword(slide)

            text += f"## {slide_title}\n"

            if slide_content:
                text += f"{slide_content}\n"

            if bullet_points:
                for point in bullet_points[:5]:  # Maksimum 5 ta bullet
                    text += f"• {point}\n"

            if image_keyword:
                text += f"[Image: {image_keyword}]\n"

            text += "\n"

        return text.strip()

    @staticmethod
    def _get_best_image_keyword(slide: Dict) -> str:
        """3-bosqichli rasm kalit so'zini olish (primary → secondary → fallback)"""
        # Yangi format: image_keywords dict
        image_keywords = slide.get("image_keywords")
        if image_keywords and isinstance(image_keywords, dict):
            primary = image_keywords.get("primary", "")
            secondary = image_keywords.get("secondary", "")
            fallback = image_keywords.get("fallback", "")
            # Eng yaxshisini qaytarish
            return primary or secondary or fallback

        # Eski format: image_keyword string (backward compatibility)
        return slide.get("image_keyword", "")

    async def get_themes(self, limit: int = 50) -> Optional[list]:
        """Shablonlarni olish"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                url = f"{self.base_url}/api/v1/ppt/template-management/summary"
                async with session.get(url) as response:
                    if response.status == 200:
                        result = json.loads(await response.text())
                        return result if isinstance(result, list) else [result]
                    return None
        except Exception as e:
            logger.error(f"Templates xato: {e}")
            return None
