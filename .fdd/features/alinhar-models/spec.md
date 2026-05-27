# Spec — Alinhar models SQLAlchemy com schema real do banco

## Objetivo

Substituir os models SQLAlchemy atuais (`Usuario`, `Assinatura`, `Venda`, `ConteudoGerado`) pelos models que refletem exatamente o schema real do banco `astrodicas`: `Assinante`, `Signo`, `Horoscopo`, `Pagamento`, `Compra`, `Postagem`.

## Requisitos funcionais

1. **WHEN** carregar models **THEN** sistema DEVE ter 6 classes: `Assinante`, `Signo`, `Horoscopo`, `Pagamento`, `Compra`, `Postagem`
2. **WHEN** rodar `init_db()` **THEN** sistema NÃO DEVE dropar ou recriar tabelas existentes (via `checkfirst=True`)
3. **WHEN** acessar `Assinante` **THEN** colunas DEVM ser: id, telegram_id, username, primeiro_nome, ativo, criado_em, atualizado_em
4. **WHEN** acessar `Signo` **THEN** colunas DEVM ser: id, nome, periodo, emoji, descricao, criado_em
5. **WHEN** acessar `Horoscopo` **THEN** colunas DEVM ser: id, signo_id (FK→signos), data, tipo, conteudo, criado_em
6. **WHEN** acessar `Pagamento` **THEN** colunas DEVM ser: id, assinante_id (FK→assinantes), valor, moeda, tipo, status, pagamento_id, expira_em, criado_em, atualizado_em
7. **WHEN** acessar `Compra` **THEN** colunas DEVM ser: id, assinante_id (FK→assinantes), pagamento_id (FK→pagamentos), produto, valor, ativo, criado_em
8. **WHEN** acessar `Postagem` **THEN** colunas DEVM ser: id, titulo, conteudo, tipo, canal_id, agendada_para, publicada_em, status, criado_em
9. **WHEN** criar sessão SQLAlchemy com `database_url` do .env **THEN** engine DEVE conectar sem erro

## Fora de escopo

- Criar novas tabelas (só alinhar com as existentes)
- Migração de dados
- Alterar schema do banco
- Lógica de negócio (handlers, scheduler)
