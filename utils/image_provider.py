"""
Bepul rasm provayderi — to'rt pog'onali fallback zanjiri:
  1. Wikimedia Commons API (rasmiy, bepul, hech qachon bloklamaydi)
  2. DuckDuckGo Images (bepul, lekin endpoint mo'rt)
  3. Unsplash Source (bepul, ro'yxatdan o'tishsiz)
  4. Pexels API (bepul, agar token bo'lsa)

Hech qaysi pog'ona ishlamasa — None qaytaradi.
Pixabay'dan farqi: relevance kuchliroq, mahalliy/tarixiy mavzularga moslashgan.
"""

import asyncio
import hashlib
import logging
import os
import re
import ssl
import tempfile
import urllib.parse
from pathlib import Path
from typing import Optional

import aiohttp
import certifi

logger = logging.getLogger(__name__)


# ─── Konfiguratsiya ────────────────────────────────────────────────────────

CACHE_DIR = Path(tempfile.gettempdir()) / "aislide_img_cache"
CACHE_DIR.mkdir(exist_ok=True)

USER_AGENT = (
    "AISlideBot/1.0 (https://aislide.uz; davronovtatu@gmail.com) "
    "python-aiohttp/3.x"
)

MIN_IMAGE_BYTES = 5000  # Bundan kichik = noto'g'ri yoki placeholder
MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8MB chegara

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15, connect=5)


# ─── Provider interfeysi ───────────────────────────────────────────────────


class ImageProvider:
    """
    Sinov tartibida rasm topadi:
      1) Wikimedia Commons (tarix, geografiya, biologiya, fan, mashhur shaxslar)
      2) DuckDuckGo (zamonaviy mavzular, abstrakt tushunchalar)
      3) Unsplash Source (bepul yuqori sifatli)
      4) Pexels API (kalit bor bo'lsa)
    """

    def __init__(self, pexels_api_key: Optional[str] = None):
        self.pexels_api_key = pexels_api_key or os.getenv("PEXELS_API_KEY")
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        try:
            ssl_ctx = ssl.create_default_context(cafile=certifi.where())
            connector = aiohttp.TCPConnector(ssl=ssl_ctx, limit=8)
        except Exception:
            connector = aiohttp.TCPConnector(ssl=False, limit=8)
        self._session = aiohttp.ClientSession(
            connector=connector,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
        return self

    async def __aexit__(self, *exc):
        if self._session:
            await self._session.close()

    # ── Public ────────────────────────────────────────────────────────────

    async def fetch(self, query: str) -> Optional[str]:
        """
        Berilgan query uchun rasm topadi va fayl yo'lini qaytaradi.
        Fallback zanjiri: Wikimedia → DuckDuckGo → Unsplash → Pexels.
        """
        if not query or not query.strip():
            return None

        # Cache ko'rib chiqish
        cache_path = self._cache_path(query)
        if cache_path.exists() and cache_path.stat().st_size > MIN_IMAGE_BYTES:
            return str(cache_path)

        # Provayderlar tartibi
        providers = [
            ("wikimedia", self._try_wikimedia),
            ("duckduckgo", self._try_duckduckgo),
            ("unsplash", self._try_unsplash),
        ]
        if self.pexels_api_key:
            providers.append(("pexels", self._try_pexels))

        for name, fn in providers:
            try:
                img_bytes = await fn(query)
                if img_bytes and MIN_IMAGE_BYTES <= len(img_bytes) <= MAX_IMAGE_BYTES:
                    cache_path.write_bytes(img_bytes)
                    logger.info(f"Image OK [{name}] '{query[:40]}': {len(img_bytes)//1024}KB")
                    return str(cache_path)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.debug(f"Image provider [{name}] failed for '{query[:40]}': {e}")
                continue

        logger.warning(f"Image NOT FOUND for '{query[:60]}' (all providers failed)")
        return None

    async def fetch_for_slide(
        self,
        slide_title: str,
        bullet_points: list[str] = None,
        topic: Optional[str] = None,
    ) -> Optional[str]:
        """
        Slayd kontekstidan eng yaxshi query qurib, rasm topadi.
        Avval slayd title + topic, keyin slayd title yolg'iz, keyin topic yolg'iz.
        """
        bullet_points = bullet_points or []
        candidates = self._build_query_candidates(slide_title, bullet_points, topic)

        for q in candidates:
            img_path = await self.fetch(q)
            if img_path:
                return img_path
        return None

    # ── Query qurilishi ───────────────────────────────────────────────────

    @staticmethod
    def _build_query_candidates(
        slide_title: str, bullets: list[str], topic: Optional[str]
    ) -> list[str]:
        """
        Slayd title + topic dan qidiruv kandidatlari ro'yxatini quradi.
        Eng aniq → eng umumiy tartibida.
        """
        title = (slide_title or "").strip()
        topic = (topic or "").strip()

        # Asosiy named entity ni topishga harakat — slayd title dan
        # (Captial letter bilan boshlanuvchi 1-3 so'z birikmasi)
        candidates = []

        # 1. Slayd title to'liq (eng aniq)
        if title and len(title.split()) >= 2:
            candidates.append(title)

        # 2. Title + topic (kontekst aniqlik)
        if title and topic and topic.lower() not in title.lower():
            candidates.append(f"{title} {topic}")

        # 3. Title dan eng konkret 2-3 so'zli birikma
        ent = ImageProvider._extract_entity(title)
        if ent and ent != title:
            candidates.append(ent)

        # 4. Topic yolg'iz (umumiy)
        if topic:
            candidates.append(topic)

        # 5. Birinchi bullet dan birinchi konkret birikma
        if bullets:
            ent_b = ImageProvider._extract_entity(bullets[0])
            if ent_b and ent_b not in candidates:
                candidates.append(ent_b)

        # Takrorlanmaslarni saqlash, har birini tozalash
        seen = set()
        cleaned = []
        for q in candidates:
            q = ImageProvider._clean_query(q)
            if q and q.lower() not in seen:
                seen.add(q.lower())
                cleaned.append(q)
        return cleaned[:5]

    @staticmethod
    def _extract_entity(text: str) -> str:
        """
        Matndan eng konkret 1-3 so'zli birikmani topadi.
        Uzbek/Russian: Capital letter bilan boshlanuvchi ketma-ket so'zlar.
        """
        if not text:
            return ""
        # Markdown va punctuation tozalash
        text = re.sub(r"[*_`#]", "", text)

        # Capital letter bilan boshlanuvchi ketma-ket so'zlarni topish
        matches = re.findall(
            r"\b([A-ZА-ЯЎҚҒҲЁ][a-zа-яўқғҳё']+(?:\s+[A-ZА-ЯЎҚҒҲЁa-zа-яўқғҳё']+){0,3})",
            text,
        )
        if matches:
            # Eng uzun (eng konkret) ni tanlash
            return max(matches, key=len)

        # Capital topilmadi — birinchi 3 so'z
        words = text.split()[:3]
        return " ".join(words) if words else ""

    @staticmethod
    def _clean_query(q: str) -> str:
        """Markdown, punctuation va keyword stop-words ni olib tashlash"""
        q = re.sub(r"[*_`#:]", "", q)
        q = re.sub(r"\s+", " ", q).strip()
        # 60 ta belgidan oshmasin (Wikimedia URL chegarasi)
        return q[:60]

    # ── Cache ─────────────────────────────────────────────────────────────

    @staticmethod
    def _cache_path(query: str) -> Path:
        h = hashlib.md5(query.lower().encode("utf-8")).hexdigest()[:16]
        return CACHE_DIR / f"{h}.jpg"

    # ── 1. Wikimedia Commons ──────────────────────────────────────────────

    async def _try_wikimedia(self, query: str) -> Optional[bytes]:
        """
        Wikimedia Commons orqali qidiruv.
        Eng yaxshi: tarixiy shaxslar, joylar, biologik obyektlar, fan obyektlari.
        """
        api_url = "https://commons.wikimedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f"filetype:bitmap {query}",
            "gsrnamespace": "6",  # Faqat File namespace
            "gsrlimit": "5",
            "prop": "imageinfo",
            "iiprop": "url|size|mime",
            "iiurlwidth": "1280",
        }

        async with self._session.get(api_url, params=params) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()

        pages = data.get("query", {}).get("pages", {})
        if not pages:
            return None

        # Eng yaxshi natijani tanlash (>800 px va valid mime)
        candidates = []
        for page in pages.values():
            ii = page.get("imageinfo", [{}])[0]
            url = ii.get("thumburl") or ii.get("url")
            mime = ii.get("mime", "")
            width = ii.get("width", 0)
            if url and mime.startswith("image/") and width >= 600:
                candidates.append((width, url))

        if not candidates:
            return None

        # Eng katta width (yaxshi sifat)
        candidates.sort(reverse=True)
        for _, url in candidates[:2]:
            img_bytes = await self._download(url)
            if img_bytes:
                return img_bytes
        return None

    # ── 2. DuckDuckGo Images ──────────────────────────────────────────────

    async def _try_duckduckgo(self, query: str) -> Optional[bytes]:
        """
        DuckDuckGo image search — vqd token ni olib, keyin i.js endpoint chaqiradi.
        Bu rasmiy emas, har payt sinishi mumkin — shuning uchun fallback sifatida.
        """
        # Step 1: vqd token olish
        encoded = urllib.parse.quote(query)
        token_url = f"https://duckduckgo.com/?q={encoded}&iax=images&ia=images"

        try:
            async with self._session.get(token_url) as resp:
                html = await resp.text()
        except Exception:
            return None

        m = re.search(r'vqd="?([\d-]+)"?', html) or re.search(r"vqd=([\d-]+)", html)
        if not m:
            return None
        vqd = m.group(1)

        # Step 2: image search
        search_url = (
            f"https://duckduckgo.com/i.js?l=us-en&o=json&q={encoded}&vqd={vqd}"
            f"&f=,,,,,&p=1"
        )
        headers = {
            "Referer": "https://duckduckgo.com/",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
        }

        try:
            async with self._session.get(search_url, headers=headers) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json(content_type=None)
        except Exception:
            return None

        results = data.get("results", [])
        for hit in results[:5]:
            img_url = hit.get("image")
            width = hit.get("width", 0)
            if img_url and width >= 600:
                img_bytes = await self._download(img_url)
                if img_bytes:
                    return img_bytes
        return None

    # ── 3. Unsplash Source (no auth) ──────────────────────────────────────

    async def _try_unsplash(self, query: str) -> Optional[bytes]:
        """
        source.unsplash.com — autentifikatsiyasiz oddiy redirect endpoint.
        1280x720 yuqori sifatli rasm beradi.
        Faqat ingliz tilidagi querylar uchun — kirill yozuvini transliterate qilamiz.
        """
        translit = self._cyrillic_to_latin(query)
        encoded = urllib.parse.quote(translit)
        url = f"https://source.unsplash.com/1280x720/?{encoded}"

        # Source.unsplash 302 redirect qiladi haqiqiy rasmga
        try:
            async with self._session.get(url, allow_redirects=True) as resp:
                if resp.status != 200:
                    return None
                ct = resp.headers.get("Content-Type", "")
                if not ct.startswith("image/"):
                    return None
                img_bytes = await resp.read()
                # Unsplash "no result" rasmidan saqlanish
                if len(img_bytes) < MIN_IMAGE_BYTES:
                    return None
                return img_bytes
        except Exception:
            return None

    # ── 4. Pexels API (optional) ──────────────────────────────────────────

    async def _try_pexels(self, query: str) -> Optional[bytes]:
        translit = self._cyrillic_to_latin(query)
        encoded = urllib.parse.quote(translit)
        url = f"https://api.pexels.com/v1/search?query={encoded}&per_page=3&orientation=landscape"
        headers = {"Authorization": self.pexels_api_key}

        try:
            async with self._session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
        except Exception:
            return None

        photos = data.get("photos", [])
        for p in photos:
            img_url = p.get("src", {}).get("large") or p.get("src", {}).get("original")
            if img_url:
                img_bytes = await self._download(img_url)
                if img_bytes:
                    return img_bytes
        return None

    # ── Yordamchilar ──────────────────────────────────────────────────────

    async def _download(self, url: str) -> Optional[bytes]:
        try:
            async with self._session.get(url) as resp:
                if resp.status != 200:
                    return None
                ct = resp.headers.get("Content-Type", "")
                if not ct.startswith("image/"):
                    return None
                cl = int(resp.headers.get("Content-Length", "0") or "0")
                if cl > MAX_IMAGE_BYTES:
                    return None
                img_bytes = await resp.read()
                if len(img_bytes) < MIN_IMAGE_BYTES:
                    return None
                return img_bytes
        except Exception:
            return None

    @staticmethod
    def _cyrillic_to_latin(text: str) -> str:
        """
        O'zbek-kirill / rus matnini lotin / inglizchaga oddiy transliteratsiya.
        Wikimedia hech qachon kerak emas (ko'p tilli), DuckDuckGo va Unsplash
        uchun foydali.
        """
        cyrillic_map = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'j', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
            'ў': 'o', 'қ': 'q', 'ғ': 'g', 'ҳ': 'h',
        }
        result = []
        for ch in text:
            low = ch.lower()
            if low in cyrillic_map:
                mapped = cyrillic_map[low]
                result.append(mapped.upper() if ch.isupper() else mapped)
            else:
                result.append(ch)
        return "".join(result)


# ─── Standalone test ───────────────────────────────────────────────────────

async def _test():
    queries = [
        "Amir Temur",
        "Toshkent shahri",
        "Sun'iy intellekt",
        "DNA molecule",
        "Photosynthesis",
        "Buyuk Ipak yo'li",
        "Quyosh tizimi",
    ]
    async with ImageProvider() as provider:
        for q in queries:
            path = await provider.fetch(q)
            status = f"✅ {os.path.getsize(path)//1024}KB" if path else "❌ topilmadi"
            print(f"  {q:30s} → {status}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    asyncio.run(_test())
