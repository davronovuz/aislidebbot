import aiohttp
import asyncio
import logging
import ssl
from typing import Optional, Dict
import json

logger = logging.getLogger(__name__)


class GammaAPI:
    """
    Gamma API client - OFFICIAL DOCUMENTATION
    Base URL: https://public-api.gamma.app/v1.0

    Endpoints:
    - POST /generations - yangi gamma yaratish
    - GET /generations/{generationId} - status va fayllar
    - GET /themes - mavjud theme'lar ro'yxati
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://public-api.gamma.app/v1.0"
        self.timeout = aiohttp.ClientTimeout(total=600)

        # SSL context (macOS uchun)
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    async def create_presentation_from_text(
            self,
            text_content: str,
            title: str = "Prezentatsiya",
            num_cards: int = 10,
            text_mode: str = "generate",
            theme_id: str = None,
            _retry_without_theme: bool = False  # Internal flag
    ) -> Optional[Dict]:
        """
        Gamma prezentatsiya yaratish

        Args:
            text_content: Matn (1-100,000 tokens)
            title: Sarlavha (faqat metadata uchun)
            num_cards: Slaydlar soni (1-75)
            text_mode: "generate" | "condense" | "preserve"
            theme_id: Theme ID (masalan: "Chisel", "Vortex", "Prism")

        Returns:
            {'generationId': '...', 'status': 'processing'}
        """
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
            "accept": "application/json"
        }

        # Official API payload struktura + PPTX export + O'ZBEK TILI
        payload = {
            "inputText": text_content,
            "textMode": text_mode,
            "format": "presentation",
            "numCards": num_cards,
            "cardSplit": "auto",
            "exportAs": "pptx",
            "textOptions": {
                "language": "uz"
            }
        }

        # Theme ID qo'shish (agar berilgan bo'lsa)
        if theme_id and not _retry_without_theme:
            payload["themeId"] = theme_id
            logger.info(f"🎨 Theme qo'shildi: {theme_id}")

        try:
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)

            async with aiohttp.ClientSession(timeout=self.timeout, connector=connector) as session:
                logger.info(f"🎯 Gamma API: POST {self.base_url}/generations")
                logger.info(
                    f"📊 Cards: {num_cards}, Mode: {text_mode}, Theme: {theme_id if theme_id and not _retry_without_theme else 'default'}")

                async with session.post(
                        f"{self.base_url}/generations",
                        headers=headers,
                        json=payload
                ) as response:

                    response_text = await response.text()
                    logger.info(f"📥 Response status: {response.status}")
                    logger.info(f"📄 Response: {response_text[:300]}")

                    if response.status in [200, 201]:
                        result = json.loads(response_text) if response_text else {}
                        generation_id = result.get('generationId')

                        if generation_id:
                            logger.info(f"✅ Generation ID: {generation_id}")
                            return {
                                'generationId': generation_id,
                                'status': 'processing'
                            }
                        else:
                            logger.error(f"❌ generationId yo'q: {result}")
                            return None
                    else:
                        logger.error(f"❌ Gamma API XATO ({response.status}): {response_text}")

                        # ✅ FALLBACK: Agar theme bilan xato bo'lsa, theme'siz qayta urinish
                        if theme_id and not _retry_without_theme and response.status in [400, 422, 500]:
                            logger.warning(f"⚠️ Theme '{theme_id}' bilan xato! Theme'siz qayta urinib ko'ramiz...")
                            return await self.create_presentation_from_text(
                                text_content=text_content,
                                title=title,
                                num_cards=num_cards,
                                text_mode=text_mode,
                                theme_id=None,
                                _retry_without_theme=True
                            )

                        return None

        except asyncio.TimeoutError:
            logger.error("⏱️ Timeout")
            return None
        except Exception as e:
            logger.error(f"💥 Xato: {e}")

            # ✅ FALLBACK: Exception bo'lsa ham theme'siz urinish
            if theme_id and not _retry_without_theme:
                logger.warning(f"⚠️ Exception! Theme'siz qayta urinib ko'ramiz...")
                return await self.create_presentation_from_text(
                    text_content=text_content,
                    title=title,
                    num_cards=num_cards,
                    text_mode=text_mode,
                    theme_id=None,
                    _retry_without_theme=True
                )

            return None

    async def get_themes(self, limit: int = 50) -> Optional[list]:
        """
        Mavjud theme'lar ro'yxatini olish

        Endpoint: GET /v1.0/themes
        """
        headers = {
            "X-API-KEY": self.api_key,
            "accept": "application/json"
        }

        try:
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)

            async with aiohttp.ClientSession(timeout=self.timeout, connector=connector) as session:
                logger.info(f"🎨 Gamma API: GET {self.base_url}/themes")

                async with session.get(
                        f"{self.base_url}/themes?limit={limit}",
                        headers=headers
                ) as response:

                    if response.status == 200:
                        result = await response.json()
                        themes = result.get('data', result if isinstance(result, list) else [])
                        logger.info(f"✅ {len(themes)} ta theme topildi")

                        # Theme ID'larni log qilish
                        for theme in themes[:10]:
                            logger.info(f"🎨 Theme: id='{theme.get('id')}', name='{theme.get('name')}'")

                        return themes
                    else:
                        response_text = await response.text()
                        logger.error(f"❌ Themes xato ({response.status}): {response_text}")
                        return None

        except Exception as e:
            logger.error(f"💥 Themes xato: {e}")
            return None

    async def check_status(self, generation_id: str) -> Optional[Dict]:
        """
        Generation holatini tekshirish

        Endpoint: GET /v1.0/generations/{generationId}
        """
        headers = {
            "X-API-KEY": self.api_key,
            "accept": "application/json"
        }

        try:
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)

            async with aiohttp.ClientSession(timeout=self.timeout, connector=connector) as session:
                async with session.get(
                        f"{self.base_url}/generations/{generation_id}",
                        headers=headers
                ) as response:

                    response_text = await response.text()

                    if response.status == 200:
                        result = json.loads(response_text)

                        logger.info(f"📋 Status response: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}")

                        status = result.get('status', 'unknown')
                        gamma_url = result.get('gammaUrl', '')
                        pptx_url = result.get('pptxUrl', '')
                        pdf_url = result.get('pdfUrl', '')
                        export_url = result.get('exportUrl', '')
                        files = result.get('files', [])
                        exports = result.get('exports', {})

                        logger.info(f"📊 Status: {status}")
                        logger.info(f"📄 PPTX URL: {pptx_url[:50] if pptx_url else 'yo`q'}")

                        return {
                            'status': status,
                            'gammaUrl': gamma_url,
                            'pptxUrl': pptx_url or export_url,
                            'pdfUrl': pdf_url,
                            'files': files,
                            'exports': exports,
                            'result': result
                        }

                    elif response.status == 202:
                        logger.info("⏳ 202 - hali ishlanmoqda")
                        return {
                            'status': 'processing',
                            'gammaUrl': '',
                            'pptxUrl': ''
                        }

                    else:
                        logger.error(f"❌ Xato ({response.status}): {response_text}")
                        return None

        except Exception as e:
            logger.error(f"💥 Status xato: {e}")
            return None

    async def download_file(self, file_url: str, output_path: str) -> bool:
        """Faylni URL dan yuklab olish"""
        try:
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)

            async with aiohttp.ClientSession(timeout=self.timeout, connector=connector) as session:
                logger.info(f"📥 Download: {file_url[:80]}...")

                async with session.get(file_url) as response:
                    if response.status == 200:
                        with open(output_path, 'wb') as f:
                            f.write(await response.read())

                        logger.info(f"✅ Saqlandi: {output_path}")
                        return True
                    else:
                        logger.error(f"❌ Download xato: {response.status}")
                        return False

        except Exception as e:
            logger.error(f"💥 Download xato: {e}")
            return False

    async def download_pptx(self, generation_id: str, output_path: str) -> bool:
        """PPTX faylni yuklab olish"""
        try:
            logger.info(f"📥 PPTX yuklab olish: {generation_id}")

            status_info = await self.check_status(generation_id)

            if not status_info:
                logger.error("❌ Status olish xato")
                return False

            status = status_info.get('status', '')

            if status != 'completed':
                logger.error(f"❌ Hali tayyor emas (status: {status})")
                return False

            pptx_url = status_info.get('pptxUrl', '')

            if pptx_url:
                logger.info(f"📥 PPTX URL topildi")
                return await self.download_file(pptx_url, output_path)

            gamma_url = status_info.get('gammaUrl', '')

            if not gamma_url:
                logger.error("❌ Na pptxUrl, na gammaUrl topilmadi")
                return False

            logger.warning("⚠️ pptxUrl yo'q, gamma URL'dan export qilishga urinamiz")
            doc_id = gamma_url.split('/')[-1]
            export_url = f"https://gamma.app/docs/{doc_id}/export/pptx"

            return await self.download_file(export_url, output_path)

        except Exception as e:
            logger.error(f"💥 PPTX xato: {e}")
            return False

    async def wait_for_completion(
            self,
            generation_id: str,
            timeout_seconds: int = 600,
            check_interval: int = 10,
            wait_for_pptx: bool = True
    ) -> bool:
        """Generation tayyor bo'lishini kutish"""
        elapsed = 0

        logger.info(f"⏳ Kutish: max {timeout_seconds}s, interval {check_interval}s")

        while elapsed < timeout_seconds:
            status_info = await self.check_status(generation_id)

            if not status_info:
                logger.warning("⚠️ Status xato, qayta...")
                await asyncio.sleep(check_interval)
                elapsed += check_interval
                continue

            status = status_info.get('status', '')

            if status == 'failed' or status == 'error':
                logger.error("❌ Generation failed!")
                return False

            if status == 'completed':
                if wait_for_pptx:
                    pptx_url = status_info.get('pptxUrl', '')
                    if pptx_url:
                        logger.info("✅ Tayyor! PPTX URL ham bor!")
                        return True
                    else:
                        logger.info("⏳ Completed, lekin PPTX URL hali yo'q...")
                else:
                    logger.info("✅ Tayyor!")
                    return True

            logger.info(f"⏳ {elapsed}s / {timeout_seconds}s (status: {status})")
            await asyncio.sleep(check_interval)
            elapsed += check_interval

        logger.error(f"⏱️ Timeout: {timeout_seconds}s")
        return False

    def format_content_for_gamma(self, content: Dict, content_type: str) -> str:
        """Content'ni Gamma uchun formatlash"""
        if content_type == 'pitch_deck':
            return self._format_pitch_deck(content)
        else:
            return self._format_presentation(content)

    def _format_pitch_deck(self, content: Dict) -> str:
        """Pitch deck - strukturali matn"""
        project_name = content.get('project_name', 'Startup')
        tagline = content.get('tagline', '')
        author = content.get('author', '')

        problem = content.get('problem', '')
        solution = content.get('solution', '')
        market = content.get('market', '')
        business_model = content.get('business_model', '')
        competition = content.get('competition', '')
        advantage = content.get('advantage', '')
        financials = content.get('financials', '')
        team = content.get('team', '')
        milestones = content.get('milestones', '')
        cta = content.get('cta', '')

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
        title = content.get('title', 'Prezentatsiya')
        subtitle = content.get('subtitle', '')
        slides = content.get('slides', [])

        text = f"{title}\n\n{subtitle}\n\n"

        for slide in slides:
            slide_title = slide.get('title', '')
            slide_content = slide.get('content', '')
            bullet_points = slide.get('bullet_points', [])

            text += f"\n{slide_title}\n\n{slide_content}\n"

            if bullet_points:
                for point in bullet_points:
                    text += f"- {point}\n"

            text += "\n"

        return text.strip()