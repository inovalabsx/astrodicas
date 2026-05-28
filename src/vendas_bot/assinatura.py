"""Vendas Bot — Lógica de assinatura.

Criação, ativação e gerenciamento de assinaturas do Plano Lua.
"""
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal

from src.database import SessionLocal
from src.database.models import Assinante, Compra, Pagamento
from src.vendas_bot.models_vendas import (
    ativar_assinante,
    registrar_pagamento,
)

logger = logging.getLogger(__name__)


def criar_assinatura_plano_lua(
    assinante_id: int,
    valor: float = 9.90,
) -> tuple[Pagamento, Compra]:
    """Cria uma nova assinatura Plano Lua para o assinante.

    Retorna (pagamento, compra).
    """
    pagamento = registrar_pagamento(
        assinante_id=assinante_id,
        valor=valor,
        tipo="assinatura",
    )

    with SessionLocal() as session:
        compra = Compra(
            assinante_id=assinante_id,
            pagamento_id=pagamento.id,
            produto="plano_lua",
            valor=Decimal(str(valor)),
            ativo=False,  # Só ativa após confirmação de pagamento
        )
        session.add(compra)
        session.commit()
        session.refresh(compra)
        return pagamento, compra


def ativar_assinatura_apos_pagamento(compra_id: int) -> bool:
    """Ativa a assinatura após confirmação de pagamento."""
    with SessionLocal() as session:
        compra = session.query(Compra).filter_by(id=compra_id).first()
        if not compra:
            return False

        compra.ativo = True

        assinante = session.query(Assinante).filter_by(id=compra.assinante_id).first()
        if assinante:
            assinante.ativo = True

        session.commit()
        return True


def expirar_assinaturas_vencidas():
    """Desativa assinaturas que venceram.

    NOTA: Implementação básica — desativa após 30 dias sem renovação.
    Futuramente integrar com Asaas para cobrança recorrente automática.
    """
    with SessionLocal() as session:
        # TODO: lógica de expiração quando houver data de expiração
        pass


def listar_assinaturas_ativas() -> list[Assinante]:
    """Lista todos os assinantes com Plano Lua ativo."""
    with SessionLocal() as session:
        return (
            session.query(Assinante)
            .filter(Assinante.ativo == True)
            .all()
        )
