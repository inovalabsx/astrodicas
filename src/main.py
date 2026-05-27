"""AstroDicas — Ponto de entrada do app."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from src.config.settings import settings
from src.database import init_db, SessionLocal

logger = logging.getLogger(__name__)

# Bot Application (inicializado no lifespan)
_bot_app = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _bot_app

    # Inicializa banco
    init_db()
    print("Banco de dados inicializado.")

    # Inicializa agendador de conteúdo
    from src.scheduler.cron import init_scheduler
    init_scheduler()
    print("Agendador de conteúdo iniciado.")

    # Inicializa o bot Telegram (webhook mode)
    from src.bot.handler import criar_app, shutdown_app
    try:
        _bot_app = await criar_app()
        # Configura webhook no Telegram
        webhook_url = f"https://{settings.domain}/webhook"
        await _bot_app.bot.set_webhook(url=webhook_url)
        print(f"Webhook configurado: {webhook_url}")
    except Exception as e:
        logger.warning(f"Bot Telegram não iniciado: {e}")
        _bot_app = None

    yield

    # Shutdown
    if _bot_app:
        await shutdown_app(_bot_app)
    from src.scheduler.cron import scheduler
    scheduler.shutdown()


app = FastAPI(
    title="AstroDicas API",
    description="Backend do ecossistema AstroDicas — signos, mapas e conteúdo automático",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok", "project": "AstroDicas"}


@app.get("/")
async def root():
    return {
        "project": "AstroDicas",
        "version": "0.1.0",
        "status": "Em desenvolvimento",
    }


@app.post("/test/postar/{tipo}")
async def test_postar(tipo: str):
    """Endpoint de teste — dispara publicação manualmente."""
    from src.scheduler.publicar import publicar
    try:
        resultado = await publicar(tipo=tipo)
        return {"ok": resultado, "tipo": tipo, "message": f"Publicação de {tipo} {'concluída' if resultado else 'falhou'}"}
    except Exception as e:
        return {"ok": False, "tipo": tipo, "error": str(e)}


@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Recebe updates do Telegram via webhook."""
    global _bot_app
    if not _bot_app:
        return {"ok": False, "error": "Bot not initialized"}

    update_data = await request.json()
    from src.bot.handler import processar_update
    asyncio.ensure_future(processar_update(_bot_app, update_data))
    return {"ok": True}
