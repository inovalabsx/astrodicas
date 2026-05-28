"""Vendas Bot — Scheduler.

Agendamentos:
- Previsão semanal (sábados às 08:00)
- Lembrete de luas cheias/novas
- Expiração automática de assinaturas (se implementado)

Usa APScheduler integrado ao bot.
"""
import json
import logging
from datetime import datetime, date, timedelta
from urllib import request as urllib_request

from telegram.ext import Application

from src.vendas_bot.settings import settings
from src.vendas_bot.models_vendas import buscar_assinante
from src.database import SessionLocal
from src.database.models import Assinante, Horoscopo, Compra, Signo

logger = logging.getLogger(__name__)

# --- Utilitários ---

WEEKDAYS_PT = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


def _get_proximas_luas() -> list[dict]:
    """Retorna as próximas luas cheias e novas (aproximadas).

    Retorno: lista de dicts com 'tipo' (cheia/nova), 'data', 'nome'
    """
    # Cálculo simplificado com datas conhecidas para 2026
    # Fonte: aproximação baseada em ciclos de ~29.5 dias
    luas = [
        # Segunda metade de 2026 - dados reais aproximados
        {"tipo": "nova", "data": date(2026, 6, 13), "nome": "Lua Nova em Gêmeos"},
        {"tipo": "cheia", "data": date(2026, 6, 28), "nome": "Lua Cheia em Capricórnio"},
        {"tipo": "nova", "data": date(2026, 7, 12), "nome": "Lua Nova em Câncer"},
        {"tipo": "cheia", "data": date(2026, 7, 27), "nome": "Lua Cheia em Aquário"},
        {"tipo": "nova", "data": date(2026, 8, 11), "nome": "Lua Nova em Leão"},
        {"tipo": "cheia", "data": date(2026, 8, 26), "nome": "Lua Cheia em Peixes"},
        {"tipo": "nova", "data": date(2026, 9, 9), "nome": "Lua Nova em Virgem"},
        {"tipo": "cheia", "data": date(2026, 9, 25), "nome": "Lua Cheia em Áries"},
        {"tipo": "nova", "data": date(2026, 10, 9), "nome": "Lua Nova em Libra"},
        {"tipo": "cheia", "data": date(2026, 10, 24), "nome": "Lua Cheia em Touro"},
    ]

    hoje = date.today()
    return [l for l in luas if l["data"] >= hoje][:2]


# --- Funções agendadas ---

async def enviar_previsao_semanal(app: Application):
    """Envia previsão semanal para todos os assinantes ativos nos sábados."""
    logger.info("📅 Enviando previsões semanais...")
    hoje = date.today()
    semana = {
        "proxima": hoje + timedelta(days=7),
        "atual": hoje,
    }

    with SessionLocal() as session:
        assinantes = session.query(Assinante).filter(
            Assinante.ativo == True,
            # telegram_id é o chat_id para DM

        ).all()

    if not assinantes:
        logger.info("Nenhum assinante ativo para previsão semanal.")
        return

    enviadas = 0
    for assinante in assinantes:
        try:
            await app.bot.send_message(
                chat_id=assinante.telegram_id,
                text=(
                    f"📅 *Previsão Semanal AstroDicas*\n\n"
                    f"Olá, {assinante.primeiro_nome}! 🌟\n\n"
                    f"Esta semana traz energias especiais para você.\n"
                    f"Fique atento às oportunidades e confie na sua intuição.\n\n"
                    f"💫 *Dica da semana:* Reserve 5 minutos por dia para "
                    f"meditar ou refletir sobre seus objetivos.\n\n"
                    f"✨ Tenha uma ótima semana!\n"
                    f"— AstroDicas 💫"
                ),
            )
            enviadas += 1
        except Exception as e:
            logger.warning(f"Erro ao enviar previsão para {assinante.telegram_id}: {e}")

    logger.info(f"📅 Previsões enviadas: {enviadas}")


async def verificar_luas(app: Application):
    """Verifica se tem lua cheia/nova próxima e avisa os assinantes."""
    logger.info("🌙 Verificando luas...")
    proximas = _get_proximas_luas()

    if not proximas:
        return

    hoje = date.today()
    for lua in proximas:
        dias_ate = (lua["data"] - hoje).days

        # Avisar 2 dias antes
        if dias_ate != 2:
            continue

        with SessionLocal() as session:
            assinantes = session.query(Assinante).filter(
                Assinante.ativo == True,
            ).all()

        for assinante in assinantes:
            try:
                if lua["tipo"] == "cheia":
                    msg = (
                        f"🌕 *Lua Cheia se aproxima!*\n\n"
                        f"Em 2 dias teremos {lua['nome']}.\n\n"
                        f"✨ As luas cheias são momentos de colheita, "
                        f"culminância e celebração. É hora de reconhecer "
                        f"seus avanços e agradecer pelo que conquistou.\n\n"
                        f"🔮 *Dica:* Faça um banho de ervas ou acenda "
                        f"uma vela branca para harmonizar as energias."
                    )
                else:
                    msg = (
                        f"🌑 *Lua Nova se aproxima!*\n\n"
                        f"Em 2 dias teremos {lua['nome']}.\n\n"
                        f"✨ As luas novas são momentos de recomeço, "
                        f"intenções e novos ciclos. É o momento ideal "
                        f"para planejar seus próximos passos.\n\n"
                        f"🔮 *Dica:* Escreva 3 intenções para este "
                        f"novo ciclo e coloque sob a luz da lua."
                    )

                await app.bot.send_message(
                chat_id=assinante.telegram_id,
                text=msg,
                )
            except Exception as e:
                logger.warning(f"Erro ao avisar lua para {assinante.telegram_id}: {e}")


async def enviar_horoscopo_personalizado(app: Application):
    """Envia horóscopo diário personalizado para cada assinante ativo.

    Gera um texto curto e personalizado via OmniRoute para o signo do assinante.
    Executa todo dia às 06:00.
    """
    logger.info("🌙 Enviando horóscopos personalizados...")

    with SessionLocal() as session:
        assinantes = (
            session.query(Assinante)
            .filter(Assinante.ativo == True)
            .all()
        )

    if not assinantes:
        logger.info("Nenhum assinante ativo para horóscopo personalizado.")
        return

    hoje = date.today()
    dia_semana = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"][
        hoje.weekday()
    ]

    enviadas = 0
    erros = 0

    for assinante in assinantes:
        if not assinante.signo_id:
            logger.warning(f"Assinante {assinante.telegram_id} sem signo definido — pulando")
            continue

        # Buscar signo
        with SessionLocal() as session:
            signo = session.query(Signo).filter_by(id=assinante.signo_id).first()

        if not signo:
            continue

        # Gerar horóscopo via LLM
        prompt = (
            f"Você é um astrólogo brasileiro. Gere um horóscopo diário personalizado "
            f"em português do Brasil para {assinante.primeiro_nome}, "
            f"que é do signo de {signo.nome} ({signo.emoji or ''}).\n\n"
            f"Data: {hoje.strftime('%d/%m/%Y')} ({dia_semana})\n\n"
            f"Formato (máximo 4 parágrafos, ~800 caracteres no total):\n"
            f"- Saudação personalizada\n"
            f"- Energia do dia para o signo\n"
            f"- Dica prática ou conselho\n"
            f"- Mensagem de encerramento positiva\n\n"
            f"Tom: acolhedor, místico, mas com conteúdo prático."
        )

        payload = json.dumps({
            "model": settings.llm_model_text,
            "messages": [
                {"role": "system", "content": "Você é um astrólogo profissional brasileiro que gera horóscopos personalizados e acolhedores."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 512,
        }).encode("utf-8")

        try:
            req = urllib_request.Request(
                f"{settings.llm_base_url}/chat/completions",
                data=payload,
                headers={
                    "Authorization": f"Bearer {settings.ominiroute_api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )

            with urllib_request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                conteudo = result["choices"][0]["message"]["content"].strip()

            msg = (
                f"🌙 *Horóscopo do Dia — {signo.emoji or ''} {signo.nome}*\n"
                f"📅 {hoje.strftime('%d/%m/%Y')}\n\n"
                f"Olá, {assinante.primeiro_nome}! 🌟\n\n"
                f"{conteudo}\n\n"
                f"— AstroDicas 💫"
            )

            await app.bot.send_message(
                chat_id=assinante.telegram_id,
                text=msg,
            )
            enviadas += 1
            logger.info(f"✅ Horóscopo enviado para {assinante.primeiro_nome} ({signo.nome})")

        except Exception as e:
            logger.warning(f"Erro ao enviar horóscopo para {assinante.telegram_id}: {e}")
            erros += 1

    logger.info(f"🌙 Horóscopos personalizados: {enviadas} enviados, {erros} erros")


# --- Função para iniciar o scheduler (chamada da main.py) ---

def configurar_scheduler(app: Application):
    """Configura os jobs agendados."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = AsyncIOScheduler()

    # Previsão semanal — sábados às 08:00
    scheduler.add_job(
        enviar_previsao_semanal,
        CronTrigger(day_of_week="sat", hour=8, minute=0),
        args=[app],
        id="previsao_semanal",
        replace_existing=True,
    )

    # Verificar luas — todo dia às 07:00
    scheduler.add_job(
        verificar_luas,
        CronTrigger(hour=7, minute=0),
        args=[app],
        id="verificar_luas",
        replace_existing=True,
    )

    # Horóscopo personalizado — todo dia às 06:00
    scheduler.add_job(
        enviar_horoscopo_personalizado,
        CronTrigger(hour=6, minute=0),
        args=[app],
        id="horoscopo_personalizado",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("⏰ Scheduler do bot de vendas configurado")
    return scheduler
