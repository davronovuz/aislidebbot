from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.database import get_db
from api.models.user import User
from api.schemas.auth import TelegramAuthData, TokenResponse
from api.services.auth import verify_telegram_init_data, create_access_token
from datetime import datetime, timezone

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/telegram", response_model=TokenResponse)
async def auth_telegram(body: TelegramAuthData, db: AsyncSession = Depends(get_db)):
    """
    Exchange Telegram WebApp initData for a JWT access token.
    Creates the user row on first visit.
    """
    tg_user = verify_telegram_init_data(body.init_data)
    telegram_id = int(tg_user["id"])

    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=tg_user.get("username"),
            first_name=tg_user.get("first_name"),
            last_name=tg_user.get("last_name"),
            free_presentations=1,
        )
        db.add(user)
        await db.flush()
    else:
        user.username = tg_user.get("username") or user.username
        user.first_name = tg_user.get("first_name") or user.first_name
        user.last_name = tg_user.get("last_name") or user.last_name
        user.last_active = datetime.now(timezone.utc)

    token = create_access_token(telegram_id, tg_user.get("first_name"))
    return TokenResponse(
        access_token=token,
        telegram_id=telegram_id,
        first_name=user.first_name,
        username=user.username,
    )
