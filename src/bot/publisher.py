"""AstroDicas — Scheduler de conteúdo e bot Telegram."""

import asyncio
import logging

from telegram import Bot
from telegram.error import TelegramError

from src.config.settings import settings
from src.scheduler.conteudo_diario import gerar_conteudo

logger = logging.getLogger(__name__)

bot = Bot(token=settings.telegram_bot_token)


async def publicar_no_canal(tipo: str):
    """Gera e publica um conteúdo no canal Telegram do AstroDicas."""
    try:
        conteudo = await gerar_conteudo(tipo=tipo)

        texto = conteudo["conteudo"]
        imagem_url = conteudo.get("imagem_url")

        if imagem_url:
            await bot.send_photo(
                chat_id=settings.telegram_channel_id,
                photo=imagem_url,
                caption=texto,
                parse_mode="HTML",
            )
        else:
            await bot.send_message(
                chat_id=settings.telegram_channel_id,
                text=texto,
                parse_mode="HTML",
            )

        logger.info(f"✅ Publicado: {tipo}")
        return True

    except TelegramError as e:
        logger.error(f"❌ Erro Telegram ao publicar {tipo}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Erro ao gerar/publicar {tipo}: {e}")
        return False


async def enviar_mensagem_direta(chat_id: int, texto: str):
    """Envia mensagem direta para um usuário."""
    try:
        await bot.send_message(chat_id=chat_id, text=texto, parse_mode="HTML")
        return True
    except TelegramError as e:
        logger.error(f"Erro ao enviar mensagem para {chat_id}: {e}")
        return False
