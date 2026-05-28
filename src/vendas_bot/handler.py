"""Vendas Bot — Handlers do Telegram (@astro_dicas_vendasbot).

Fluxos:
  - /start → menu principal
  - Assinar Plano Lua → onboarding (nome, signo, data/hora/local nascimento) → cobrança PIX
  - Comprar Mapa Avulso → seleção → dados → cobrança PIX
  - /pago → usuário avisa que pagou
  - /admin <telegram_id> → admin ativa manualmente
"""
import logging
from datetime import date, datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)

from src.vendas_bot.settings import settings
from src.vendas_bot.models_vendas import (
    get_signos,
    find_signo_by_nome,
    buscar_assinante,
    criar_assinante,
    ativar_assinante,
    registrar_pagamento,
)

logger = logging.getLogger(__name__)

# --- Estados da ConversationHandler ---
(NOME, SIGNO, DATA_NASC, HORA_NASC, CIDADE_NASC, MAPA_SELECAO, MAPA_DADOS) = range(7)

# --- PIX info ---
PIX_MSG = (
    f"💳 *Dados para pagamento via PIX*\n\n"
    f"📱 *Chave PIX:* `{settings.pix_chave}`\n"
    f"🏦 *Banco:* {settings.pix_banco}\n"
    f"👤 *Nome:* {settings.pix_nome}\n\n"
    f"Após realizar o pagamento, envie /pago aqui no bot "
    f"para avisar que você pagou. Nosso time irá confirmar "
    f"e ativar suas compras em breve! ✨"
)

# --- Comandos ---

async def start(update: Update, context):
    """Menu principal do bot de vendas."""
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("🌙 Assinar Plano Lua (R$9,90)", callback_data="assinar_plano_lua")],
        [InlineKeyboardButton("🔮 Comprar Mapa Avulso", callback_data="comprar_mapa")],
        [InlineKeyboardButton("📋 Minhas Assinaturas", callback_data="minhas_assinaturas")],
        [InlineKeyboardButton("❓ Ajuda", callback_data="ajuda")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"✨ Olá, {user.first_name}! Bem-vindo à *AstroDicas Vendas*!\n\n"
        "🌟 Escolha uma opção abaixo:",
        reply_markup=reply_markup,
    )


async def help_cmd(update: Update, context):
    """Comando /ajuda."""
    await update.message.reply_text(
        "❓ *Ajuda - AstroDicas Vendas*\n\n"
        "🌙 *Plano Lua* — R$9,90/mês\n"
        "  • Horóscopo diário personalizado no DM\n"
        "  • Previsão semanal (sábados)\n"
        "  • Lembrete de luas cheias/novas\n"
        "  • 🎁 Mapa Astral PDF de brinde\n"
        "  • 30% OFF em mapas avulsos\n\n"
        "🔮 *Mapas Avulsos* — R$19,90 (assinante: R$13,93)\n"
        "  • Mapa Astral Completo\n"
        "  • Sinastria (Amor)\n"
        "  • Mapa da Carreira\n"
        "  • Revolução Solar\n\n"
        "💳 *Pagamento:* PIX para {settings.pix_chave}\n"
        "  Depois use /pago para avisar\n\n"
        "📞 *Dúvidas:* Fale com @astro_dicas"
    )


async def pago_command(update: Update, context):
    """Usuário avisa que pagou."""
    user = update.effective_user
    assinante = buscar_assinante(user.id)

    if not assinante:
        await update.message.reply_text(
            "❓ Você ainda não iniciou uma assinatura ou compra.\n"
            "Use /start e escolha uma opção primeiro!"
        )
        return

    # Verificar se tem pagamento pendente
    from src.database.models import Pagamento
    from src.database import SessionLocal

    with SessionLocal() as session:
        pag = (
            session.query(Pagamento)
            .filter(
                Pagamento.assinante_id == assinante.id,
                Pagamento.status == "pendente",
            )
            .order_by(Pagamento.criado_em.desc())
            .first()
        )

    if not pag:
        await update.message.reply_text(
            "✅ Você não tem pagamentos pendentes no momento!\n"
            "Seus produtos já devem estar ativos."
        )
        return

    # Notificar admin
    if settings.admin_user_id:
        try:
            await context.bot.send_message(
                chat_id=settings.admin_user_id,
                text=(
                    f"💰 *Novo aviso de pagamento!*\n\n"
                    f"👤 *Usuário:* {user.first_name} (@{user.username or 'sem username'})\n"
                    f"🆔 *Telegram ID:* `{user.id}`\n"
                    f"📋 *Pagamento ID:* `{pag.id}`\n"
                    f"💵 *Valor:* R$ {pag.valor:.2f}\n"
                    f"📦 *Tipo:* {pag.tipo}\n\n"
                    f"Use `/ativar {user.id}` para confirmar manualmente."
                ),
            )
        except Exception as e:
            logger.warning(f"Erro ao notificar admin: {e}")

    await update.message.reply_text(
        f"✅ *Aviso recebido!*\n\n"
        f"Recebemos seu aviso de pagamento. Nosso time irá verificar "
        f"e ativar seus produtos em breve.\n\n"
        f"Se tiver dúvidas, entre em contato: @astro_dicas"
    )


async def ativar_command(update: Update, context):
    """Admin ativa assinante manualmente. Uso: /ativar <telegram_id>"""
    if not context.args:
        await update.message.reply_text(
            "❌ Uso: `/ativar <telegram_id>`\n\n"
            "Exemplo: `/ativar 123456789`"
        )
        return

    if not settings.admin_user_id or update.effective_user.id != settings.admin_user_id:
        await update.message.reply_text("❌ Comando restrito ao admin.")
        return

    try:
        telegram_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Telegram ID inválido.")
        return

    assinante = buscar_assinante(telegram_id)
    if not assinante:
        await update.message.reply_text(f"❌ Assinante com ID `{telegram_id}` não encontrado.")
        return

    if ativar_assinante(assinante.id):
        # Atualizar pagamento pendente para confirmado
        from src.database.models import Pagamento
        from src.database import SessionLocal

        with SessionLocal() as session:
            pag = (
                session.query(Pagamento)
                .filter(
                    Pagamento.assinante_id == assinante.id,
                    Pagamento.status == "pendente",
                )
                .order_by(Pagamento.criado_em.desc())
                .first()
            )
            if pag:
                pag.status = "confirmado"
                session.commit()

        # Notificar o usuário
        try:
            await context.bot.send_message(
                chat_id=telegram_id,
                text=(
                    "🎉✨ *SUA ASSINATURA FOI ATIVADA!* ✨🎉\n\n"
                    "Seu *Plano Lua* está ativo! Agora você vai receber:\n\n"
                    "🌙 Horóscopo diário personalizado aqui no DM\n"
                    "📅 Previsão semanal todo sábado\n"
                    "🌕 Lembrete de luas cheias e novas\n"
                    "🔮 Mapa Astral PDF de brinde (em breve)\n\n"
                    "Obrigado por fazer parte da AstroDicas! ⭐"
                ),
            )
        except Exception as e:
            logger.warning(f"Erro ao notificar usuário {telegram_id}: {e}")

        await update.message.reply_text(
            f"✅ Assinante `{telegram_id}` ({assinante.primeiro_nome}) ATIVADO com sucesso!"
        )
    else:
        await update.message.reply_text("❌ Erro ao ativar assinante.")


# --- Callbacks (botões inline) ---

async def button_handler(update: Update, context):
    """Processa cliques nos botões inline."""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "assinar_plano_lua":
        await query.edit_message_text(
            "🌙 *Plano Lua — R$9,90/mês*\n\n"
            "Você vai receber:\n"
            "• Horóscopo diário personalizado\n"
            "• Previsão semanal (sábados)\n"
            "• Lembrete de luas cheias/novas\n"
            "• 🎁 Mapa Astral PDF de brinde\n"
            "• 30% OFF em mapas avulsos\n\n"
            "Vamos começar! Qual é o seu *nome*?"
        )
        return NOME

    elif data == "comprar_mapa":
        keyboard = [
            [InlineKeyboardButton("🔮 Mapa Astral Completo — R$19,90", callback_data="mapa_astral")],
            [InlineKeyboardButton("💕 Sinastria (Amor) — R$19,90", callback_data="mapa_sinastria")],
            [InlineKeyboardButton("💼 Mapa da Carreira — R$19,90", callback_data="mapa_carreira")],
            [InlineKeyboardButton("🎂 Revolução Solar — R$19,90", callback_data="mapa_revolucao")],
            [InlineKeyboardButton("🔙 Voltar", callback_data="voltar_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🔮 *Mapas Avulsos*\n\n"
            "Escolha o mapa que deseja:\n\n"
            "💡 *Assinantes do Plano Lua têm 30% OFF!*\n"
            "(R$13,93 em vez de R$19,90)",
            reply_markup=reply_markup,
        )
        return

    elif data.startswith("mapa_"):
        # Guardar tipo de mapa selecionado
        context.user_data["mapa_tipo"] = data.replace("mapa_", "")
        nomes = {
            "astral": "Mapa Astral Completo",
            "sinastria": "Sinastria (Amor)",
            "carreira": "Mapa da Carreira",
            "revolucao": "Revolução Solar",
        }
        nome = nomes.get(context.user_data["mapa_tipo"], "Mapa")
        await query.edit_message_text(
            f"🔮 *{nome}*\n\n"
            "Para gerar seu mapa, preciso de alguns dados:\n\n"
            "📅 *Qual a sua data de nascimento?* (DD/MM/AAAA)"
        )
        return MAPA_DADOS

    elif data == "minhas_assinaturas":
        user = update.effective_user
        assinante = buscar_assinante(user.id)
        if not assinante:
            await query.edit_message_text(
                "📋 *Minhas Assinaturas*\n\n"
                "Você ainda não tem nenhuma assinatura ou compra.\n\n"
                "Quer começar? Use /start e escolha uma opção!"
            )
            return

        from src.vendas_bot.models_vendas import assinante_assinaturas_ativas

        ativas = assinante_assinaturas_ativas(assinante.id)
        if not ativas:
            status = "✅ *Inativa*" if not assinante.ativo else "⚠️ *Aguardando confirmação*"
            msg = (
                f"📋 *Minhas Assinaturas*\n\n"
                f"👤 *Nome:* {assinante.primeiro_nome}\n"
                f"📌 *Status:* {status}\n\n"
                "Você não tem assinaturas ou compras ativas no momento."
            )
        else:
            msg = (
                f"📋 *Minhas Assinaturas*\n\n"
                f"👤 *Nome:* {assinante.primeiro_nome}\n"
                f"📌 *Status:* {'✅ Ativo' if assinante.ativo else '⏳ Pendente'}\n\n"
                "*Produtos ativos:*\n"
            )
            for c in ativas:
                msg += f"  • {c.produto}\n"
            if ativas and any(c.produto == "plano_lua" for c in ativas):
                msg += "\n🌙 Você receberá o horóscopo diário aqui no DM!"

        await query.edit_message_text(msg)
        return

    elif data == "ajuda":
        await query.edit_message_text(
            "❓ *Ajuda - AstroDicas Vendas*\n\n"
            f"💳 *Pagamento:* PIX para `{settings.pix_chave}`\n"
            "  Depois use /pago para avisar\n\n"
            "📞 *Dúvidas:* @astro_dicas\n\n"
            "Use /start para voltar ao menu principal."
        )
        return

    elif data == "voltar_menu":
        keyboard = [
            [InlineKeyboardButton("🌙 Assinar Plano Lua (R$9,90)", callback_data="assinar_plano_lua")],
            [InlineKeyboardButton("🔮 Comprar Mapa Avulso", callback_data="comprar_mapa")],
            [InlineKeyboardButton("📋 Minhas Assinaturas", callback_data="minhas_assinaturas")],
            [InlineKeyboardButton("❓ Ajuda", callback_data="ajuda")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🌟 Escolha uma opção:",
            reply_markup=reply_markup,
        )
        return

    return


async def receber_nome(update: Update, context):
    """Recebe o nome do usuário (fluxo assinatura)."""
    nome = update.message.text.strip()
    if len(nome) < 2:
        await update.message.reply_text("❓ Por favor, digite um nome válido (mínimo 2 caracteres).")
        return NOME

    context.user_data["nome"] = nome

    # Mostrar lista de signos
    signos = get_signos()
    signos_text = "\n".join(f"{s.emoji or '⭐'} *{s.nome}* ({s.periodo})" for s in signos)
    await update.message.reply_text(
        f"✍️ Legal, {nome}!\n\n"
        "Agora me diga: qual é o seu *signo*?\n\n"
        f"{signos_text}\n\n"
        "Digite o nome do seu signo (ex: Áries, Touro...)"
    )
    return SIGNO


async def receber_signo(update: Update, context):
    """Recebe o signo do usuário."""
    texto = update.message.text.strip()
    signo = find_signo_by_nome(texto)

    if not signo:
        await update.message.reply_text(
            "❓ Não encontrei esse signo. Digite o nome de um dos 12 signos:\n\n"
            "Áries, Touro, Gêmeos, Câncer, Leão, Virgem, Libra, Escorpião, Sagitário, Capricórnio, Aquário, Peixes"
        )
        return SIGNO

    context.user_data["signo_id"] = signo.id
    context.user_data["signo_nome"] = signo.nome

    await update.message.reply_text(
        f"⭐ {signo.emori or ''} *{signo.nome}*! Ótima escolha!\n\n"
        "📅 Agora, qual a sua *data de nascimento*? (formato: DD/MM/AAAA)\n\n"
        "Isso é usado para gerar seu Mapa Astral de brinde!"
    )
    return DATA_NASC


async def receber_data_nascimento(update: Update, context):
    """Recebe a data de nascimento."""
    texto = update.message.text.strip()
    try:
        dia, mes, ano = texto.split("/")
        data_nasc = date(int(ano), int(mes), int(dia))
    except (ValueError, IndexError):
        await update.message.reply_text(
            "❓ Formato inválido! Use DD/MM/AAAA (ex: 15/03/1995)"
        )
        return DATA_NASC

    context.user_data["data_nascimento"] = data_nasc

    await update.message.reply_text(
        "🕐 Qual a *hora do seu nascimento*? (formato HH:MM, ex: 14:30)\n\n"
        "💡 Se não souber, digite \"não sei\" — usaremos 12:00 como padrão."
    )
    return HORA_NASC


async def receber_hora_nascimento(update: Update, context):
    """Recebe a hora de nascimento."""
    texto = update.message.text.strip().lower()
    if texto in ("não sei", "nao sei", "não", "nao", "ns"):
        context.user_data["hora_nascimento"] = "12:00"
    else:
        # Validar formato
        try:
            h, m = texto.split(":")
            h, m = int(h), int(m)
            if h < 0 or h > 23 or m < 0 or m > 59:
                raise ValueError
            context.user_data["hora_nascimento"] = f"{h:02d}:{m:02d}"
        except (ValueError, IndexError):
            await update.message.reply_text(
                "❓ Formato inválido! Use HH:MM (ex: 14:30) ou digite \"não sei\""
            )
            return HORA_NASC

    await update.message.reply_text(
        "📍 Qual a *cidade onde você nasceu*?\n\n"
        "Isso também é usado para gerar seu Mapa Astral com precisão!"
    )
    return CIDADE_NASC


async def receber_cidade(update: Update, context):
    """Recebe a cidade e finaliza o onboarding."""
    cidade = update.message.text.strip()
    if len(cidade) < 3:
        await update.message.reply_text("❓ Por favor, digite o nome da cidade.")
        return CIDADE_NASC

    context.user_data["cidade_nascimento"] = cidade

    # Criar assinante no banco
    user = update.effective_user
    assinante = criar_assinante(
        telegram_id=user.id,
        primeiro_nome=context.user_data["nome"],
        username=user.username,
        signo_id=context.user_data["signo_id"],
        data_nascimento=context.user_data["data_nascimento"],
        hora_nascimento=context.user_data["hora_nascimento"],
        cidade_nascimento=cidade,
    )

    # Registrar pagamento pendente
    pagamento = registrar_pagamento(
        assinante_id=assinante.id,
        valor=settings.preco_plano_lua,
        tipo="assinatura",
    )

    await update.message.reply_text(
        f"✨ *Tudo pronto, {context.user_data['nome']}!*\n\n"
        f"⭐ *Signo:* {context.user_data['signo_nome']}\n"
        f"📅 *Nascimento:* {context.user_data['data_nascimento'].strftime('%d/%m/%Y')} "
        f"às {context.user_data['hora_nascimento']}\n"
        f"📍 *Cidade:* {cidade}\n\n"
        "Agora é só fazer o pagamento para ativar seu *Plano Lua*!\n\n"
    )
    await update.message.reply_text(PIX_MSG)

    # Limpar user_data
    context.user_data.clear()

    return ConversationHandler.END


async def cancelar(update: Update, context):
    """Cancela o fluxo atual."""
    await update.message.reply_text(
        "❌ Operação cancelada. Use /start para recomeçar."
    )
    context.user_data.clear()
    return ConversationHandler.END


async def mapa_receber_data(update: Update, context):
    """Recebe data de nascimento para mapa avulso."""
    texto = update.message.text.strip()
    try:
        dia, mes, ano = texto.split("/")
        data_nasc = date(int(ano), int(mes), int(dia))
    except (ValueError, IndexError):
        await update.message.reply_text(
            "❓ Formato inválido! Use DD/MM/AAAA (ex: 15/03/1995)"
        )
        return MAPA_DADOS

    context.user_data["mapa_data_nasc"] = data_nasc

    mapa_tipo = context.user_data.get("mapa_tipo", "astral")
    nomes = {
        "astral": "Mapa Astral Completo",
        "sinastria": "Sinastria (Amor)",
        "carreira": "Mapa da Carreira",
        "revolucao": "Revolução Solar",
    }
    nome = nomes.get(mapa_tipo, "Mapa")

    # Verificar se é assinante para calcular preço
    user = update.effective_user
    assinante = buscar_assinante(user.id)
    preco = settings.preco_mapa_avulso
    if assinante and assinante.ativo:
        preco = round(preco * (1 - settings.desconto_assinante), 2)

    # Criar pagamento e assinante (simplificado)
    if not assinante:
        assinante = criar_assinante(
            telegram_id=user.id,
            primeiro_nome=user.first_name or "Cliente",
            username=user.username,
        )

    pagamento = registrar_pagamento(
        assinante_id=assinante.id,
        valor=preco,
        tipo=f"mapa_{mapa_tipo}",
    )

    await update.message.reply_text(
        f"🔮 *{nome}*\n\n"
        f"📅 Data de nascimento: {data_nasc.strftime('%d/%m/%Y')}\n"
        f"💵 *Valor:* R$ {preco:.2f}\n\n"
        "Agora é só fazer o pagamento!\n\n"
    )
    await update.message.reply_text(PIX_MSG)

    context.user_data.clear()
    return ConversationHandler.END


# --- Handlers do bot principal ---

async def receber_mapa_avulso(update: Update, context):
    """Handler genérico para receber texto no fluxo de mapa avulso."""
    # Se chegou aqui sem contexto, ignorar
    if not context.user_data.get("mapa_tipo"):
        return ConversationHandler.END
    return await mapa_receber_data(update, context)


# --- Criação do Application ---

def assinar_conversation_handler() -> ConversationHandler:
    """Handler de conversação para fluxo de assinatura Plano Lua."""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^assinar_plano_lua$")],
        states={
            NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_nome)],
            SIGNO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_signo)],
            DATA_NASC: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_data_nascimento)],
            HORA_NASC: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_hora_nascimento)],
            CIDADE_NASC: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_cidade)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )


def mapa_conversation_handler() -> ConversationHandler:
    """Handler de conversação para compra de mapa avulso."""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^mapa_")],
        states={
            MAPA_DADOS: [MessageHandler(filters.TEXT & ~filters.COMMAND, mapa_receber_data)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )


async def criar_app() -> Application:
    """Cria e configura o Application do Telegram (modo webhook)."""
    app = (
        Application.builder()
        .token(settings.telegram_vendas_bot_token)
        .updater(None)  # Webhook mode
        .build()
    )

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", help_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("pago", pago_command))
    app.add_handler(CommandHandler("ativar", ativar_command))

    # Conversation handlers
    app.add_handler(assinar_conversation_handler())

    # Callback handler genérico (para botões fora de conversação)
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(comprar_mapa|minhas_assinaturas|ajuda|voltar_menu)$"))

    await app.initialize()
    await app.start()
    logger.info("🤖 Bot de Vendas Telegram iniciado (webhook)")
    return app


async def processar_update(app: Application, update_data: dict) -> None:
    """Processa um update do Telegram recebido via webhook."""
    from telegram import Update as TelegramUpdate

    update = TelegramUpdate.de_json(update_data, app.bot)
    if update:
        await app.process_update(update)


async def shutdown_app(app: Application) -> None:
    """Para o bot de forma segura."""
    try:
        await app.stop()
        await app.shutdown()
        logger.info("🤖 Bot de Vendas Telegram parado")
    except Exception as e:
        logger.warning(f"Erro ao parar bot de vendas: {e}")
