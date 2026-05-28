"""Vendas Bot — Handlers do Telegram (@astro_dicas_vendasbot).

Fluxo reformulado para ser mais amigável e vendável:
  1. /start → apresentação acolhedora + "Conheça nossos planos"
  2. Clique em "Assinar Plano Lua" → explicação do plano
  3. Pede nome → data de nascimento → signo é descoberto automaticamente
  4. Hora (opcional) + cidade → aviso "seu mapa está sendo preparado" → PIX
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
    descobrir_signo_por_data,
)

logger = logging.getLogger(__name__)

# --- Estados da ConversationHandler ---
(NOME, DATA_NASC, HORA_NASC, CIDADE_NASC) = range(4)

# --- PIX info ---
PIX_MSG = (
    "💳 *Dados para pagamento via PIX*\n\n"
    f"📱 *Chave PIX:* `{settings.pix_chave}`\n"
    f"🏦 *Banco:* {settings.pix_banco}\n"
    f"👤 *Nome:* {settings.pix_nome}\n\n"
    "Após realizar o pagamento, envie /pago aqui no bot "
    "para avisar que você pagou. Nosso time irá confirmar "
    "e ativar suas compras em breve! ✨"
)

# --- Comandos ---

async def start(update: Update, context):
    """Menu principal — apresentação acolhedora e vendável."""
    user = update.effective_user

    mensagem = (
        f"✨🌟 *Olá, {user.first_name}!* 🌟✨\n\n"
        "Seja bem-vindo ao *AstroDicas*! 🌙\n\n"
        "Aqui você vai descobrir o que os astros têm a dizer "
        "sobre seu dia, sua vida e seu futuro. "
        "Todo dia um horóscopo feito especialmente *para você*, "
        "com base no seu Mapa Astral! 🔮\n\n"
        "👇 *Conheça nossos planos:*"
    )

    keyboard = [
        [InlineKeyboardButton("🌙 Assinar Plano Lua — R$9,90/mês", callback_data="assinar_plano_lua")],
        [InlineKeyboardButton("🔮 Comprar Mapa Avulso — R$19,90", callback_data="comprar_mapa")],
        [InlineKeyboardButton("📋 Minhas Assinaturas", callback_data="minhas_assinaturas")],
        [InlineKeyboardButton("❓ Ajuda", callback_data="ajuda")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(mensagem, reply_markup=reply_markup)


async def help_cmd(update: Update, context):
    """Comando /ajuda."""
    await update.message.reply_text(
        "❓ *Ajuda — AstroDicas Vendas*\n\n"
        "🌙 *Plano Lua* — R\$9,90/mês\n"
        "  • Horóscopo diário personalizado no seu DM 🪐\n"
        "  • Previsão semanal todo sábado 📅\n"
        "  • Lembrete de luas cheias e novas 🌕\n"
        "  • 🎁 *Mapa Astral PDF de brinde* ao assinar!\n"
        "  • 30% OFF em todos os mapas avulsos 🔥\n\n"
        "🔮 *Mapas Avulsos* — R\$19,90 (assinante: R\$13,93)\n"
        "  • Mapa Astral Completo\n"
        "  • Sinastria (Amor) 💕\n"
        "  • Mapa da Carreira 💼\n"
        "  • Revolução Solar 🎂\n\n"
        "💳 *Pagamento:* PIX\n"
        f"  Chave: `{settings.pix_chave}`\n"
        "  Depois use /pago para avisar\n\n"
        "📞 *Dúvidas:* Fale com @astro_dicas\n\n"
        "Use /start para voltar ao menu principal ✨"
    )


async def pago_command(update: Update, context):
    """Usuário avisa que pagou."""
    user = update.effective_user
    assinante = buscar_assinante(user.id)

    if not assinante:
        await update.message.reply_text(
            "❓ Você ainda não iniciou uma assinatura ou compra.\n"
            "Use /start e escolha uma opção primeiro! ✨"
        )
        return

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
            "Seus produtos já devem estar ativos. 🌟"
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
        f"Se tiver dúvidas, entre em contato: @astro_dicas ✨"
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
            "🌙 *Plano Lua — R\$9,90/mês*\n\n"
            "Com o Plano Lua você recebe:\n"
            "🪐 *Horóscopo diário* — todo dia uma mensagem dos astros "
            "feita especialmente para o seu signo 🌟\n"
            "📅 *Previsão semanal* — todo sábado um panorama da semana\n"
            "🌕 *Luas cheias e novas* — lembrete na hora certa\n"
            "🎁 *Mapa Astral PDF de brinde* — seu mapa completo!\n"
            "🔥 *30% OFF* em mapas avulsos\n\n"
            "Vamos começar? 😊\n"
            "Primeiro, *qual é o seu nome completo?*"
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
            "(R\$13,93 em vez de R\$19,90)",
            reply_markup=reply_markup,
        )
        return

    elif data.startswith("mapa_"):
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
        return DATA_NASC  # reusa mesmo estado

    elif data == "minhas_assinaturas":
        user = update.effective_user
        assinante = buscar_assinante(user.id)
        if not assinante:
            await query.edit_message_text(
                "📋 *Minhas Assinaturas*\n\n"
                "Você ainda não tem nenhuma assinatura ou compra.\n\n"
                "Quer começar? Use /start e escolha uma opção! ✨"
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
            "❓ *Ajuda — AstroDicas Vendas*\n\n"
            f"💳 *Pagamento:* PIX para `{settings.pix_chave}`\n"
            "  Depois use /pago para avisar\n\n"
            "📞 *Dúvidas:* @astro_dicas\n\n"
            "Use /start para voltar ao menu principal ✨"
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
            "🌟 *AstroDicas* — Escolha uma opção:",
            reply_markup=reply_markup,
        )
        return

    return


# --- Fluxo de Assinatura (novo, mais amigável) ---

async def receber_nome(update: Update, context):
    """Recebe o nome completo do usuário."""
    nome = update.message.text.strip()
    if len(nome) < 3:
        await update.message.reply_text(
            "😊 Por favor, digite seu *nome completo* (mínimo 3 letras)."
        )
        return NOME

    context.user_data["nome"] = nome
    await update.message.reply_text(
        f"✍️ Que nome bonito, {nome.split()[0]}! 😊\n\n"
        "📅 Agora me conta: *qual a sua data de nascimento?* (formato: DD/MM/AAAA)\n\n"
        "💡 É rapidinho — com ela eu descubro seu signo e já começo "
        "a preparar tudo com carinho pra você! 🌟"
    )
    return DATA_NASC


async def receber_data_nascimento(update: Update, context):
    """Recebe a data de nascimento e descobre o signo automaticamente."""
    texto = update.message.text.strip()
    try:
        dia, mes, ano = texto.split("/")
        data_nasc = date(int(ano), int(mes), int(dia))
        if data_nasc > date.today():
            await update.message.reply_text(
                "❓ Essa data é futura! 😅 Digite sua data de nascimento real (DD/MM/AAAA)."
            )
            return DATA_NASC
    except (ValueError, IndexError):
        await update.message.reply_text(
            "❓ Formato inválido! Use DD/MM/AAAA (ex: 15/03/1995)"
        )
        return DATA_NASC

    context.user_data["data_nascimento"] = data_nasc

    # Descobrir signo automaticamente pela data!
    signo = descobrir_signo_por_data(data_nasc)

    if signo:
        context.user_data["signo_id"] = signo.id
        context.user_data["signo_nome"] = signo.nome
        emoji = signo.emoji or ""
        await update.message.reply_text(
            f"{emoji} Olha só! Você é de *{signo.nome}*! Que legal! 🌟\n\n"
            "🕐 Agora, *qual a hora do seu nascimento?* (formato HH:MM, ex: 14:30)\n\n"
            "💡 Se não souber, pode responder \"não sei\" — usamos 12:00 como padrão.\n"
            "Isso ajuda a deixar seu mapa ainda mais preciso! 🔮"
        )
    else:
        await update.message.reply_text(
            "⭐ Hmm, não consegui identificar seu signo com essa data. "
            "Você pode *digitar o nome do seu signo*? (ex: Áries, Touro...)"
        )
        return DATA_NASC  # pede de novo

    return HORA_NASC


async def receber_hora_nascimento(update: Update, context):
    """Recebe a hora de nascimento."""
    texto = update.message.text.strip().lower()
    if texto in ("não sei", "nao sei", "não", "nao", "ns", "nsei"):
        context.user_data["hora_nascimento"] = "12:00"
    else:
        try:
            h, m = texto.split(":")
            h, m = int(h), int(m)
            if h < 0 or h > 23 or m < 0 or m > 59:
                raise ValueError
            context.user_data["hora_nascimento"] = f"{h:02d}:{m:02d}"
        except (ValueError, IndexError):
            await update.message.reply_text(
                "❓ Formato inválido! Use HH:MM (ex: 14:30) ou digite \"não sei\" 😊"
            )
            return HORA_NASC

    await update.message.reply_text(
        "📍 Agora me conta: *qual a cidade onde você nasceu?*\n\n"
        "Isso também é importante para eu gerar seu Mapa Astral "
        "com a maior precisão possível! 🌍✨"
    )
    return CIDADE_NASC


async def receber_cidade(update: Update, context):
    """Recebe a cidade, avisa que o mapa está sendo preparado, e mostra PIX."""
    cidade = update.message.text.strip()
    if len(cidade) < 3:
        await update.message.reply_text("😊 Por favor, digite o nome da cidade.")
        return CIDADE_NASC

    context.user_data["cidade_nascimento"] = cidade

    # Criar assinante no banco
    user = update.effective_user
    assinante = criar_assinante(
        telegram_id=user.id,
        primeiro_nome=context.user_data["nome"],
        username=user.username,
        signo_id=context.user_data.get("signo_id"),
        data_nascimento=context.user_data["data_nascimento"],
        hora_nascimento=context.user_data.get("hora_nascimento", "12:00"),
        cidade_nascimento=cidade,
    )

    # Registrar pagamento pendente
    pagamento = registrar_pagamento(
        assinante_id=assinante.id,
        valor=settings.preco_plano_lua,
        tipo="assinatura",
    )

    # Mensagem de "seu mapa está sendo preparado"
    await update.message.reply_text(
        f"✨🌟✨🌟✨🌟✨🌟✨🌟✨🌟✨\n\n"
        f"{context.user_data['nome'].split()[0]}, recebemos seus dados! 📝\n\n"
        f"⭐ *Seu signo:* {context.user_data.get('signo_nome', '—')}\n"
        f"📅 *Nascimento:* {context.user_data['data_nascimento'].strftime('%d/%m/%Y')} "
        f"às {context.user_data.get('hora_nascimento', '12:00')}\n"
        f"📍 *Cidade:* {cidade}\n\n"
        "🔮 *Seu Mapa Astral personalizado está sendo preparado...*\n\n"
        "Assim que seu pagamento for confirmado, tudo chega direto "
        "aqui no nosso chat! 🌙\n\n"
        "✨🌟✨🌟✨🌟✨🌟✨🌟✨🌟✨"
    )

    # Agora a parte do pagamento
    await update.message.reply_text(
        "💳 *Para ativar seu Plano Lua, é só fazer o PIX:*\n\n"
        f"📱 *Chave PIX:* `{settings.pix_chave}`\n"
        f"🏦 *Banco:* {settings.pix_banco}\n"
        f"👤 *Nome:* {settings.pix_nome}\n"
        f"💰 *Valor:* R\$ {settings.preco_plano_lua:.2f}\n\n"
        "📌 Depois de pagar, use o comando /pago aqui no bot "
        "para avisar a gente! 💚"
    )

    # Limpar user_data
    context.user_data.clear()

    return ConversationHandler.END


async def cancelar(update: Update, context):
    """Cancela o fluxo atual."""
    await update.message.reply_text(
        "❌ Tudo bem, operação cancelada. Use /start quando quiser voltar! 😊"
    )
    context.user_data.clear()
    return ConversationHandler.END


# --- Fluxo de Mapa Avulso ---

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
        return DATA_NASC

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
        await update.message.reply_text(
            "🎉 *Assinante detectado!* Você ganhou 30% OFF! 🔥"
        )

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
        f"📅 Data: {data_nasc.strftime('%d/%m/%Y')}\n"
        f"💵 *Valor:* R\$ {preco:.2f}\n\n"
        "✨ Seu mapa já está sendo preparado!\n\n"
        "Agora é só fazer o pagamento:"
    )
    await update.message.reply_text(PIX_MSG)

    context.user_data.clear()
    return ConversationHandler.END


async def receber_mapa_avulso(update: Update, context):
    """Handler genérico para receber texto no fluxo de mapa avulso."""
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
            DATA_NASC: [MessageHandler(filters.TEXT & ~filters.COMMAND, mapa_receber_data)],
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
