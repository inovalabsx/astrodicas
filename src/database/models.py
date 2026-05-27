"""AstroDicas — Modelos de banco de dados."""

import uuid
from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey,
    Integer, Numeric, String, Text, Time, UUID,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    telegram_id = Column(Integer, unique=True, nullable=False)
    nome = Column(String(255), nullable=False)
    username = Column(String(255), nullable=True)

    # Dados para mapa astral
    data_nascimento = Column(Date, nullable=True)
    hora_nascimento = Column(Time, nullable=True)
    cidade = Column(String(255), nullable=True)
    estado = Column(String(100), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    assinaturas = relationship("Assinatura", back_populates="usuario")
    vendas = relationship("Venda", back_populates="usuario")


class Assinatura(Base):
    __tablename__ = "assinaturas"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    usuario_id = Column(UUID, ForeignKey("usuarios.id"), nullable=False)
    status = Column(String(50), default="ativa")  # ativa, cancelada, expirada
    plano = Column(String(50), default="mensal")  # mensal, anual
    inicio = Column(DateTime, default=datetime.utcnow)
    fim = Column(DateTime, nullable=True)
    ultimo_pagamento = Column(DateTime, nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)

    usuario = relationship("Usuario", back_populates="assinaturas")


class Venda(Base):
    __tablename__ = "vendas"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    usuario_id = Column(UUID, ForeignKey("usuarios.id"), nullable=False)

    # Stripe Payment Intent ID
    stripe_payment_intent_id = Column(String(255), nullable=True)
    # Produto (ex: mapa_astral, assinatura_mensal)
    produto = Column(String(100), nullable=False)

    valor_brl = Column(Numeric(10, 2), nullable=False)

    status = Column(String(50), default="pendente")  # pendente, confirmado, cancelado, reembolsado

    # Dados do PIX gerado
    pix_cobranca_id = Column(String(255), nullable=True)
    pix_qrcode = Column(Text, nullable=True)
    pix_copia_cola = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    confirmado_at = Column(DateTime, nullable=True)

    usuario = relationship("Usuario", back_populates="vendas")


class ConteudoGerado(Base):
    __tablename__ = "conteudos_gerados"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    tipo = Column(String(50), nullable=False)  # horoscopo, lua, frase, quiz, etc.
    conteudo = Column(Text, nullable=False)
    imagem_url = Column(Text, nullable=True)
    prompt_imagem = Column(Text, nullable=True)
    publicado_telegram = Column(Boolean, default=False)
    publicado_instagram = Column(Boolean, default=False)
    data_referencia = Column(Date, default=date.today)
    created_at = Column(DateTime, default=datetime.utcnow)
