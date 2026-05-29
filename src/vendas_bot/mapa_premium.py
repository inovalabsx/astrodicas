"""Gerador Premium de Mapa Astral em PDF — estilo Personare.

PDF de 15+ páginas com:
- Capa personalizada por tipo de mapa
- Roda astrológica (imagem gerada)
- Sumário automático
- Interpretação completa por seção (LLM)
- Layout premium com cores e identidade visual

Tipos de mapa:
- astral    → Mapa Astral Completo (roxo/místico)
- sinastria → Sinastria Amorosa (rosa/quente)
- carreira  → Mapa da Carreira (azul/dourado)
- revolucao → Revolução Solar (verde/energético)
"""
from __future__ import annotations

import io
import json
import logging
import os
from datetime import date, datetime
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# ── Paletas por tipo de mapa ───────────────────────────────────────────────────

PALETAS = {
    "astral": {
        "cor_principal": (108, 59, 140),    # roxo astral
        "cor_secundaria": (60, 40, 100),
        "cor_terciaria": (180, 160, 220),   # lilás claro
        "cor_texto": (240, 235, 255),
        "cor_fundo": (18, 12, 35),
        "cor_destaque": (220, 180, 255),
        "cor_texto_escuro": (30, 20, 50),
        "cor_card": (35, 25, 60),
        "cor_linha": (80, 60, 120),
        "gradiente_inicio": (80, 40, 120),
        "gradiente_fim": (20, 10, 40),
        "icone_titulo": "✦",
        "cor_tag": (160, 120, 200),
    },
    "sinastria": {
        "cor_principal": (200, 60, 100),     # rosa/vermelho quente
        "cor_secundaria": (160, 40, 80),
        "cor_terciaria": (255, 200, 210),
        "cor_texto": (255, 245, 248),
        "cor_fundo": (40, 10, 25),
        "cor_destaque": (255, 140, 160),
        "cor_texto_escuro": (50, 20, 30),
        "cor_card": (60, 20, 40),
        "cor_linha": (180, 80, 110),
        "gradiente_inicio": (160, 40, 80),
        "gradiente_fim": (30, 5, 20),
        "icone_titulo": "♥",
        "cor_tag": (220, 100, 140),
    },
    "carreira": {
        "cor_principal": (30, 80, 160),      # azul/dourado
        "cor_secundaria": (20, 60, 120),
        "cor_terciaria": (220, 180, 80),
        "cor_texto": (240, 235, 220),
        "cor_fundo": (15, 20, 40),
        "cor_destaque": (255, 210, 80),
        "cor_texto_escuro": (20, 25, 50),
        "cor_card": (20, 30, 60),
        "cor_linha": (60, 100, 180),
        "gradiente_inicio": (40, 80, 160),
        "gradiente_fim": (10, 15, 35),
        "icone_titulo": "★",
        "cor_tag": (100, 160, 220),
    },
    "revolucao": {
        "cor_principal": (40, 140, 80),       # verde energizado
        "cor_secundaria": (20, 100, 60),
        "cor_terciaria": (180, 240, 200),
        "cor_texto": (230, 250, 240),
        "cor_fundo": (10, 30, 20),
        "cor_destaque": (100, 255, 150),
        "cor_texto_escuro": (20, 40, 30),
        "cor_card": (15, 45, 30),
        "cor_linha": (50, 160, 100),
        "gradiente_inicio": (30, 120, 70),
        "gradiente_fim": (8, 20, 15),
        "icone_titulo": "☀",
        "cor_tag": (80, 200, 130),
    },
}

TIPO_NOMES = {
    "astral": "Mapa Astral Completo",
    "sinastria": "Sinastria Amorosa",
    "carreira": "Mapa da Carreira",
    "revolucao": "Revolução Solar",
}


# ── Utilitários de imagem ──────────────────────────────────────────────────────

def hex_to_rgb(hex_str: str) -> tuple:
    h = hex_str.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def interp_color(c1: tuple, c2: tuple, t: float) -> tuple:
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def rgb_to_hex(c: tuple) -> str:
    return '#%02x%02x%02x' % c


def font_manager():
    """Retorna dicionário com caminhos de fontes disponíveis."""
    paths = {
        # Tenta DejaVu primeiro (tem negrito e suporte unicode)
        "regular": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "italic": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
        "bolditalic": "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf",
        # Fallback: Liberation Sans (similar Arial)
        "fallback_regular": "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "fallback_bold": "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    }
    result = {}
    for key, path in paths.items():
        if os.path.exists(path):
            result[key] = path
    return result


def _gerar_capa(
    nome: str, tipo: str, signo: str,
    data_nascimento: str, cidade: str, paleta: dict,
) -> Image.Image:
    """Gera imagem de capa decorada."""
    fonts = font_manager()
    font_bold = fonts.get("bold", fonts.get("fallback_bold"))
    font_reg = fonts.get("regular", fonts.get("fallback_regular"))

    w, h = 1080, 1528  # proporção A4 ~1:1.414
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)

    # Fundo gradiente
    for y in range(h):
        t = y / h
        color = interp_color(paleta["gradiente_inicio"], paleta["gradiente_fim"], t)
        draw.line([(0, y), (w, y)], fill=color)

    # Círculo decorativo central
    cx, cy = w // 2, h // 2 - 80
    for r in range(300, 100, -20):
        alpha = int(8 + 4 * (1 - (r - 100) / 200))
        cor_circulo = paleta["cor_principal"] + (alpha,)
        # Pillow não suporta alpha em RGB puro, vamos apenas desenhar com cor mais escura
        t_circulo = (r - 100) / 200
        cor = interp_color(paleta["cor_principal"], paleta["cor_secundaria"], t_circulo)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=cor, width=2)

    # Símbolo zodiacal central (usando texto grande)
    simbolos = {
        "Áries": "♈", "Touro": "♉", "Gêmeos": "♊", "Câncer": "♋",
        "Leão": "♌", "Virgem": "♍", "Libra": "♎", "Escorpião": "♏",
        "Sagitário": "♐", "Capricórnio": "♑", "Aquário": "♒", "Peixes": "♓",
    }
    simb = simbolos.get(signo, "✦")

    # Título: tipo de mapa
    titulo = TIPO_NOMES.get(tipo, tipo)
    try:
        font_titulo = ImageFont.truetype(font_bold, 48) if font_bold else ImageFont.load_default()
        font_nome = ImageFont.truetype(font_bold, 36) if font_bold else ImageFont.load_default()
        font_info = ImageFont.truetype(font_reg, 22) if font_reg else ImageFont.load_default()
        font_simbolo = ImageFont.truetype(font_reg, 140) if font_reg else ImageFont.load_default()
    except Exception:
        font_titulo = font_nome = font_info = font_simbolo = ImageFont.load_default()

    # Símbolo grande
    bbox = draw.textbbox((0, 0), simb, font=font_simbolo)
    sw, sh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((w - sw) // 2, cy - sh // 2),
        simb, fill=paleta["cor_texto"], font=font_simbolo,
    )

    # Título abaixo do símbolo
    bbox = draw.textbbox((0, 0), titulo, font=font_titulo)
    tw = bbox[2] - bbox[0]
    draw.text(((w - tw) // 2, cy + 120), titulo,
              fill=paleta["cor_destaque"], font=font_titulo)

    # Nome
    bbox = draw.textbbox((0, 0), nome.upper(), font=font_nome)
    nw = bbox[2] - bbox[0]
    draw.text(((w - nw) // 2, cy + 190), nome.upper(),
              fill=paleta["cor_texto"], font=font_nome)

    # Informações (data, signo, cidade)
    info = f"{signo}  |  {data_nascimento}  |  {cidade}"
    bbox = draw.textbbox((0, 0), info, font=font_info)
    iw = bbox[2] - bbox[0]
    draw.text(((w - iw) // 2, cy + 240), info,
              fill=paleta["cor_tag"], font=font_info)

    # Rodapé
    bbox = draw.textbbox((0, 0), "astro dicas", font=font_info)
    fw = bbox[2] - bbox[0]
    draw.text(((w - fw) // 2, h - 80), "astro dicas",
              fill=paleta["cor_terciaria"], font=font_info)

    return img


# ── Geração de seção via LLM ──────────────────────────────────────────────────

def _gerar_secao_llm(
    secao: dict, dados: dict, settings,
) -> str:
    """Gera conteúdo de uma seção via LLM (fallback se falhar)."""
    from urllib import request as urllib_request
    import json as jmod

    prompt = (
        f"Você é um astrólogo brasileiro. Gere o conteúdo da seção "
        f"'{secao['titulo']}' ({secao['subtitulo']}) do Mapa Astral de {dados['nome']}.\n\n"
        f"Dados astrológicos:\n"
        f"- Signo: {dados['signo']}\n"
        f"- Ascendente: {dados['ascendente']} ({dados['ascendente_grau']})\n"
        f"- Planeta Sol: em {dados.get('planetas', {}).get('Sol', 'desconhecido')}\n\n"
        f"Regras:\n"
        f"- 300 a 500 palavras\n"
        f"- Tom místico e acolhedor\n"
        f"- Texto corrido, parágrafos, sem markdown\n"
        f"- Conteúdo que preencha bem a página\n"
        f"- NÃO use ** ou caracteres especiais\n"
        f"- Retorne APENAS o texto da seção"
    )

    payload = jmod.dumps({
        "model": settings.llm_model_text,
        "messages": [
            {"role": "system", "content": "Você é um astrólogo profissional brasileiro."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 900,
    }).encode("utf-8")

    req = urllib_request.Request(
        f"{settings.llm_base_url}/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {settings.ominiroute_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib_request.urlopen(req, timeout=120) as resp:
            result = jmod.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning(f"Erro ao gerar seção '{secao['titulo']}': {e}")
        return (
            f"✦ {secao['titulo']} ✦\n\n"
            f"Esta seção do seu mapa está sendo preparada com carinho. "
            f"Em breve você terá a interpretação completa desta parte do seu Mapa Astral.\n\n"
            f"A AstroDicas agradece sua confiança! 🌟"
        )


# ── PDF completo ──────────────────────────────────────────────────────────────

def _pdf_page_capa(pdf, img_capa: Image.Image):
    """Adiciona página de capa ao PDF (imagem)."""
    buf = io.BytesIO()
    img_capa.save(buf, format='PNG', quality=95)
    buf.seek(0)
    pdf.add_page()
    pdf.image(buf, x=0, y=0, w=210, h=297)


def _pdf_page_roda(pdf, roda_path: str, assinatura: str):
    """Adiciona página com a roda astrológica."""
    pdf.add_page()
    w, h = 210, 297

    # Fundo escuro
    pdf.set_fill_color(13, 13, 26)
    pdf.rect(0, 0, w, h, style='F')

    # Título
    pdf.set_font("DejaVu", "B", 16)
    pdf.set_text_color(220, 180, 255)
    pdf.cell(0, 12, "Roda Astrológica", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(3)

    pdf.set_font("DejaVu", "", 10)
    pdf.set_text_color(150, 130, 200)
    pdf.cell(0, 8, assinatura, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)

    # Roda centralizada
    if os.path.exists(roda_path):
        # Calcular tamanho pra caber na página
        img_w, img_h = 160, 160  # mm
        x = (w - img_w) / 2
        pdf.image(roda_path, x=x, y=pdf.get_y(), w=img_w)

    # Legenda
    pdf.set_y(200)
    pdf.set_font("DejaVu", "", 8)
    pdf.set_text_color(100, 100, 140)
    pdf.multi_cell(0, 5,
        "Esta imagem representa a disposição dos planetas nos signos e "
        "casas astrológicas no momento do seu nascimento. Cada posição "
        "influencia diferentes aspectos da sua personalidade e destino.",
        align="C"
    )


def _pdf_page_secao(
    pdf,
    titulo: str,
    subtitulo: str,
    conteudo: str,
    paleta: dict,
    num_pagina: int,
):
    """Adiciona página de conteúdo de seção com layout melhorado.

    - Header com fundo escuro e texto claro
    - Conteúdo com fonte 11 e line-height 7
    - Footer relativo ao final do conteúdo, nunca sobrepondo
    - Se conteúdo curto (< meia página), espalha com mais espaçamento
    """
    pdf.add_page()
    w, h = 210, 297
    margem_esq = 18
    margem_dir = 18
    largura_texto = w - margem_esq - margem_dir

    # ── Header ────────────────────────────────────────────────────────────
    header_h = 35
    pdf.set_fill_color(*paleta["cor_principal"])
    pdf.rect(0, 0, w, header_h, style='F')

    pdf.set_font("DejaVu", "B", 18)
    pdf.set_text_color(*paleta["cor_texto"])  # sempre claro
    pdf.set_xy(15, 10)
    pdf.cell(0, 10, f"{paleta['icone_titulo']} {titulo}",
             new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("DejaVu", "", 10)
    pdf.set_text_color(*paleta["cor_destaque"])  # claro/destaque
    pdf.cell(0, 5, subtitulo, new_x="LMARGIN", new_y="NEXT")

    # ── Conteúdo ──────────────────────────────────────────────────────────
    pdf.ln(12)

    # Fonte maior (11) e line-height maior (7)
    pdf.set_font("DejaVu", "", 11)
    pdf.set_text_color(220, 215, 240)  # texto claro sobre fundo escuro

    paragrafos = conteudo.split("\n")
    espaco_base = 7   # line-height maior
    espaco_entre_pars = 6

    inicio_conteudo = pdf.get_y()
    for par in paragrafos:
        par = par.strip()
        if not par:
            pdf.ln(espaco_entre_pars)
            continue
        pdf.set_x(margem_esq)
        pdf.multi_cell(largura_texto, espaco_base, par)
        pdf.ln(4)

    fim_conteudo = pdf.get_y()

    # ── Verificar se conteúdo ocupou pelo menos meia página ──────────────
    # meia página útil = (h - header_h - espaco_footer) / 2
    espaco_minimo = (h - header_h - 25) // 2
    if (fim_conteudo - inicio_conteudo) < espaco_minimo:
        # Espalhar com padding extra antes do footer
        extra = espaco_minimo - (fim_conteudo - inicio_conteudo)
        pdf.ln(extra)

    # ── Footer (posição dinâmica) ────────────────────────────────────────
    y_rodape = pdf.get_y() + 8  # espaço após o conteúdo
    if y_rodape > h - 25:      # se passou do limite, quebra página
        pdf.add_page()
        y_rodape = h - 25

    footer_h = 25  # altura fixa
    # Se o footer cair em cima do conteúdo, adicionar página
    if y_rodape + footer_h > h - 15:
        pdf.add_page()
        y_rodape = h - 22

    pdf.set_y(y_rodape)
    pdf.set_fill_color(*paleta["cor_card"])
    pdf.rect(0, y_rodape, w, footer_h, style='F')

    pdf.set_font("DejaVu", "", 8)
    pdf.set_text_color(140, 130, 180)
    pdf.cell(0, 8, f"AstroDicas — astrodicas.inovalabx.com.br  |  Pág {num_pagina}",
             new_x="LMARGIN", new_y="NEXT", align="C")


def _pdf_page_sumario(pdf, secoes: list, paleta: dict, nome: str, tipo: str):
    """Adiciona página de sumário (índice) com contraste melhorado."""
    pdf.add_page()
    w, h = 210, 297

    # Header
    pdf.set_fill_color(*paleta["cor_principal"])
    pdf.rect(0, 0, w, 40, style='F')

    pdf.set_font("DejaVu", "B", 20)
    pdf.set_text_color(*paleta["cor_texto"])
    pdf.set_xy(15, 10)
    pdf.cell(0, 12, f"{paleta['icone_titulo']} Índice do seu Mapa", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("DejaVu", "", 11)
    pdf.set_text_color(*paleta["cor_destaque"])
    pdf.cell(0, 6, f"{TIPO_NOMES.get(tipo, tipo)} — {nome}",
             new_x="LMARGIN", new_y="NEXT")

    pdf.ln(10)

    # ── Lista de seções (FUNDO ESCURO + TEXTO CLARO) ─────────────────
    for idx, s in enumerate(sorted(secoes, key=lambda x, fallback=999: x.get("ordem", fallback))):
        pdf.set_x(20)

        # Card de fundo escuro + borda sutil
        pdf.set_fill_color(*paleta["cor_card"])
        pdf.set_draw_color(*paleta["cor_linha"])
        y_card = pdf.get_y()
        pdf.rect(18, y_card, w - 36, 18, style='DF')  # DF = fill + draw

        # Título da seção em texto CLARO
        pdf.set_font("DejaVu", "B", 11)
        pdf.set_text_color(*paleta["cor_texto"])  # ← CORRIGIDO: antes era cor_texto_escuro
        pdf.set_xy(22, y_card + 1)
        pdf.cell(0, 8, f"{s.get('ordem', idx+1):02d}.  {s['titulo']}",
                 new_x="LMARGIN", new_y="NEXT")

        # Subtítulo em tom mais claro
        pdf.set_font("DejaVu", "", 9)
        pdf.set_text_color(*paleta["cor_destaque"])  # ← CORRIGIDO: antes era 80,80,120
        pdf.set_xy(28, y_card + 9)
        pdf.cell(0, 7, f"{s.get('subtitulo', '')}",
                 new_x="LMARGIN", new_y="NEXT")

        pdf.ln(6)


def _gerar_rodape_premium(pdf, paleta: dict, paginas: list):
    """Adiciona página final com mensagem premium."""
    pdf.add_page()
    w, h = 210, 297

    pdf.set_fill_color(*paleta["cor_fundo"])
    pdf.rect(0, 0, w, h, style='F')

    # Centro decorativo — com espaçamento generoso
    pdf.set_font("DejaVu", "B", 16)
    pdf.set_text_color(*paleta["cor_destaque"])
    pdf.cell(0, 60, "", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.cell(0, 14, f"{paleta['icone_titulo']} Seu mapa está completo {paleta['icone_titulo']}",
             new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.set_font("DejaVu", "B", 12)
    pdf.set_text_color(*paleta["cor_texto"])
    pdf.ln(8)
    pdf.multi_cell(0, 7,
        "Este documento foi preparado com carinho e precisão astrológica. "
        "Cada posição planetária, aspecto e casa foi considerada para trazer "
        "a você uma visão profunda e personalizada do seu mapa astral.",
        align="C"
    )

    pdf.ln(12)
    pdf.set_font("DejaVu", "", 11)
    pdf.set_text_color(*paleta["cor_destaque"])
    pdf.multi_cell(0, 6,
        "Lembre-se: você co-cria o seu destino. "
        "Use estas informações como ferramenta de autoconhecimento e empoderamento.",
        align="C"
    )

    pdf.ln(20)
    pdf.set_font("DejaVu", "B", 14)
    pdf.set_text_color(*paleta["cor_destaque"])
    pdf.cell(0, 10, "✦ AstroDicas ✦", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("DejaVu", "", 10)
    pdf.set_text_color(140, 130, 180)
    pdf.cell(0, 6, "astrodicas.inovalabx.com.br",
             new_x="LMARGIN", new_y="NEXT", align="C")


# ── API principal ──────────────────────────────────────────────────────────────

def gerar_mapa_premium(
    nome: str,
    signo: str,
    data_nascimento: date,
    hora_nascimento: str,
    cidade: str,
    tipo: str = "astral",
) -> Optional[str]:
    """Gera o PDF premium e retorna o caminho do arquivo.

    Args:
        nome: nome completo do cliente
        signo: signo solar (string)
        data_nascimento: date de nascimento
        hora_nascimento: string "HH:MM"
        cidade: nome da cidade
        tipo: "astral" | "sinastria" | "carreira" | "revolucao"

    Returns:
        Caminho do PDF gerado ou None em caso de erro.
    """
    try:
        from fpdf import FPDF
        from src.vendas_bot.settings import settings
        from src.vendas_bot.astro_math import (
            posicoes_planetas, calcular_ascendente_casas,
            aspectos_planetas, geocode_cidade, _graus_to_signo,
        )
        from src.vendas_bot.roda_astrologica import salvar_roda

        paleta = PALETAS.get(tipo, PALETAS["astral"])

        # ── 1. Parsear data/hora de nascimento ──────────────────────────────
        h, m = map(int, hora_nascimento.split(":"))
        dt_nasc = datetime(
            data_nascimento.year, data_nascimento.month, data_nascimento.day,
            h, m, 0,
        )
        lat, lon = geocode_cidade(cidade)

        # ── 2. Calcular mapa ───────────────────────────────────────────────
        posicoes = posicoes_planetas(dt_nasc)
        asc_grau, casas, mc_grau = calcular_ascendente_casas(dt_nasc, lat, lon)
        aspectos = aspectos_planetas(posicoes, orbe_max=8)

        ascendente = {"grau": asc_grau, "signo": _graus_to_signo(asc_grau)[0],
                      "grau_signo": _graus_to_signo(asc_grau)[1]}

        assinatura = f"{nome} · {signo} · {data_nascimento.strftime('%d/%m/%Y')} · {cidade}"

        # ── 3. Gerar capa ──────────────────────────────────────────────────
        img_capa = _gerar_capa(
            nome=nome,
            tipo=tipo,
            signo=signo,
            data_nascimento=data_nascimento.strftime("%d/%m/%Y"),
            cidade=cidade,
            paleta=paleta,
        )

        # ── 4. Gerar roda astrológica ─────────────────────────────────────
        os.makedirs("/tmp/mapas_astrais/rodas", exist_ok=True)
        nome_arquivo = nome.lower().replace(" ", "_")
        data_str = data_nascimento.isoformat()
        roda_path = f"/tmp/mapas_astrais/rodas/roda_{nome_arquivo}_{data_str}.png"

        salvar_roda(
            dt_nasc=dt_nasc,
            lat=lat, lon=lon,
            posicoes=posicoes, casas=casas,
            asc_grau=asc_grau, aspectos=aspectos,
            caminho=roda_path, tamanho=1200,
        )

        # ── 5. Gerar conteúdo completo (UMA chamada LLM) ──────────────────
        from urllib import request as urllib_request

        dados_astrologicos = {
            "nome": nome,
            "signo": signo,
            "ascendente": ascendente["signo"],
            "ascendente_grau": f"{ascendente['grau_signo']:.0f}°",
            "cidade": cidade,
            "planetas": {p: f"{sig} {g:.0f}°" for p, (g, sig, gg) in posicoes.items()},
            "aspectos": [f"{a[0]} {a[2]} {a[1]}" for a in aspectos[:8]],
            "tipo": TIPO_NOMES.get(tipo, tipo),
        }

        prompt_conteudo = (
            "Você é um astrólogo profissional brasileiro. "
            "Gere o conteúdo COMPLETO de um Mapa Astral Premium.\n\n"
            f"Dados do cliente:\n{json.dumps(dados_astrologicos, ensure_ascii=False, indent=2)}\n\n"
            "Retorne UM JSON com 10 seções. Cada seção tem:\n"
            '  {"titulo": "...", "subtitulo": "...", "ordem": N, "conteudo": "texto com 300-500 palavras"}\n\n'
            "SEÇÕES (nesta ordem):\n"
            "1. Introdução — visão geral do mapa, energia do momento\n"
            "2. Sol — Sua Essência — o que te move, propósito\n"
            "3. Lua — Suas Emoções — como você sente e reage\n"
            "4. Ascendente — Sua Primeira Impressão — como os outros te veem\n"
            "5. Mercúrio — Sua Comunicação — como pensa e fala\n"
            "6. Vênus — Seu Amor — como ama e se relaciona\n"
            "7. Marte — Sua Energia — como age e luta\n"
            "8. Júpiter e Saturno — sorte, expansão, limites\n"
            "9. Aspectos em Foco — conexões cósmicas mais fortes\n"
            "10. Mensagem Final — encerramento, caminho cósmico\n\n"
            "REGRAS:\n"
            "- Linguagem acolhedora, mística COM conteúdo real\n"
            "- Cada seção: 300-500 palavras (importante: preencher a página!)\n"
            "- Use parágrafos, sem markdown, sem **\n"
            "- Adapte ao signo e posições do cliente\n"
            "- NÃO use caracteres especiais (✦, ★, etc)\n"
            "- Retorne APENAS o JSON, sem ```\n"
            "- Em caso de erro na geração, retorne um texto genérico de fallback para cada seção"
        )

        payload = json.dumps({
            "model": settings.llm_model_text,
            "messages": [
                {"role": "system", "content": "Você é um astrólogo profissional brasileiro."},
                {"role": "user", "content": prompt_conteudo},
            ],
            "temperature": 0.7,
            "max_tokens": 16384,
        }).encode("utf-8")

        req = urllib_request.Request(
            f"{settings.llm_base_url}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {settings.ominiroute_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        secoes = None
        try:
            with urllib_request.urlopen(req, timeout=180) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                content = result["choices"][0]["message"]["content"].strip()
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                secoes = json.loads(content)
                logger.info(f"✅ Conteúdo gerado com {len(secoes)} seções")
        except Exception as e:
            logger.warning(f"Erro na LLM, usando fallback: {e}")
            secoes = None

        if not secoes or not isinstance(secoes, list) or len(secoes) < 8:
            # Fallback completo — textos EXPANDIDOS (300+ palavras cada)
            secoes = _gerar_fallback_completo(
                nome, signo, ascendente, cidade
            )

        # ── 6. Montar PDF ──────────────────────────────────────────────────
        pdf = FPDF()
        pdf.add_font("DejaVu", "", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", uni=True)
        pdf.add_font("DejaVu", "B", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", uni=True)
        pdf.set_auto_page_break(auto=True, margin=25)
        pdf.set_margins(15, 15, 15)

        # Página 1: Capa
        _pdf_page_capa(pdf, img_capa)

        # Página 2: Sumário
        _pdf_page_sumario(pdf, secoes, paleta, nome, tipo)

        # Página 3: Roda astrológica
        _pdf_page_roda(pdf, roda_path, assinatura)

        # Páginas 4+: Seções (usa conteudo do JSON gerado ou fallback)
        paginas_geradas = 0
        for secao in sorted(secoes, key=lambda x: x.get("ordem", 99)):
            conteudo = secao.get("conteudo", "")
            if not conteudo:
                conteudo = f"Seção {secao['titulo']} em preparação."
            _pdf_page_secao(
                pdf, secao["titulo"], secao["subtitulo"],
                conteudo, paleta, paginas_geradas + 4,
            )
            paginas_geradas += 1

        # Página final
        _gerar_rodape_premium(pdf, paleta, [])

        # ── 7. Salvar ─────────────────────────────────────────────────────
        os.makedirs("/tmp/mapas_astrais", exist_ok=True)
        filename = f"/tmp/mapas_astrais/{tipo}_premium_{nome_arquivo}_{data_str}.pdf"
        pdf.output(filename)
        logger.info(f"📄 PDF premium gerado: {filename}")
        return filename

    except ImportError as e:
        logger.warning(f"Dependência faltando: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro ao gerar mapa premium: {e}")
        import traceback
        traceback.print_exc()
        return None


# ── Fallback expandido ─────────────────────────────────────────────────────────

def _gerar_fallback_completo(
    nome: str,
    signo: str,
    ascendente: dict,
    cidade: str,
) -> list[dict]:
    """Gera fallback com textos LONGOS (300+ palavras) para preencher as páginas."""
    return [
        {
            "titulo": "Introdução",
            "subtitulo": "Sua essência cósmica",
            "ordem": 1,
            "conteudo": (
                f"Querida {nome}, seu Mapa Astral é um retrato do céu no momento exato do seu nascimento. "
                f"Ele revela não apenas quem você é, mas também quem você pode se tornar. Cada planeta, "
                f"cada signo e cada casa astrológica contam uma parte da sua história cósmica, uma história "
                f"que começou a ser escrita muito antes de você nascer. Quando o universo se alinhou para "
                f"recebê-lo, cada estrela e cada planeta ocupavam posições únicas que influenciam diretamente "
                f"sua personalidade, seus talentos, seus desafios e seu propósito de vida.\n\n"
                f"Com Sol em {signo}, você carrega a sensibilidade e a intuição características deste signo "
                f"de água. Sua alma é profunda como o oceano e suas emoções fluem com a intensidade das marés. "
                f"Seu ascendente em {ascendente['signo']} {ascendente['grau_signo']:.0f}° adiciona uma camada "
                f"extra de personalidade que molda como você se apresenta ao mundo e como os outros percebem "
                f"sua presença. Esta combinação única faz de você uma pessoa complexa, misteriosa e "
                f"profundamente sensível às energias ao seu redor.\n\n"
                f"Este mapa foi calculado com precisão astronômica para a cidade de {cidade} e reflete o céu "
                f"no momento exato do seu nascimento. Ao longo destas páginas, você encontrará interpretações "
                f"detalhadas de cada aspecto da sua carta natal, desde a posição do Sol até os aspectos mais "
                f"sutis entre os planetas. Cada informação foi preparada com carinho para ajudar você a se "
                f"conhecer melhor e a navegar sua jornada com mais consciência e propósito. Que esta leitura "
                f"seja uma ferramenta de autoconhecimento e transformação na sua vida."
            ),
        },
        {
            "titulo": "Sol — Sua Essência",
            "subtitulo": "O que te move",
            "ordem": 2,
            "conteudo": (
                f"O Sol no mapa astral representa sua essência mais profunda, sua identidade central, aquilo "
                f"que você veio ser neste mundo. É o núcleo da sua personalidade, a faísca divina que ilumina "
                f"seu caminho e define sua expressão mais autêntica. Quando alguém pensa em você, é a energia "
                f"do seu Sol que sente primeiro, mesmo sem saber explicar.\n\n"
                f"Com o Sol em {signo}, sua essência é marcada pela profundidade emocional e pela conexão com "
                f"o mundo interior. Você é guiado pela intuição e possui uma sensibilidade que poucos "
                f"compreendem. Sua força está na capacidade de sentir o que outros não percebem, transformando "
                f"emoção em sabedoria. Você não vive na superfície das coisas — sua alma busca o significado "
                f"oculto em cada experiência, cada relação, cada momento.\n\n"
                f"As pessoas com esta posição solar têm uma memória emocional poderosa e uma capacidade única "
                f"de criar laços profundos. Você protege seu coração com carinho, mas quando confia, se entrega "
                f"com intensidade e lealdade. Seu propósito de vida está ligado à sua capacidade de cuidar, "
                f"de nutrir e de transformar emoções em arte, cura ou sabedoria. O mundo precisa da sua "
                f"sensibilidade e da sua coragem de sentir profundamente."
            ),
        },
        {
            "titulo": "Lua — Suas Emoções",
            "subtitulo": "Como você sente",
            "ordem": 3,
            "conteudo": (
                "A Lua no mapa astral governa suas emoções, seu mundo interior, sua forma de reagir "
                "instintivamente às situações da vida. Ela revela como você busca conforto, segurança e "
                "acolhimento. Enquanto o Sol mostra sua identidade consciente, a Lua revela a alma que "
                "existe por trás da máscara que você mostra ao mundo.\n\n"
                "Sua vida emocional é rica e intensa, com uma necessidade profunda de segurança afetiva. "
                "Você se nutre de momentos de conexão genuína e silêncio contemplativo. Quando algo te "
                "mexe por dentro, você sente como uma onda que toma conta de todo o seu ser. Sua intuição "
                "é aguçada e muitas vezes você sabe como as pessoas estão se sentindo antes mesmo delas "
                "dizerem uma palavra.\n\n"
                "O desafio da Lua no seu mapa é aprender a lidar com a intensidade das próprias emoções "
                "sem se deixar afogar por elas. Você precisa de rituais de autocuidado, de momentos de "
                "solidão criativa e de um ambiente seguro para processar seus sentimentos. A Lua também "
                "revela sua relação com a figura materna e como você cuida dos outros. Sua capacidade de "
                "acolher e nutrir é um dos seus maiores dons, mas lembre-se de que você também precisa "
                "ser cuidada. Criar um lar interior seguro é tão importante quanto ter um lar físico onde "
                "seu coração se sinta em paz."
            ),
        },
        {
            "titulo": "Ascendente — Sua Primeira Impressão",
            "subtitulo": "Como os outros te veem",
            "ordem": 4,
            "conteudo": (
                f"O Ascendente é a máscara que você usa ao encontrar o mundo pela primeira vez. É a primeira "
                f"impressão que as pessoas têm de você, a energia que você projeta antes mesmo de falar. "
                f"Enquanto o Sol é quem você é por dentro, o Ascendente é como você se apresenta. É a pele "
                f"da sua alma, a embalagem do seu espírito, o filtro através do qual o mundo te enxerga.\n\n"
                f"Com ascendente em {ascendente['signo']} {ascendente['grau_signo']:.0f}°, você projeta uma "
                f"imagem que cativa e intriga. As pessoas te percebem como alguém profundo e magnético antes "
                f"mesmo de conhecerem sua verdadeira essência. Há algo em você que chama atenção sem que você "
                f"precise fazer esforço — um brilho natural que atrai olhares e despertas curiosidade.\n\n"
                f"Seu Ascendente também influencia sua aparência física e seu estilo pessoal. É comum que "
                f"pessoas com este ascendente tenham olhos expressivos e uma presença que ocupa o espaço "
                f"sem precisar de palavras. Você tem um jeito único de se movimentar pelo mundo, uma "
                f"assinatura energética que fica gravada na memória de quem te encontra. À medida que você "
                f"amadurece, aprende a integrar melhor a energia do seu Ascendente com a do seu Sol, "
                f"tornando-se cada vez mais autêntica e completa. O Ascendente é o presente que você dá ao "
                f"mundo quando chega — e com o tempo, ele se transforma em quem você está destinada a ser."
            ),
        },
        {
            "titulo": "Mercúrio — Sua Comunicação",
            "subtitulo": "Como você pensa e fala",
            "ordem": 5,
            "conteudo": (
                "Mercúrio rege sua mente, sua comunicação, sua forma de processar informações e de se "
                "expressar. É o planeta que define como você aprende, como ensina, como escreve e como "
                "conversa. Ele mostra o estilo da sua inteligência e como você organiza seus pensamentos "
                "para transformá-los em palavras e ações.\n\n"
                "Sua mente é ágil e intuitiva, captando nuances que passam despercebidas pela maioria das "
                "pessoas. Você se comunica com sensibilidade e prefere conversas que toquem a alma. "
                "Palavras têm poder para você, e sabe usá-las com cuidado e precisão. Sua comunicação não "
                "é superficial — você busca o significado por trás das palavras, o não dito que existe "
                "entre uma frase e outra.\n\n"
                "Você tem talento para escrever, para criar narrativas que envolvem e cativam. Sua mente "
                "funciona como uma esponja, absorvendo informações do ambiente e transformando-as em "
                "insights profundos. Às vezes você pode ser reservada, guardando seus pensamentos mais "
                "íntimos para poucos, mas quando compartilha, suas palavras carregam peso e verdade. "
                "O desafio de Mercúrio no seu mapa é equilibrar a profundidade do seu pensamento com a "
                "clareza da comunicação. Seu dom é traduzir o complexo em simples, o profundo em "
                "acessível, transformando sabedoria em palavras que tocam corações."
            ),
        },
        {
            "titulo": "Vênus — Seu Amor",
            "subtitulo": "Como você ama",
            "ordem": 6,
            "conteudo": (
                "Vênus é o planeta do amor, da beleza, dos afetos e dos valores. Ele revela como você ama, "
                "o que busca em um relacionamento, como expressa carinho e o que considera bonito e "
                "valioso na vida. Vênus também fala sobre sua relação com o dinheiro, com o prazer e com "
                "as coisas que trazem alegria ao seu coração.\n\n"
                "No amor, você busca conexão profunda e significado. Não se contenta com superficialidades "
                "— precisa de alguém que compreenda sua complexidade emocional. Sua lealdade é imensa "
                "quando encontra uma parceria que valoriza a alma tanto quanto o coração. Para você, "
                "amor não é apenas sentimento — é compromisso, é presença, é escolha diária.\n\n"
                "Você valoriza gestos sinceros mais do que grandes declarações. Um olhar que entende, um "
                "silêncio compartilhado, uma mão estendida no momento certo — é isso que faz seu coração "
                "se sentir amado. Sua sensualidade é sutil mas intensa, e você se conecta através da "
                "troca de energias sutis. O desafio de Vênus no seu mapa é não se fechar para o amor "
                "por medo de se machucar. Sua sensibilidade é seu maior presente nos relacionamentos, "
                "desde que você aprenda a usá-la como ponte e não como muro. Ame com coragem, porque "
                "sua capacidade de amar profundamente é um dos seus maiores dons."
            ),
        },
        {
            "titulo": "Marte — Sua Energia",
            "subtitulo": "Como você age",
            "ordem": 7,
            "conteudo": (
                "Marte rege sua energia, sua ação, sua força de vontade e como você luta pelo que quer. "
                "É o planeta que mostra seu estilo de afirmação, sua raiva, sua paixão e sua libido. "
                "Marte é o guerreiro interior que se levanta quando algo precisa ser conquistado ou "
                "defendido. É a chama que acende quando você decide que algo é importante demais para "
                "ser ignorado.\n\n"
                "Sua energia é direcionada por emoções. Você age quando sente, e isso torna suas ações "
                "poderosas e autênticas. Quando algo toca seu coração, você move montanhas. Não é do "
                "tipo que faz as coisas pela metade — quando você se compromete, entrega tudo de si. "
                "Sua força está na intensidade com que você se dedica às causas que abraça.\n\n"
                "O desafio é canalizar essa força sem se deixar levar pela impulsividade. Marte no seu "
                "mapa pede que você aprenda a agir com estratégia, não apenas com emoção. Sua raiva, "
                "quando bem direcionada, pode ser um motor poderoso de transformação — use-a para "
                "quebrar barreiras, não para construir muros. Você tem uma energia sexual magnética e "
                "uma capacidade de sedução que vai além do físico. Seu magnetismo pessoal é forte e "
                "as pessoas sentem sua presença quando você entra em um ambiente. Marte te dá coragem "
                "para seguir seus instintos e lutar pelo que você acredita."
            ),
        },
        {
            "titulo": "Júpiter e Saturno",
            "subtitulo": "Sorte e limitações",
            "ordem": 8,
            "conteudo": (
                "Júpiter e Saturno são os planetas sociais que falam sobre sua expansão e seus limites. "
                "Júpiter é o grande benéfico, o planeta da sorte, da abundância, da expansão e da "
                "sabedoria. Ele mostra onde você encontra crescimento, onde a vida te presenteia com "
                "oportunidades e como você busca significado e propósito. Júpiter é o professor que "
                "abre portas e expande horizontes.\n\n"
                "Júpiter no seu mapa traz expansão através da espiritualidade e do autoconhecimento. "
                "Sua sorte está em confiar na intuição e buscar crescimento interior. Você atrai "
                "oportunidades quando está alinhada com seu propósito mais profundo. A generosidade "
                "é uma das suas marcas — você dá sem esperar receber, e o universo retorna em dobro. "
                "Sua fé na vida, mesmo nos momentos difíceis, é seu maior trunfo.\n\n"
                "Saturno, por outro lado, é o mestre das lições. Ele pede disciplina emocional, "
                "estrutura e responsabilidade. Saturno no seu mapa mostra onde você precisa construir "
                "fundações sólidas, onde a vida vai te testar para te fortalecer. Os desafios de "
                "Saturno não são punições — são treinamentos para sua alma. Cada obstáculo que você "
                "enfrenta desenvolve uma força que nada pode tirar de você.\n\n"
                "O equilíbrio entre Júpiter e Saturno é uma das chaves do seu mapa. Júpiter te convida "
                "a sonhar grande, a expandir seus horizontes, a confiar na abundância do universo. "
                "Saturno te pede para construir bases sólidas para que esses sonhos se sustentem. "
                "Juntos, eles formam a dupla perfeita: a fé que move montanhas e a disciplina que "
                "constrói estradas. Honre os dois e encontrará o equilíbrio entre expansão e estrutura."
            ),
        },
        {
            "titulo": "Aspectos em Foco",
            "subtitulo": "Conexões cósmicas",
            "ordem": 9,
            "conteudo": (
                "Os aspectos são os ângulos que os planetas formam entre si no seu mapa astral. Eles "
                "revelam como as diferentes partes da sua personalidade se relacionam, onde há harmonia "
                "e onde há tensão criativa. Cada aspecto é uma conversa entre dois planetas, uma dança "
                "cósmica que cria padrões únicos na sua personalidade. São as conexões invisíveis que "
                "fazem de você quem você é.\n\n"
                "Os aspectos entre seus planetas revelam dinâmicas importantes. Há tensões criativas que "
                "impulsionam seu crescimento e harmonias que trazem dons naturais. As conjunções "
                "intensificam as energias envolvidas, enquanto os trígonos trazem fluidez e talento "
                "nato. As quadraturas e oposições são os pontos de crescimento — onde a vida te desafia "
                "a evoluir e a encontrar equilíbrio entre forças opostas.\n\n"
                "Os aspectos mais fortes do seu mapa mostram onde sua energia se concentra. São como "
                "holofotes cósmicos iluminando áreas específicas da sua vida que pedem atenção e "
                "desenvolvimento. Um aspecto tenso não é uma maldição — é um convite para crescer. "
                "Um aspecto harmonioso não é uma garantia — é um talento que precisa ser cultivado.\n\n"
                "A chave está em integrar essas energias opostas para encontrar equilíbrio e propósito. "
                "Não se trata de eliminar as tensões, mas de aprender a dançar com elas. Cada aspecto "
                "no seu mapa é uma ferramenta, um recurso que você pode usar para navegar a vida com "
                "mais consciência. Os aspectos mais desafiadores são, frequentemente, seus maiores "
                "presentes — são eles que te empurram para fora da zona de conforto e te fazem crescer."
            ),
        },
        {
            "titulo": "Mensagem Final",
            "subtitulo": "Seu caminho cósmico",
            "ordem": 10,
            "conteudo": (
                f"{nome}, chegamos ao final desta jornada pelo seu Mapa Astral, mas seu caminho de "
                f"autoconhecimento está apenas começando. Este documento é um mapa da sua alma, um guia "
                f"para navegar as águas profundas da sua própria existência. Cada posição planetária, "
                f"cada aspecto e cada casa revelam um pedaço do quebra-cabeça que é você.\n\n"
                f"As estrelas no momento do seu nascimento desenharam um potencial único. Você não é "
                f"apenas o produto dos astros — você é a consciência que os observa, a alma que os "
                f"interpreta e a mão que escreve sua própria história. O mapa astral não é um destino "
                f"fixo; é um mapa de possibilidades. Você pode escolher quais caminhos seguir, quais "
                f"energias cultivar e quais desafios enfrentar.\n\n"
                f"Use este conhecimento como ferramenta de autodescoberta, não como corrente que te "
                f"prende. Você é a autora da sua jornada — os astros apenas iluminam o caminho. "
                f"Confie na sua intuição, honre sua sensibilidade e siga seu chamado interior. "
                f"Você tem dentro de si toda a sabedoria que precisa para viver uma vida plena e "
                f"significativa.\n\n"
                f"A AstroDicas agradece sua confiança e espera que este mapa astral tenha trazido "
                f"clareza, inspiração e um novo olhar sobre quem você é. Lembre-se: o universo está "
                f"sempre conspirando a seu favor. Confie no processo, confie em você e siga iluminando "
                f"o mundo com sua luz única e especial. Que os astros guiem seus passos e que seu "
                f"coração encontre sempre o caminho de volta para casa."
            ),
        },
    ]
