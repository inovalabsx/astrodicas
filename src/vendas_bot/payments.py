"""Camada de pagamentos do bot de vendas.

Suporta modo simulado (default) e stub de API PIX externa.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from src.vendas_bot.settings import settings


@dataclass
class PaymentIntent:
    provider: str
    external_id: str
    status: str
    amount: float
    instructions: str
    expires_at: datetime | None = None


class PaymentProvider:
    """Interface base para criação de cobranças."""

    def create_payment(self, *, amount: float, description: str, payer_ref: str) -> PaymentIntent:
        raise NotImplementedError


class SimulatedPaymentProvider(PaymentProvider):
    def create_payment(self, *, amount: float, description: str, payer_ref: str) -> PaymentIntent:
        ext_id = f"sim_{uuid.uuid4().hex[:12]}"
        return PaymentIntent(
            provider="simulado",
            external_id=ext_id,
            status="pendente",
            amount=amount,
            instructions=(
                "🧪 *Modo de pagamento simulado*\n"
                "Sem cobrança real nesta etapa.\n"
                "Use /pago para simular o aviso do cliente."
            ),
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )


class PixApiStubProvider(PaymentProvider):
    """Stub para futuro provedor PIX via API (Asaas/MP/etc)."""

    def create_payment(self, *, amount: float, description: str, payer_ref: str) -> PaymentIntent:
        ext_id = f"pixstub_{uuid.uuid4().hex[:12]}"
        instructions = (
            "💳 *Cobrança PIX criada (stub)*\n"
            "Integração final da API PIX ainda não conectada.\n"
            f"Chave: `{settings.pix_chave}`\n"
            f"Banco: {settings.pix_banco}\n"
            f"Nome: {settings.pix_nome}\n"
            f"Valor: R$ {amount:.2f}\n\n"
            "Depois do pagamento, use /pago aqui no bot."
        )
        return PaymentIntent(
            provider="pix_api",
            external_id=ext_id,
            status="pendente",
            amount=amount,
            instructions=instructions,
            expires_at=datetime.utcnow() + timedelta(hours=24),
        )


def get_payment_provider() -> PaymentProvider:
    mode = (settings.payment_mode or "simulado").strip().lower()
    if mode == "pix_api":
        return PixApiStubProvider()
    return SimulatedPaymentProvider()


payment_provider = get_payment_provider()
