from pydantic import BaseModel


class TelegramAuthData(BaseModel):
    """Telegram WebApp initData validation payload"""
    init_data: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    telegram_id: int
    first_name: str | None = None
    username: str | None = None
