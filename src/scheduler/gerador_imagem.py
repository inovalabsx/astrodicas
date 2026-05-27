"""AstroDicas — Geração de imagens via Ominiroute /v1/images/generations."""

import base64
import json
import logging
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional

from src.config.settings import settings

logger = logging.getLogger(__name__)

IMAGE_GEN_URL = f"{settings.llm_base_url.rstrip('/')}/images/generations"


def gerar_imagem(prompt: str, model: Optional[str] = None) -> Optional[str]:
    """Gera imagem via Ominiroute /v1/images/generations e salva em arquivo local.

    Usa POST direto com requests HTTP (não OpenAI SDK) porque o SDK
    do OpenAI bate em /v1/images/generations de forma diferente do que
    o Ominiroute espera com modelo provider/model.

    Returns:
        Caminho absoluto do arquivo de imagem (suffix .jpg), ou None se falhar.
    """
    if not settings.ominiroute_api_key:
        logger.warning("OMINIROUTE_API_KEY não configurada — pulando geração de imagem")
        return None

    model = model or settings.llm_model_image
    logger.info(f"🎨 Gerando imagem com model={model}, prompt={prompt[:80]}...")

    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
    }).encode()

    req = urllib.request.Request(IMAGE_GEN_URL, data=payload)
    req.add_header("Authorization", f"Bearer {settings.ominiroute_api_key}")
    req.add_header("Content-Type", "application/json")

    try:
        resp = urllib.request.urlopen(req, timeout=120)
        raw = resp.read()
        logger.info(f"HTTP {resp.status}, {len(raw)} bytes recebidos")

        data = json.loads(raw)
        img_data = data.get("data", [{}])[0]

        # 1. Tenta b64_json (formato do antigravity/gemini-3.1-flash-image)
        b64 = img_data.get("b64_json", "")
        if b64:
            img_bytes = base64.b64decode(b64)
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp.write(img_bytes)
                path = tmp.name
            logger.info(f"✅ Imagem gerada via b64_json: {len(img_bytes)} bytes -> {path}")
            return path

        # 2. Tenta URL (formato clássico DALL-E)
        url = img_data.get("url", "")
        if url:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                path = tmp.name
            urllib.request.urlretrieve(url, path)
            file_size = Path(path).stat().st_size
            logger.info(f"✅ Imagem baixada de URL: {file_size} bytes -> {path}")
            return path

        logger.warning(f"Resposta sem b64_json nem url: {json.dumps(img_data)[:200]}")
        return None

    except Exception as e:
        logger.error(f"❌ Erro ao gerar imagem: {e}")
        return None
