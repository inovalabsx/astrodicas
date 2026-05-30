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
import math
import time
from datetime import date, datetime
from typing import Optional
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

from PIL import Image, ImageDraw, ImageFont
from fpdf import FPDF

from src.vendas_bot.settings import settings

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
    "prosperidade": {
        "cor_principal": (0, 100, 60),        # verde esmeralda
        "cor_secundaria": (0, 70, 40),
        "cor_terciaria": (180, 230, 150),     # verde claro
        "cor_texto": (240, 255, 240),
        "cor_fundo": (5, 25, 15),
        "cor_destaque": (255, 215, 0),        # dourado
        "cor_texto_escuro": (20, 40, 25),
        "cor_card": (10, 40, 25),
        "cor_linha": (60, 160, 100),
        "gradiente_inicio": (0, 80, 50),
        "gradiente_fim": (5, 20, 10),
        "icone_titulo": "◆",                  # diamante
        "cor_tag": (130, 200, 150),
    },
    "sinastria_sem": {
        "cor_principal": (200, 60, 100),
        "cor_secundaria": (160, 40, 80),
        "cor_terciaria": (255, 180, 200),
        "cor_texto": (255, 240, 245),
        "cor_fundo": (30, 10, 20),
        "cor_destaque": (255, 200, 220),
        "cor_texto_escuro": (50, 20, 35),
        "cor_card": (50, 20, 35),
        "cor_linha": (180, 80, 120),
        "gradiente_inicio": (180, 40, 80),
        "gradiente_fim": (30, 10, 20),
        "icone_titulo": "♥",
        "cor_tag": (220, 140, 160),
    },
}

TIPO_NOMES = {
    "astral": "Mapa Astral Completo",
    "sinastria": "Sinastria Amorosa",
    "sinastria_sem": "Guia Amoroso Pessoal",
    "carreira": "Mapa da Carreira",
    "prosperidade": "Mapa da Prosperidade",
}

# ── Símbolos planetários (para exibir nas seções de interpretação) ──────────────

PLANETAS_SIMBOLOS = {
    "Sol": "☉",
    "Lua": "☽",
    "Mercúrio": "☿",
    "Venus": "♀",
    "Vênus": "♀",
    "Marte": "♂",
    "Jupiter": "♃",
    "Júpiter": "♃",
    "Saturno": "♄",
    "Urano": "♅",
    "Netuno": "♆",
    "Plutão": "♇",
}


def _gerar_secoes_llm(
    nome: str,
    signo: str,
    ascendente: dict,
    cidade: str,
    tipo: str,
) -> Optional[list[dict]]:
    """Gera seções estruturadas via LLM em markdown e parseia localmente."""
    if not settings.ominiroute_api_key:
        logger.warning("OMINIROUTE_API_KEY ausente — usando fallback")
        return None

    asc_txt = f"{ascendente.get('signo', 'Desconhecido')} {float(ascendente.get('grau_signo', 0)):.0f}°"
    tipo_nome = TIPO_NOMES.get(tipo, "Mapa Astral Completo")
    qtd_secoes = 14 if tipo != "astral" else 15

    instrucoes = (
        "Você é astrólogo profissional brasileiro e redator premium. "
        "Responda APENAS em markdown estruturado, sem JSON, sem explicações extras. "
        "Formato obrigatório por seção:\n"
        "## <título da seção>\n"
        "### <subtítulo curto>\n"
        "<conteúdo da seção em 4-7 parágrafos, com boa densidade e exemplos práticos>\n\n"
        f"Gere exatamente {qtd_secoes} seções. "
        "Cada seção deve ter conteúdo consistente, específico e útil, em português-BR natural. "
        "Em TODAS as seções, mencionar explicitamente e de forma natural o signo solar e/ou ascendente da pessoa, "
        "conectando a interpretação ao perfil dela. "
        "Não repetir frases entre seções."
    )

    pedido = (
        f"Tipo: {tipo_nome} ({tipo})\n"
        f"Nome: {nome}\n"
        f"Signo solar: {signo}\n"
        f"Ascendente: {asc_txt}\n"
        f"Cidade: {cidade}\n"
        f"Quantidade de seções: {qtd_secoes}\n"
    )

    payload = json.dumps({
        "model": settings.llm_model_text,
        "messages": [
            {"role": "system", "content": instrucoes},
            {"role": "user", "content": pedido},
        ],
        "temperature": 0.8,
        "max_tokens": 7000,
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

    def _parse_markdown_secoes(md: str) -> list[dict]:
        txt = (md or "").replace("\r\n", "\n").strip()
        if not txt:
            return []

        linhas = txt.split("\n")
        secoes = []
        atual = None

        def _finalizar(sec):
            if not sec:
                return
            conteudo = "\n".join([l for l in sec["conteudo"] if l.strip()]).strip()
            if sec["titulo"].strip() and conteudo:
                secoes.append({
                    "titulo": sec["titulo"].strip(),
                    "subtitulo": sec["subtitulo"].strip(),
                    "ordem": len(secoes) + 1,
                    "conteudo": conteudo,
                })

        for linha in linhas:
            l = linha.strip()
            if l.startswith("## "):
                _finalizar(atual)
                atual = {"titulo": l[3:].strip(), "subtitulo": "", "conteudo": []}
                continue
            if atual is None:
                continue
            if l.startswith("### ") and not atual["subtitulo"]:
                atual["subtitulo"] = l[4:].strip()
                continue
            atual["conteudo"].append(linha)

        _finalizar(atual)
        return secoes

    max_tentativas = 3
    backoff_segundos = 2

    for tentativa in range(1, max_tentativas + 1):
        try:
            with urllib_request.urlopen(req, timeout=180) as resp:
                raw_txt = resp.read().decode("utf-8", "ignore")

                # Alguns gateways podem responder em SSE (data: ...), mesmo sem stream explícito.
                # Nesse caso, remontamos o texto a partir dos chunks delta.content.
                if raw_txt.lstrip().startswith("data:"):
                    partes = []
                    for linha in raw_txt.splitlines():
                        l = linha.strip()
                        if not l.startswith("data:"):
                            continue
                        payload_linha = l[5:].strip()
                        if not payload_linha or payload_linha == "[DONE]":
                            continue
                        try:
                            chunk = json.loads(payload_linha)
                        except Exception:
                            continue
                        delta = (((chunk.get("choices") or [{}])[0]).get("delta") or {})
                        pedaco = delta.get("content")
                        if pedaco:
                            partes.append(str(pedaco))
                    content = "".join(partes)
                else:
                    result = json.loads(raw_txt)
                    content = result["choices"][0]["message"].get("content", "")

                normalizadas = _parse_markdown_secoes(str(content))

                if len(normalizadas) < 10:
                    raise ValueError(f"LLM retornou poucas seções parseáveis ({len(normalizadas)})")

                logger.info(f"LLM premium markdown ok na tentativa {tentativa}/{max_tentativas}")
                return normalizadas

        except (HTTPError, URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError) as e:
            logger.warning(
                f"Erro LLM tentativa {tentativa}/{max_tentativas} (mapa premium): {e}"
            )
            if tentativa < max_tentativas:
                time.sleep(backoff_segundos * tentativa)
                continue
            return None
        except Exception as e:
            logger.warning(
                f"Erro inesperado LLM tentativa {tentativa}/{max_tentativas} (mapa premium): {e}"
            )
            if tentativa < max_tentativas:
                time.sleep(backoff_segundos * tentativa)
                continue
            return None

    return None



class FPDFPremium(FPDF):
    """Extensão do FPDF com footer automático no final de cada página."""

    def __init__(self, paleta: dict):
        super().__init__()
        self._paleta = paleta
        self._footer_h = 16

    def footer(self):
        """Desenha o footer automaticamente em todas as páginas."""
        # Só desenha se a página tiver um fundo escuro completo
        # (evita desenhar na capa, roda, etc.)
        if self.page_no() <= 1:
            return

        self.set_y(-self._footer_h - 3)
        cor_card = self._paleta.get("cor_card", (35, 25, 60))
        cor_texto = self._paleta.get("cor_tag", (140, 130, 180))

        self.set_fill_color(*cor_card)
        self.rect(0, self.get_y(), self.w, self._footer_h, style='F')

        self.set_font("DejaVu", "", 8)
        self.set_text_color(*cor_texto)
        self.cell(0, 8, f"AstroDicas — astrodicas.inovalabx.com.br  |  Pág {self.page_no()}",
                  new_x="LMARGIN", new_y="NEXT", align="C")


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
    """Gera imagem de capa decorada com elementos visuais por tipo de mapa."""
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

    cx, cy = w // 2, h // 2 - 80

    # ── Elementos visuais por tipo ──────────────────────────────────────────
    if tipo == "sinastria":
        # Anéis entrelaçados (dois círculos sobrepostos)
        for r in range(220, 60, -15):
            t_circulo = (r - 60) / 160
            cor = interp_color(paleta["cor_destaque"], paleta["cor_secundaria"], t_circulo)
            # Círculo esquerdo
            draw.ellipse([cx - r - 30, cy - r, cx - r + 30 + r*2, cy + r],
                         outline=cor, width=2)
            # Círculo direito
            draw.ellipse([cx + r - r - 30, cy - r, cx + r + 30, cy + r],
                         outline=cor, width=2)

        # Pequenos corações decorativos no entorno
        for ang in range(0, 360, 45):
            rad = math.radians(ang - 90)
            rx = cx + 320 * math.cos(rad)
            ry = cy + 320 * math.sin(rad)
            draw.text((rx - 10, ry - 10), "♥",
                      fill=paleta["cor_terciaria"],
                      font=ImageFont.truetype(font_reg, 24) if font_reg else ImageFont.load_default())

    elif tipo == "carreira":
        # Elementos SOMENTE nas bordas — centro livre pro texto
        # 1. Linhas ascendentes nas laterais (esquerda e direita)
        for side in [-1, 1]:
            for i in range(20):
                y_pos = int(cy - 300 + i * 30)
                x_start = cx + side * (int(w * 0.35) - i * 8)
                x_end = cx + side * (int(w * 0.42) - i * 4)
                t_lin = i / 20
                cor = interp_color(paleta["cor_destaque"], paleta["cor_linha"], t_lin)
                draw.line([(x_start, y_pos), (x_end, y_pos)], fill=cor, width=1)

        # 2. Arcos geométricos nos cantos superiores
        for side in [-1, 1]:
            cx_canto = cx + side * int(w * 0.42)
            cy_canto = cy - 250
            for r in range(30, 120, 10):
                t_arco = (r - 30) / 90
                cor = interp_color(paleta["cor_destaque"], paleta["cor_fundo"], t_arco)
                # Desenha arco de 0 a 180 (lado esquerdo vira direito)
                for ang in range(0, 91, 5):
                    rad = math.radians(ang)
                    px = cx_canto + side * int(r * math.cos(rad))
                    py = cy_canto + int(r * math.sin(rad))
                    draw.ellipse([px-1, py-1, px+1, py+1], fill=cor, outline=None)

        # 3. Pequenas partículas diagonais (sem tocar o centro)
        for i in range(50):
            ang = math.radians(i * 73)
            raio = int(400 + 100 * math.sin(i * 0.5))
            if raio < 200:
                continue
            px = cx + int(raio * math.cos(ang))
            py = cy + 80 + int(raio * math.sin(ang))
            # Skip if within text zone
            if abs(px - cx) < 250 and abs(py - cy - 80) < 300:
                continue
            t_p = abs(i - 25) / 25
            cor = interp_color(paleta["cor_destaque"], paleta["cor_secundaria"], t_p)
            raio_p = max(1, int(3 - t_p * 2))
            draw.ellipse([px - raio_p, py - raio_p, px + raio_p, py + raio_p],
                         fill=cor, outline=None)

        # 4. Seta sutil no canto inferior apontando pra cima
        y_seta = cy + 350
        for side in [-1, 1]:
            x_base = cx + side * 300
            pontos_seta = [
                (x_base, y_seta - 30),
                (x_base - 15, y_seta),
                (x_base - 6, y_seta),
                (x_base - 6, y_seta + 20),
                (x_base + 6, y_seta + 20),
                (x_base + 6, y_seta),
                (x_base + 15, y_seta),
            ]
            draw.polygon(pontos_seta, fill=paleta["cor_linha"], outline=None)

    elif tipo == "prosperidade":
        # Diamante central (losango facetado)
        diamante_y = cy - 60
        # Facetas do diamante
        faces_diamante = [
            [(cx, diamante_y - 100), (cx - 60, diamante_y - 20), (cx, diamante_y + 40)],
            [(cx, diamante_y - 100), (cx + 60, diamante_y - 20), (cx, diamante_y + 40)],
            [(cx, diamante_y - 100), (cx - 60, diamante_y - 20), (cx, diamante_y - 20)],
            [(cx, diamante_y - 100), (cx + 60, diamante_y - 20), (cx, diamante_y - 20)],
            [(cx - 60, diamante_y - 20), (cx, diamante_y + 40), (cx, diamante_y - 20)],
            [(cx + 60, diamante_y - 20), (cx, diamante_y + 40), (cx, diamante_y - 20)],
        ]
        for idx, face in enumerate(faces_diamante):
            t_face = idx / len(faces_diamante)
            cor = interp_color(paleta["cor_destaque"], paleta["cor_secundaria"], t_face * 0.7)
            draw.polygon(face, fill=cor, outline=paleta["cor_terciaria"], width=1)

        # Brilho em volta do diamante (halo radial)
        for r in range(160, 60, -10):
            t_brilho = (r - 60) / 100
            cor = (255, 215, 0, int(40 * t_brilho))
            cor_rgb = (min(255, int(paleta["cor_destaque"][0] * t_brilho + paleta["cor_fundo"][0] * (1-t_brilho))),
                       min(255, int(paleta["cor_destaque"][1] * t_brilho + paleta["cor_fundo"][1] * (1-t_brilho))),
                       min(255, int(paleta["cor_destaque"][2] * t_brilho + paleta["cor_fundo"][2] * (1-t_brilho))))
            draw.ellipse([cx - r, diamante_y - r, cx + r, diamante_y + r],
                         outline=cor_rgb, width=1)

        # Moedas/partículas de ouro em volta
        for i in range(24):
            ang = i * 15
            rad = math.radians(ang - 90)
            rx = cx + 280 * math.cos(rad)
            ry = diamante_y + 60 + 220 * math.sin(rad)
            t_moeda = (i % 8) / 8
            cor_m = interp_color(paleta["cor_destaque"], paleta["cor_principal"], t_moeda)
            raio_m = 8 if i % 3 == 0 else 5
            draw.ellipse([rx - raio_m, ry - raio_m, rx + raio_m, ry + raio_m],
                         fill=cor_m, outline=paleta["cor_terciaria"], width=1)

        # Linhas de energia ascendentes
        for i in range(60, 0, -1):
            ang = i * 6.28 / 60
            px = cx + int(100 * math.cos(ang * 3) * (i / 60))
            py = diamante_y + 200 - i * 5
            t_en = i / 60
            cor_en = interp_color(paleta["cor_destaque"], paleta["cor_fundo"], t_en)
            draw.ellipse([px - 2, py - 2, px + 2, py + 2], fill=cor_en, outline=None)

    else:  # astral (padrão)
        # Círculo decorativo central (já existente)
        for r in range(300, 100, -20):
            t_circulo = (r - 100) / 200
            cor = interp_color(paleta["cor_principal"], paleta["cor_secundaria"], t_circulo)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=cor, width=2)

        # Estrelas decorativas (✦) em volta
        for ang in range(0, 360, 30):
            rad = math.radians(ang - 90)
            rx = cx + 340 * math.cos(rad)
            ry = cy + 340 * math.sin(rad)
            t_estrela = (ang % 360) / 360
            cor_estrela = interp_color(paleta["cor_tag"], paleta["cor_secundaria"], t_estrela)
            font_estrela = ImageFont.truetype(font_reg, 20) if font_reg else ImageFont.load_default()
            draw.text((rx - 8, ry - 8), "✦",
                      fill=cor_estrela, font=font_estrela)

    # ── Elementos comuns a todos os tipos ──────────────────────────────────
    simbolos = {
        "Áries": "♈", "Touro": "♉", "Gêmeos": "♊", "Câncer": "♋",
        "Leão": "♌", "Virgem": "♍", "Libra": "♎", "Escorpião": "♏",
        "Sagitário": "♐", "Capricórnio": "♑", "Aquário": "♒", "Peixes": "♓",
    }
    simb = simbolos.get(signo, "✦")
    titulo = TIPO_NOMES.get(tipo, tipo)

    try:
        font_titulo = ImageFont.truetype(font_bold, 48) if font_bold else ImageFont.load_default()
        font_nome = ImageFont.truetype(font_bold, 36) if font_bold else ImageFont.load_default()
        font_info = ImageFont.truetype(font_reg, 22) if font_reg else ImageFont.load_default()
        font_simbolo = ImageFont.truetype(font_reg, 140) if font_reg else ImageFont.load_default()
    except Exception:
        font_titulo = font_nome = font_info = font_simbolo = ImageFont.load_default()

    # Símbolo grande central
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

    # Info extra abaixo
    extra_info = f"{data_nascimento}  ·  {signo}  ·  {cidade}"
    bbox = draw.textbbox((0, 0), extra_info, font=font_info)
    ew = bbox[2] - bbox[0]
    draw.text(((w - ew) // 2, cy + 250), extra_info,
              fill=paleta["cor_terciaria"], font=font_info)

    # Marca d'água sutil
    marca = "AstroDicas"
    bbox = draw.textbbox((0, 0), marca, font=font_info)
    mw = bbox[2] - bbox[0]
    draw.text(((w - mw) // 2, h - 80), marca,
              fill=paleta["cor_tag"], font=font_info)

    return img


# ── Funções de página do PDF ───────────────────────────────────────────────────

def _pdf_page_capa(pdf: FPDFPremium, img_capa: Image.Image):
    """Adiciona a capa como primeira página — ocupa a A4 inteira."""
    pdf.add_page()
    w, h = 210, 297
    pdf.set_fill_color(*pdf._paleta["cor_fundo"])
    pdf.rect(0, 0, w, h, style='F')

    # Converter PIL p/ temp file e inserir — OCUPA A PÁGINA INTEIRA
    capa_path = "/tmp/_capa_temp.png"
    img_capa.save(capa_path, "PNG")
    pdf.image(capa_path, x=0, y=0, w=w, h=h)


def _pdf_page_sumario(pdf: FPDFPremium, secoes: list, paleta: dict, nome: str, tipo: str):
    """Adiciona página de sumário (índice) com contraste melhorado."""
    pdf.add_page()
    w, h = 210, 297

    # Ajuste fino por tipo: sinastria pode respirar mais; demais ficam compactos
    if tipo == "sinastria":
        header_h = 46
        titulo_size = 19
        subtitulo_size = 10
        card_h = 13
        item_titulo_size = 10
        item_sub_size = 8
        ln_item = 3
        y_title = 8
        y_sub = 7
        y_after_header = 6
    else:
        header_h = 42
        titulo_size = 18
        subtitulo_size = 9
        card_h = 12
        item_titulo_size = 9
        item_sub_size = 7
        ln_item = 2
        y_title = 7
        y_sub = 6
        y_after_header = 5

    pdf.set_fill_color(*paleta["cor_principal"])
    pdf.rect(0, 0, w, header_h, style='F')

    pdf.set_font("DejaVu", "B", titulo_size)
    pdf.set_text_color(*paleta["cor_texto"])
    pdf.set_xy(15, y_title)
    pdf.cell(0, 10, f"{paleta['icone_titulo']} Índice do seu Mapa", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("DejaVu", "", subtitulo_size)
    pdf.set_text_color(*paleta["cor_destaque"])
    pdf.cell(0, 5, f"{TIPO_NOMES.get(tipo, tipo)} — {nome}",
             new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(header_h + y_after_header)

    # ── Lista de seções (FUNDO ESCURO + TEXTO CLARO) ─────────────────
    for idx, s in enumerate(sorted(secoes, key=lambda x, fallback=999: x.get("ordem", fallback))):
        pdf.set_x(18)

        # Card com compactação adaptativa por tipo
        pdf.set_fill_color(*paleta["cor_card"])
        pdf.set_draw_color(*paleta["cor_linha"])
        y_card = pdf.get_y()
        pdf.rect(16, y_card, w - 32, card_h, style='DF')  # DF = fill + draw

        # Título
        pdf.set_font("DejaVu", "B", item_titulo_size)
        pdf.set_text_color(*paleta["cor_texto"])
        pdf.set_xy(20, y_card + 0.5)
        pdf.cell(0, 6, f"{s.get('ordem', idx+1):02d}.  {s['titulo']}",
                 new_x="LMARGIN", new_y="NEXT")

        # Subtítulo
        pdf.set_font("DejaVu", "", item_sub_size)
        pdf.set_text_color(*paleta["cor_tag"])
        pdf.set_xy(26, y_card + y_sub)
        pdf.cell(0, 5, f"{s.get('subtitulo', '')}",
                 new_x="LMARGIN", new_y="NEXT")

        pdf.ln(ln_item)


def _pdf_page_roda(pdf: FPDFPremium, roda_path: str, assinatura: str):
    """Adiciona página com a roda astrológica centralizada."""
    pdf.add_page()
    w, h = 210, 297

    # Fundo escuro completo
    pdf.set_fill_color(*pdf._paleta["cor_fundo"])
    pdf.rect(0, 0, w, h, style='F')

    # Inserir roda centralizada — MAIOR (185mm)
    img_size = 185
    x_offset = (w - img_size) / 2
    pdf.image(roda_path, x=x_offset, y=15, w=img_size, h=img_size)

    # Assinatura abaixo
    pdf.set_y(215)
    pdf.set_font("DejaVu", "", 16)
    pdf.set_text_color(*pdf._paleta["cor_destaque"])
    pdf.cell(0, 12, assinatura, new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.set_font("DejaVu", "", 10)
    pdf.set_text_color(*pdf._paleta["cor_texto"])
    pdf.cell(0, 8, "Céu do momento do seu nascimento",
             new_x="LMARGIN", new_y="NEXT", align="C")


def _pdf_page_secao(
    pdf: FPDFPremium,
    titulo: str,
    subtitulo: str,
    conteudo: str,
    paleta: dict,
    num_pagina: int,
):
    """Adiciona página de conteúdo de seção com layout melhorado.

    - Header com fundo escuro e texto claro
    - Conteúdo com fonte 11 e line-height 7
    - O footer é desenhado AUTOMATICAMENTE pelo método footer() da classe FPDFPremium
    - Texto em tom legível: 200, 195, 220
    - Se conteúdo curto, distribui espaçamento extra entre parágrafos
    """
    pdf.add_page()
    w, h = 210, 297
    margem_esq = 18
    margem_dir = 18
    largura_texto = w - margem_esq - margem_dir

    # ── Header com símbolo planetário ────────────────────────────────────────
    header_h = 35
    pdf.set_fill_color(*paleta["cor_principal"])
    pdf.rect(0, 0, w, header_h, style='F')

    # Extrair símbolo planetário do título
    simb_planeta = ""
    for nome_planeta, simb in PLANETAS_SIMBOLOS.items():
        if titulo.startswith(nome_planeta):
            simb_planeta = simb + " "
            break

    pdf.set_font("DejaVu", "B", 20)
    pdf.set_text_color(*paleta["cor_texto"])
    pdf.set_xy(15, 10)
    pdf.cell(0, 12, f"{paleta['icone_titulo']} {simb_planeta}{titulo}",
             new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("DejaVu", "", 11)
    pdf.set_text_color(*paleta["cor_destaque"])
    pdf.cell(0, 5, subtitulo, new_x="LMARGIN", new_y="NEXT")

    # ── Conteúdo ──────────────────────────────────────────────────────────
    pdf.ln(12)

    pdf.set_font("DejaVu", "", 13)
    pdf.set_text_color(120, 115, 150)

    # Substituir nomes de planetas por símbolo + nome no corpo
    for nome_planeta, simb in PLANETAS_SIMBOLOS.items():
        # Só substitui palavras inteiras (com boundaries)
        conteudo = conteudo.replace(f" {nome_planeta} ", f" {simb}{nome_planeta} ")

    # Processar parágrafos
    paragrafos = conteudo.split("\n")
    paragrafos = [p.strip() for p in paragrafos if p.strip()]

    # Espaço útil pro conteúdo (header → espaço antes do footer automático)
    footer_reserve = 25
    espaco_util = h - header_h - footer_reserve - pdf.get_y() + header_h

    # Estimar linhas
    chars_por_linha = 65
    linhas = sum(max(1, len(p) // chars_por_linha + 1) for p in paragrafos)
    linhas += len(paragrafos) - 1  # espaços entre parágrafos

    lh = 8
    altura_estimada = linhas * lh

    # Distribuir espaço extra entre parágrafos se conteúdo for muito curto
    espaco_extra_par = 0
    qtd_pars = len(paragrafos)
    if altura_estimada < espaco_util * 0.55 and qtd_pars > 1:
        deficit = (espaco_util * 0.8) - altura_estimada
        espaco_extra_par = int(deficit // qtd_pars)
        espaco_extra_par = max(2, min(espaco_extra_par, 25))

    for i, par in enumerate(paragrafos):
        pdf.set_x(margem_esq)
        pdf.multi_cell(largura_texto, lh, par)
        if i < len(paragrafos) - 1:
            pdf.ln(3 + espaco_extra_par)
def _gerar_rodape_premium(pdf: FPDFPremium, paleta: dict, paginas: list):
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
    """Gera PDF premium completo.

    Fluxo:
    1. Gera roda astrológica (roda_astrologica)
    2. Gera capa decorada (Pillow)
    3. Calcula ascendente + posições (astro_math)
    4. Monta seções (LLM ou fallback)
    5. Gera PDF (fpdf2) com capa → sumário → roda → seções → rodapé
    6. Salva em /tmp/mapas_astrais/
    """
    try:
        from fpdf import FPDF

        # ── 1. Roda astrológica ──────────────────────────────────────────
        paleta = PALETAS.get(tipo, PALETAS["astral"])
        roda_path = "/tmp/roda_astrologica.png"
        assinatura = f"{nome.upper()} — {data_nascimento.strftime('%d/%m/%Y')}"
        try:
            from .roda_astrologica import salvar_roda
            from .astro_math import geocode_cidade
            dt_nasc = datetime.combine(data_nascimento, datetime.strptime(hora_nascimento, "%H:%M").time())
            lat, lon = geocode_cidade(cidade)
            bg_hex = '#%02x%02x%02x' % paleta.get("cor_fundo", (18, 12, 35))
            salvar_roda(dt_nasc, lat, lon, roda_path, bg_color=bg_hex)
        except Exception as e:
            logger.warning(f"Roda não gerada, seguindo com placeholder: {e}")
            _criar_roda_placeholder(roda_path, nome, tipo, signo)

        # ── 2. Capa ───────────────────────────────────────────────────────
        data_str = data_nascimento.strftime("%Y-%m-%d")
        nome_arquivo = nome.lower().replace(" ", "_")
        img_capa = _gerar_capa(
            nome, tipo, signo,
            data_nascimento.strftime("%d/%m/%Y"), cidade, paleta,
        )

        # ── 3. Calcular ascendente ────────────────────────────────────────
        ascendente = {"signo": "Peixes", "grau_signo": 15.0}
        try:
            from .astro_math import calcular_ascendente_casas, geocode_cidade, _graus_to_signo
            dt_nasc = datetime.combine(data_nascimento, datetime.strptime(hora_nascimento, "%H:%M").time())
            lat, lon = geocode_cidade(cidade)
            asc_grau, _cuspides, _mc = calcular_ascendente_casas(dt_nasc, lat, lon)
            asc_signo, asc_grau_no_signo = _graus_to_signo(asc_grau)
            ascendente = {"signo": asc_signo, "grau_signo": asc_grau_no_signo}
        except Exception as e:
            logger.warning(f"Astro math indisponível: {e}")

        # ── 4. Gerar seções ───────────────────────────────────────────────
        secoes = _gerar_secoes_llm(nome, signo, ascendente, cidade, tipo)

        if not secoes or not isinstance(secoes, list) or len(secoes) < 8:
            # Fallback completo quando LLM falha
            secoes = _gerar_fallback_completo(
                nome, signo, ascendente, cidade, tipo
            )

        # ── 5. Montar PDF com FPDFPremium ─────────────────────────────────
        pdf = FPDFPremium(paleta)
        pdf.add_font("DejaVu", "", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", uni=True)
        pdf.add_font("DejaVu", "B", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", uni=True)
        pdf.set_auto_page_break(auto=True, margin=30)
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

        # ── 6. Salvar ─────────────────────────────────────────────────────
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
    tipo: str = "astral",
) -> list[dict]:
    """Fallback robusto com conteúdo longo e temático (14-16 seções)."""

    asc_txt = f"{ascendente.get('signo', 'Desconhecido')} {float(ascendente.get('grau_signo', 0)):.0f}°"

    def sec(titulo: str, subtitulo: str, ordem: int, *paragrafos: str) -> dict:
        return {
            "titulo": titulo,
            "subtitulo": subtitulo,
            "ordem": ordem,
            "conteudo": "\n\n".join(paragrafos),
        }

    if tipo == "sinastria":
        return [
            sec("Introdução à Sinastria", "A dança de duas almas", 1,
                f"{nome}, a sinastria mostra como dois mapas natais se encontram no amor. Em vez de olhar apenas quem você é sozinha, ela revela como sua energia conversa com a energia de outra pessoa: onde há fluidez, onde há tensão e onde existe potencial real de construção.",
                f"Seu Sol em {signo} e seu ascendente em {asc_txt} indicam busca por vínculos profundos, lealdade e presença emocional. Você não se satisfaz com conexões rasas: precisa de sentido, troca verdadeira e maturidade afetiva.",
                "Neste guia, o foco é usar a astrologia como ferramenta prática: entender padrão de atração, comunicação, intimidade, conflitos e propósito da relação. Amor saudável não é ausência de desafio; é capacidade de crescer junto."
            ),
            sec("Vênus em Compatibilidade", "Estilo de amar", 2,
                "Vênus mostra linguagem afetiva: como cada pessoa demonstra carinho, o que considera romântico e quais sinais a fazem se sentir amada. Quando Vênus de ambos conversa bem, o afeto flui naturalmente.",
                "Quando há tensão venusiana, a relação pode ter amor, mas com desencontro de expectativa. O segredo é tradução emocional consciente.",
                "Compatibilidade não exige igualdade total, e sim disposição para aprender o idioma amoroso do outro sem abandonar o próprio."
            ),
            sec("Lua em Compatibilidade", "Segurança emocional", 3,
                "A Lua é a base íntima da relação: acolhimento, vulnerabilidade e necessidades emocionais profundas.",
                "Quando as Luas entram em atrito, surgem mal-entendidos sobre cuidado e proteção.",
                "Entender a Lua um do outro reduz ruído, aumenta empatia e fortalece o vínculo a longo prazo."
            ),
            sec("Marte e Química", "Desejo, impulso e erotismo", 4,
                "Marte descreve atração física e forma de agir no conflito. Em sinastria, ele acende paixão e iniciativa.",
                "Aspectos intensos podem gerar química poderosa e também disputas de ego.",
                "Canalizado com respeito, Marte vira combustível para construção."
            ),
            sec("Mercúrio e Diálogo", "Como vocês se entendem", 5,
                "Mercúrio mostra como o casal conversa, negocia e resolve problemas.",
                "Tensão mercurial pede escuta ativa e linguagem menos defensiva.",
                "Sem diálogo maduro, pequenos temas viram grandes feridas."
            ),
            sec("Júpiter no Casal", "Expansão e bênçãos", 6,
                "Júpiter representa crescimento conjunto: estudos, viagens, fé e visão de futuro.",
                "Boa sinastria jupiteriana traz sensação de sorte a dois e expansão prática.",
                "Atenção ao excesso de promessas sem base concreta."
            ),
            sec("Saturno no Casal", "Compromisso e maturidade", 7,
                "Saturno testa constância, limites e responsabilidade afetiva.",
                "Pode indicar laço sério de longo prazo, desde que exista leveza emocional.",
                "A lição é equilibrar dever e afeto."
            ),
            sec("Netuno no Amor", "Encanto e ilusão", 8,
                "Netuno traz magia e conexão espiritual.",
                "Também pode gerar idealização e frustração tardia.",
                "Poesia com realidade: coração aberto e pés no chão."
            ),
            sec("Plutão e Transformação", "Intensidade do vínculo", 9,
                "Plutão aprofunda desejo, apego, medo e renascimento.",
                "Com maturidade, vira força de cura e regeneração do casal.",
                "Esse vínculo pede verdade e coragem para transformar padrões antigos."
            ),
            sec("Casas Ativadas", "Áreas da vida em destaque", 10,
                "Planetas do parceiro nas suas casas mostram onde ele te impacta mais: romance, rotina, carreira, sexualidade, propósito.",
                "Casa 5 ativa paixão; Casa 7 parceria; Casa 8 intimidade; Casa 10 metas e imagem pública.",
                "Mapear casas ativadas facilita acordos práticos no relacionamento."
            ),
            sec("Pontos de Atrito", "Diferença como evolução", 11,
                "Aspectos tensos não são sentença de fracasso — são pontos de evolução.",
                "Sem consciência, viram repetição de briga; com consciência, viram maturidade.",
                "A pergunta-chave: como resolver juntos sem se destruir?"
            ),
            sec("Padrões Kármicos", "O que se repete no amor", 12,
                "Algumas relações ativam feridas antigas e padrões familiares.",
                "Identificar gatilhos ajuda a sair do automático emocional.",
                "Relacionamento consciente é evolução com responsabilidade afetiva."
            ),
            sec("Potencial de Construção", "Projeto de vida a dois", 13,
                "Compatibilidade real inclui sonho e rotina: finanças, família, liberdade, intimidade e metas.",
                "Casais fortes alinham valores antes de alinhar estética.",
                "Com propósito e respeito, o amor vira obra."
            ),
            sec("Mensagem Final", "Amor com consciência", 14,
                f"{nome}, sua sinastria mostra potenciais — não sentença. O rumo depende de escolhas diárias.",
                "Use este mapa para fortalecer diálogo, ajustar expectativa e construir vínculo mais verdadeiro.",
                "Amor maduro é parceria viva entre duas pessoas dispostas a crescer."
            ),
        ]

    if tipo == "sinastria_sem":
        return [
            sec("Guia Amoroso Pessoal", "Seu mapa sem parceiro", 1,
                f"{nome}, este guia foi feito para seu autoconhecimento amoroso sem depender do mapa de outra pessoa.",
                f"Com Sol em {signo} e ascendente em {asc_txt}, você busca intensidade emocional e verdade afetiva.",
                "Entender seu padrão afetivo melhora suas escolhas e reduz repetição de sofrimento."
            ),
            sec("Seu Estilo de Amar", "Vênus pessoal", 2,
                "Você valoriza reciprocidade, presença e profundidade.",
                "Relações mornas drenam sua energia e senso de valor.",
                "Entrega com limites é a base do amor saudável para você."
            ),
            sec("Necessidades Emocionais", "Lua pessoal", 3,
                "Você precisa de segurança emocional e clareza para florescer no amor.",
                "Ambiguidade constante ativa ansiedade afetiva.",
                "Nomear necessidade cedo evita frustração acumulada."
            ),
            sec("Desejo e Magnetismo", "Marte pessoal", 4,
                "Sua atração é intensa, com presença marcante.",
                "Química importa, mas sem valor comum não sustenta.",
                "Equilíbrio entre paixão e discernimento protege seu coração."
            ),
            sec("Comunicação no Amor", "Mercúrio pessoal", 5,
                "Você se conecta por conversas honestas e profundas.",
                "Silêncios defensivos podem virar distância desnecessária.",
                "Falar com clareza fortalece vínculo e evita ruído."
            ),
            sec("Padrões de Repetição", "O que observar", 6,
                "Há tendência de insistir em vínculos intensos sem reciprocidade concreta.",
                "Consciência desse padrão é ponto de virada.",
                "Tempo e observação prática filtram melhor quem merece sua entrega."
            ),
            sec("Parceiro Compatível", "Perfil que soma", 7,
                "Você combina com pessoas emocionalmente disponíveis e coerentes entre fala e ação.",
                "Atração sem responsabilidade afetiva vira desgaste.",
                "Compatibilidade real mistura química, valor e projeto de vida."
            ),
            sec("Limites Saudáveis", "Amor sem autoabandono", 8,
                "Limite não afasta amor verdadeiro; afasta confusão.",
                "Quando você se escolhe, para de aceitar migalhas emocionais.",
                "O amor que permanece após limites tende a ser o mais seguro."
            ),
            sec("Autocuidado Afetivo", "Base da estabilidade", 9,
                "Seu centro emocional melhora com rotina, descanso, espiritualidade e vínculos de suporte.",
                "Quanto mais inteiro seu cotidiano, menos dependente de validação externa você fica.",
                "Autocuidado é estratégia afetiva, não luxo."
            ),
            sec("Janelas Favoráveis", "Ciclos de abertura", 10,
                "Fases venusianas e jupiterianas costumam favorecer encontros e reconexões.",
                "Mais importante que timing astrológico é disponibilidade interna.",
                "Quando você muda padrão, muda também o tipo de amor que atrai."
            ),
            sec("Cura de Feridas", "Quíron no amor", 11,
                "Feridas antigas podem confundir intensidade com segurança.",
                "Curar é parar de deixar o passado dirigir escolhas atuais.",
                "Terapia, escrita e práticas de presença ajudam a reprogramar o afeto."
            ),
            sec("Amor e Propósito", "Relação que expande", 12,
                "Relações alinhadas ampliam sua potência em vez de reduzir seu mundo.",
                "Se um vínculo exige que você diminua quem é, há desalinhamento.",
                "Amor saudável protege identidade e fortalece caminho."
            ),
            sec("Preparação Consciente", "Como atrair melhor", 13,
                "Defina critérios: inegociáveis, flexíveis e limites de segurança emocional.",
                "Observe atitude no tempo, não promessa no início.",
                "Escolha com processo, não só com impulso."
            ),
            sec("Mensagem Final", "Seu coração com direção", 14,
                f"{nome}, sua vida amorosa começa quando você se escolhe com firmeza.",
                "Com autoconhecimento e limite, você abre espaço para vínculos verdadeiros.",
                "O amor que você procura também procura alguém com a sua coragem."
            ),
        ]

    if tipo == "carreira":
        return [
            sec("Introdução à Carreira", "Propósito em ação", 1,
                f"{nome}, seu mapa profissional mostra como transformar talento em trabalho com sentido.",
                f"Com Sol em {signo} e ascendente em {asc_txt}, você rende melhor com autonomia, profundidade e impacto humano.",
                "Carreira sustentável nasce do encontro entre competência, valor e propósito."
            ),
            sec("Vocação Central", "Onde você brilha", 2,
                "Sua vocação aponta para análise humana, estratégia sensível, comunicação profunda e criação com significado.",
                "Você se destaca ao unir técnica e intuição.",
                "Quando o trabalho tem sentido, seu desempenho sobe de forma clara."
            ),
            sec("Talentos Naturais", "Forças de base", 3,
                "Leitura fina de contexto, síntese e percepção de nuance são ativos seus.",
                "Você traduz complexidade em orientação prática.",
                "Esses talentos aumentam seu diferencial competitivo."
            ),
            sec("Mercúrio Profissional", "Mente e comunicação", 4,
                "Sua comunicação convence por consistência e clareza.",
                "Aprimorar escrita e apresentação amplia alcance sem perder autenticidade.",
                "Comunicação é multiplicador direto de carreira."
            ),
            sec("Marte na Carreira", "Execução e ritmo", 5,
                "Você alterna ciclos de alta intensidade e necessidade de recuperação.",
                "Sem estrutura, pode haver picos e exaustão.",
                "Com rotina inteligente, sua produtividade se estabiliza."
            ),
            sec("Júpiter Profissional", "Expansão e oportunidades", 6,
                "Seu crescimento vem de estudo contínuo, visibilidade qualificada e rede de confiança.",
                "Você prospera ao compartilhar conhecimento.",
                "Foco evita dispersão de energia."
            ),
            sec("Saturno Profissional", "Estrutura e legado", 7,
                "Saturno pede método: processos, métricas, limites e responsabilidade com prazo.",
                "Talento sem estrutura se perde; com estrutura, vira legado.",
                "Construa base antes de acelerar expansão."
            ),
            sec("Imagem e Autoridade", "Reputação no mercado", 8,
                "Autoridade cresce quando posicionamento e entrega estão alinhados.",
                "Mostre método, resultado e visão.",
                "Reputação é ativo composto ao longo do tempo."
            ),
            sec("Dinheiro e Valor", "Remuneração justa", 9,
                "Prosperidade profissional pede precificação coerente com impacto entregue.",
                "Cobrar abaixo do valor drena energia e limita crescimento.",
                "Estratégia comercial é parte da sua evolução de carreira."
            ),
            sec("Ambiente de Trabalho", "Onde rende melhor", 10,
                "Você performa melhor em contextos com autonomia e relações maduras.",
                "Micromanagement e ambiente tóxico reduzem sua potência.",
                "Escolher ecossistema é decisão estratégica."
            ),
            sec("Parcerias e Networking", "Alianças inteligentes", 11,
                "Parcerias certas aceleram mais que esforço isolado.",
                "Busque reciprocidade, clareza de papel e visão comum.",
                "Networking eficaz é confiança construída no tempo."
            ),
            sec("Desafios Recorrentes", "Pontos de atenção", 12,
                "Autocobrança elevada e perfeccionismo podem atrasar movimento.",
                "Sobrecarga silenciosa também pode virar gargalo de crescimento.",
                "Delegar, priorizar e simplificar são competências-chave."
            ),
            sec("Plano de Evolução", "Próximos ciclos", 13,
                "Defina metas trimestrais com foco em resultado e energia sustentável.",
                "Combine aprendizado técnico, visibilidade e execução consistente.",
                "Pequenos avanços semanais vencem planos sem continuidade."
            ),
            sec("Mensagem Final", "Carreira com alma", 14,
                f"{nome}, seu sucesso cresce quando talento e propósito caminham juntos.",
                "Use o mapa como direção estratégica, não como limite.",
                "Você tem estrutura para construir carreira forte, lucrativa e com sentido."
            ),
        ]

    if tipo == "prosperidade":
        return [
            sec("Introdução à Prosperidade", "Abundância integral", 1,
                f"{nome}, prosperidade no seu mapa vai além de dinheiro: inclui autonomia, paz, vínculos saudáveis e propósito.",
                f"Com Sol em {signo} e ascendente em {asc_txt}, você prospera quando une intuição com estratégia prática.",
                "Abundância sustentável nasce de valor real entregue com consistência."
            ),
            sec("Relação com Dinheiro", "Crença e comportamento", 2,
                "Seu resultado financeiro também reflete crenças de merecimento e segurança.",
                "Identificar padrões de escassez é passo essencial de virada.",
                "Prosperidade começa na mentalidade e consolida no hábito."
            ),
            sec("Júpiter Financeiro", "Onde expandir", 3,
                "Júpiter aponta expansão por estudo, rede e novos mercados.",
                "Compartilhar valor tende a ampliar retorno.",
                "Expansão com método evita ganhos frágeis."
            ),
            sec("Saturno Financeiro", "Base e proteção", 4,
                "Saturno pede orçamento, reserva e gestão de risco.",
                "Sem base, crescimento oscila; com base, crescimento sustenta.",
                "Disciplina financeira é liberdade no longo prazo."
            ),
            sec("Vênus e Valor", "Preço, prazer e equilíbrio", 5,
                "Vênus mostra relação com prazer, consumo e autoestima financeira.",
                "Você merece conforto, mas precisa alinhar gasto com prioridade.",
                "Equilíbrio entre desfrutar e investir fortalece patrimônio."
            ),
            sec("Marte e Ação", "Como gerar renda", 6,
                "Marte revela sua capacidade de iniciativa para abrir receita.",
                "Ação impulsiva arrisca; ação com critério constrói.",
                "Coragem com estratégia acelera prosperidade."
            ),
            sec("Diversificação", "Múltiplas fontes", 7,
                "Prosperidade robusta raramente depende de uma fonte única.",
                "Diversificar reduz risco e aumenta previsibilidade.",
                "Combine renda ativa, semi-passiva e investimento de longo prazo."
            ),
            sec("Reserva e Segurança", "Estabilidade emocional e financeira", 8,
                "Reserva de emergência protege decisão e reduz ansiedade.",
                "Com colchão financeiro, você negocia melhor e escolhe melhor.",
                "Segurança prática aumenta autoconfiança para crescer."
            ),
            sec("Padrões de Escassez", "O que cortar", 9,
                "Autossabotagem pode aparecer como culpa ao cobrar ou medo de visibilidade.",
                "Esses padrões drenam resultado sem percepção imediata.",
                "Consciência e ação objetiva interrompem o ciclo."
            ),
            sec("Prosperidade e Propósito", "Dinheiro com sentido", 10,
                "Ganhos mais sólidos vêm de coerência entre valor pessoal e valor entregue.",
                "Dinheiro sem sentido cansa; dinheiro com propósito energiza.",
                "Coerência é multiplicador de abundância no longo prazo."
            ),
            sec("Parcerias de Crescimento", "Quem soma", 11,
                "Parcerias certas ampliam alcance e reduzem curva de aprendizado.",
                "Busque alianças com clareza, confiança e visão comum.",
                "Prosperidade compartilhada tende a ser mais estável."
            ),
            sec("Ciclos e Timing", "Quando acelerar", 12,
                "Há fases para expandir e fases para consolidar.",
                "Respeitar timing melhora resultado e protege caixa.",
                "Estratégia boa combina impulso com leitura de contexto."
            ),
            sec("Plano de Abundância", "Prática mensal", 13,
                "Defina metas simples: faturamento, margem, reserva e investimento.",
                "Revise mensalmente sem culpa: ajuste, aprenda, continue.",
                "Prosperidade é processo contínuo, não evento isolado."
            ),
            sec("Mensagem Final", "Você em fluxo", 14,
                f"{nome}, sua abundância cresce quando você honra valor, método e propósito.",
                "Confie na sua capacidade de criar, organizar e expandir.",
                "Você merece prosperar com estabilidade, liberdade e paz."
            ),
        ]

    # astral
    return [
        sec("Introdução", "Seu mapa de alma", 1,
            f"{nome}, seu mapa astral é o retrato do céu no seu nascimento em {cidade}. Ele descreve potenciais, padrões e caminhos de evolução.",
            f"Com Sol em {signo} e ascendente em {asc_txt}, você combina profundidade emocional com presença marcante no mundo.",
            "Astrologia aqui é ferramenta de autoconhecimento prático para escolhas mais alinhadas."
        ),
        sec("Sol", "Identidade e propósito", 2,
            "O Sol representa sua essência consciente: o que te move e organiza por dentro.",
            "Honrar essa essência aumenta vitalidade e coerência decisória.",
            "Negar o Sol costuma gerar dispersão e sensação de desencontro."
        ),
        sec("Lua", "Emoções e segurança", 3,
            "A Lua mostra seu mundo afetivo, gatilhos e necessidade de acolhimento.",
            "Conhecer sua Lua ajuda a regular emoção sem autoabandono.",
            "Segurança emocional é base para maturidade relacional e prática."
        ),
        sec("Ascendente", "Como o mundo te vê", 4,
            "O ascendente descreve sua presença imediata e forma de iniciar ciclos.",
            "Ele também indica habilidades de adaptação em contextos novos.",
            "Integrar ascendente e Sol fortalece autenticidade."
        ),
        sec("Mercúrio", "Mente e comunicação", 5,
            "Mercúrio mostra como você aprende, pensa e se expressa.",
            "Comunicação clara reduz ruído e melhora vínculos.",
            "Aprimorar linguagem é ganho transversal para toda a vida."
        ),
        sec("Vênus", "Afeto, prazer e valores", 6,
            "Vênus revela linguagem de amor e critérios de valor.",
            "Também influencia autoestima e relação com recursos.",
            "Vênus bem cuidada melhora escolhas afetivas e financeiras."
        ),
        sec("Marte", "Ação e coragem", 7,
            "Marte mostra impulso, assertividade e modo de enfrentar desafio.",
            "Com método, sua força vira conquista sustentável.",
            "Coragem madura é ação com direção."
        ),
        sec("Júpiter", "Expansão e fé", 8,
            "Júpiter amplia visão, oportunidades e aprendizado.",
            "Ele potencializa talentos, mas também excessos se faltar medida.",
            "Fé prática combina crença com execução consistente."
        ),
        sec("Saturno", "Limite e construção", 9,
            "Saturno ensina responsabilidade, estrutura e paciência estratégica.",
            "O que Saturno constrói tende a durar.",
            "A disciplina certa protege seu futuro."
        ),
        sec("Urano", "Mudança e liberdade", 10,
            "Urano representa inovação, autonomia e quebra de padrão estagnado.",
            "Ele sinaliza quando a vida pede atualização de rota.",
            "Mudança consciente evita rupturas caóticas."
        ),
        sec("Netuno", "Sensibilidade e visão", 11,
            "Netuno amplia intuição, imaginação e espiritualidade.",
            "Também pede cuidado com idealização e fuga.",
            "Inspiração com discernimento é a melhor síntese netuniana."
        ),
        sec("Plutão", "Transformação profunda", 12,
            "Plutão atua em ciclos de morte e renascimento psicológico.",
            "Ele revela força para atravessar crise e se reconstruir.",
            "Transformar é tornar-se mais verdadeira."
        ),
        sec("Casas Astrológicas", "Áreas da vida", 13,
            "As casas mostram onde cada energia planetária se manifesta na prática.",
            "Elas conectam o mapa com vida real: trabalho, amor, família, propósito.",
            "Aplicação prática é o que torna o mapa útil de verdade."
        ),
        sec("Aspectos", "Conversa entre planetas", 14,
            "Aspectos mostram harmonia e tensão entre partes internas da personalidade.",
            "Trígonos facilitam, quadraturas desafiam, oposições pedem equilíbrio.",
            "Seu mapa pede integração, não perfeição."
        ),
        sec("Mensagem Final", "Seu caminho", 15,
            f"{nome}, seu mapa é bússola, não sentença. Ele amplia consciência para escolhas melhores.",
            "Use esta leitura para viver com mais verdade e direção.",
            "Quanto mais você se conhece, mais liberdade você conquista."
        ),
    ]

# ── Placeholder roda ───────────────────────────────────────────────────────────

def _criar_roda_placeholder(roda_path: str, nome: str, tipo: str, signo: str):
    """Cria roda astrológica placeholder se a geração real falhar."""
    img = Image.new("RGB", (1200, 1200), (18, 12, 35))
    draw = ImageDraw.Draw(img)
    from PIL import ImageFont
    font = ImageFont.load_default()
    cx, cy = 600, 600
    draw.ellipse([100, 100, 1100, 1100], outline=(108, 59, 140), width=3)
    draw.ellipse([400, 400, 800, 800], outline=(60, 40, 100), width=1)
    draw.text((cx - 40, cy - 10), signo, fill=(240, 235, 255), font=font)
    img.save(roda_path)
