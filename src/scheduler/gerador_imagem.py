"""AstroDicas — Geração de imagens com DALL-E / Stability."""

import logging
from typing import Optional

from openai import OpenAI
import requests

from src.config.settings import settings

logger = logging.getLogger(__name__)


def gerar_imagem(prompt: str, model: Optional[str] = None) -> Optional[str]:
    """Gera uma imagem via DALL-E e retorna a URL.

    Args:
        prompt: Descrição da imagem
        model: Modelo (padrão: settings.image_model)

    Returns:
        URL da imagem gerada, ou None se falhar
    """
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY não configurada — pulando geração de imagem")
        return None

    client = OpenAI(api_key=settings.openai_api_key)
    model = model or settings.image_model

    try:
        response = client.images.generate(
            model=model,
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        url = response.data[0].url
        logger.info(f"✅ Imagem gerada via {model}: {url[:80]}...")
        return url
    except Exception as e:
        logger.error(f"❌ Erro ao gerar imagem: {e}")
        return None


def baixar_imagem(url: str, destino: str) -> bool:
    """Baixa imagem de uma URL para arquivo local."""
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        with open(destino, "wb") as f:
            f.write(r.content)
        logger.info(f"✅ Imagem salva em {destino}")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao baixar imagem: {e}")
        return False
