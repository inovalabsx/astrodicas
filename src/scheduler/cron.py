"""AstroDicas — Agendador de conteúdo automático."""

import asyncio
from datetime import datetime, date, timedelta

from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.config.settings import settings
from src.scheduler.publicar import publicar
from src.database import SessionLocal

TZ = settings.timezone  # America/Sao_Paulo
TZ_OBJ = ZoneInfo(TZ)


def _now() -> datetime:
    """Retorna datetime com timezone do Brasil."""
    return datetime.now(TZ_OBJ)


def _hoje() -> date:
    """Retorna data atual no Brasil."""
    return _now().date()


# Horários agendados (hora, minuto, tipo)
HORARIOS = [
    (settings.post_morning, "horoscopo"),
    (settings.post_afternoon, "lua"),
    (settings.post_night, "frase"),
]
# Extra: domingo 10:00
TRANSITO_HORARIO = "10:00"


def _ultima_postagem_hoje(tipo: str) -> datetime | None:
    """Retorna o horário da última postagem bem-sucedida de hoje para o tipo.

    Consulta a tabela postagens filtrando por tipo e data de hoje.
    Retorna None se não houver postagem ou se todas falharam.
    """
    try:
        db = SessionLocal()
        from sqlalchemy import text
        result = db.execute(
            text(
                "SELECT publicada_em FROM postagens "
                "WHERE tipo = :tipo AND publicada_em IS NOT NULL "
                "AND DATE(publicada_em AT TIME ZONE 'UTC') = :hoje "
                "ORDER BY publicada_em DESC LIMIT 1"
            ),
            {"tipo": tipo, "hoje": _hoje().isoformat()},
        ).scalar()
        return result
    except Exception:
        return None
    finally:
        try:
            db.close()
        except Exception:
            pass


def _tem_postagem_hoje(tipo: str) -> bool:
    """Verifica se já existe postagem publicada hoje para o tipo."""
    ultima = _ultima_postagem_hoje(tipo)
    return ultima is not None


def _horario_passou(hora_str: str, tolerancia_min: int = 30) -> bool:
    """Verifica se o horário + tolerância já passou no fuso Brasil."""
    agora = _now()
    try:
        h, m = map(int, hora_str.split(":"))
        limite = agora.replace(hour=h, minute=m, second=0, microsecond=0) + timedelta(
            minutes=tolerancia_min
        )
        return agora >= limite
    except Exception:
        return False


async def _repor_se_perdido(tipo: str, hora_str: str):
    """Se o horário + 30 min já passou e não há postagem hoje, dispara."""
    if _horario_passou(hora_str) and not _tem_postagem_hoje(tipo):
        logger.info(
            f"[FALLBACK] Postagem {tipo} perdida (horário {hora_str} passou sem postar) — repondo..."
        )
        sucesso = await publicar(tipo=tipo)
        if sucesso:
            logger.info(f"[FALLBACK] ✅ {tipo} reposto com sucesso!")
        else:
            logger.warning(f"[FALLBACK] ❌ Falha ao repor {tipo}")
        return sucesso
    return False


async def job_publicar(tipo: str):
    """Gera e publica um conteúdo no canal Telegram."""
    try:
        sucesso = await publicar(tipo=tipo)
        if sucesso:
            print(f"[{_now()}] Conteudo publicado: {tipo}")
        else:
            print(f"[{_now()}] Aviso: Conteudo gerado mas NAO publicado: {tipo}")
    except Exception as e:
        print(f"[{_now()}] ERRO em job_publicar({tipo}): {e}")
    finally:
        _log_status(tipo)


# ── Watchdog: verifica periodicamente se algum post foi perdido ──────

_ultimos_logs: dict[str, datetime] = {}


def _log_status(tipo: str):
    """Registra o timestamp do último post/log."""
    _ultimos_logs[tipo] = _now()
    # Limpa logs antigos (mais de 24h)
    limite = _now() - timedelta(hours=24)
    for k in list(_ultimos_logs.keys()):
        if _ultimos_logs[k] < limite:
            del _ultimos_logs[k]


async def watchdog_verificar():
    """Executado a cada 15 minutos.

    Verifica se algum horário agendado passou (com tolerância de 30 min)
    sem que a postagem correspondente tenha sido feita. Se sim, dispara
    o fallback automaticamente.
    """
    agora = _now()
    hora_atual = agora.hour
    minuto_atual = agora.minute

    # Verifica horários regulares (manhã, tarde, noite)
    for hora_str, tipo in HORARIOS:
        await _repor_se_perdido(tipo, hora_str)

    # Verifica trânsito (domingo)
    if agora.weekday() == 6:  # domingo
        await _repor_se_perdido("transito", TRANSITO_HORARIO)


scheduler = AsyncIOScheduler()


def init_scheduler():
    """Inicializa os jobs agendados + watchdog + startup recovery."""

    for horario, tipo in HORARIOS:
        hora, minuto = horario.split(":")
        scheduler.add_job(
            job_publicar,
            trigger=CronTrigger(hour=int(hora), minute=int(minuto), timezone=TZ),
            args=[tipo],
            id=f"post_{tipo}",
            replace_existing=True,
        )
        print(f"Agendado: {tipo} as {horario} BRT")

    # Post extra de trânsito nos domingos
    scheduler.add_job(
        job_publicar,
        trigger=CronTrigger(day_of_week="sun", hour=10, minute=0, timezone=TZ),
        args=["transito"],
        id="post_transito_domingo",
        replace_existing=True,
    )
    print(f"Agendado: transito aos domingos 10:00 BRT")

    # Watchdog: a cada 15 minutos verifica posts perdidos
    scheduler.add_job(
        watchdog_verificar,
        trigger=IntervalTrigger(minutes=15, timezone=TZ),
        id="watchdog_fallback",
        replace_existing=True,
    )
    print("Watchdog fallback: a cada 15 minutos")

    scheduler.start()
    print("Scheduler iniciado com sucesso!")

    # ── Startup recovery: verifica posts perdidos logo na inicialização ──
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Já tem loop rodando (FastAPI lifespan) — cria task
            asyncio.ensure_future(_startup_recovery())
        else:
            # Loop parado — roda síncrono
            loop.run_until_complete(_startup_recovery())
    except RuntimeError:
        # Sem loop ativo ainda — agendar pra rodar em breve
        scheduler.add_job(
            _startup_recovery,
            trigger=IntervalTrigger(seconds=10, timezone=TZ),
            id="startup_recovery",
            max_instances=1,
            replace_existing=True,
        )
        print("Startup recovery agendado para +10s")


async def _startup_recovery():
    """Verifica todos os horários na inicialização do container.

    Roda uma vez após o scheduler iniciar. Se algum post do dia já
    deveria ter sido feito (hora + tolerância passou) e não foi postado,
    dispara o fallback.
    """
    # Pequeno delay pra dar tempo do banco conectar etc
    await asyncio.sleep(5)

    print(f"[STARTUP] Verificando postagens perdidas ({_now()})...")
    recuperados = 0

    # Verifica posts regulares
    for hora_str, tipo in HORARIOS:
        if await _repor_se_perdido(tipo, hora_str):
            recuperados += 1

    # Verifica trânsito (se for domingo)
    if _now().weekday() == 6:
        if await _repor_se_perdido("transito", TRANSITO_HORARIO):
            recuperados += 1

    if recuperados > 0:
        print(f"[STARTUP] ✅ {recuperados} postagen(s) recuperada(s)!")
    else:
        print("[STARTUP] Nenhuma postagem perdida encontrada.")
