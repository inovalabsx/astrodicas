"""Vendas Bot — AstroDicas (@astro_dicas_vendasbot).

FastAPI app com webhook do Telegram e scheduler de conteúdo.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.vendas_bot.settings import settings
from src.vendas_bot.handler import criar_app, processar_update, shutdown_app
from src.vendas_bot.scheduler import configurar_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Variável global do bot Telegram
telegram_app = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan: inicia e para o bot Telegram."""
    global telegram_app
    logger.info("🚀 Iniciando bot de vendas AstroDicas...")
    telegram_app = await criar_app()
    logger.info(f"🤖 Bot de vendas rodando em modo webhook")

    # Iniciar scheduler
    scheduler = configurar_scheduler(telegram_app)

    yield

    # Parar scheduler
    if scheduler:
        scheduler.shutdown(wait=False)
    await shutdown_app(telegram_app)
    logger.info("👋 Bot de vendas finalizado")


app = FastAPI(
    title="AstroDicas Vendas Bot",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {"status": "ok", "project": "AstroDicas Vendas"}


@app.get("/health")
async def health():
    return {"status": "ok", "bot": "vendas", "version": "1.0.0"}


@app.post("/webhook")
async def webhook(request: Request):
    """Webhook do Telegram — recebe updates do bot de vendas."""
    if telegram_app is None:
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": "Bot not initialized"},
        )

    try:
        update_data = await request.json()
        await processar_update(telegram_app, update_data)
        return {"ok": True}
    except Exception as e:
        logger.exception("Erro ao processar webhook")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(e)},
        )


@app.post("/webhook/admin")
async def admin_webhook(request: Request):
    """Webhook para comandos administrativos."""
    if telegram_app is None:
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": "Bot not initialized"},
        )

    try:
        update_data = await request.json()
        await processar_update(telegram_app, update_data)
        return {"ok": True}
    except Exception as e:
        logger.exception("Erro ao processar admin webhook")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(e)},
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
