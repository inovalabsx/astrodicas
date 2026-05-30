# Tasks — vendas-refactor-pix-afiliados

1. [x] Atualizar `settings.py` com novos preços e flags de pagamento.
2. [x] Criar módulo `payments.py` com interface de provider + provider simulado + stub pix_api.
3. [x] Refatorar `handler.py` para copy vendável, catálogo "Mapa" e explicações por tipo.
4. [x] Ajustar fluxo de criação de pagamento para usar provider (não hardcode de PIX manual).
5. [x] Implementar módulo base de afiliados com regras de comissão e saque.
6. [x] Integrar geração de comissão no evento de compra aprovada.
7. [x] Integrar verificação de chave PIX + saque mínimo no fluxo de payout.
8. [x] Validar compilação e atualizar `.fdd/state.md` com evidências.
