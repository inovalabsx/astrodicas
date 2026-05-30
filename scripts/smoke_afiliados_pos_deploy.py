#!/usr/bin/env python3
"""Smoke test pós-deploy do fluxo de afiliados (/ativar-driven).

Objetivo: validar rapidamente no ambiente real as regras principais sem acionar Telegram.

Fluxo coberto:
1) Cria afiliado e indicado de teste
2) Registra lead (equivalente ao /start AFxxxxxx)
3) Simula pagamento aprovado + compra (equivalente ao /ativar)
4) Gera comissão
5) Força vencimento D+7 e libera comissão
6) Atualiza PIX e solicita saque
7) Limpa os dados de teste ao final
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from decimal import Decimal

from src.database import SessionLocal
from src.database.models import (
    Afiliado,
    AfiliadoComissao,
    AfiliadoLead,
    AfiliadoSaque,
    Assinante,
    Compra,
    Pagamento,
)
from src.vendas_bot.afiliados import (
    atualizar_pix_afiliado,
    get_or_create_afiliado,
    liberar_comissoes_vencidas,
    registrar_comissao_por_pagamento,
    registrar_lead_por_codigo,
    saldo_afiliado,
    solicitar_saque,
)


def _cleanup_by_telegram_ids(telegram_ids: list[int]) -> None:
    with SessionLocal() as s:
        assinantes = s.query(Assinante).filter(Assinante.telegram_id.in_(telegram_ids)).all()
        for a in assinantes:
            afiliado = s.query(Afiliado).filter(Afiliado.assinante_id == a.id).first()
            if afiliado:
                s.query(AfiliadoSaque).filter(AfiliadoSaque.afiliado_id == afiliado.id).delete()
                s.query(AfiliadoComissao).filter(AfiliadoComissao.afiliado_id == afiliado.id).delete()
                s.query(AfiliadoLead).filter(AfiliadoLead.afiliado_id == afiliado.id).delete()
                s.delete(afiliado)
            s.query(Compra).filter(Compra.assinante_id == a.id).delete()
            s.query(Pagamento).filter(Pagamento.assinante_id == a.id).delete()
            s.delete(a)
        s.commit()


def main() -> None:
    suffix = random.randint(100000, 999999)
    afiliado_tg = 870000000 + suffix
    indicado_tg = 880000000 + suffix

    try:
        _cleanup_by_telegram_ids([afiliado_tg, indicado_tg])

        with SessionLocal() as s:
            afiliado_ass = Assinante(
                telegram_id=afiliado_tg,
                username=f"smoke_af_{suffix}",
                primeiro_nome="Smoke Afiliado",
                ativo=True,
            )
            indicado_ass = Assinante(
                telegram_id=indicado_tg,
                username=f"smoke_ind_{suffix}",
                primeiro_nome="Smoke Indicado",
                ativo=True,
            )
            s.add_all([afiliado_ass, indicado_ass])
            s.commit()
            s.refresh(afiliado_ass)
            s.refresh(indicado_ass)
            afiliado_ass_id = afiliado_ass.id
            indicado_ass_id = indicado_ass.id

        afiliado = get_or_create_afiliado(afiliado_ass_id)
        lead_ok = registrar_lead_por_codigo(afiliado.codigo, indicado_tg, origem="smoke_pos_deploy")

        with SessionLocal() as s:
            pagamento = Pagamento(
                assinante_id=indicado_ass_id,
                valor=Decimal("30.00"),
                moeda="BRL",
                tipo="smoke_produto",
                status="pago",
                pagamento_id=f"smoke_{suffix}",
            )
            s.add(pagamento)
            s.commit()
            s.refresh(pagamento)

            compra = Compra(
                assinante_id=indicado_ass_id,
                pagamento_id=pagamento.id,
                produto="smoke_produto",
                valor=Decimal("30.00"),
                ativo=True,
            )
            s.add(compra)
            s.commit()
            pagamento_db_id = pagamento.id

        comissao_ok = registrar_comissao_por_pagamento(
            indicado_telegram_id=indicado_tg,
            assinante_id=indicado_ass_id,
            pagamento_id=pagamento_db_id,
            valor_venda=Decimal("30.00"),
        )

        with SessionLocal() as s:
            c = s.query(AfiliadoComissao).filter(AfiliadoComissao.pagamento_id == pagamento_db_id).first()
            if c:
                c.liberacao_prevista_em = datetime.utcnow() - timedelta(minutes=1)
                s.commit()

        liberadas = liberar_comissoes_vencidas()
        saldo_liberado, saldo_pendente = saldo_afiliado(afiliado_ass_id)
        pix_ok = atualizar_pix_afiliado(afiliado_ass_id, f"smoke-pix-{suffix}@email.com")
        saque = solicitar_saque(afiliado_ass_id, modo="simulado")

        print(f"lead_ok={lead_ok}")
        print(f"comissao_ok={comissao_ok}")
        print(f"comissoes_liberadas={liberadas}")
        print(f"saldo_liberado={saldo_liberado} saldo_pendente={saldo_pendente}")
        print(f"pix_ok={pix_ok}")
        print(f"saque_ok={saque.ok}")
        print(f"saque_msg={saque.mensagem}")

        if not (lead_ok and comissao_ok and saque.ok):
            raise SystemExit("SMOKE_RESULT=FAIL")

        print("SMOKE_RESULT=PASS")

    finally:
        _cleanup_by_telegram_ids([afiliado_tg, indicado_tg])


if __name__ == "__main__":
    main()
