# Spec — Scheduler ativo: salvar + publicar conteúdo

## Objetivo
Fazer o scheduler diário realmente funcionar: gerar conteúdo, salvar no banco (`postagens` e `horoscopos`), gerar imagem via Ominiroute/IMAGENS, e publicar no canal Telegram @astro_dicas.

## Requisitos funcionais

### 1. Salvar postagem no banco
**WHEN** `job_publicar(tipo)` for executado **THEN** sistema DEVE:
- Gerar conteúdo via `conteudo_diario.gerar_conteudo(tipo)`
- Criar registro na tabela `postagens` com: titulo (baseado no tipo), conteudo (texto gerado), tipo, status="rascunho", criado_em=now

### 2. Gerar imagem para a postagem
**WHEN** conteúdo for gerado **THEN** sistema DEVE:
- Usar o `imagem_prompt` retornado por `gerar_conteudo()`
- Chamar `gerador_imagem.gerar_imagem(prompt)` via Ominiroute/IMAGENS
- Se imagem gerada com sucesso, baixar para arquivo temporário
- Se falhar, logar warning e continuar sem imagem

### 3. Publicar no canal Telegram
**WHEN** conteúdo + imagem estiverem prontos **THEN** sistema DEVE:
- Enviar texto + imagem (se houver) para `settings.telegram_channel_id`
- Usar o bot token `settings.telegram_bot_token` (bot @astro_dicas_bot)
- Após envio bem-sucedido, atualizar `postagens.status` para "publicado" e `publicada_em` para now
- Se falhar no envio, manter status="rascunho" e logar erro

### 4. Gerar horóscopo para todos os 12 signos
**WHEN** tipo="horoscopo" **THEN** sistema DEVE:
- Buscar lista de signos da tabela `signos`
- Para cada signo, gerar conteúdo individual via LLM com prompt específico
- Salvar cada resultado na tabela `horoscopos` com signo_id, data=today, tipo="diario"
- Os 12 horóscopos individuais NÃO são enviados para o canal (só o conteúdo agregado)

### 5. Agendamento preservado
**WHEN** scheduler iniciar **THEN** sistema DEVE:
- Manter os 3 horários: 06:00 (horoscopo), 12:00 (lua), 18:00 (frase)
- Manter post extra domingo 10:00 (transito)
- Usar `settings.timezone` = America/Sao_Paulo

### 6. Robusto a falhas
**WHEN** qualquer passo falhar (LLM, banco, Telegram, imagem) **THEN** sistema DEVE:
- Logar erro com detalhes
- Não abortar outros passos (ex: falha na imagem não impede publicação)
- Não crashar o scheduler nem o app

## Fora de escopo
- Bot de DM (@astro_dicas_bot responder comandos) — próxima feature
- Bot de vendas (@astro_dicas_vendasbot) — feature separada
- Cache de conteúdo já gerado no dia
- Cálculo astrológico real (PyEphem) — placeholder continua
