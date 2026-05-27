# State — AstroDicas

## Status
✅ Scheduler ativo: salvar + publicar no Telegram
✅ Bot webhook integrado no FastAPI
✅ Provider Ominiroute configurado

## Última ação (27/05/2026)
Feature: **Scheduler Ativo** — gerar, salvar no banco e publicar no Telegram

**Feature:** `scheduler-ativo`
**Spec:** `.fdd/features/scheduler-ativo/spec.md`

### O que foi feito
#### Scheduler (já rodava, agora faz algo útil)
- `publicar.py` — novo módulo com fluxo completo: gerar conteúdo → salvar `postagens` → gerar imagem Ominiroute/IMAGENS → enviar pro Telegram → atualizar status
- `cron.py` — refatorado pra chamar `publicar()` em vez de só printar
- `conteudo_diario.py` — adicionado prompt `horoscopo_individual` pra gerar horóscopo de cada signo

#### Bot webhook
- `handler.py` — refatorado: `criar_app()` sem `updater` (modo webhook), funções `processar_update()` e `shutdown_app()`
- `main.py` — lifespan usa `criar_app()`, configura webhook no Telegram, endpoint `POST /webhook` recebe updates
- `settings.py` — adicionado campo `domain` (default: `bot.astrodicas.inovalabx.com.br`)

#### Gerar horóscopos individuais
- `publicar._gerar_e_salvar_horoscopos_individuais()` — gera conteúdo pra cada um dos 12 signos via Ominiroute/CODING-BASIC, salva na tabela `horoscopos`
- Chamado automaticamente nos posts de horóscopo (06:00)

#### Limpeza
- `.env` — template atualizado (removeu campos antigos `LLM_MODEL`, `IMAGE_MODEL`, `IMAGE_STYLE`, `OPENAI_API_KEY`; adicionou `OMINIROUTE_API_KEY`, `DOMAIN`, `LLM_BASE_URL`, `LLM_MODEL_TEXT`, `LLM_MODEL_IMAGE`)

### Arquivos alterados/criados
- `src/scheduler/publicar.py` — **CRIADO** (887 linhas)
- `src/scheduler/cron.py` — reescrito (chama `publicar()`)
- `src/scheduler/conteudo_diario.py` — prompt `horoscopo_individual` + handler
- `src/bot/handler.py` — webhook mode (criar_app sem updater)
- `src/main.py` — webhook integrado, lifespan com bot + scheduler
- `src/config/settings.py` — campo `domain`
- `.env` — template atualizado

### Testes
- ✅ Importação de todos os módulos (settings, models, init_db, publicar, handler)
- ✅ FastAPI rotas OK (/health, /, /webhook)
- ✅ 5 prompts de conteúdo (horoscopo, lua, frase, transito, horoscopo_individual)
- ✅ 12 pares signo/elemento no publicar
- ✅ publicar() falha graciosamente sem rede (não crasha)

### Próximos passos
- [ ] Commit + push + deploy Coolify
- [ ] Bot de vendas (@astro_dicas_vendasbot) — próxima feature
- [ ] Testar E2E no canal Telegram real (no próximo horário agendado)
