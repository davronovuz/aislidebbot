"""
Telegram WebApp initData HMAC-SHA256 verification + JWT generation.
https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote, parse_qsl

from jose import jwt, JWTError
from fastapi import HTTPException, status

from api.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def verify_telegram_init_data(init_data: str) -> dict:
    """
    Verify Telegram WebApp initData.
    Returns parsed user dict on success, raises HTTPException on failure.
    """
    try:
        params = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = params.pop("hash", None)
        if not received_hash:
            raise HTTPException(status_code=400, detail="hash missing from initData")

        # Build data-check-string: sorted key=value pairs joined by \n
        data_check = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))

        # secret_key = HMAC-SHA256(bot_token, "WebAppData")
        secret_key = hmac.new(b"WebAppData", settings.bot_token.encode(), hashlib.sha256).digest()
        expected_hash = hmac.new(secret_key, data_check.encode(), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(expected_hash, received_hash):
            raise HTTPException(status_code=401, detail="Invalid Telegram initData signature")

        user_raw = params.get("user")
        if not user_raw:
            raise HTTPException(status_code=400, detail="user field missing from initData")

        user = json.loads(unquote(user_raw))
        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"initData verification error: {e}")
        raise HTTPException(status_code=401, detail="initData verification failed")


def create_access_token(telegram_id: int, first_name: str | None = None) -> str:
    payload = {
        "sub": str(telegram_id),
        "first_name": first_name or "",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_api_secret(authorization: str) -> bool:
    """Simple Bearer secret for bot→API internal calls"""
    return authorization == f"Bearer {settings.api_secret}"
