"""AstroDicas — Modelos de banco de dados.

Alinhado com o schema real do banco `astrodicas` no PostgreSQL do Coolify.
Tabelas: assinantes, signos, horoscopos, pagamentos, compras, postagens
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Assinante(Base):
    """Assinantes do AstroDicas — usuários do bot de vendas."""

    __tablename__ = "assinantes"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(Text, nullable=True)
    primeiro_nome = Column(Text, nullable=True)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pagamentos = relationship("Pagamento", back_populates="assinante")
    compras = relationship("Compra", back_populates="assinante")


class Signo(Base):
    """Os 12 signos do zodíaco."""

    __tablename__ = "signos"

    id = Column(Integer, primary_key=True)
    nome = Column(Text, unique=True, nullable=False)
    periodo = Column(Text, nullable=False)
    emoji = Column(Text, nullable=True)
    descricao = Column(Text, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    horoscopos = relationship("Horoscopo", back_populates="signo")


class Horoscopo(Base):
    """Horóscopos gerados por signo e data/tipo."""

    __tablename__ = "horoscopos"

    id = Column(Integer, primary_key=True)
    signo_id = Column(Integer, ForeignKey("signos.id"), nullable=True)
    data = Column(Date, nullable=False)
    tipo = Column(Text, default="diario")
    conteudo = Column(Text, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)

    signo = relationship("Signo", back_populates="horoscopos")


class Pagamento(Base):
    """Pagamentos dos assinantes — PIX, cartão, etc."""

    __tablename__ = "pagamentos"

    id = Column(Integer, primary_key=True)
    assinante_id = Column(Integer, ForeignKey("assinantes.id"), nullable=True)
    valor = Column(Numeric(10, 2), nullable=False)
    moeda = Column(Text, default="BRL")
    tipo = Column(Text, nullable=False)
    status = Column(Text, default="pendente")
    pagamento_id = Column(Text, nullable=True)
    expira_em = Column(DateTime, nullable=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assinante = relationship("Assinante", back_populates="pagamentos")
    compras = relationship("Compra", back_populates="pagamento")


class Compra(Base):
    """Compras realizadas pelos assinantes — produtos adquiridos."""

    __tablename__ = "compras"

    id = Column(Integer, primary_key=True)
    assinante_id = Column(Integer, ForeignKey("assinantes.id"), nullable=True)
    pagamento_id = Column(Integer, ForeignKey("pagamentos.id"), nullable=True)
    produto = Column(Text, nullable=False)
    valor = Column(Numeric(10, 2), nullable=True)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)

    assinante = relationship("Assinante", back_populates="compras")
    pagamento = relationship("Pagamento", back_populates="compras")


class Postagem(Base):
    """Conteúdo publicado no canal Telegram do AstroDicas."""

    __tablename__ = "postagens"

    id = Column(Integer, primary_key=True)
    titulo = Column(Text, nullable=True)
    conteudo = Column(Text, nullable=False)
    tipo = Column(Text, default="texto")
    canal_id = Column(Integer, nullable=True)
    agendada_para = Column(DateTime, nullable=True)
    publicada_em = Column(DateTime, nullable=True)
    status = Column(Text, default="rascunho")
    criado_em = Column(DateTime, default=datetime.utcnow)
