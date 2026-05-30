# FDD State — bot-signos

## Data
2026-05-30

## Feature ativa
`vendas-refactor-pix-afiliados`

## Fase atual
Fase 6 — State (implementação concluída e validada)

## Decisões de produto confirmadas
- Plano Lua: R$ 16,90
- Mapa: R$ 19,90
- Catálogo: remover termo "Mapa Avulso" e manter "Mapa"
- Afiliado: 40% em Plano Lua e Mapa
- Janela de atribuição por link: 30 dias
- Carência da comissão: D+7
- Saque mínimo: R$ 10,00
- Saque: automático por fluxo interno (simulado enquanto API PIX final não estiver plugada)
- Enquanto API PIX não for escolhida: modo simulado habilitado

## O que foi concluído nesta feature
1. Refactor de UX/copy no `handler.py` com preços atualizados e catálogo "Mapa".
2. Camada de pagamento agnóstica implementada (`simulado` + `pix_api` stub).
3. Persistência de `pagamento_id` externo em pagamentos.
4. Base de afiliados implementada no domínio:
   - modelos: `afiliados`, `afiliado_leads`, `afiliado_comissoes`, `afiliado_saques`
   - regras: comissão 40%, D+7, saque mínimo R$10, chave PIX obrigatória.
5. Deep-link de indicação no `/start` (`/start AFxxxxxx`) registrando lead com janela de 30 dias.
6. Comandos afiliado adicionados:
   - `/afiliado`
   - `/pix <chave>`
   - `/afiliado_saldo`
   - `/afiliado_sacar`
7. Integração de comissão no fluxo de confirmação manual `/ativar`:
   - confirma pagamento pendente
   - cria/ativa `Compra`
   - gera comissão quando houver lead válido.

## Arquivos alterados
- `src/database/models.py`
- `src/vendas_bot/afiliados.py` (novo)
- `src/vendas_bot/handler.py`
- `src/vendas_bot/models_vendas.py`
- `src/vendas_bot/settings.py`
- `src/vendas_bot/payments.py`
- `.fdd/features/vendas-refactor-pix-afiliados/tasks.md`

## Evidências de validação
- Compilação sintática OK:
  - `python -m py_compile src/database/models.py src/vendas_bot/afiliados.py src/vendas_bot/handler.py src/vendas_bot/models_vendas.py src/vendas_bot/settings.py`
  - exit code: `0`

## Pendências pós-feature
- Criar migration SQL/DDL no banco real para novas tabelas de afiliado.
- Integrar payout com provedor PIX real (Asaas/MP) para substituir transação simulada.
- Validar fluxo E2E em produção (deep-link → pagamento → ativação → comissão → saque).
