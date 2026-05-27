"""AstroDicas — Agendador de conteúdo automático."""

import asyncio
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config.settings import settings
from src.scheduler.publicar import publicar


scheduler = AsyncIOScheduler()


def _get_event_loop():
    """Retorna o event loop ativo, ou cria um se não existir."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop


async def job_publicar(tipo: str):
    """Gera e publica um conteúdo no canal Telegram."""
    try:
        sucesso = await publicar(tipo=tipo)
        if sucesso:
            print(f"[{datetime.now()}] ✅ Conteúdo publicado: {tipo}")
        else:
            print(f"[{datetime.now()}] ⚠️ Conteúdo gerado mas NÃO publicado: {tipo}")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ ERRO em job_publicar({tipo}): {e}")


def init_scheduler():
    """Inicializa os jobs agendados."""

    horarios = [
        (settings.post_morning, "horoscopo"),
        (settings.post_afternoon, "lua"),
        (settings.post_night, "frase"),
    ]

    for horario, tipo in horarios:
        hora, minuto = horario.split(":")
        scheduler.add_job(
            job_publicar,
            trigger=CronTrigger(hour=int(hora), minute=int(minuto)),
            args=[tipo],
            id=f"post_{tipo}",
            replace_existing=True,
        )
        print(f"📅 Agendado: {tipo} às {horario}")

    # Post extra de trânsito nos domingos
    scheduler.add_job(
        job_publicar,
        trigger=CronTrigger(day_of_week="sun", hour=10, minute=0),
        args=["transito"],
        id="post_transito_domingo",
        replace_existing=True,
    )
    print(f"📅 Agendado: trânsito aos domingos 10:00")

    scheduler.start()
    print("✅ Scheduler iniciado com sucesso!")
