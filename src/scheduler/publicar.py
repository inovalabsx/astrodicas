"""AstroDicas — Publicação de conteúdo no canal Telegram."""

import logging
import random
import tempfile
from datetime import date
from pathlib import Path

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from sqlalchemy import text

from src.config.settings import settings
from src.database import SessionLocal
from src.database.models import Horoscopo, Postagem, Signo
from src.scheduler.conteudo_diario import gerar_conteudo
from src.scheduler.gerador_imagem import baixar_imagem, gerar_imagem

logger = logging.getLogger(__name__)

BOT_TOKEN = settings.telegram_bot_token
CHANNEL_ID = settings.telegram_channel_id
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Mapeamento elemento -> signos
SIGNOS_ELEMENTOS = [
    ("Áries", "Fogo"), ("Touro", "Terra"), ("Gêmeos", "Ar"),
    ("Câncer", "Água"), ("Leão", "Fogo"), ("Virgem", "Terra"),
    ("Libra", "Ar"), ("Escorpião", "Água"), ("Sagitário", "Fogo"),
    ("Capricórnio", "Terra"), ("Aquário", "Ar"), ("Peixes", "Água"),
]

PROMPT_HOROSCOPO_INDIVIDUAL = """Você é um astrólogo brasileiro. Gere o horóscopo do dia para o signo {signo} em português brasileiro natural.

Data: {data}
Elemento: {elemento}

Regras:
- 2 parágrafos curtos
- Tom pessoal, como se fosse um conselho direto pro nativo do signo
- Inclua uma dica prática ou alerta
- Use emojis com moderação (🌙 ✨ ⭐)
- Termine com uma frase positiva
- NÃO use "previsão" nem "segundo os astros"

Formato:
🔮 {signo} | {data}

[texto]

✨ Dica: [dica prática]"""


def _salvar_postagem(tipo: str, conteudo: str, titulo: str) -> int | None:
    """Salva registro na tabela postagens e retorna o id."""
    db = SessionLocal()
    try:
        post = Postagem(titulo=titulo, conteudo=conteudo, tipo=tipo, status="rascunho")
        db.add(post)
        db.commit()
        db.refresh(post)
        logger.info(f"Postagem salva: id={post.id}, tipo={tipo}")
        return post.id
    except Exception as e:
        logger.error(f"Falha ao salvar postagem: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def _atualizar_status_postagem(post_id: int, status: str) -> None:
    db = SessionLocal()
    try:
        db.execute(
            text("UPDATE postagens SET status = :s, publicada_em = now() WHERE id = :id"),
            {"s": status, "id": post_id},
        )
        db.commit()
    except Exception as e:
        logger.error(f"Falha ao atualizar status da postagem {post_id}: {e}")
        db.rollback()
    finally:
        db.close()


async def _enviar_telegram(texto: str, image_path: str | None = None) -> bool:
    if image_path and Path(image_path).exists():
        return await _enviar_com_foto(texto, image_path)
    return await _enviar_texto(texto)


async def _enviar_texto(texto: str) -> bool:
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": CHANNEL_ID, "text": texto, "parse_mode": "HTML"}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=payload)
            if r.status_code == 200:
                logger.info("✅ Mensagem enviada ao canal (texto)")
                return True
            logger.error(f"❌ Erro Telegram sendMessage: {r.status_code} {r.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Erro ao enviar Telegram: {e}")
        return False


async def _enviar_com_foto(texto: str, image_path: str) -> bool:
    url = f"{BASE_URL}/sendPhoto"
    try:
        with open(image_path, "rb") as photo:
            async with httpx.AsyncClient(timeout=60) as client:
                form = {"chat_id": CHANNEL_ID, "caption": texto, "parse_mode": "HTML"}
                files = {"photo": (image_path.split("/")[-1], photo, "image/jpeg")}
                r = await client.post(url, data=form, files=files)
                if r.status_code == 200:
                    logger.info("✅ Mensagem enviada ao canal (foto)")
                    return True
                logger.error(f"❌ Erro Telegram sendPhoto: {r.status_code} {r.text}")
                return await _enviar_texto(texto)
    except Exception as e:
        logger.error(f"❌ Erro ao enviar foto: {e}")
        return await _enviar_texto(texto)


def _get_llm() -> ChatOpenAI:
    """Cria instância do LLM (Ominiroute CODING-BASIC)."""
    return ChatOpenAI(
        model=settings.llm_model_text,
        api_key=settings.ominiroute_api_key,
        base_url=settings.llm_base_url,
    )


async def _gerar_e_salvar_horoscopos_individuais(data: date) -> None:
    """Gera horóscopo individual para todos os 12 signos e salva na tabela horoscopos."""
    llm = _get_llm()
    db = SessionLocal()
    try:
        signos = db.query(Signo).all()
        logger.info(f"Gerando horóscopos individuais para {len(signos)} signos...")
    finally:
        db.close()

    for signo in signos:
        try:
            # Pula se já existe pro dia
            db = SessionLocal()
            existente = db.query(Horoscopo).filter(
                Horoscopo.signo_id == signo.id,
                Horoscopo.data == data,
                Horoscopo.tipo == "diario",
            ).first()
            db.close()
            if existente:
                logger.debug(f"⏭️ {signo.nome}: já existe para {data}")
                continue

            # Descobre o elemento
            elemento = ""
            for s_nome, s_elem in SIGNOS_ELEMENTOS:
                if s_nome == signo.nome:
                    elemento = s_elem
                    break

            # Gera via LLM
            prompt_texto = PROMPT_HOROSCOPO_INDIVIDUAL.format(
                signo=signo.nome,
                data=data.strftime("%d/%m/%Y"),
                elemento=elemento,
            )
            response = await llm.ainvoke([
                SystemMessage(content="Você é um astrólogo brasileiro experiente, fala português natural e acolhedor."),
                HumanMessage(content=prompt_texto),
            ])

            db = SessionLocal()
            salvo = Horoscopo(
                signo_id=signo.id,
                data=data,
                tipo="diario",
                conteudo=response.content,
            )
            db.add(salvo)
            db.commit()
            logger.info(f"  ✅ {signo.nome}: horóscopo salvo")
            db.close()
        except Exception as e:
            logger.error(f"  ❌ Falha ao gerar horóscopo de {signo.nome}: {e}")
            try:
                db.close()
            except Exception:
                pass
            continue


async def publicar(tipo: str) -> bool:
    """Fluxo completo: gerar → salvar → imagem → publicar Telegram."""
    logger.info(f"[PUBLICAR] Iniciando publicação tipo={tipo}")

    # 1. Gerar conteúdo geral (pra ir pro canal)
    try:
        result = await gerar_conteudo(tipo=tipo)
    except Exception as e:
        logger.error(f"[PUBLICAR] Falha ao gerar conteúdo: {e}")
        return False

    conteudo = result["conteudo"]
    imagem_prompt = result["imagem_prompt"]

    titulos = {
        "horoscopo": "🌙 Horóscopo do Dia",
        "lua": "🌕 Lua do Dia",
        "frase": "✨ Frase do Dia",
        "transito": "🔭 Trânsito Astral",
    }
    titulo = titulos.get(tipo, tipo.capitalize())

    # 2. Salvar como rascunho no banco
    post_id = _salvar_postagem(tipo=tipo, conteudo=conteudo, titulo=titulo)

    # 3. Gerar imagem (não crítica — se falhar, segue sem)
    image_path = None
    try:
        image_url = gerar_imagem(prompt=imagem_prompt)
        if image_url:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp_path = tmp.name
            if baixar_imagem(image_url, tmp_path):
                image_path = tmp_path
                logger.info(f"✅ Imagem baixada: {tmp_path}")
    except Exception as e:
        logger.warning(f"[PUBLICAR] Imagem ignorada (não crítica): {e}")

    # 4. Publicar no Telegram
    enviado = await _enviar_telegram(texto=conteudo, image_path=image_path)

    # 5. Atualizar status da postagem
    if post_id:
        status = "publicado" if enviado else "rascunho"
        _atualizar_status_postagem(post_id, status)

    # 6. Se horóscopo, gerar conteúdo individual pros 12 signos
    if tipo == "horoscopo" and not settings.ominiroute_api_key.startswith("TEST_"):
        await _gerar_e_salvar_horoscopos_individuais(data=date.today())

    # Cleanup imagem temporária
    if image_path and Path(image_path).exists():
        try:
            Path(image_path).unlink()
        except Exception:
            pass

    logger.info(f"[PUBLICAR] Finalizado — tipo={tipo}, enviado={enviado}")
    return enviado
