"""AstroDicas — Geração de conteúdo diário."""

import random
from datetime import date, datetime
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from src.config.settings import settings


# Prompts base para cada tipo de conteúdo
PROMPTS = {
    "horoscopo": """Você é um astrólogo brasileiro. Gere o horóscopo GERAL DO DIA para o canal @astro_dicas em português brasileiro natural, acolhedor e místico.

Data: {data}
Contexto astrológico do dia: {contexto_astral}

Este post vai no CANAL para TODOS os assinantes. Deve cobrir TODOS os 12 signos.

Regras:
- Comece com 2 parágrafos sobre a energia geral do dia
- Depois liste CADA um dos 12 signos com 1-2 frases cada
- Tom acolhedor e místico, sem exageros
- Inclua uma dica geral no final
- Use emojis com moderação
- NÃO use a palavra "previsão"

Signos para incluir (TODOS): Áries 🔥, Touro 🌱, Gêmeos 💨, Câncer 🌊, Leão 🔥, Virgem 🌱, Libra 💨, Escorpião 🌊, Sagitário 🔥, Capricórnio 🌱, Aquário 💨, Peixes 🌊

Formato:
🌙 HORÓSCOPO GERAL DO DIA | {data}

[energia geral do dia em 2 parágrafos]

🔮 Áries: ...
🔮 Touro: ...
🔮 Gêmeos: ...
🔮 Câncer: ...
🔮 Leão: ...
🔮 Virgem: ...
🔮 Libra: ...
🔮 Escorpião: ...
🔮 Sagitário: ...
🔮 Capricórnio: ...
🔮 Aquário: ...
🔮 Peixes: ...

✨ Dica do dia: [dica prática geral]""",

    "lua": """Você é um astrólogo brasileiro. Gere um post sobre a lua do dia em português brasileiro natural.

Data: {data}
Fase lunar: {fase_lua}
Signo da lua: {signo_lua}

Regras:
- Explique o significado da fase lunar + signo
- Como isso afeta cada signo (liste os 4 signos mais impactados)
- Tom poético mas direto
- Máximo 4 parágrafos
- Termine com uma prática recomendada
- Use 🌙 no início""",

    "frase": """Você é um astrólogo brasileiro. Crie uma frase inspiradora do dia com tema astrológico em português brasileiro.

Contexto astrológico: {contexto_astral}

Regras:
- Uma frase curta (máximo 30 palavras)
- Deve parecer um "recado do universo" para o dia
- Tom poético, não religioso
- Pode mencionar signos indiretamente
- NÃO use clichês como "o universo conspira"
- Termine com uma explicação de 1 parágrafo sobre o significado astrológico""",

    "horoscopo_individual": """Você é um astrólogo brasileiro. Gere o horóscopo do dia para o signo {signo} em português brasileiro natural.

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

✨ Dica: [dica prática]""",

    "trânsito": """Você é um astrólogo brasileiro. Explique um trânsito astrológico importante do dia em português brasileiro.

Data: {data}
Trânsito: {transito}
Planetas envolvidos: {planetas}

Regras:
- Explique o que significa na prática para o dia a dia
- Liste quais signos são mais afetados
- Duração esperada do trânsito
- Dica de como aproveitar essa energia
- Tom educativo e acessível
- Máximo 4 parágrafos"""
}


# Lista de signos com elementos
SIGNOS = [
    ("Áries", "Fogo"), ("Touro", "Terra"), ("Gêmeos", "Ar"),
    ("Câncer", "Água"), ("Leão", "Fogo"), ("Virgem", "Terra"),
    ("Libra", "Ar"), ("Escorpião", "Água"), ("Sagitário", "Fogo"),
    ("Capricórnio", "Terra"), ("Aquário", "Ar"), ("Peixes", "Água"),
]

# Frases de encerramento variadas
ENCERRAMENTOS = [
    "Brilhe hoje ✨",
    "Que os astros te guiem 🌙",
    "Siga a energia do universo ⭐",
    "Hoje é seu dia de brilhar 🌟",
    "Que a luz dos astros te acompanhe 🌌",
]


def _get_contexto_astral(data: date) -> str:
    """Gera contexto astrológico básico do dia."""
    # Placeholder — depois substituir por cálculo real com PyEphem
    fase_lua = random.choice(["Nova", "Crescente", "Cheia", "Minguante"])
    signo_lua = random.choice([s[0] for s in SIGNOS])
    return f"Lua {fase_lua} em {signo_lua}. Clima astral de introspecção e renovação."


def _get_signo_do_dia() -> str:
    """Retorna o signo do dia baseado na data."""
    # Mantido por compatibilidade histórica, não usado mais pelo fluxo novo
    return "Áries"


async def gerar_conteudo(
    tipo: str,
    llm: Optional[ChatOpenAI] = None,
    data: Optional[date] = None
) -> dict:
    """Gera um conteúdo do tipo especificado.

    Args:
        tipo: Tipo de conteúdo (horoscopo, lua, frase, transito)
        llm: Instância do LLM (opcional — cria uma se não fornecido)
        data: Data do conteúdo (opcional — usa hoje se não fornecido)

    Returns:
        dict com tipo, conteudo, imagem_prompt e data
    """
    if llm is None:
        llm = ChatOpenAI(
            model=settings.llm_model_text,
            api_key=settings.ominiroute_api_key,
            base_url=settings.llm_base_url,
        )

    if data is None:
        data = date.today()

    contexto = _get_contexto_astral(data)
    prompt = PROMPTS.get(tipo)

    if not prompt:
        raise ValueError(f"Tipo de conteúdo desconhecido: {tipo}")

    if tipo == "horoscopo":
        mensagem = prompt.format(
            data=data.strftime("%d/%m/%Y"),
            contexto_astral=contexto,
        )
        imagem_prompt = "Wheel of zodiac with all 12 signs, dark purple mystical background"
    elif tipo == "horoscopo_individual":
        # Prompt específico pra um signo (usado ao popular horoscopos de todos os 12)
        signo = None
        elemento = None
        mensagem = None
        # Será chamado com signo e elemento externamente (via publicar.py)
        # Esse bloco não é usado diretamente — o publicar.py monta a mensagem separadamente
        imagem_prompt = "Zodiac wheel with all 12 signs, dark purple background"
        raise ValueError("horoscopo_individual não deve ser chamado via gerar_conteudo() diretamente")
    elif tipo == "lua":
        fase = random.choice(["Nova", "Crescente", "Cheia", "Minguante"])
        mensagem = prompt.format(
            data=data.strftime("%d/%m/%Y"),
            fase_lua=fase,
            signo_lua=random.choice([s[0] for s in SIGNOS]),
        )
        imagem_prompt = f"Glowing {fase} moon on dark purple sky with stars..."
    elif tipo == "frase":
        mensagem = prompt.format(contexto_astral=contexto)
        imagem_prompt = "Open book with golden light emanations, dark purple background..."
    elif tipo == "transito":
        planetas = random.choice([
            "Mercúrio e Vênus",
            "Marte e Júpiter",
            "Saturno e Netuno",
        ])
        mensagem = prompt.format(
            data=data.strftime("%d/%m/%Y"),
            transito=f"{planetas} em aspecto harmonioso",
            planetas=planetas,
        )
        imagem_prompt = "Planetary alignment dots connected by golden lines..."

    # Gera o texto via LLM
    response = await llm.ainvoke([
        SystemMessage(content="Você é um astrólogo brasileiro experiente, fala português natural e acolhedor."),
        HumanMessage(content=mensagem),
    ])

    return {
        "tipo": tipo,
        "conteudo": response.content,
        "imagem_prompt": imagem_prompt,
        "data": data.isoformat(),
    }
