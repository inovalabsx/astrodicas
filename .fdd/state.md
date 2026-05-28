# State — AstroDicas

## Status
✅ **App rodando** — https://bot-astrodicas.inovalabx.com.br (Coolify Hetzner)
✅ **Scheduler ativo** — 06:00 (horoscopo), 12:00 (lua), 18:00 (frase), dom 10:00 (transito)
✅ **Bot webhook** — @astro_dicas_bot integrado no FastAPI
✅ **Provider Ominiroute** — CODING-BASIC (texto) + antigravity/gemini-3.1-flash-image (imagem)
✅ **Models alinhados** — 6 tabelas: assinantes, signos, horoscopos, pagamentos, compras, postagens
✅ **Geração de imagem funcional** — POST direto /v1/images/generations com b64_json
✅ **Envio de foto com texto** — caption truncado (~1000 chars), texto completo em msg separada

## Features completadas

### 1. Scheduler Ativo (27/05)
**Spec:** `.fdd/features/scheduler-ativo/spec.md`

- `publicar.py` — fluxo completo: gerar conteúdo → salvar `postagens` → gerar imagem → enviar Telegram → atualizar status
- `cron.py` — refatorado pra chamar `publicar()`
- `conteudo_diario.py` — prompt `horoscopo_individual` pra cada signo
- `handler.py` — webhook mode (criar_app sem updater)
- `main.py` — webhook integrado, lifespan com bot + scheduler
- `settings.py` — campo `domain`, variáveis Ominiroute

### 2. Alinhar Models com Banco (27/05)
**Spec:** `.fdd/features/alinhar-models/spec.md`

- `src/database/models.py` — reescrito com 6 classes: Assinante, Signo, Horoscopo, Pagamento, Compra, Postagem
- Colunas e FKs exatamente como no schema real do banco `astrodicas` (PostgreSQL Coolify)
- `checkfirst=True` — não dropa/recria tabelas

### 3. Fix Geração de Imagem (28/05)
**Skill:** `ominiroute-image-gen`

- **Problema:** OpenAI SDK (`client.images.generate()`) não serializa `provider/model` corretamente para Ominiroute
- **Solução:** `gerador_imagem.py` reescrito com `urllib.request` direto ao `POST /v1/images/generations`
- Modelo: `antigravity/gemini-3.1-flash-image` (1024×1024, JPEG)
- Alternativa: `codex/gpt-5.5` (1792×1024)
- Resposta: `b64_json` → decodifica → salva como arquivo temporário .jpg

### 4. Fix Caption Truncado (28/05)
- **Problema:** `sendPhoto` caption > 1024 chars → "Bad Request: message caption is too long"
- **Solução:** função `_enviar_com_foto()` trunca caption para ~1000 chars (corta no último `\n`), se truncado envia texto completo como `sendMessage` separado

### 5. Deploy Coolify Hetzner (28/05)
- App UUID: `ivsnnh48a94llvg5r08xsf12`
- Domínio: `https://bot-astrodicas.inovalabx.com.br`
- Banco: PostgreSQL `astrodicas` (6 tabelas)
- Repositório: `github.com/inovalabsx/astrodicas` (branch master)

## Arquivos alterados/criados (desde último state)

| Arquivo | Ação |
|---|---|
| `src/database/models.py` | **REESCRITO** — 6 classes alinhadas ao banco |
| `src/scheduler/gerador_imagem.py` | **REESCRITO** — urllib.request direto ao /v1/images/generations |
| `src/config/settings.py` | Patch — `llm_model_image` = `antigravity/gemini-3.1-flash-image` |
| `src/scheduler/publicar.py` | Patch — função `_enviar_com_foto()` com caption truncado |
| `.fdd/features/alinhar-models/spec.md` | **CRIADO** — spec de alinhamento |
| `.fdd/state.md` | **ATUALIZADO** — este arquivo |

## Testes

- ✅ Importação de todos os módulos (settings, models, init_db, publicar, handler)
- ✅ FastAPI rotas OK (/health, /, /webhook)
- ✅ 5 prompts de conteúdo (horoscopo, lua, frase, transito, horoscopo_individual)
- ✅ 12 pares signo/elemento no publicar
- ✅ publicar() falha graciosamente sem rede
- ✅ 6 modelos SQLAlchemy → 6 tabelas no banco (init_db sem erro)
- ✅ POST /test/postar/horoscopo → imagem + texto enviados juntos no canal
- ✅ Geração de imagem via POST direto: antigravity/gemini-3.1-flash-image (1024×1024) e codex/gpt-5.5 (1792×1024) retornam b64_json válido
- ✅ Envio com caption truncado: imagem + caption curto + texto completo separado

### 6. Bot de Vendas (@astro_dicas_vendasbot) (28/05)
**Spec:** `.fdd/features/bot-vendas/spec.md`
**Map:** `.fdd/features/bot-vendas/map.md`

- **Gateway:** PIX manual — chave: `astrodicas@pix.com` (admin ativa com `/ativar`)
- **Planos:** Plano Lua R$9,90/mês (horóscopo diário DM + previsão semanal + lembrete luas + Mapa PDF brinde + 30% OFF mapas)
- **Mapas avulsos:** R$19,90 (R$13,93 assinante): Mapa Astral, Sinastria, Carreira, Revolução Solar
- **`src/vendas_bot/`** — módulo independente no mesmo repositório, deploy separado no Coolify
  - `settings.py` — env vars: TELEGRAM_VENDAS_BOT_TOKEN, ADMIN_USER_ID, PIX_CHAVE
  - `models_vendas.py` — helpers: criar/ativar assinante, registrar pagamento, CRUD
  - `handler.py` — ConversationHandler onboarding (nome → signo → data → hora → cidade → PIX), /pago, /ativar
  - `main.py` — FastAPI + webhook + lifespan
  - `assinatura.py` — lógica de ativação pós-pagamento
  - `mapa_astral.py` — geração de PDF via LLM OmniRoute + fpdf2
  - `scheduler.py` — horóscopo personalizado 06:00, previsão semanal sáb 08:00, luas 07:00
  - `migration.sql` — ALTER TABLE assinantes ADD COLUMN signo_id, data_nascimento, hora_nascimento, cidade_nascimento
- **`docker/vendas_bot/Dockerfile`** — CMD uvicorn src.vendas_bot.main:app --port 3000
- **Models:** Assinante estendido com signo_id, data_nascimento, hora_nascimento, cidade_nascimento
- **Deps:** fpdf2 adicionado ao requirements.txt

## Arquivos alterados/criados (desde último state)

| Arquivo | Ação |
|---|---|
| `src/database/models.py` | **PATCH** — Assinante +4 colunas (signo_id, data_nascimento, hora_nascimento, cidade_nascimento), +relationships signo |
| `src/vendas_bot/__init__.py` | **CRIADO** |
| `src/vendas_bot/settings.py` | **CRIADO** |
| `src/vendas_bot/models_vendas.py` | **CRIADO** |
| `src/vendas_bot/handler.py` | **CRIADO** |
| `src/vendas_bot/main.py` | **CRIADO** |
| `src/vendas_bot/assinatura.py` | **CRIADO** |
| `src/vendas_bot/mapa_astral.py` | **CRIADO** |
| `src/vendas_bot/scheduler.py` | **CRIADO** |
| `src/vendas_bot/migration.sql` | **CRIADO** |
| `docker/vendas_bot/Dockerfile` | **CRIADO** |
| `requirements.txt` | **PATCH** — reportlab → fpdf2 |
| `.fdd/features/bot-vendas/spec.md` | **PATCH** — gateway PIX manual |
| `.fdd/features/bot-vendas/map.md` | **CRIADO** |
| `.fdd/state.md` | **ATUALIZADO** — este arquivo |

## Próximos passos

- [x] Bot de vendas implementado (src/vendas_bot/) — pendente deploy no Coolify
- [ ] **Executar migration SQL** no banco astrodicas (ALTER TABLE assinantes)
- [ ] **Configurar deploy** no Coolify: app separado `astrodicas-vendas-bot`
- [ ] **Configurar env vars** no Coolify: TELEGRAM_VENDAS_BOT_TOKEN, ADMIN_USER_ID, PIX_CHAVE, DATABASE_URL_ASTRODICAS, OMINIROUTE_API_KEY
- [ ] **Setar webhook** do Telegram: `https://bot-vendas.astrodicas.inovalabx.com.br/webhook`
- [ ] Testar scheduler automático no próximo horário agendado (06:00)
