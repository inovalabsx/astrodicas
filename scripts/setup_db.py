"""Script pra criar as tabelas no banco PostgreSQL."""

import os
import sys
from pathlib import Path

os.environ["TELEGRAM_BOT_TOKEN"] = "123:test"
os.environ["TELEGRAM_CHANNEL_ID"] = "-100test"
os.environ["OPENAI_API_KEY"] = "sk-test"

# Path = project root (parent of src/)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database import engine
from src.database.models import Base
from sqlalchemy import inspect

print("📦 Conectando ao banco...")
print(f"  Engine: {engine.url}")

inspector = inspect(engine)
tables = inspector.get_table_names()

if not tables:
    print("📝 Criando tabelas...")
    Base.metadata.create_all(bind=engine)
    tables = inspector.get_table_names()
    print(f"  ✅ Tabelas criadas: {tables}")
else:
    print(f"  ⚠️  Tabelas já existem: {tables}")

print(f"\n📋 Total: {len(tables)} tabelas")
for t in tables:
    cols = inspector.get_columns(t)
    print(f"  📊 {t}: {len(cols)} colunas")
    for c in cols[:4]:
        print(f"    - {c['name']}: {c['type']}")
    if len(cols) > 4:
        print(f"    ... mais {len(cols)-4} colunas")

print("\n✅ Banco pronto!")
