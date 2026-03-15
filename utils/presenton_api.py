# utils/presenton_api.py
# Presenton API client - Gamma API o'rniga bepul, open-source alternativa
# Self-hosted Docker konteyner orqali ishlaydi

import aiohttp
import asyncio
import logging
import os
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class PresentonAPI:
    """
    Presenton API client - self-hosted prezentatsiya generator

    Base URL: http://presenton:80 (Docker network ichida)
    Hech qanday API key talab qilmaydi (self-hosted)

    Endpoints:
    - POST /api/v3/presentation/generate/async - asinxron yaratish
    - GET  /api/v3/async-task/status/{id}      - status tekshirish
    - POST /api/v3/presentation/export         - PPTX/PDF eksport
    - GET  /api/v3/standard-template/all       - shablonlar ro'yxati
    """

    # Presenton themelari - Gamma themelarga mapping
    THEME_MAPPING = {
        "chisel": {"theme": "professional-blue", "template": "neo-standard"},
        "coal": {"theme": "professional-dark", "template": "neo-modern"},
        "blues": {"theme": "professional-blue", "template": "neo-standard"},
        "elysia": {"theme": "light-rose", "template": "neo-modern"},
        "breeze": {"theme": "mint-blue", "template": "neo-swift"},
        "aurora": {"theme": "professional-dark", "template": "neo-modern"},
        "coral-glow": {"theme": "light-rose", "template": "neo-general"},
        "gamma": {"theme": "edge-yellow", "template": "neo-swift"},
        "creme": {"theme": "edge-yellow", "template": "neo-standard"},
        "gamma-dark": {"theme": "professional-dark", "template": "neo-modern"},
    }

    def __init__(self, base_url: str = None):
        self.base_url = (base_url or os.getenv("PRESENTON_URL", "http://presenton:80")).rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=600)

    def _get_presenton_theme(self, gamma_theme_id: str) -> Dict:
        """Gamma theme ID ni Presenton theme/template ga mapping qilish"""
        if gamma_theme_id and gamma_theme_id.lower() in self.THEME_MAPPING:
            return self.THEME_MAPPING[gamma_theme_id.lower()]
        return {"theme": "professional-blue", "template": "neo-standard"}

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

        Args:
            text_content: Matn (kontent)
            title: Sarlavha
            num_cards: Slaydlar soni
            text_mode: "generate" | "condense" | "preserve"
            theme_id: Gamma theme ID (avtomatik mapping qilinadi)

        Returns:
            {'generationId': 'task-xxx', 'status': 'processing'}
        """
        # Gamma theme ni Presenton ga mapping
        theme_config = self._get_presenton_theme(theme_id if not _retry_without_theme else None)

        # text_mode ni Presenton formatiga o'girish
        content_generation_map = {
            "generate": "enhance",
            "condense": "condense",
            "preserve": "preserve",
        }

        payload = {
            "content": text_content,
            "n_slides": num_cards,
            "tone": "professional",
            "verbosity": "standard",
            "content_generation": content_generation_map.get(text_mode, "enhance"),
            "markdown_emphasis": True,
            "image_type": "stock",
            "theme": theme_config["theme"],
            "standard_template": theme_config["template"],
            "language": "Uzbek",
            "include_title_slide": True,
            "include_table_of_contents": False,
            "export_as": "pptx",
        }

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                url = f"{self.base_url}/api/v3/presentation/generate/async"
                logger.info(f"Presenton API: POST {url}")
                logger.info(f"Cards: {num_cards}, Theme: {theme_config['theme']}, Template: {theme_config['template']}")

                async with session.post(url, json=payload) as response:
                    response_text = await response.text()
                    logger.info(f"Response status: {response.status}")
                    logger.info(f"Response: {response_text[:300]}")

                    if response.status in [200, 201]:
                        import json
                        result = json.loads(response_text) if response_text else {}

                        task_id = result.get("id")
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
                        logger.error(f"Presenton API XATO ({response.status}): {response_text}")

                        # Fallback: theme'siz qayta urinish
                        if theme_id and not _retry_without_theme and response.status in [400, 422, 500]:
                            logger.warning(f"Theme '{theme_id}' bilan xato! Theme'siz qayta urinib ko'ramiz...")
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
                logger.warning("Exception! Theme'siz qayta urinib ko'ramiz...")
                return await self.create_presentation_from_text(
                    text_content=text_content,
                    title=title,
                    num_cards=num_cards,
                    text_mode=text_mode,
                    theme_id=None,
                    _retry_without_theme=True,
                )
            return None

    async def check_status(self, generation_id: str) -> Optional[Dict]:
        """
        Async task status tekshirish

        Endpoint: GET /api/v3/async-task/status/{id}
        """
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                url = f"{self.base_url}/api/v3/async-task/status/{generation_id}"

                async with session.get(url) as response:
                    response_text = await response.text()

                    if response.status == 200:
                        import json
                        result = json.loads(response_text)

                        logger.info(f"Status response: {str(result)[:500]}")

                        status = result.get("status", "unknown")

                        # Presenton statuslarni Gamma formatiga mapping
                        status_map = {
                            "pending": "processing",
                            "completed": "completed",
                            "error": "failed",
                        }
                        mapped_status = status_map.get(status, status)

                        # Completed bo'lsa, data ichidan PPTX URL olish
                        pptx_url = ""
                        data = result.get("data")
                        if data and isinstance(data, dict):
                            pptx_url = data.get("path", "")

                        return {
                            "status": mapped_status,
                            "pptxUrl": pptx_url,
                            "gammaUrl": "",
                            "pdfUrl": "",
                            "files": [],
                            "exports": {},
                            "result": result,
                            "presentation_id": data.get("presentation_id", "") if data else "",
                        }
                    else:
                        logger.error(f"Status xato ({response.status}): {response_text}")
                        return None

        except Exception as e:
            logger.error(f"Status xato: {e}")
            return None

    async def download_file(self, file_url: str, output_path: str) -> bool:
        """Faylni URL dan yuklab olish"""
        try:
            # Agar file_url nisbiy bo'lsa, base_url qo'shish
            if file_url.startswith("/"):
                file_url = f"{self.base_url}{file_url}"
            elif not file_url.startswith("http"):
                file_url = f"{self.base_url}/{file_url}"

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                logger.info(f"Download: {file_url[:80]}...")

                async with session.get(file_url) as response:
                    if response.status == 200:
                        with open(output_path, "wb") as f:
                            f.write(await response.read())

                        file_size = os.path.getsize(output_path)
                        logger.info(f"Saqlandi: {output_path} ({file_size} bytes)")
                        return True
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

            pptx_url = status_info.get("pptxUrl", "")
            if pptx_url:
                logger.info("PPTX URL topildi")
                return await self.download_file(pptx_url, output_path)

            # Fallback: presentation_id orqali export qilish
            presentation_id = status_info.get("presentation_id", "")
            if presentation_id:
                logger.info(f"Export orqali PPTX olish: {presentation_id}")
                return await self._export_presentation(presentation_id, output_path, "pptx")

            logger.error("Na pptxUrl, na presentation_id topilmadi")
            return False

        except Exception as e:
            logger.error(f"PPTX xato: {e}")
            return False

    async def _export_presentation(self, presentation_id: str, output_path: str, export_as: str = "pptx") -> bool:
        """Prezentatsiyani eksport qilish"""
        try:
            payload = {
                "id": presentation_id,
                "export_as": export_as,
            }

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                url = f"{self.base_url}/api/v3/presentation/export"
                logger.info(f"Export: {url}")

                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        import json
                        result = json.loads(await response.text())
                        file_url = result.get("path", "")

                        if file_url:
                            return await self.download_file(file_url, output_path)

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
        """Oddiy prezentatsiya"""
        title = content.get("title", "Prezentatsiya")
        subtitle = content.get("subtitle", "")
        slides = content.get("slides", [])

        text = f"{title}\n\n{subtitle}\n\n"

        for slide in slides:
            slide_title = slide.get("title", "")
            slide_content = slide.get("content", "")
            bullet_points = slide.get("bullet_points", [])

            text += f"\n{slide_title}\n\n{slide_content}\n"

            if bullet_points:
                for point in bullet_points:
                    text += f"- {point}\n"

            text += "\n"

        return text.strip()

    async def get_templates(self) -> Optional[list]:
        """Mavjud shablonlar ro'yxatini olish"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                url = f"{self.base_url}/api/v3/standard-template/all"
                logger.info(f"Presenton API: GET {url}")

                async with session.get(url) as response:
                    if response.status == 200:
                        import json
                        result = json.loads(await response.text())
                        templates = result if isinstance(result, list) else result.get("data", [])
                        logger.info(f"{len(templates)} ta shablon topildi")
                        return templates
                    else:
                        logger.error(f"Templates xato ({response.status})")
                        return None

        except Exception as e:
            logger.error(f"Templates xato: {e}")
            return None

    # Gamma API bilan mos interface - get_themes ni get_templates ga yo'naltirish
    async def get_themes(self, limit: int = 50) -> Optional[list]:
        """Gamma API mos interface - shablonlarni theme sifatida qaytarish"""
        return await self.get_templates()
