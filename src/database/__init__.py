"""AstroDicas — Config do banco e sessão."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config.settings import settings
from src.database.models import Base

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Cria todas as tabelas."""
    Base.metadata.create_all(bind=engine)


def get_session():
    """Retorna uma sessão do banco."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
