"""Vendas Bot — domínio de afiliados.

Regras:
- comissão 40%
- janela de atribuição por lead: 30 dias
- liberação da comissão: D+7
- saque mínimo: R$10 e chave PIX obrigatória
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from src.database import SessionLocal
from src.database.models import Afiliado, AfiliadoComissao, AfiliadoLead, AfiliadoSaque

COMISSAO_PERCENTUAL = Decimal("40.00")
LIBERACAO_DIAS = 7
JANELA_LEAD_DIAS = 30
SAQUE_MINIMO = Decimal("10.00")


@dataclass
class SaqueResultado:
    ok: bool
    mensagem: str
    saque_id: Optional[int] = None
    transacao_id: Optional[str] = None


def _to_money(valor: Decimal | float | int) -> Decimal:
    if isinstance(valor, Decimal):
        v = valor
    else:
        v = Decimal(str(valor))
    return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _gerar_codigo_assinante(assinante_id: int) -> str:
    return f"AF{assinante_id:06d}"


def get_or_create_afiliado(assinante_id: int) -> Afiliado:
    with SessionLocal() as session:
        afiliado = session.query(Afiliado).filter(Afiliado.assinante_id == assinante_id).first()
        if afiliado:
            return afiliado

        codigo = _gerar_codigo_assinante(assinante_id)
        existente = session.query(Afiliado).filter(Afiliado.codigo == codigo).first()
        if existente:
            codigo = f"{codigo}X"

        afiliado = Afiliado(
            assinante_id=assinante_id,
            codigo=codigo,
            ativo=True,
        )
        session.add(afiliado)
        session.commit()
        session.refresh(afiliado)
        return afiliado


def buscar_afiliado_por_codigo(codigo: str) -> Optional[Afiliado]:
    with SessionLocal() as session:
        return (
            session.query(Afiliado)
            .filter(Afiliado.codigo == (codigo or "").strip().upper(), Afiliado.ativo == True)
            .first()
        )


def registrar_lead_por_codigo(codigo: str, indicado_telegram_id: int, origem: str = "telegram_start") -> bool:
    afiliado = buscar_afiliado_por_codigo(codigo)
    if not afiliado:
        return False

    with SessionLocal() as session:
        lead = (
            session.query(AfiliadoLead)
            .filter(
                AfiliadoLead.afiliado_id == afiliado.id,
                AfiliadoLead.indicado_telegram_id == indicado_telegram_id,
            )
            .first()
        )
        if lead:
            lead.expira_em = datetime.utcnow() + timedelta(days=JANELA_LEAD_DIAS)
            session.commit()
            return True

        novo = AfiliadoLead(
            afiliado_id=afiliado.id,
            indicado_telegram_id=indicado_telegram_id,
            origem=origem,
            expira_em=datetime.utcnow() + timedelta(days=JANELA_LEAD_DIAS),
        )
        session.add(novo)
        session.commit()
        return True


def atualizar_pix_afiliado(assinante_id: int, pix_chave: str) -> bool:
    with SessionLocal() as session:
        afiliado = session.query(Afiliado).filter(Afiliado.assinante_id == assinante_id).first()
        if not afiliado:
            return False
        afiliado.pix_chave = pix_chave.strip()
        session.commit()
        return True


def _lead_valido_para_indicado(indicado_telegram_id: int) -> Optional[AfiliadoLead]:
    with SessionLocal() as session:
        return (
            session.query(AfiliadoLead)
            .filter(
                AfiliadoLead.indicado_telegram_id == indicado_telegram_id,
                AfiliadoLead.expira_em >= datetime.utcnow(),
                AfiliadoLead.convertido_em.is_(None),
            )
            .order_by(AfiliadoLead.criado_em.desc())
            .first()
        )


def registrar_comissao_por_pagamento(
    indicado_telegram_id: int,
    assinante_id: int,
    pagamento_id: int,
    valor_venda: Decimal | float,
) -> bool:
    lead = _lead_valido_para_indicado(indicado_telegram_id)
    if not lead:
        return False

    valor = _to_money(valor_venda)
    valor_comissao = _to_money((valor * COMISSAO_PERCENTUAL) / Decimal("100"))

    with SessionLocal() as session:
        existente = (
            session.query(AfiliadoComissao)
            .filter(AfiliadoComissao.pagamento_id == pagamento_id)
            .first()
        )
        if existente:
            return False

        comissao = AfiliadoComissao(
            afiliado_id=lead.afiliado_id,
            assinante_id=assinante_id,
            pagamento_id=pagamento_id,
            valor_venda=valor,
            percentual=COMISSAO_PERCENTUAL,
            valor_comissao=valor_comissao,
            status="pendente",
            liberacao_prevista_em=datetime.utcnow() + timedelta(days=LIBERACAO_DIAS),
        )
        session.add(comissao)

        lead_db = session.query(AfiliadoLead).filter(AfiliadoLead.id == lead.id).first()
        if lead_db and lead_db.convertido_em is None:
            lead_db.convertido_em = datetime.utcnow()

        session.commit()
        return True


def liberar_comissoes_vencidas() -> int:
    with SessionLocal() as session:
        itens = (
            session.query(AfiliadoComissao)
            .filter(
                AfiliadoComissao.status == "pendente",
                AfiliadoComissao.liberacao_prevista_em <= datetime.utcnow(),
            )
            .all()
        )
        total = 0
        for c in itens:
            c.status = "liberado"
            c.liberado_em = datetime.utcnow()
            total += 1

        if total:
            session.commit()
        return total


def saldo_afiliado(assinante_id: int) -> tuple[Decimal, Decimal]:
    """Retorna (saldo_liberado, saldo_pendente)."""
    with SessionLocal() as session:
        afiliado = session.query(Afiliado).filter(Afiliado.assinante_id == assinante_id).first()
        if not afiliado:
            return Decimal("0.00"), Decimal("0.00")

        liberadas = (
            session.query(AfiliadoComissao)
            .filter(
                AfiliadoComissao.afiliado_id == afiliado.id,
                AfiliadoComissao.status == "liberado",
            )
            .all()
        )
        pendentes = (
            session.query(AfiliadoComissao)
            .filter(
                AfiliadoComissao.afiliado_id == afiliado.id,
                AfiliadoComissao.status == "pendente",
            )
            .all()
        )
        pagos = (
            session.query(AfiliadoComissao)
            .filter(
                AfiliadoComissao.afiliado_id == afiliado.id,
                AfiliadoComissao.status == "pago",
            )
            .all()
        )

        total_liberado = sum((_to_money(c.valor_comissao) for c in liberadas), Decimal("0.00"))
        total_pendente = sum((_to_money(c.valor_comissao) for c in pendentes), Decimal("0.00"))
        total_pago = sum((_to_money(c.valor_comissao) for c in pagos), Decimal("0.00"))

        disponivel = _to_money(total_liberado - total_pago)
        if disponivel < 0:
            disponivel = Decimal("0.00")
        return disponivel, _to_money(total_pendente)


def solicitar_saque(assinante_id: int, modo: str = "simulado") -> SaqueResultado:
    with SessionLocal() as session:
        afiliado = session.query(Afiliado).filter(Afiliado.assinante_id == assinante_id).first()
        if not afiliado:
            return SaqueResultado(False, "Você ainda não é afiliado. Use /afiliado para ativar.")

        if not afiliado.pix_chave:
            return SaqueResultado(False, "Cadastre sua chave PIX primeiro com /pix <sua_chave>.")

        saldo_liberado, _ = saldo_afiliado(assinante_id)
        if saldo_liberado < SAQUE_MINIMO:
            return SaqueResultado(False, f"Saque mínimo é R$ {SAQUE_MINIMO:.2f}. Seu saldo liberado: R$ {saldo_liberado:.2f}.")

        transacao_id = f"pix_sim_{int(datetime.utcnow().timestamp())}"
        status = "pago" if modo == "simulado" else "solicitado"

        saque = AfiliadoSaque(
            afiliado_id=afiliado.id,
            valor=saldo_liberado,
            status=status,
            pix_chave=afiliado.pix_chave,
            transacao_id=transacao_id,
            pago_em=datetime.utcnow() if status == "pago" else None,
        )
        session.add(saque)

        comissoes = (
            session.query(AfiliadoComissao)
            .filter(
                AfiliadoComissao.afiliado_id == afiliado.id,
                AfiliadoComissao.status == "liberado",
            )
            .all()
        )
        for c in comissoes:
            c.status = "pago"

        session.commit()
        session.refresh(saque)

        msg = (
            f"Saque {'pago' if status == 'pago' else 'solicitado'} com sucesso. "
            f"Valor: R$ {saldo_liberado:.2f}. ID: {transacao_id}"
        )
        return SaqueResultado(True, msg, saque_id=saque.id, transacao_id=transacao_id)
