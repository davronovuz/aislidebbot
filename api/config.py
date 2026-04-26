from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://aislide:aislide@postgres:5432/aislide"
    database_url_sync: str = "postgresql://aislide:aislide@postgres:5432/aislide"

    # Redis / Dramatiq
    redis_url: str = "redis://redis:6379/0"

    # Telegram
    bot_token: str
    admins: str = ""  # comma-separated IDs

    # OpenAI
    openai_api_key: str

    # Security
    api_secret: str = "aislide_secret_2026"
    jwt_secret: str = "change_me_in_production_jwt_secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Cloudflare R2
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "aislide"
    r2_public_url: str = ""  # optional CDN URL

    # Pixabay
    pixabay_api_key: str = ""

    # Presenton fallback
    presenton_url: str = "http://presenton:80"

    @property
    def admin_ids(self) -> list[int]:
        if not self.admins:
            return []
        return [int(x.strip()) for x in self.admins.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
