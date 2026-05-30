"""Vendas Bot — Settings específicas.

Herda configurações globais do projeto e adiciona as específicas do bot de vendas.
"""
from src.config.settings import settings as global_settings
from typing import Optional


class VendasSettings:
    """Settings do bot de vendas — carregadas de env vars separadas."""

    # Token do bot de vendas (via env var TELEGRAM_VENDAS_BOT_TOKEN)
    telegram_vendas_bot_token: str = ""

    # Admin
    admin_user_id: int = 0  # Telegram ID do admin (configurar no Coolify)

    # PIX
    pix_chave: str = "astrodicas@pix.com"
    pix_nome: str = "AstroDicas LTDA"
    pix_banco: str = "Nubank"

    # Produtos
    preco_plano_lua: float = 16.90
    preco_mapa_avulso: float = 19.90
    desconto_assinante: float = 0.30  # 30%

    # Pagamentos
    payment_mode: str = "simulado"  # simulado | pix_api
    pix_api_base_url: str = ""
    pix_api_key: str = ""

    # Herdados do settings global
    database_url: str = ""
    ominiroute_api_key: str = ""
    llm_base_url: str = ""
    llm_model_text: str = ""
    dominio: str = ""

    def __init__(self):
        # Tentar carregar de env vars (injetadas pelo Coolify)
        import os

        self.telegram_vendas_bot_token = os.getenv(
            "TELEGRAM_VENDAS_BOT_TOKEN",
            global_settings.telegram_bot_token,  # fallback pro token do bot principal
        )
        try:
            self.admin_user_id = int(os.getenv("ADMIN_USER_ID", "0"))
        except ValueError:
            self.admin_user_id = 0

        self.pix_chave = os.getenv("PIX_CHAVE", self.pix_chave)
        self.pix_nome = os.getenv("PIX_NOME", self.pix_nome)
        self.pix_banco = os.getenv("PIX_BANCO", self.pix_banco)

        self.payment_mode = os.getenv("PAYMENT_MODE", self.payment_mode).strip().lower() or "simulado"
        self.pix_api_base_url = os.getenv("PIX_API_BASE_URL", "").strip()
        self.pix_api_key = os.getenv("PIX_API_KEY", "").strip()

        # Herdar configurações globais
        self.database_url = os.getenv(
            "DATABASE_URL_ASTRODICAS", global_settings.database_url
        )
        self.ominiroute_api_key = os.getenv(
            "OMINIROUTE_API_KEY", global_settings.ominiroute_api_key
        )
        self.llm_base_url = global_settings.llm_base_url
        self.llm_model_text = global_settings.llm_model_text
        self.dominio = os.getenv(
            "VENDAS_DOMINIO", "bot-vendas.astrodicas.inovalabx.com.br"
        )


settings = VendasSettings()
