"""Vendas Bot — Handlers do Telegram (@astro_dicas_vendasbot).

Fluxo vendável simplificado:
  1. /start → apresentação → "Conheça nossos planos"
  2. "Assinar Plano Lua" → explicação → já mostra PIX (sem perguntar nada)
  3. /pago → avisa admin
  4. Admin /ativar → confirma → "use /dados"
  5. /dados → pergunta NOME → DATA → HORA → CIDADE
  6. Gera o mapa personalizado
"""
import logging
import os
from datetime import date, datetime
from decimal import Decimal

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
from src.vendas_bot.payments import payment_provider
from src.vendas_bot.afiliados import (
    get_or_create_afiliado,
    registrar_lead_por_codigo,
    atualizar_pix_afiliado,
    liberar_comissoes_vencidas,
    registrar_comissao_por_pagamento,
    saldo_afiliado,
    solicitar_saque,
)

logger = logging.getLogger(__name__)


def _resolver_tipo_mapa_do_assinante(assinante_id: int) -> str:
    """Resolve tipo de mapa a entregar com base no pagamento/compra recente."""
    from src.database import SessionLocal
    from src.database.models import Compra, Pagamento

    with SessionLocal() as session:
        compra = (
            session.query(Compra)
            .filter(Compra.assinante_id == assinante_id, Compra.ativo == True)
            .order_by(Compra.criado_em.desc())
            .first()
        )
        if compra and compra.produto:
            produto = str(compra.produto).lower()
            if produto in {"mapa_astral", "astral"}:
                return "astral"
            if produto in {"mapa_sinastria", "sinastria"}:
                return "sinastria"
            if produto in {"mapa_carreira", "carreira"}:
                return "carreira"
            if produto in {"mapa_prosperidade", "prosperidade"}:
                return "prosperidade"
            if produto in {"mapa_sinastria_sem", "sinastria_sem"}:
                return "sinastria_sem"

        pag = (
            session.query(Pagamento)
            .filter(Pagamento.assinante_id == assinante_id)
            .order_by(Pagamento.criado_em.desc())
            .first()
        )

    if pag and pag.tipo:
        tipo = str(pag.tipo).lower()
        if tipo.startswith("mapa_"):
            tipo = tipo.removeprefix("mapa_")
        if tipo in {"astral", "sinastria", "carreira", "prosperidade", "sinastria_sem"}:
            return tipo

    return "astral"


async def _gerar_e_enviar_mapa_premium(update: Update, context, assinante) -> bool:
    """Gera e envia PDF premium real para o cliente no fluxo de produção."""
    from src.vendas_bot.mapa_premium import gerar_mapa_premium

    tipo = _resolver_tipo_mapa_do_assinante(assinante.id)
    nome = (assinante.primeiro_nome or update.effective_user.first_name or "Cliente").strip()
    data_nasc = assinante.data_nascimento
    hora_nasc = assinante.hora_nascimento or "12:00"
    cidade = assinante.cidade_nascimento or "São Paulo"
    signo_nome = context.user_data.get("signo_nome", "Peixes")

    await update.message.reply_text(
        f"🛠️ Gerando seu PDF premium ({tipo})... pode levar alguns minutinhos."
    )

    pdf_path = gerar_mapa_premium(
        nome=nome,
        signo=signo_nome,
        data_nascimento=data_nasc,
        hora_nascimento=hora_nasc,
        cidade=cidade,
        tipo=tipo,
    )

    if not pdf_path or not os.path.exists(pdf_path):
        await update.message.reply_text(
            "⚠️ Deu erro na geração agora. Vou tentar de novo automaticamente..."
        )
        pdf_path = gerar_mapa_premium(
            nome=nome,
            signo=signo_nome,
            data_nascimento=data_nasc,
            hora_nascimento=hora_nasc,
            cidade=cidade,
            tipo=tipo,
        )

    if not pdf_path or not os.path.exists(pdf_path):
        logger.error("Falha ao gerar mapa premium após retry")
        await update.message.reply_text(
            "❌ Não consegui gerar seu mapa agora. Já deixei sinalizado pra equipe resolver já."
        )
        return False

    with open(pdf_path, "rb") as f:
        await context.bot.send_document(
            chat_id=update.effective_user.id,
            document=f,
            filename=os.path.basename(pdf_path),
            caption="✨ Seu Mapa Premium chegou!",
            read_timeout=180,
            write_timeout=180,
            connect_timeout=60,
            pool_timeout=60,
        )

    await update.message.reply_text("✅ Pronto! Te entreguei o PDF premium completo aqui no chat.")
    return True


# Estados pós-pagamento (coleta de dados)
(DADOS_NOME, DADOS_NASC, DADOS_HORA, DADOS_CIDADE) = range(10, 14)

# --- Pagamento info ---
def _mensagem_pix_manual(valor: float) -> str:
    return (
        "💳 *Para ativar, é só fazer o PIX:*\n\n"
        f"📱 *Chave PIX:* `{settings.pix_chave}`\n"
        f"🏦 *Banco:* {settings.pix_banco}\n"
        f"👤 *Nome:* {settings.pix_nome}\n"
        f"💰 *Valor:* R$ {valor:.2f}\n\n"
        "📌 Depois use /pago aqui no bot pra avisar a gente. 💚"
    )


def _get_or_create_assinante(user):
    assinante = buscar_assinante(user.id)
    if assinante:
        return assinante
    return criar_assinante(
        telegram_id=user.id,
        primeiro_nome=user.first_name or "Anônimo",
        username=user.username,
    )


def _criar_pagamento(assinante_id: int, valor: float, tipo: str, payer_ref: str):
    intent = payment_provider.create_payment(
        amount=valor,
        description=tipo,
        payer_ref=payer_ref,
    )
    pagamento = registrar_pagamento(
        assinante_id=assinante_id,
        valor=valor,
        tipo=tipo,
        status=intent.status,
        pagamento_id=intent.external_id,
    )
    return pagamento, intent


# --- Comandos ---

async def start(update: Update, context):
    """Menu principal — apresentação acolhedora e vendável."""
    user = update.effective_user

    # Libera comissões vencidas em oportunidades de entrada no fluxo
    try:
        liberar_comissoes_vencidas()
    except Exception as e:
        logger.warning(f"Erro ao liberar comissões vencidas: {e}")

    # Captura referral via deep link: /start AF000123
    if context.args:
        codigo_ref = (context.args[0] or "").strip().upper()
        if codigo_ref and codigo_ref.startswith("AF"):
            ok_ref = registrar_lead_por_codigo(codigo_ref, user.id, origem="telegram_start")
            if ok_ref:
                await update.message.reply_text("🎁 Você entrou por link de indicação e já garantiu benefícios especiais!")

    # Verificar se usuário já pagou mas não deu os dados ainda
    assinante = buscar_assinante(user.id)
    if assinante and assinante.ativo and not assinante.data_nascimento:
        await update.message.reply_text(
            "🌙 *Bem-vindo de volta!*\n\n"
            "Sua assinatura já está ativa! 🎉\n"
            "Pra começar a receber seu horóscopo, preciso dos seus dados.\n\n"
            "👉 Digite /dados pra começar! 🔮"
        )
        return

    keyboard = [
        [InlineKeyboardButton("🌙 Assinar Plano Lua — R$16,90/mês", callback_data="assinar_plano_lua")],
        [InlineKeyboardButton("🔮 Comprar Mapa — R$19,90", callback_data="comprar_mapa")],
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

    if assinante.data_nascimento and assinante.primeiro_nome:
        await update.message.reply_text(
            "✅ Seus dados já foram cadastrados!\n"
            "Você já deve estar recebendo seu horóscopo personalizado. 🌙"
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "✍️ Primeiro, *qual é o seu nome completo?* 😊"
    )
    return DADOS_NOME


async def help_cmd(update: Update, context):
    """Comando /ajuda."""
    await update.message.reply_text(
        "❓ *Ajuda — AstroDicas Vendas*\n\n"
        "🌙 *Plano Lua* — R$16,90/mês\n"
        "  • Horóscopo diário personalizado no seu DM 🪐\n"
        "  • Previsão semanal todo sábado 📅\n"
        "  • Lembrete de luas cheias e novas 🌕\n"
        "  • 🎁 *Mapa Astral PDF de brinde* ao assinar!\n"
        "  • 30% OFF em todos os mapas 🔥\n\n"
        "🔮 *Mapa* — R$19,90 (assinante: R$13,93)\n"
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


async def afiliado_command(update: Update, context):
    """Ativa/consulta conta de afiliado e retorna link próprio."""
    user = update.effective_user
    assinante = _get_or_create_assinante(user)
    afiliado = get_or_create_afiliado(assinante.id)
    link = f"https://t.me/{context.bot.username}?start={afiliado.codigo}"

    await update.message.reply_text(
        "🤝 *Programa de Afiliados AstroDicas*\n\n"
        f"🔗 *Seu código:* `{afiliado.codigo}`\n"
        f"🔗 *Seu link:* {link}\n\n"
        "📌 Regras:\n"
        "• Comissão: *40%* por venda confirmada\n"
        "• Liberação: *D+7*\n"
        "• Saque mínimo: *R$ 10,00*\n"
        "• Chave PIX obrigatória para saque\n\n"
        "Comandos:\n"
        "`/pix <sua_chave>` para cadastrar PIX\n"
        "`/afiliado_saldo` para ver saldo\n"
        "`/afiliado_sacar` para solicitar saque"
    )


async def afiliado_pix_command(update: Update, context):
    """Cadastra chave PIX do afiliado."""
    if not context.args:
        await update.message.reply_text("❌ Uso: `/pix <sua_chave_pix>`")
        return

    user = update.effective_user
    assinante = _get_or_create_assinante(user)
    get_or_create_afiliado(assinante.id)

    chave = " ".join(context.args).strip()
    if len(chave) < 4:
        await update.message.reply_text("❌ Chave PIX inválida.")
        return

    if atualizar_pix_afiliado(assinante.id, chave):
        await update.message.reply_text("✅ Chave PIX cadastrada com sucesso!")
    else:
        await update.message.reply_text("❌ Não consegui cadastrar sua chave PIX agora.")


async def afiliado_saldo_command(update: Update, context):
    """Mostra saldos do afiliado."""
    user = update.effective_user
    assinante = buscar_assinante(user.id)
    if not assinante:
        await update.message.reply_text("Você ainda não é afiliado. Use /afiliado primeiro.")
        return

    try:
        liberar_comissoes_vencidas()
    except Exception as e:
        logger.warning(f"Erro ao liberar comissões no saldo: {e}")

    liberado, pendente = saldo_afiliado(assinante.id)
    await update.message.reply_text(
        "💰 *Saldo de Afiliado*\n\n"
        f"✅ Liberado: R$ {liberado:.2f}\n"
        f"⏳ Pendente (D+7): R$ {pendente:.2f}\n\n"
        "Para sacar: /afiliado_sacar"
    )


async def afiliado_sacar_command(update: Update, context):
    """Solicita saque do saldo liberado."""
    user = update.effective_user
    assinante = buscar_assinante(user.id)
    if not assinante:
        await update.message.reply_text("Você ainda não é afiliado. Use /afiliado primeiro.")
        return

    try:
        liberar_comissoes_vencidas()
    except Exception as e:
        logger.warning(f"Erro ao liberar comissões no saque: {e}")

    resultado = solicitar_saque(assinante.id, modo=settings.payment_mode)
    if resultado.ok:
        await update.message.reply_text(
            f"✅ {resultado.mensagem}\n"
            f"🧾 Saque ID: `{resultado.saque_id}`"
        )
    else:
        await update.message.reply_text(f"❌ {resultado.mensagem}")


async def pago_command(update: Update, context):
    """Usuário avisa que pagou."""
    user = update.effective_user
    assinante = buscar_assinante(user.id)

    # Se não existe assinante ainda, cria um anônimo só com telegram_id
    if not assinante:
        assinante = criar_assinante(
            telegram_id=user.id,
            primeiro_nome=user.first_name or "Anônimo",
            username=user.username,
        )
        pagamento = registrar_pagamento(
            assinante_id=assinante.id,
            valor=settings.preco_plano_lua,
            tipo="assinatura",
        )

    if assinante.ativo and assinante.data_nascimento and assinante.primeiro_nome:
        await update.message.reply_text(
            "✅ Sua assinatura já está ativa e completa!\n"
            "Você já vai começar a receber seu horóscopo personalizado. 🌙"
        )
        return

    if assinante.ativo and not assinante.data_nascimento:
        await update.message.reply_text(
            "✅ Seu pagamento já foi confirmado! 🎉\n\n"
            "👉 Use /dados pra fornecer seus dados e liberar seu Mapa Astral! 🔮"
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
    """Admin ativa assinante manualmente. Uso: /ativar <telegram_id>"""
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
        from src.database.models import Pagamento, Compra
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

                compra = (
                    session.query(Compra)
                    .filter(Compra.pagamento_id == pag.id)
                    .first()
                )
                if not compra:
                    produto = "plano_lua" if pag.tipo == "assinatura" else str(pag.tipo)
                    compra = Compra(
                        assinante_id=assinante.id,
                        pagamento_id=pag.id,
                        produto=produto,
                        valor=Decimal(str(pag.valor or 0)),
                        ativo=True,
                    )
                    session.add(compra)
                else:
                    compra.ativo = True

                session.commit()

                try:
                    registrar_comissao_por_pagamento(
                        indicado_telegram_id=telegram_id,
                        assinante_id=assinante.id,
                        pagamento_id=pag.id,
                        valor_venda=Decimal(str(pag.valor or 0)),
                    )
                except Exception as e:
                    logger.warning(f"Erro ao registrar comissão afiliado: {e}")

        # Notificar usuário
        try:
            await context.bot.send_message(
                chat_id=telegram_id,
                text=(
                    "🎉✨ *PAGAMENTO CONFIRMADO!* ✨🎉\n\n"
                    "Sua assinatura do *Plano Lua* está ativa! 🚀🔥\n\n"
                    "Agora preciso dos seus dados pra gerar "
                    "seu Mapa Astral personalizado. 🔮\n\n"
                    "👉 Digite /dados aqui no chat pra começar! 😊🌙"
                ),
            )
        except Exception as e:
            logger.warning(f"Erro ao notificar usuário {telegram_id}: {e}")

        await update.message.reply_text(
            f"✅ Assinante `{telegram_id}` ({assinante.primeiro_nome}) ATIVADO com sucesso!\n"
            "Notificado para usar /dados."
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
        user = update.effective_user
        assinante = _get_or_create_assinante(user)
        _, intent = _criar_pagamento(
            assinante_id=assinante.id,
            valor=settings.preco_plano_lua,
            tipo="assinatura",
            payer_ref=str(user.id),
        )

        await query.edit_message_text(
            "🌙 *Plano Lua — R$16,90/mês*\n\n"
            "Com ele você recebe:\n"
            "🪐 *Horóscopo diário personalizado*\n"
            "📅 *Previsão semanal*\n"
            "🌕 *Alertas lunares*\n"
            "🎁 *Mapa Astral PDF de brinde*\n"
            "🔥 *30% OFF* em todos os mapas\n\n"
            "Pra ativar agora, siga o pagamento abaixo:"
        )
        await query.message.reply_text(intent.instructions if intent.provider != "pix_api" else _mensagem_pix_manual(settings.preco_plano_lua))
        return

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
            "🔮 *Mapas*\n\n"
            "Escolha o tipo ideal pra você:\n\n"
            "• *Astral Completo:* visão geral da sua personalidade e ciclos\n"
            "• *Sinastria:* compatibilidade amorosa\n"
            "• *Carreira:* talentos, desafios e direção profissional\n"
            "• *Revolução Solar:* tendências do seu novo ano\n\n"
            "💡 *Assinantes do Plano Lua têm 30% OFF* (R$13,93)",
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
            [InlineKeyboardButton("🌙 Assinar Plano Lua (R$16,90)", callback_data="assinar_plano_lua")],
            [InlineKeyboardButton("🔮 Comprar Mapa", callback_data="comprar_mapa")],
            [InlineKeyboardButton("📋 Minhas Assinaturas", callback_data="minhas_assinaturas")],
            [InlineKeyboardButton("❓ Ajuda", callback_data="ajuda")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🌟 *AstroDicas* — Escolha uma opção:",
            reply_markup=reply_markup,
        )
        return

    # Callbacks de mapa
    elif data.startswith("mapa_"):
        mapa_tipos = {
            "mapa_astral": "astral",
            "mapa_sinastria": "sinastria",
            "mapa_carreira": "carreira",
            "mapa_revolucao": "revolucao",
        }
        tipo = mapa_tipos.get(data)
        if tipo:
            nomes = {
                "astral": "Mapa Astral Completo",
                "sinastria": "Sinastria (Amor)",
                "carreira": "Mapa da Carreira",
                "revolucao": "Revolução Solar",
            }

            user = update.effective_user
            assinante = _get_or_create_assinante(user)

            preco = settings.preco_mapa_avulso
            if assinante.ativo:
                preco = round(preco * (1 - settings.desconto_assinante), 2)

            _, intent = _criar_pagamento(
                assinante_id=assinante.id,
                valor=preco,
                tipo=f"mapa_{tipo}",
                payer_ref=str(user.id),
            )

            await query.edit_message_text(
                f"🔮 *{nomes[tipo]}*\n\n"
                f"💵 *Valor:* R$ {preco:.2f}\n\n"
                "Perfeito! Aqui estão as instruções de pagamento:"
            )
            await query.message.reply_text(intent.instructions if intent.provider != "pix_api" else _mensagem_pix_manual(preco))
            return

    return


# --- Fluxo pós-pagamento (coleta dados + nome) ---

async def receber_dados_nome(update: Update, context):
    """Recebe o nome do usuário."""
    nome = update.message.text.strip()
    if len(nome) < 3:
        await update.message.reply_text(
            "😊 Por favor, digite seu *nome completo* (mínimo 3 letras)."
        )
        return DADOS_NOME

    context.user_data["nome"] = nome

    await update.message.reply_text(
        f"✍️ Legal, {nome.split()[0]}! 😊\n\n"
        "📅 *Qual a sua data de nascimento?* (DD/MM/AAAA)\n\n"
        "Com ela eu descubro seu signo e começo a preparar "
        "seu Mapa Astral personalizado! 🔮"
    )
    return DADOS_NASC


async def receber_dados_nascimento(update: Update, context):
    """Recebe data de nascimento."""
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
    """Recebe a cidade e finaliza — salva dados + avisa preparação."""
    cidade = update.message.text.strip()
    if len(cidade) < 3:
        await update.message.reply_text("😊 Por favor, digite o nome da cidade.")
        return DADOS_CIDADE

    user = update.effective_user
    assinante = buscar_assinante(user.id)
    if not assinante:
        await update.message.reply_text("❓ Erro ao buscar seus dados. Use /start.")
        return ConversationHandler.END

    # Atualizar assinante com dados completos
    from src.database import SessionLocal
    with SessionLocal() as session:
        assinante_db = session.query(type(assinante)).filter_by(id=assinante.id).first()
        if assinante_db:
            assinante_db.primeiro_nome = context.user_data.get("nome", assinante_db.primeiro_nome)
            assinante_db.data_nascimento = context.user_data["data_nascimento"]
            assinante_db.hora_nascimento = context.user_data.get("hora_nascimento", "12:00")
            assinante_db.cidade_nascimento = cidade
            if context.user_data.get("signo_id"):
                assinante_db.signo_id = context.user_data["signo_id"]
            session.commit()

    signo_nome = context.user_data.get('signo_nome', '—')
    await update.message.reply_text(
        f"✨🌟✨🌟✨🌟✨🌟✨🌟✨🌟✨\n\n"
        f"{context.user_data.get('nome', '').split()[0] or 'Queridx'}, recebi seus dados! 📝\n\n"
        f"⭐ *Signo:* {signo_nome}\n"
        f"📅 *Nascimento:* {context.user_data['data_nascimento'].strftime('%d/%m/%Y')} "
        f"às {context.user_data.get('hora_nascimento', '12:00')}\n"
        f"📍 *Cidade:* {cidade}\n\n"
        "🔮 *Seu Mapa Astral personalizado está sendo preparado...*\n\n"
        "✨🌟✨🌟✨🌟✨🌟✨🌟✨🌟✨"
    )

    try:
        await _gerar_e_enviar_mapa_premium(update, context, assinante)
    except Exception as e:
        logger.exception(f"Erro ao gerar/enviar mapa premium no fluxo real: {e}")
        await update.message.reply_text(
            "❌ Tive um erro inesperado ao entregar seu PDF. Já registrei aqui pra corrigir."
        )

    await update.message.reply_text(
        "Bem-vindo ao *Plano Lua*! 🌙🎉\n"
        "Todo dia seu horóscopo personalizado vai chegar direto pra você. 🪐"
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

def dados_conversation_handler() -> ConversationHandler:
    """Handler para coleta de dados pós-pagamento (nome + data + hora + cidade).

    Entry point: /dados
    """
    return ConversationHandler(
        entry_points=[CommandHandler("dados", dados_command)],
        states={
            DADOS_NOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_dados_nome)],
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
    app.add_handler(CommandHandler("afiliado", afiliado_command))
    app.add_handler(CommandHandler("pix", afiliado_pix_command))
    app.add_handler(CommandHandler("afiliado_saldo", afiliado_saldo_command))
    app.add_handler(CommandHandler("afiliado_sacar", afiliado_sacar_command))

    # Conversation handler de dados
    app.add_handler(dados_conversation_handler())

    # Callback handler (todos os botões inline)
    app.add_handler(
        CallbackQueryHandler(
            button_handler,
            pattern="^(assinar_plano_lua|comprar_mapa|minhas_assinaturas|ajuda|voltar_menu|mapa_.*)$",
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
