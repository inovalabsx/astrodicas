# State — AstroDicas

## Status
✅ Alinhamento models ↔ banco real concluído

## Última ação (27/05/2026)
Alinhar models SQLAlchemy com schema real do banco `astrodicas`:

**Feature:** `alinhar-models`
**Spec:** `.fdd/features/alinhar-models/spec.md`

### O que foi feito
- Models reescritos: `Assinante`, `Signo`, `Horoscopo`, `Pagamento`, `Compra`, `Postagem`
- Models antigos removidos: `Usuario`, `Assinatura`, `Venda`, `ConteudoGerado`
- `settings.py` com DATABASE_URL real (Coolify)
- `docker-compose.yml` sem postgres (usa banco do Coolify)
- `main.py` ajustado (import Usuario removido)
- `.env` virado template (sem tokens reais)
- `spec.md` ajustada p/ refletir colunas reais da tabela `compras` e `postagens`
- 12 signos populados no banco

### Arquivos alterados
- `src/database/models.py` — reescrito
- `src/config/settings.py` — DATABASE_URL atualizada
- `docker-compose.yml` — postgres removido
- `src/main.py` — import Usuario removido
- `.env` — template limpo

### Testes
- ✅ `test_alinhamento_banco.py` — 9/9 requisitos passaram (via Hetzner, IP 10.0.1.7)
- ✅ `test_conteudo_offline.py` — testes offline passaram (não quebrou nada)

### Próximos passos
- [ ] Push pro GitHub (inovalabsx/astrodicas)
- [ ] Deploy no Coolify
- [ ] Implementar bot de postagem (@astro_dicas_bot)
- [ ] Implementar bot de vendas (@astro_dicas_vendasbot)
