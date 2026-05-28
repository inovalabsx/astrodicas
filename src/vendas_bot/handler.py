"""Vendas Bot — Handlers do Telegram (@astro_dicas_vendasbot).

Fluxo vendável:
  1. /start → apresentação → "Conheça nossos planos"
  2. "Assinar Plano Lua" → explicação → pede SÓ o nome
  3. Nome → já mostra PIX (não pede mais dados)
  4. Admin confirma /ativar → bot avisa "dê /dados"
  5. /dados → pergunta data → hora → cidade
  6. Gera o mapa personalizado
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
(NOME) = range(1)
# Estados pós-pagamento (separados)
(DADOS_NASC, DADOS_HORA, DADOS_CIDADE) = range(10, 13)

# --- PIX info ---
PIX_MSG = (
    "💳 *Para ativar, é só fazer o PIX:*\n\n"
    f"📱 *Chave PIX:* `{settings.pix_chave}`\n"
    f"🏦 *Banco:* {settings.pix_banco}\n"
    f"👤 *Nome:* {settings.pix_nome}\n"
    f"💰 *Valor:* R\$ {settings.preco_plano_lua:.2f}\n\n"
    "📌 Use /pago aqui no bot depois de pagar pra avisar a gente! 💚"
)

# --- Comandos ---

async def start(update: Update, context):
    """Menu principal — apresentação acolhedora e vendável."""
    user = update.effective_user

    # Verificar se usuário já pagou mas não deu os dados ainda
    assinante = buscar_assinante(user.id)
    if assinante and assinante.ativo and not assinante.data_nascimento:
        await update.message.reply_text(
            "🌙 *Bem-vindo de volta!*\n\n"
            "Sua assinatura já está ativa! 🎉\n"
            "Pra começar a receber seu horóscopo, preciso dos seus dados.\n\n"
            "👉 Digite /dados pra fornecer sua data de nascimento! 🔮"
        )
        return

    keyboard = [
        [InlineKeyboardButton("🌙 Assinar Plano Lua — R$9,90/mês", callback_data="assinar_plano_lua")],
        [InlineKeyboardButton("🔮 Comprar Mapa Avulso — R$19,90", callback_data="comprar_mapa")],
        [InlineKeyboardButton("📋 Minhas Assinaturas", callback_data="minhas_assinaturas")],
        [InlineKeyboardButton("❓ Ajuda", callback_data="ajuda")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"✨🌟 *Olá, {user.first_name}!* 🌟✨\n\n"
        "Seja bem-vindo ao *AstroDicas*! 🌙\n\n"
        "Aqui você descobre o que os astros têm a dizer "
        "sobre seu dia, sua vida e seu futuro. 🔮\n"
        "Todo dia um horóscopo feito especialmente *para você*, "
        "com base no seu Mapa Astral!\n\n"
        "👇 *Conheça nossos planos:*",
        reply_markup=reply_markup,
    )


async def dados_command(update: Update, context):
    """Usuário fornece dados de nascimento (pós-pagamento).

    Entry point do conversation handler de dados.
    """
    user = update.effective_user
    assinante = buscar_assinante(user.id)

    if not assinante or not assinante.ativo:
        await update.message.reply_text(
            "❓ Você ainda não tem uma assinatura ativa.\n"
            "Use /start e escolha *Assinar Plano Lua* primeiro! ✨"
        )
        return ConversationHandler.END

    if assinante.data_nascimento:
        await update.message.reply_text(
            "✅ Seus dados já foram cadastrados!\n"
            "Você já deve estar recebendo seu horóscopo personalizado. 🌙"
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "📅 *Qual a sua data de nascimento?* (DD/MM/AAAA)\n\n"
        "Com ela eu descubro seu signo e começo a preparar "
        "seu Mapa Astral personalizado! 🔮"
    )
    return DADOS_NASC


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
            "❓ Você ainda não iniciou uma assinatura.\n"
            "Use /start e escolha *Assinar Plano Lua* primeiro! ✨"
        )
        return

    if assinante.ativo and assinante.data_nascimento:
        await update.message.reply_text(
            "✅ Sua assinatura já está ativa e completa!\n"
            "Você já vai começar a receber seu horóscopo personalizado. 🌙"
        )
        return

    if assinante.ativo and not assinante.data_nascimento:
        await update.message.reply_text(
            "✅ Seu pagamento já foi confirmado! 🎉\n\n"
            "👉 Use /dados pra fornecer sua data de nascimento "
            "e liberar seu Mapa Astral! 🔮"
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
        "✅ *Aviso recebido!*\n\n"
        "Recebemos seu aviso de pagamento. Nosso time vai confirmar "
        "e ativar sua assinatura em breve. ✨\n\n"
        "Assim que for ativada, volte aqui e use /dados pra fornecer "
        "seus dados e liberar seu Mapa Astral personalizado! 🪐\n\n"
        "Se tiver dúvidas: @astro_dicas"
    )


async def ativar_command(update: Update, context):
    """Admin ativa assinante manualmente. Uso: /ativar <telegram_id>

    Após ativar, orienta usuário a usar /dados.
    """
    if not context.args:
        await update.message.reply_text("❌ Uso: `/ativar <telegram_id>`")
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

    if assinante.ativo:
        await update.message.reply_text(f"ℹ️ Assinante `{telegram_id}` já está ativo.")
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

        # Notificar usuário — pedir pra usar /dados
        try:
            await context.bot.send_message(
                chat_id=telegram_id,
                text=(
                    "🎉✨ *PAGAMENTO CONFIRMADO!* ✨🎉\n\n"
                    "Sua assinatura do *Plano Lua* está ativa! 🚀🔥\n\n"
                    "Agora preciso dos seus dados de nascimento pra gerar "
                    "seu Mapa Astral personalizado. 🔮\n\n"
                    "👉 Digite /dados aqui no chat pra começar! 😊🌙"
                ),
            )
        except Exception as e:
            logger.warning(f"Erro ao notificar usuário {telegram_id}: {e}")

        await update.message.reply_text(
            f"✅ Assinante `{telegram_id}` ({assinante.primeiro_nome}) ATIVADO com sucesso!\n"
            "Notificado para usar /dados e fornecer informações de nascimento."
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
            "Com ele você recebe:\n"
            "🪐 *Horóscopo diário* — todo dia uma mensagem dos astros "
            "feita especialmente *para você* 🌟\n"
            "📅 *Previsão semanal* — todo sábado\n"
            "🌕 *Luas cheias e novas* — lembrete na hora certa\n"
            "🎁 *Mapa Astral PDF de brinde* assim que assinar!\n"
            "🔥 *30% OFF* em mapas avulsos\n\n"
            "Vamos começar? 😊\n"
            "*Qual é o seu nome?*"
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
            "💡 *Assinantes do Plano Lua têm 30% OFF!* "
            "(R\$13,93 em vez de R\$19,90)",
            reply_markup=reply_markup,
        )
        return

    elif data == "minhas_assinaturas":
        user = update.effective_user
        assinante = buscar_assinante(user.id)
        if not assinante:
            await query.edit_message_text(
                "📋 *Minhas Assinaturas*\n\n"
                "Você ainda não tem nenhuma assinatura.\n\n"
                "Quer começar? Use /start ✨"
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
                "Você não tem assinaturas ativas no momento."
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
            if assinante.ativo and not assinante.data_nascimento:
                msg += "\n📅 *Importante:* Ainda não tenho seus dados de nascimento!\n"
                msg += "👉 Use /dados pra liberar seu Mapa Astral! 🔮"
            elif ativas and any(c.produto == "plano_lua" for c in ativas):
                msg += "\n🌙 Você recebe o horóscopo diário aqui no DM!"

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

    # Callbacks de mapa (redireciona para o handler de mapa)
    elif data.startswith("mapa_"):
        mapa_tipos = {
            "mapa_astral": "astral",
            "mapa_sinastria": "sinastria",
            "mapa_carreira": "carreira",
            "mapa_revolucao": "revolucao",
        }
        tipo = mapa_tipos.get(data)
        if tipo:
            context.user_data["mapa_tipo"] = tipo
            nomes = {
                "astral": "Mapa Astral Completo",
                "sinastria": "Sinastria (Amor)",
                "carreira": "Mapa da Carreira",
                "revolucao": "Revolução Solar",
            }
            await query.edit_message_text(
                f"🔮 *{nomes[tipo]}*\n\n"
                f"Valor: R\$19,90\n\n"
                "✍️ Digite seu *nome completo* para começar:"
            )
            return

    # Se não reconheceu, retorna None (não inicia conversa)
    return


# --- Fluxo de Assinatura (só nome → PIX) ---

async def receber_nome(update: Update, context):
    """Recebe o nome, já manda o PIX na sequência."""
    nome = update.message.text.strip()
    if len(nome) < 3:
        await update.message.reply_text(
            "😊 Por favor, digite seu *nome completo* (mínimo 3 letras)."
        )
        return NOME

    # Criar assinante no banco (sem dados de nascimento ainda)
    user = update.effective_user
    assinante = criar_assinante(
        telegram_id=user.id,
        primeiro_nome=nome,
        username=user.username,
    )

    # Registrar pagamento pendente
    pagamento = registrar_pagamento(
        assinante_id=assinante.id,
        valor=settings.preco_plano_lua,
        tipo="assinatura",
    )

    await update.message.reply_text(
        f"✍️ Legal, {nome.split()[0]}! 😊\n\n"
        "Seu *Plano Lua* está quase todo seu!\n"
        "É rapidinho — só fazer o PIX e pronto:\n\n"
    )
    await update.message.reply_text(PIX_MSG)

    return ConversationHandler.END


# --- Fluxo pós-pagamento (coleta dados de nascimento) ---

async def receber_dados_nascimento(update: Update, context):
    """Recebe data de nascimento após pagamento confirmado."""
    texto = update.message.text.strip()
    try:
        dia, mes, ano = texto.split("/")
        data_nasc = date(int(ano), int(mes), int(dia))
        if data_nasc > date.today():
            await update.message.reply_text(
                "❓ Essa data é futura! 😅 Digite sua data real (DD/MM/AAAA)."
            )
            return DADOS_NASC
    except (ValueError, IndexError):
        await update.message.reply_text(
            "❓ Formato inválido! Use DD/MM/AAAA (ex: 15/03/1995)"
        )
        return DADOS_NASC

    user = update.effective_user
    assinante = buscar_assinante(user.id)

    if not assinante or not assinante.ativo:
        await update.message.reply_text(
            "❓ Sua assinatura ainda não está ativa.\n"
            "Aguarde a confirmação ou use /start para verificar."
        )
        return ConversationHandler.END

    context.user_data["data_nascimento"] = data_nasc

    # Descobrir signo automaticamente
    signo = descobrir_signo_por_data(data_nasc)
    if signo:
        context.user_data["signo_id"] = signo.id
        context.user_data["signo_nome"] = signo.nome
        await update.message.reply_text(
            f"{signo.emoji or ''} Olha só! Você é de *{signo.nome}*! 🌟\n\n"
            "🕐 Agora, *qual a hora do seu nascimento?* (HH:MM, ex: 14:30)\n\n"
            "💡 Se não souber, digite \"não sei\" (usamos 12:00 como padrão).\n"
            "Isso ajuda a deixar seu mapa mais preciso! 🔮"
        )
    else:
        await update.message.reply_text(
            "⭐ Hmm, não consegui identificar seu signo. "
            "Pode *digitar o nome do seu signo*? (ex: Áries, Touro...)"
        )
        return DADOS_NASC

    return DADOS_HORA


async def receber_dados_hora(update: Update, context):
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
                "❓ Formato inválido! Use HH:MM ou digite \"não sei\" 😊"
            )
            return DADOS_HORA

    await update.message.reply_text(
        "📍 *Qual a cidade onde você nasceu?*\n\n"
        "Isso também é importante pra gerar seu Mapa Astral "
        "com a máxima precisão! 🌍✨"
    )
    return DADOS_CIDADE


async def receber_dados_cidade(update: Update, context):
    """Recebe a cidade e finaliza — avisa que o mapa está sendo preparado."""
    cidade = update.message.text.strip()
    if len(cidade) < 3:
        await update.message.reply_text("😊 Por favor, digite o nome da cidade.")
        return DADOS_CIDADE

    user = update.effective_user
    assinante = buscar_assinante(user.id)
    if not assinante:
        await update.message.reply_text("❓ Erro ao buscar seus dados. Use /start.")
        return ConversationHandler.END

    # Atualizar assinante com dados de nascimento
    from src.database import SessionLocal
    with SessionLocal() as session:
        assinante_db = session.query(type(assinante)).filter_by(id=assinante.id).first()
        if assinante_db:
            assinante_db.data_nascimento = context.user_data["data_nascimento"]
            assinante_db.hora_nascimento = context.user_data.get("hora_nascimento", "12:00")
            assinante_db.cidade_nascimento = cidade
            if context.user_data.get("signo_id"):
                assinante_db.signo_id = context.user_data["signo_id"]
            session.commit()

    await update.message.reply_text(
        f"✨🌟✨🌟✨🌟✨🌟✨🌟✨🌟✨\n\n"
        f"{assinante.primeiro_nome.split()[0]}, recebi seus dados! 📝\n\n"
        f"⭐ *Signo:* {context.user_data.get('signo_nome', '—')}\n"
        f"📅 *Nascimento:* {context.user_data['data_nascimento'].strftime('%d/%m/%Y')} "
        f"às {context.user_data.get('hora_nascimento', '12:00')}\n"
        f"📍 *Cidade:* {cidade}\n\n"
        "🔮 *Seu Mapa Astral personalizado está sendo preparado...*\n\n"
        "Em breve você vai receber tudo aqui no chat! 🌙\n"
        "E todo dia seu horóscopo personalizado vai chegar direto pra você. 🪐\n\n"
        "✨🌟✨🌟✨🌟✨🌟✨🌟✨🌟✨\n\n"
        "Bem-vindo ao *Plano Lua*! 🌙🎉"
    )

    context.user_data.clear()
    return ConversationHandler.END


async def cancelar(update: Update, context):
    """Cancela o fluxo atual."""
    await update.message.reply_text(
        "❌ Tudo bem, operação cancelada. Use /start quando quiser voltar! 😊"
    )
    context.user_data.clear()
    return ConversationHandler.END


# --- Criação do Application ---

def assinar_conversation_handler() -> ConversationHandler:
    """Handler de conversação para fluxo de assinatura (só nome → PIX)."""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^assinar_plano_lua$")],
        states={
            NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_nome)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )


def dados_nascimento_conversation_handler() -> ConversationHandler:
    """Handler para coleta de dados de nascimento PÓS-pagamento.

    Entry point: /dados (comando que verifica se assinante está ativo sem dados).
    """
    return ConversationHandler(
        entry_points=[CommandHandler("dados", dados_command)],
        states={
            DADOS_NASC: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_dados_nascimento)],
            DADOS_HORA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_dados_hora)],
            DADOS_CIDADE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_dados_cidade)],
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

    # Handlers avulsos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", help_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("pago", pago_command))
    app.add_handler(CommandHandler("ativar", ativar_command))

    # Conversation handlers
    app.add_handler(assinar_conversation_handler())
    app.add_handler(dados_nascimento_conversation_handler())

    # Callback handler genérico (botões de menu que não iniciam conv)
    app.add_handler(
        CallbackQueryHandler(
            button_handler,
            pattern="^(comprar_mapa|minhas_assinaturas|ajuda|voltar_menu|mapa_.*)$",
        )
    )

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
