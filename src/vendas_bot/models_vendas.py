"""Models específicos do bot de vendas.

Extends the base models with vendas-specific logic and helpers.
"""
from typing import Optional
from datetime import date, datetime

from src.database.models import (
    Assinante as BaseAssinante,
    Pagamento as BasePagamento,
    Compra as BaseCompra,
    Signo,
)
from src.database import SessionLocal


# --- Helpers ---

def get_signos() -> list[Signo]:
    """Retorna lista de todos os signos do banco."""
    with SessionLocal() as session:
        return session.query(Signo).order_by(Signo.id).all()


def find_signo_by_nome(nome: str) -> Optional[Signo]:
    """Busca signo pelo nome."""
    with SessionLocal() as session:
        return session.query(Signo).filter(Signo.nome.ilike(nome)).first()


def buscar_assinante(telegram_id: int) -> Optional[BaseAssinante]:
    """Busca assinante pelo telegram_id."""
    with SessionLocal() as session:
        return (
            session.query(BaseAssinante)
            .filter(BaseAssinante.telegram_id == telegram_id)
            .first()
        )


def criar_assinante(
    telegram_id: int,
    primeiro_nome: str,
    username: Optional[str] = None,
    signo_id: Optional[int] = None,
    data_nascimento: Optional[date] = None,
    hora_nascimento: Optional[str] = None,
    cidade_nascimento: Optional[str] = None,
) -> BaseAssinante:
    """Cria um novo assinante."""
    with SessionLocal() as session:
        assinante = BaseAssinante(
            telegram_id=telegram_id,
            primeiro_nome=primeiro_nome,
            username=username,
            signo_id=signo_id,
            data_nascimento=data_nascimento,
            hora_nascimento=hora_nascimento,
            cidade_nascimento=cidade_nascimento,
            ativo=False,
        )
        session.add(assinante)
        session.commit()
        session.refresh(assinante)
        return assinante


def ativar_assinante(assinante_id: int) -> bool:
    """Ativa um assinante manualmente (admin confirma pagamento)."""
    with SessionLocal() as session:
        assinante = session.query(BaseAssinante).filter_by(id=assinante_id).first()
        if not assinante:
            return False
        assinante.ativo = True
        session.commit()
        return True


def registrar_pagamento(
    assinante_id: int,
    valor: float,
    tipo: str = "assinatura",
    status: str = "pendente",
) -> BasePagamento:
    """Registra um pagamento pendente."""
    with SessionLocal() as session:
        pag = BasePagamento(
            assinante_id=assinante_id,
            valor=valor,
            tipo=tipo,
            status=status,
        )
        session.add(pag)
        session.commit()
        session.refresh(pag)
        return pag


def confirmar_pagamento(pagamento_id: int) -> bool:
    """Confirma um pagamento e ativa a assinatura."""
    from src.database import SessionLocal as Session

    with Session() as session:
        pag = session.query(BasePagamento).filter_by(id=pagamento_id).first()
        if not pag:
            return False
        pag.status = "confirmado"

        # Se for assinatura, ativa o assinante
        if pag.tipo == "assinatura" and pag.assinante_id:
            assinante = session.query(BaseAssinante).filter_by(id=pag.assinante_id).first()
            if assinante:
                assinante.ativo = True

        session.commit()
        return True


def assinante_tem_plano_lua(assinante_id: int) -> bool:
    """Verifica se assinante tem assinatura ativa do plano lua."""
    from src.database import SessionLocal as Session

    with Session() as session:
        compra = (
            session.query(BaseCompra)
            .filter(
                BaseCompra.assinante_id == assinante_id,
                BaseCompra.produto == "plano_lua",
                BaseCompra.ativo == True,
            )
            .first()
        )
        return compra is not None


def assinante_assinaturas_ativas(assinante_id: int) -> list:
    """Retorna lista de assinaturas ativas do assinante."""
    from src.database import SessionLocal as Session

    with Session() as session:
        compras = (
            session.query(BaseCompra)
            .filter(
                BaseCompra.assinante_id == assinante_id,
                BaseCompra.ativo == True,
            )
            .all()
        )
        return compras
