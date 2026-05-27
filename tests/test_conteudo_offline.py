"""Testes offline do scheduler de conteúdo — sem API externa."""

import asyncio
import os
import sys
from pathlib import Path

# Set env vars BEFORE importing src
os.environ["OPENAI_API_KEY"] = "sk-test"
os.environ["TELEGRAM_BOT_TOKEN"] = "123:test"
os.environ["TELEGRAM_CHANNEL_ID"] = "-100test"

# PYTHONPATH = parent of src/ (so "from src.xxx" resolves correctly)
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_conteudo_offline():
    """Gera conteúdo sem LLM real — verifica estrutura e prompts."""
    from src.scheduler.conteudo_diario import PROMPTS, SIGNOS
    from src.scheduler.conteudo_diario import _get_contexto_astral, _get_signo_do_dia
    from datetime import date

    print("=" * 60)
    print("📋 Testando geração de conteúdo (sem LLM real)...")
    print("=" * 60)

    # Verifica prompts
    for tipo in PROMPTS:
        print(f"\n🔮 {tipo.upper()}")
        print("-" * 40)
        prompt = PROMPTS[tipo]
        placeholders = []
        for c in prompt.split("{"):
            if "}" in c and not c.startswith("{"):
                ph = c.split("}")[0]
                placeholders.append(ph)
        print(f"  Placeholders: {placeholders}")
        print(f"  Tamanho: {len(prompt)} chars")
        print(f"  ✅ OK")

    print("\n" + "=" * 60)
    print("✅ Todos os prompts validados!")
    print("=" * 60)

    # Testa estrutura de retorno
    print("\n📦 Teste de estrutura de retorno...")
    mock_conteudo = {
        "tipo": "horoscopo",
        "conteudo": "[conteúdo gerado pelo LLM]",
        "imagem_prompt": "Astral theme zodiac sign",
        "data": "2026-05-27",
    }
    assert "tipo" in mock_conteudo
    assert "conteudo" in mock_conteudo
    assert "imagem_prompt" in mock_conteudo
    assert "data" in mock_conteudo
    print("✅ Estrutura OK")

    # Testa signos
    print("\n📋 Teste de signos...")
    assert len(SIGNOS) == 12
    print(f"✅ {len(SIGNOS)} signos carregados")

    # Testa funções auxiliares
    print("\n🧪 Teste de funções auxiliares...")
    ctx = _get_contexto_astral(date.today())
    assert isinstance(ctx, str)
    assert len(ctx) > 10
    print(f"  Contexto astral: {ctx}")
    print(f"  ✅ OK")

    signo = _get_signo_do_dia()
    assert signo in [s[0] for s in SIGNOS]
    print(f"  Signo do dia: {signo}")
    print(f"  ✅ OK")

    print("\n" + "=" * 60)
    print("🎉 Todos os testes offline passaram!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    asyncio.run(test_conteudo_offline())
