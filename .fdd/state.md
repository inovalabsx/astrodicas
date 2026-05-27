# State — AstroDicas

## Status
🛠️ Fase 1 em implementação

## Fase atual
Fase 1: Canal Telegram com conteúdo automático — estrutura criada, testes offline OK

## Última ação
- Estrutura de pastas criada (`src/`, `tests/`, config)
- `settings.py` + `pyproject.toml` + `.env.example`
- `docker-compose.yml` + `Dockerfile`
- `models.py` (usuarios, assinaturas, vendas, conteudos_gerados)
- `database/__init__.py` (engine + session)
- `migrations/env.py` (Alembic)
- `conteudo_diario.py` — 4 tipos de conteúdo (horoscopo, lua, frase, transito)
- `gerador_imagem.py` — DALL-E integration
- `cron.py` — APScheduler com jobs 3x/dia + domingo
- `bot/handler.py` — Telegram bot com /start, /menu, buttons
- `bot/publisher.py` — publicar_no_canal(), enviar_mensagem_direta()
- `config/identities/estilo.txt` — identidade visual
- `tests/test_conteudo_offline.py` — ✅ testes offline passaram

## Próximo passo
- Configurar Telegram token e testar publicação real no canal
- Ou aguardar configuração de variáveis de ambiente + deploy
