# Map — Bot de Vendas

## Dependências do código existente

| Arquivo/função | Reutilizado? | Como |
|---|---|---|
| `src/config/settings.py` | ✅ **Sim** | Herda configurações (Ominiroute, banco, Asaas) |
| `src/database/models.py` | ✅ **Sim** | Classes Assinante, Pagamento, Compra já existem |
| `src/database/__init__.py` | ✅ **Sim** | Função `init_db()`, engine, SessionLocal |
| `src/scheduler/conteudo_diario.py` | 🟡 Parcial | Prompt `horoscopo_individual` reutilizado pra previsão semanal |
| `src/scheduler/gerador_imagem.py` | 🟡 Parcial | Pode usar pra gerar capa dos PDFs |
| `src/bot/handler.py` | 🟡 Parcial | Inspiração pra webhook mode + criação do app |

## Novo código necessário

### `src/vendas_bot/` — módulo completo

| Arquivo | O que faz |
|---|---|
| `__init__.py` | Exports |
| `main.py` | FastAPI app + lifespan + webhook setup + scheduler |
| `handler.py` | Handlers do python-telegram-bot (comandos, callbacks, mensagens) |
| `pagamento.py` | Integração Asaas: criar cobrança, verificar status, webhook |
| `assinatura.py` | Lógica de assinatura: criar, expirar, renovar, avisar |
| `mapa_astral.py` | Geração de PDF via LLM + fpdf2/weasyprint |
| `scheduler.py` | APScheduler: previsão semanal, lembretes, expiração |
| `models_vendas.py` | Models específicos de vendas (signo do assinante, preferências) |
| `settings.py` | Settings adicionais (token do bot de vendas, admin_id) |
| `README.md` | Instruções do módulo |

### Dockerfile separado

| Arquivo | Onde |
|---|---|
| `docker/vendas_bot/Dockerfile` | Dockerfile específico pra esse bot |
| `docker/vendas_bot/docker-compose.yml` | Deploy no Coolify |

## Schema de banco — colunas extras necessárias

Tabela `assinantes` precisa de colunas adicionais (que não existem no schema atual):

| Coluna | Tipo | Descrição |
|---|---|---|
| `signo_id` | FK → signos.id | Signo do assinante |
| `data_nascimento` | DATE | Data de nascimento |
| `hora_nascimento` | TIME / VARCHAR(5) | Hora de nascimento (opcional) |
| `cidade_nascimento` | VARCHAR(255) | Cidade de nascimento |
| `telegram_chat_id` | BIGINT | Chat ID pra enviar DM (mesmo que telegram_id no modelo atual) |

*(Estas colunas serão adicionadas via migration ou `ALTER TABLE`)*

## Deploy

- **Nome do app no Coolify:** `astrodicas-vendas-bot`
- **Domínio:** `bot-vendas.astrodicas.inovalabx.com.br`
- **Porta:** 3000 (padrão)
- **Webhook Telegram:** `https://bot-vendas.astrodicas.inovalabx.com.br/webhook`
- **Webhook Asaas:** `https://bot-vendas.astrodicas.inovalabx.com.br/asaas/webhook`
