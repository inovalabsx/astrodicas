# Spec — Bot de Vendas (@astro_dicas_vendasbot)

## Objetivo

Bot Telegram que vende **assinatura mensal** (Plano Lua R$9,90) e **mapas astrais avulsos** (R$19,90 cada). Gerencia cadastro de assinantes, cobranças via Asaas, entrega de PDFs por DM, e conteúdo recorrente semanal.

---

## Discovery — Definições de negócio

### Modelo de assinatura

| Item | Detalhe |
|---|---|
| **Plano Lua** | R$9,90/mês |
| **Brinde de boas-vindas** | Mapa Astral Completo em PDF (na ativação) |
| **Conteúdo recorrente** | Horóscopo diário personalizado (06:00) + previsão semanal (sábado) + lembrete de fases da lua |
| **Desconto** | 30% OFF em mapas extras (R$19,90 → R$13,93) |

### Produtos avulsos — R$19,90 cada (assinante paga R$13,93)

1. **Mapa Astral Completo** — Planetas, casas, aspectos, interpretação completa
2. **Sinastria (Mapa do Amor)** — Compatibilidade entre 2 pessoas
3. **Mapa da Carreira** — Talento, vocação, Casa 10
4. **Revolução Solar** — Previsão do ano do aniversário até o próximo

*(Mapa Kármico futuramente)*

### Gateway
- **Asaas** — PIX, cartão, boleto. Sandbox primeiro, depois produção.

### Arquitetura
- App separado no mesmo repositório: `src/vendas_bot/`
- Deploy separado no Coolify (serviço independente)
- Webhook mode (python-telegram-bot)
- Compartilha banco PostgreSQL `astrodicas` com o app principal

---

## Requisitos funcionais

### Fluxo 1 — Comando /start e onboarding

1. **WHEN** usuário enviar `/start` **THEN** bot DEVE responder com menu de opções: "Assinar Plano Lua (R$9,90)" / "Comprar Mapa Avulso" / "Minhas Assinaturas" / "Ajuda"
2. **WHEN** usuário escolher "Assinar Plano Lua" **THEN** bot DEVE:
   - Perguntar o **nome** do usuário (usar como `primeiro_nome`)
   - Perguntar qual é o **signo** do usuário (lista dos 12)
   - Perguntar **data de nascimento** (DD/MM/AAAA) — para gerar o mapa astral de brinde
   - Perguntar **cidade de nascimento** (para gerar mapa astral)
   - Perguntar **hora de nascimento** (opcional, se não souber usa 12:00)
   - Criar registro em `assinantes` com telegram_id, nome, username, signo_id, data_nascimento
   - Gerar cobrança via Asaas no valor de R$9,90
   - Enviar dados do pagamento (PIX copia-e-cola ou link de cartão)
3. **WHEN** usuário escolher "Comprar Mapa Avulso" **THEN** bot DEVE:
   - Mostrar lista dos mapas disponíveis com preço e descrição curta
   - Se usuário for assinante ativo, mostrar preço com 30% OFF
   - Após seleção, perguntar dados necessários (data/hora/local para Astral, 2 pessoas para Sinastria, etc.)
   - Gerar cobrança via Asaas
4. **WHEN** usuário escolher "Minhas Assinaturas" **THEN** bot DEVE mostrar status da assinatura (ativa/inativa), data de expiração, e histórico de compras

### Fluxo 2 — Pagamento e confirmação

5. **WHEN** usuário realizar pagamento **THEN** sistema DEVE:
   - Receber notificação de confirmação via webhook do Asaas
   - Atualizar `pagamentos.status` para "confirmado"
   - Se for assinatura: criar registro em `compras` com produto="plano_lua", valor=9.90, ativo=True, criado_em=now
   - Se for mapa avulso: iniciar geração do PDF
6. **WHEN** pagamento de assinatura for confirmado **THEN** sistema DEVE:
   - Gerar Mapa Astral Completo em PDF usando dados do usuário (data/hora/local)
   - Enviar PDF no DM do usuário via Telegram
   - Definir expira_em = now + 30 dias em `pagamentos`
7. **WHEN** pagamento de mapa avulso for confirmado **THEN** sistema DEVE:
   - Gerar PDF do mapa escolhido com os dados fornecidos
   - Enviar PDF no DM do usuário
   - Registrar em `compras` com produto="<tipo_mapa>", valor=19.90 (ou 13.93 se assinante)
8. **WHEN** pagamento expirar (não confirmado em 24h) **THEN** sistema DEVE:
   - Atualizar `pagamentos.status` para "expirado"
   - Notificar usuário que o link de pagamento venceu e oferecer novo

### Fluxo 3 — Conteúdo recorrente (Plano Lua)

9. **WHEN** for sábado às 08:00 BRT **THEN** scheduler DO BOT DE VENDAS DEVE:
   - Buscar todos assinantes com `compras.ativo=True` e produto="plano_lua"
   - Para cada um, gerar previsão semanal personalizada via LLM com base no signo
   - Enviar a previsão no DM do assinante
10. **WHEN** for 06:00 BRT de qualquer dia **THEN** scheduler DO BOT DE VENDAS DEVE:
   - Buscar todos assinantes com `compras.ativo=True` e produto="plano_lua"
   - Para cada um, buscar o horóscopo do dia na tabela `horoscopos` filtrado pelo signo do assinante
   - Se horóscopo não existir, aguardar/ignorar (o scheduler do bot principal gera às 06:00)
   - Enviar SÓ TEXTO no DM: "Bom dia, {nome}! 🌞 Seu horóscopo de hoje:\n\n{conteudo}"
   - Sem imagem, sem PDF — apenas texto personalizado
11. **WHEN** faltar 1 dia para Lua Nova ou Lua Cheia **THEN** sistema DEVE:
    - Buscar todos assinantes ativos
    - Enviar lembrete: "Amanhã é Lua Nova/Cheia! 🌙 Como isso afeta [signo]: [texto gerado]"
12. **WHEN** assinatura completar 30 dias **THEN** sistema DEVE:
    - Avisar usuário que a assinatura vai vencer em 3 dias
    - Oferecer renovação com novo link de pagamento
13. **WHEN** assinatura expirar (sem renovação) **THEN** sistema DEVE:
    - Atualizar `compras.ativo=False`
    - Parar de enviar previsão semanal e lembretes
    - Notificar usuário que a assinatura foi desativada

### Fluxo 4 — Geração de PDF

13. **WHEN** sistema precisar gerar um mapa astral **THEN** DEVE:
    - Construir prompt detalhado com: data, hora, cidade, tipo_do_mapa
    - Enviar para LLM (Ominiroute/CODING-BASIC) com instrução de gerar texto completo em markdown
    - Converter markdown para PDF formatado (com fpdf2 ou weasyprint)
    - Incluir capa com: nome do mapa, nome do usuário, data de geração
    - Salvar PDF temporário e enviar via Telegram
14. **WHEN** LLM falhar ao gerar conteúdo **THEN** sistema DEVE:
    - Tentar novamente 1 vez
    - Se falhar de novo, avisar usuário que o mapa está sendo gerado e será enviado em breve
    - Agendar retry para 1 hora depois
15. **WHEN** PDF tiver mais de 50MB **THEN** sistema DEVE dividir em partes ou comprimir

### Fluxo 5 — Administração

16. **WHEN** admin enviar /admin **THEN** bot DEVE (apenas para admin_id configurado):
    - Mostrar: total de assinantes ativos, receita do mês, pagamentos pendentes
17. **WHEN** admin enviar /broadcast <mensagem> **THEN** bot DEVE:
    - Enviar mensagem para todos assinantes ativos
    - Limitar a 30 mensagens/minuto (rate limit Telegram)
18. **WHEN** admin enviar /cancelar <telegram_id> **THEN** bot DEVE desativar assinatura do usuário

---

## Fora de escopo

- Bot de DM conversacional (@astro_dicas_bot responder perguntas) — feature separada
- Grupo VIP de assinantes — feature futura
- Cálculo astrológico real com PyEphem — usar IA pura pra gerar conteúdo dos mapas
- Cache de mapas já gerados — cada mapa é único (ou quase)
- Página web de checkout — tudo via Telegram DM
- Integração com Instagram — feature separada
- Mapa Infantil, Mapa Kármico — adicionar depois do lançamento
- Suporte a mais de 1 pagamento simultâneo por usuário (fila simples)

---

## Dependências

- **Banco:** tabelas `assinantes`, `pagamentos`, `compras` já existem no PostgreSQL `astrodicas`
- **LLM:** instância Ominiroute (`lua.ominiroute.inovalabx.com.br/v1`) + CODING-BASIC para gerar conteúdo dos mapas
- **Asaas:** chave API em `settings.asaas_api_key`, ambiente sandbox primeiro
- **Telegram bot token** pra @astro_dicas_vendasbot (precisa ser criado com @BotFather)
- **Rate limit:** Asaas API (60 req/min), Telegram (30 msg/min), LLM (sem limite prático)

---

## Critérios de aceite

- [ ] /start mostra menu com opções
- [ ] Fluxo de assinatura: selecionar signo → dados nascimento → cobrança Asaas → confirmação → PDF enviado
- [ ] Fluxo de mapa avulso: selecionar tipo → dados → cobrança → confirmação → PDF
- [ ] Assinantes ativos recebem previsão semanal no sábado
- [ ] Assinantes ativos recebem lembrete de luas
- [ ] Desconto de 30% aplicado automaticamente pra assinantes
- [ ] Assinatura expira em 30 dias com aviso prévio
- [ ] Webhook Asaas atualiza status do pagamento no banco
- [ ] Comandos admin funcionam (admin, broadcast, cancelar)
- [ ] Health check endpoint responde OK
