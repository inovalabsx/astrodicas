-- Migration: Adicionar colunas de assinante para o bot de vendas
-- Executar no banco astrodicas antes de iniciar o bot de vendas

ALTER TABLE assinantes
  ADD COLUMN IF NOT EXISTS signo_id INTEGER REFERENCES signos(id),
  ADD COLUMN IF NOT EXISTS data_nascimento DATE,
  ADD COLUMN IF NOT EXISTS hora_nascimento VARCHAR(5),
  ADD COLUMN IF NOT EXISTS cidade_nascimento TEXT;
