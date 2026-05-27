"""AstroDicas — Handler do bot Telegram (webhook)."""

import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from src.config.settings import settings

logger = logging.getLogger(__name__)


async def start(update: Update, context):
    """Comando /start — boas-vindas."""
    user = update.effective_user
    await update.message.reply_text(
        f"✨ Olá, {user.first_name}! Bem-vindo ao AstroDicas!\n\n"
        "Sou seu guia astral pessoal. Aqui você pode:\n\n"
        "🌙 Ver o horóscopo do dia\n"
        "⭐ Saber sua previsão personalizada\n"
        "🔮 Comprar seu mapa astral completo em PDF\n"
        "💎 Assinar conteúdo premium diário\n\n"
        "Use /menu para ver todas as opções."
    )


async def menu(update: Update, context):
    """Comando /menu — opções disponíveis."""
    keyboard = [
        [InlineKeyboardButton("🌙 Horóscopo do Dia", callback_data="horoscopo_hoje")],
        [InlineKeyboardButton("🔮 Mapa Astral PDF", callback_data="mapa_astral")],
        [InlineKeyboardButton("💎 Assinatura Premium", callback_data="assinatura")],
        [InlineKeyboardButton("⭐ Sobre o AstroDicas", callback_data="sobre")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🌟 Escolha uma opção:", reply_markup=reply_markup
    )


async def button_handler(update: Update, context):
    """Processa cliques nos botões inline."""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "horoscopo_hoje":
        await query.edit_message_text(
            "🔮 O horóscopo é publicado automaticamente no canal @AstroDicas "
            "três vezes ao dia!\n\n"
            "👉 Entre no canal para conferir: @AstroDicas"
        )
    elif data == "mapa_astral":
        await query.edit_message_text(
            "🔮 **Mapa Astral Personalizado em PDF**\n\n"
            "Receba seu mapa completo com:\n"
            "• Posição dos planetas no seu nascimento\n"
            "• Interpretação de cada casa astrológica\n"
            "• Aspectos planetários\n"
            "• Previsões personalizadas\n\n"
            "💰 **Valor: R$ 49,90**\n\n"
            "Quer encomendar o seu? Em breve disponível! 🚀"
        )
    elif data == "assinatura":
        await query.edit_message_text(
            "💎 **Assinatura Premium AstroDicas**\n\n"
            "Conteúdo exclusivo diário:\n"
            "• Horóscopo detalhado personalizado\n"
            "• Previsão semanal por signo\n"
            "• Trânsitos astrológicos\n"
            "• Dicas de autoconhecimento\n\n"
            "💰 **R$ 19,90/mês**\n\n"
            "Em breve! 🚀"
        )
    elif data == "sobre":
        await query.edit_message_text(
            "⭐ **AstroDicas**\n\n"
            "Conteúdo astrológico de qualidade em português!\n\n"
            "🌙 Horóscopos diários\n"
            "🔮 Mapas astrais personalizados\n"
            "💎 Conteúdo premium exclusivo\n"
            "⭐ Numerologia\n\n"
            "Siga @AstroDicas no Telegram e Instagram!"
        )


async def receber_mapa(update: Update, context):
    """Recebe dados do usuário para gerar mapa astral."""
    texto = update.message.text
    await update.message.reply_text(
        "Obrigado! Seus dados foram recebidos. "
        "Em breve você poderá solicitar seu mapa completo aqui mesmo! 🚀"
    )


async def criar_app() -> Application:
    """Cria e configura o Application do Telegram (modo webhook)."""
    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .updater(None)  # Sem polling — usaremos webhook via FastAPI
        .build()
    )

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_mapa))

    await app.initialize()
    await app.start()
    logger.info("🤖 Bot Telegram iniciado (webhook)")
    return app


async def processar_update(app: Application, update_data: dict) -> None:
    """Processa um update do Telegram recebido via webhook."""
    update = Update.de_json(update_data, app.bot)
    if update:
        await app.process_update(update)


async def shutdown_app(app: Application) -> None:
    """Para o bot de forma segura."""
    try:
        await app.stop()
        await app.shutdown()
        logger.info("🤖 Bot Telegram parado")
    except Exception as e:
        logger.warning(f"Erro ao parar bot: {e}")
