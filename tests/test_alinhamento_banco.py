"""Teste de alinhamento models ↔ banco real.
Roda dentro da Hetzner onde o hostname Docker resolve."""

import sys
import os

# Set env vars
os.environ["DATABASE_URL"] = "postgresql://postgres:M2X1X8H9klP10T8xxmywPr8ZDq5b4ejYS3aRNaDCvNoIHNnQ2DKYAKu39CHRS0Av@rt6ykrued0duumj46mk70kpw:5432/astrodicas"
os.environ["TELEGRAM_BOT_TOKEN"] = "test:token"
os.environ["TELEGRAM_CHANNEL_ID"] = "-100test"
os.environ["OPENAI_API_KEY"] = "sk-test"

sys.path.insert(0, "/app/src")

from sqlalchemy import inspect, text
from src.database import init_db, engine
from src.database.models import (
    Base, Assinante, Signo, Horoscopo, Pagamento, Compra, Postagem,
)

errors = []

# Req 1: 6 classes
expected_models = {
    "Assinante": Assinante,
    "Signo": Signo,
    "Horoscopo": Horoscopo,
    "Pagamento": Pagamento,
    "Compra": Compra,
    "Postagem": Postagem,
}
for name, cls in expected_models.items():
    assert cls.__tablename__ in Base.metadata.tables, f"Tabela {cls.__tablename__} não registrada"
    print(f"  ✅ Req 1: {name} -> {cls.__tablename__}")

# Req 2: init_db não recria
init_db()
print("  ✅ Req 2: init_db() executou sem erro (checkfirst=True)")

# Req 3-8: verificar colunas no banco real
inspector = inspect(engine)

expected_columns = {
    "assinantes": ["id", "telegram_id", "username", "primeiro_nome", "ativo", "criado_em", "atualizado_em"],
    "signos": ["id", "nome", "periodo", "emoji", "descricao", "criado_em"],
    "horoscopos": ["id", "signo_id", "data", "tipo", "conteudo", "criado_em"],
    "pagamentos": ["id", "assinante_id", "valor", "moeda", "tipo", "status", "pagamento_id", "expira_em", "criado_em", "atualizado_em"],
    "compras": ["id", "assinante_id", "pagamento_id", "produto", "valor", "status", "criado_em", "confirmado_em"],
    "postagens": ["id", "tipo", "conteudo", "imagem_url", "publicado_em", "criado_em"],
}

for table, cols in expected_columns.items():
    db_cols = [c["name"] for c in inspector.get_columns(table)]
    for col in cols:
        assert col in db_cols, f"Coluna {col} não encontrada em {table}"
    print(f"  ✅ Req 3-8: {table} → {len(cols)} colunas OK")

# Req 9: conexão funcional
with engine.connect() as conn:
    result = conn.execute(text("SELECT count(*) FROM signos"))
    count = result.scalar()
    print(f"  ✅ Req 9: conexão OK — {count} signos no banco")

print("\n🎉 Todos os 9 requisitos passaram!")
