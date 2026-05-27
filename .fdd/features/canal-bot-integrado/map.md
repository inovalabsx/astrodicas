# Map — AstroDicas

> Arquitetura e componentes do ecossistema AstroDicas

## Visão geral

```
                   ┌─────────────────────┐
                   │   Coolify (Deploy)   │
                   └────────┬────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
    ┌────▼────┐      ┌─────▼─────┐      ┌─────▼─────┐
    │ Telegram │      │  LangGraph │      │ Insta   │
    │  API     │◄────►│   Agent    │◄────►│  API     │
    └──────────┘      └─────┬─────┘      └──────────┘
                            │
               ┌────────────┼────────────┐
               │            │            │
          ┌────▼───┐  ┌────▼───┐  ┌─────▼─────┐
          │ Redis   │  │Postgres│  │  Imagem   │
          │(cache/  │  │(dados) │  │  API      │
          │ sessão) │  └────────┘  │(DALL-E)   │
          └─────────┘              └───────────┘
```

---

## Estrutura de pastas

```
/bots/Projects/bot-signos/
├── .fdd/                        ← Specs e estado
├── src/
│   ├── agent/                   ← LangGraph
│   │   ├── graph.py              ← Definição do grafo (nós + arestas)
│   │   ├── nodes/                ← Nós do grafo
│   │   │   ├── classifier.py     ← Classifica intenção do usuário
│   │   │   ├── signo.py          ← Responde perguntas sobre signo
│   │   │   ├── mapa.py           ← Gera mapa astral
│   │   │   ├── pagamento.py      ← Processa pagamento PIX
│   │   │   ├── assinatura.py     ← Gerencia assinaturas
│   │   │   └── conteudo.py       ← Gera conteúdo automático
│   │   ├── tools/                ← Ferramentas do agente
│   │   │   ├── efemerides.py     ← Cálculos astrológicos (PyEphem)
│   │   │   ├── pdf_generator.py  ← Gera PDF do mapa
│   │   │   ├── pagamento_api.py  ← Integração Asaas/Stripe
│   │   │   ├── crypto_swap.py    ← Conversão BRL→USDT
│   │   │   └── image_gen.py      ← Geração de imagem (DALL-E)
│   │   └── prompts/              ← System prompts
│   │       ├── astrologo.txt     ← Personalidade do astrólogo
│   │       └── conteudo.txt      ← Template de conteúdo
│   ├── bot/                      ← Interface Telegram
│   │   ├── telegram.py           ← Conexão com Telegram API
│   │   ├── handlers.py           ← Handlers de comandos/mensagens
│   │   └── keyboards.py          ← Teclados inline
│   ├── instagram/                ← Integração Instagram
│   │   ├── poster.py             ← Publica posts automaticamente
│   │   └── image.py              ← Formata imagem pro formato do Insta
│   ├── admin/                    ← Painel admin
│   │   ├── app.py                ← Web app (FastAPI ou Streamlit?)
│   │   ├── templates/            ← HTML/CSS
│   │   └── api.py                ← API interna pro painel
│   ├── database/                 ← Banco de dados
│   │   ├── models.py             ← Modelos SQLAlchemy / raw SQL
│   │   ├── migrations/           ← Migrações
│   │   └── queries.py            ← Consultas
│   ├── scheduler/                ← Conteúdo automático
│   │   ├── cron.py               ← Agendador de tarefas
│   │   └── conteudo_diario.py    ← Geração de posts do dia
│   └── config/                   ← Configuração
│       ├── settings.py           ← Variáveis de ambiente
│       └── identities/           ← Identidade visual
│           ├── cores.txt
│           ├── fontes.txt
│           └── estilo.txt
├── tests/
├── requirements.txt
├── Dockerfile
├── docker-compose.yml            ← App + Redis + Postgres
└── coolify.json                  ← Config Coolify
```

---

## Modelos de dados (PostgreSQL)

### `usuarios`
| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | UUID | PK |
| telegram_id | BIGINT | ID do Telegram |
| nome | TEXT | Nome no Telegram |
| data_nascimento | DATE | Para mapa astral |
| hora_nascimento | TIME | Opcional |
| cidade | TEXT | Para mapa |
| estado | TEXT | Para mapa |
| created_at | TIMESTAMP | |

### `assinaturas`
| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | UUID | PK |
| usuario_id | UUID | FK → usuarios |
| status | TEXT | ativa/cancelada/expirada |
| plano | TEXT | mensal/anual |
| inicio | TIMESTAMP | |
| fim | TIMESTAMP | |
| ultimo_pagamento | TIMESTAMP | |

### `vendas`
| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | UUID | PK |
| usuario_id | UUID | FK → usuarios |
| produto | TEXT | mapa_astral, mapa_amoroso, etc. |
| valor_brl | DECIMAL | Valor em reais |
| valor_usdt | DECIMAL | Valor convertido |
| status | TEXT | pendente/confirmado/cancelado |
| pix_cobranca | TEXT | Código da cobrança PIX |
| pix_qrcode | TEXT | QR code |
| webhook_id | TEXT | ID do webhook de confirmação |
| created_at | TIMESTAMP | |
| confirmado_at | TIMESTAMP | |

### `conteudos_gerados`
| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | UUID | PK |
| tipo | TEXT | horoscopo, lua, frase, etc. |
| conteudo | TEXT | Texto gerado |
| imagem_url | TEXT | URL da imagem gerada |
| publicado_telegram | BOOL | |
| publicado_instagram | BOOL | |
| created_at | TIMESTAMP | |

---

## Fluxos principais

### Fluxo do bot (LangGraph)
```
mensagem → classifier
  ├── "signo" → signo.py → responde direto
  ├── "quero mapa" → mapa.py → pede dados → calcula → gera PDF → pagamento.py → entrega
  ├── "assinar" → assinatura.py → pagamento.py → ativa
  ├── "ajuda" → menu.py
  └── "outro" → fallback → astrólogo responde
```

### Fluxo de conteúdo automático
```
cron (6h/12h/18h)
  → conteudo_diario.py decide tema do dia
  → gera texto (via LLM)
  → image_gen.py gera imagem (DALL-E c/ identidade visual)
  → publica no Telegram
  → poster.py publica no Instagram
  → salva em conteudos_gerados
```

### Fluxo de pagamento
```
usuário escolhe produto
  → pagamento_api.py gera cobrança PIX (Asaas)
  → envia QR code via Telegram
  → aguarda webhook de confirmação
  → confirma → libera produto (PDF/assinatura)
  → crypto_swap.py converte BRL→USDT (Binance)
```

---

## Componentes externos

| Serviço | Uso | API |
|---------|-----|-----|
| Telegram API | Bot + Canal | python-telegram-bot |
| Instagram API | Posts automáticos | graph-api |
| OpenAI/Anthropic | LLM do agente | API key |
| DALL-E / Stability | Imagens | API key |
| Asaas ou Stripe | PIX | API + webhook |
| Binance API | BRL→USDT | API key |
| Redis | Cache, sessões, fila | local |
| PostgreSQL | Dados persistentes | local |

---

## Painel admin (sugestão)

**Stack**: FastAPI (backend) + HTML/CSS simples (frontend sem framework pesado)

Ou algo ainda mais simples tipo **Streamlit** — menos código, já entrega.

Páginas:
- Dashboard (gráfico de vendas, faturamento)
- Vendas (lista com filtros)
- Assinaturas (ativas/canceladas)
- Usuários
- Conteúdos gerados

---

## Próximos passos
1. Setup do projeto (estrutura de pastas, docker-compose)
2. Banco de dados (models + migrations)
3. Fase 1 — Conteúdo automático no Telegram
4. Fase 2 — Instagram
5. Fase 3 — Bot + Vendas + Painel
