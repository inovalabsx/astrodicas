-- Migration: base de afiliados (idempotente)
-- Data: 2026-05-30
-- Banco alvo: astrodicas

BEGIN;

CREATE TABLE IF NOT EXISTS afiliados (
  id SERIAL PRIMARY KEY,
  assinante_id INTEGER NOT NULL UNIQUE REFERENCES assinantes(id) ON DELETE CASCADE,
  codigo VARCHAR(32) NOT NULL UNIQUE,
  pix_chave TEXT,
  ativo BOOLEAN NOT NULL DEFAULT TRUE,
  criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
  atualizado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS afiliado_leads (
  id SERIAL PRIMARY KEY,
  afiliado_id INTEGER NOT NULL REFERENCES afiliados(id) ON DELETE CASCADE,
  indicado_telegram_id BIGINT NOT NULL,
  origem TEXT NOT NULL DEFAULT 'telegram_start',
  expira_em TIMESTAMP WITHOUT TIME ZONE NOT NULL,
  convertido_em TIMESTAMP WITHOUT TIME ZONE,
  criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_afiliado_lead UNIQUE (afiliado_id, indicado_telegram_id)
);

CREATE TABLE IF NOT EXISTS afiliado_comissoes (
  id SERIAL PRIMARY KEY,
  afiliado_id INTEGER NOT NULL REFERENCES afiliados(id) ON DELETE CASCADE,
  assinante_id INTEGER NOT NULL REFERENCES assinantes(id) ON DELETE CASCADE,
  pagamento_id INTEGER NOT NULL REFERENCES pagamentos(id) ON DELETE CASCADE,
  valor_venda NUMERIC(10,2) NOT NULL,
  percentual NUMERIC(5,2) NOT NULL DEFAULT 40.00,
  valor_comissao NUMERIC(10,2) NOT NULL,
  status TEXT NOT NULL DEFAULT 'pendente',
  liberacao_prevista_em TIMESTAMP WITHOUT TIME ZONE NOT NULL,
  liberado_em TIMESTAMP WITHOUT TIME ZONE,
  criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS afiliado_saques (
  id SERIAL PRIMARY KEY,
  afiliado_id INTEGER NOT NULL REFERENCES afiliados(id) ON DELETE CASCADE,
  valor NUMERIC(10,2) NOT NULL,
  status TEXT NOT NULL DEFAULT 'solicitado',
  pix_chave TEXT NOT NULL,
  transacao_id TEXT,
  pago_em TIMESTAMP WITHOUT TIME ZONE,
  criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

-- Índices úteis para consultas do fluxo
CREATE INDEX IF NOT EXISTS idx_afiliado_leads_indicado_telegram_id ON afiliado_leads(indicado_telegram_id);
CREATE INDEX IF NOT EXISTS idx_afiliado_leads_expira_em ON afiliado_leads(expira_em);
CREATE INDEX IF NOT EXISTS idx_afiliado_comissoes_afiliado_status ON afiliado_comissoes(afiliado_id, status);
CREATE INDEX IF NOT EXISTS idx_afiliado_comissoes_liberacao_prevista_em ON afiliado_comissoes(liberacao_prevista_em);
CREATE INDEX IF NOT EXISTS idx_afiliado_saques_afiliado_status ON afiliado_saques(afiliado_id, status);

-- Evitar comissão duplicada por pagamento
CREATE UNIQUE INDEX IF NOT EXISTS uq_afiliado_comissoes_pagamento_id ON afiliado_comissoes(pagamento_id);

COMMIT;
