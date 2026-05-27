# Spec — AstroDicas (v1)

> Canal Telegram + Instagram + Bot agente de IA sobre astrologia/signos

## Objetivo
Criar ecossistema completo AstroDicas: canal no Telegram com conteúdo automático de signos, Instagram integrado com mesma identidade visual, e bot agente de IA que vende mapas astrais, numerologia e assinatura premium, com painel admin pra acompanhar vendas.

---

## Fase 1 — Canal Telegram

### RF1. Canal público
O canal `@AstroDicas` deve ser público e acessível sem convite.

### RF2. Conteúdo diário automático
WHEN chegar o horário configurado (ex: 6h, 12h, 18h) THEN o sistema DEVE gerar e publicar conteúdo automaticamente no canal.

### RF3. Tipos de conteúdo
O conteúdo automático DEVE incluir:
- Horóscopo do dia (texto curto, por signo ou geral)
- Lua do dia / trânsitos importantes
- Frase do dia com tema astrológico
- Datas especiais (lua cheia, eclipse, retrogradação)
- Conteúdo interativo: enquetes, quizzes, chamada pro bot

### RF4. Identidade visual do canal
WHEN publicar qualquer conteúdo THEN o formato DEVE seguir identidade visual consistente (cores, fontes, estilo).

### RF5. Engajamento
WHEN um seguidor interagir (enquete, comentário) THEN o sistema DEVE considerar pra adaptar conteúdo futuro.

---

## Fase 2 — Instagram

### RF6. Postagem automática no Instagram
WHEN um post for publicado no Telegram THEN o sistema DEVE gerar versão para Instagram automaticamente.

### RF7. Identidade visual consistente
Todos os posts no Instagram DEVEM usar a mesma identidade visual do canal Telegram.

### RF8. Imagens geradas por IA
WHEN gerar um post THEN o sistema DEVE criar imagem via API de IA (DALL-E / Stability) com:
- Mesma identidade visual
- Tema do dia
- Texto sobreposto legível

---

## Fase 3 — Bot Agente (LangGraph)

### RF9. Bot no Telegram
WHEN usuário enviar mensagem para @AstroDicasBot THEN o agente DEVE responder com personalidade de astrólogo em PT-BR natural.

### RF10. Perguntas sobre signos
WHEN usuário perguntar sobre signo, ascendente, compatibilidade THEN o agente DEVE responder com base em conhecimento astrológico.

### RF11. Cálculo de mapa astral real
WHEN usuário solicitar mapa astral THEN o agente DEVE:
- Solicitar: nome completo, data de nascimento, hora de nascimento (opcional), cidade e estado
- Calcular mapa com efemérides (PyEphem / SwissEph)
- Gerar PDF com interpretação

### RF12. Tipos de mapa
O sistema DEVE oferecer:
- Mapa astral completo
- Mapa amoroso (+ opcional: adicionar outra pessoa para compatibilidade)
- Mapa de carreira
- Mapa de prosperidade
- Numerologia (baseada no nome)
- Mapa do nome

### RF13. Pagamento PIX
WHEN usuário escolher um produto pago THEN o agente DEVE:
- Gerar cobrança PIX (via Asaas/Stripe)
- Aguardar confirmação de pagamento via webhook
- Liberar o produto (PDF ou conteúdo premium)

### RF14. Pagamento em crypto para o dono
WHEN pagamento for confirmado THEN o sistema DEVE converter automaticamente BRL recebido para USDT/BTC (via Binance API ou PayDay).

### RF15. Assinatura premium
WHEN usuário assinar plano mensal THEN o sistema DEVE:
- Cobrar recorrentemente via PIX
- Entregar conteúdo exclusivo diário
- Gerenciar status da assinatura (ativa/cancelada)

### RF16. Painel admin
WHEN admin acessar o painel THEN DEVE visualizar:
- Vendas realizadas (produto, valor, data, status)
- Assinantes ativos e cancelados
- Total faturado (BRL e estimado em crypto)
- Últimas interações do bot

---

## Fora de escopo (v1)
- Site próprio (tudo via Telegram + Instagram)
- App mobile nativo
- Suporte humanizado 24h (bot faz tudo)
- Múltiplos idiomas (apenas PT-BR)

---

## Critérios de Aceite (gerais)

- Canal Telegram com conteúdo automático rodando 3x/dia
- Instagram com posts automáticos sincronizados
- Bot respondendo perguntas de signo em PT-BR natural
- Geração de PDF de mapa astral funcional
- Pagamento PIX → liberação de produto → conversão crypto
- Painel admin mostrando vendas e assinaturas
- Tudo rodando em Coolify
