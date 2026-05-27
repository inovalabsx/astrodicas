from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: str
    telegram_channel_id: str

    # LLM
    openai_api_key: str
    llm_model: str = "gpt-4o-mini"

    # Database
    database_url: str = "postgresql://postgres:M2X1X8H9klP10T8xxmywPr8ZDq5b4ejYS3aRNaDCvNoIHNnQ2DKYAKu39CHRS0Av@rt6ykrued0duumj46mk70kpw:5432/astrodicas"
    redis_url: str = "redis://redis:6379/0"

    # Pagamento
    asaas_api_key: Optional[str] = None
    asaas_env: str = "sandbox"
    stripe_api_key: Optional[str] = None
    stripe_pix_enabled: bool = True

    # Crypto
    binance_api_key: Optional[str] = None
    binance_secret_key: Optional[str] = None
    crypto_swap_enabled: bool = True

    # Instagram
    instagram_access_token: Optional[str] = None
    instagram_account_id: Optional[str] = None

    # Imagem
    image_api_key: Optional[str] = None
    image_model: str = "dall-e-3"
    image_style: str = "astrodicas"

    # Admin
    admin_username: str = "admin"
    admin_password: str = ""

    # Scheduler
    post_morning: str = "06:00"
    post_afternoon: str = "12:00"
    post_night: str = "18:00"
    timezone: str = "America/Sao_Paulo"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
