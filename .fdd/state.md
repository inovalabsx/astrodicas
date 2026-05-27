# State — AstroDicas

## Status
🛠️ Fase 1: estrutura pronta, banco rodando, bot Telegram detectado

## Última ação
- **.env** configurado com tokens reais (Telegram, GitHub)
- **PostgreSQL** rodando via Docker — 4 tabelas criadas (usuarios, assinaturas, vendas, conteudos_gerados)
- **Bot Telegram** @astro_dicas_bot testado — OK
- **Canal @AstroDicas** descoberto (ID: -1003955074430)
- **Git** configurado e commit inicial feito (34 arquivos)
- **Testes offline** passando

## Pendente
- ❗ Adicionar @astro_dicas_bot como **admin** no canal @AstroDicas pra permitir postagens automáticas
- Configurar **OpenAI API Key** no .env pra gerar conteúdo com LLM real
- Testar publicação real no canal
- Deploy no Coolify
- Git remote (by-lua/astrodicas)

## Próximo passo
Assim que bot for admin no canal, testar postagem real e configurar scheduler automático
