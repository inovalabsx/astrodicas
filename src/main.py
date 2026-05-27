"""AstroDicas — Ponto de entrada do app."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config.settings import settings
from src.database import init_db, SessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup e shutdown do app."""
    # Inicializa banco
    init_db()
    print("Banco de dados inicializado.")

    # Inicializa agendador de conteúdo
    from src.scheduler.cron import init_scheduler
    init_scheduler()
    print("Agendador de conteúdo iniciado.")

    yield

    # Shutdown
    scheduler = app.state.get("scheduler")
    if scheduler:
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


# Import routers quando criados
# from src.admin.api import router as admin_router
# app.include_router(admin_router, prefix="/admin")
