"""Telegram bot notifications sent from workers."""
import logging
import httpx

from api.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

TELEGRAM_API = f"https://api.telegram.org/bot{settings.bot_token}"


async def send_message(chat_id: int, text: str, parse_mode: str = "HTML") -> bool:
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            r = await client.post(
                f"{TELEGRAM_API}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
            )
            return r.status_code == 200
        except Exception as e:
            logger.error(f"send_message to {chat_id} failed: {e}")
            return False


async def send_message_id(chat_id: int, text: str, parse_mode: str = "HTML") -> int | None:
    """sendMessage va message_id qaytaradi (keyinchalik edit qilish uchun)."""
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            r = await client.post(
                f"{TELEGRAM_API}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
            )
            if r.status_code == 200:
                return r.json().get("result", {}).get("message_id")
            return None
        except Exception as e:
            logger.error(f"send_message_id to {chat_id} failed: {e}")
            return None


async def edit_message(chat_id: int, message_id: int, text: str, parse_mode: str = "HTML") -> bool:
    """editMessageText — progress yangilash uchun."""
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            r = await client.post(
                f"{TELEGRAM_API}/editMessageText",
                json={
                    "chat_id": chat_id, "message_id": message_id,
                    "text": text, "parse_mode": parse_mode,
                },
            )
            # 400 — "message is not modified" yoki rate limit; xato ham emas
            return r.status_code == 200
        except Exception as e:
            logger.debug(f"edit_message {message_id} to {chat_id} failed: {e}")
            return False


async def delete_message(chat_id: int, message_id: int) -> bool:
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.post(
                f"{TELEGRAM_API}/deleteMessage",
                json={"chat_id": chat_id, "message_id": message_id},
            )
            return r.status_code == 200
        except Exception:
            return False


async def send_document(chat_id: int, file_id: str, caption: str = "", parse_mode: str = "HTML") -> bool:
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            r = await client.post(
                f"{TELEGRAM_API}/sendDocument",
                json={"chat_id": chat_id, "document": file_id, "caption": caption, "parse_mode": parse_mode},
            )
            return r.status_code == 200
        except Exception as e:
            logger.error(f"send_document to {chat_id} failed: {e}")
            return False


async def send_file_bytes(chat_id: int, file_bytes: bytes, filename: str, caption: str = "") -> str | None:
    """Upload file bytes to Telegram, return file_id."""
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            r = await client.post(
                f"{TELEGRAM_API}/sendDocument",
                data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
                files={"document": (filename, file_bytes, "application/octet-stream")},
            )
            if r.status_code == 200:
                result = r.json()
                return result.get("result", {}).get("document", {}).get("file_id")
            logger.error(f"send_file_bytes failed: {r.text}")
            return None
        except Exception as e:
            logger.error(f"send_file_bytes to {chat_id} failed: {e}")
            return None
