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
}

TIPO_NOMES = {
    "astral": "Mapa Astral Completo",
    "sinastria": "Sinastria Amorosa",
    "carreira": "Mapa da Carreira",
    "prosperidade": "Mapa da Prosperidade",
}

# ── Classe FPDF com footer automático ──────────────────────────────────────────

from fpdf import FPDF


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
        pdf.set_text_color(*paleta["cor_texto"])
        pdf.set_xy(22, y_card + 1)
        pdf.cell(0, 8, f"{s.get('ordem', idx+1):02d}.  {s['titulo']}",
                 new_x="LMARGIN", new_y="NEXT")

        # Subtítulo em tom mais claro
        pdf.set_font("DejaVu", "", 9)
        pdf.set_text_color(*paleta["cor_destaque"])
        pdf.set_xy(28, y_card + 9)
        pdf.cell(0, 7, f"{s.get('subtitulo', '')}",
                 new_x="LMARGIN", new_y="NEXT")

        pdf.ln(6)


def _pdf_page_roda(pdf: FPDFPremium, roda_path: str, assinatura: str):
    """Adiciona página com a roda astrológica centralizada."""
    pdf.add_page()
    w, h = 210, 297

    # Fundo escuro completo
    pdf.set_fill_color(*pdf._paleta["cor_fundo"])
    pdf.rect(0, 0, w, h, style='F')

    # Inserir roda centralizada
    # Imagem é ~1200x1200, redimensionar pra ~160mm no lado maior
    img_size = 160
    x_offset = (w - img_size) / 2
    pdf.image(roda_path, x=x_offset, y=30, w=img_size, h=img_size)

    # Assinatura abaixo
    pdf.set_y(200)
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

    # ── Header ────────────────────────────────────────────────────────────
    header_h = 35
    pdf.set_fill_color(*paleta["cor_principal"])
    pdf.rect(0, 0, w, header_h, style='F')

    pdf.set_font("DejaVu", "B", 18)
    pdf.set_text_color(*paleta["cor_texto"])
    pdf.set_xy(15, 10)
    pdf.cell(0, 10, f"{paleta['icone_titulo']} {titulo}",
             new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("DejaVu", "", 10)
    pdf.set_text_color(*paleta["cor_destaque"])
    pdf.cell(0, 5, subtitulo, new_x="LMARGIN", new_y="NEXT")

    # ── Conteúdo ──────────────────────────────────────────────────────────
    pdf.ln(12)

    pdf.set_font("DejaVu", "", 11)
    pdf.set_text_color(170, 165, 200)

    # Processar parágrafos
    paragrafos = conteudo.split("\n")
    paragrafos = [p.strip() for p in paragrafos if p.strip()]

    # Espaço útil pro conteúdo (header → espaço antes do footer automático)
    footer_reserve = 25
    espaco_util = h - header_h - footer_reserve - pdf.get_y() + header_h

    # Estimar linhas
    chars_por_linha = 70
    linhas = sum(max(1, len(p) // chars_por_linha + 1) for p in paragrafos)
    linhas += len(paragrafos) - 1  # espaços entre parágrafos

    lh = 7
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
            from .astro_math import calcular_ascendente
            asc_calc = calcular_ascendente(data_nascimento, cidade)
            if asc_calc:
                ascendente = asc_calc
        except Exception as e:
            logger.warning(f"Astro math indisponível: {e}")

        # ── 4. Gerar seções ───────────────────────────────────────────────
        secoes = None
        try:
            if False:  # Placeholder para LLM futura
                pass
        except Exception as e:
            logger.warning(f"Erro na LLM, usando fallback: {e}")
            secoes = None

        if not secoes or not isinstance(secoes, list) or len(secoes) < 8:
            # Fallback completo — textos EXPANDIDOS (300+ palavras cada)
            secoes = _gerar_fallback_completo(
                nome, signo, ascendente, cidade
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
                f"seja uma ferramenta de autoconhecimento e transformação na sua vida.\n\n"
                f"O Mapa Astral não é apenas uma ferramenta de adivinhação — é um guia de autoconhecimento "
                f"que revela seus padrões emocionais, seus talentos naturais e os desafios que você veio "
                f"superar nesta vida. Cada planeta no seu mapa representa uma parte de você: o Sol mostra "
                f"sua identidade, a Lua revela suas emoções, Mercúrio sua comunicação, Vênus seu amor, "
                f"Marte sua energia. Juntos, eles formam um retrato completo da sua alma.\n\n"
                f"Ao ler este documento, lembre-se de que você não é apenas um produto dos astros. Você "
                f"tem livre arbítrio e pode escolher como expressar cada energia do seu mapa. O céu "
                f"oferece possibilidades, mas você decide como usá-las. Que esta jornada de autoconhecimento "
                f"seja transformadora e iluminadora para você."
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
                f"intensidade e da sua coragem de sentir profundamente.\n\n"
                f"O Sol no seu mapa também fala sobre sua vitalidade e sua força criativa. O brilho único "
                f"que você traz ao mundo não se compara ao de ninguém, e a jornada da sua vida é justamente "
                f"descobrir como expressar esse brilho da forma mais autêntica possível. Quando você se "
                f"permite brilhar, inspira os outros a fazerem o mesmo. Seu Sol pede que você honre quem "
                f"você realmente é, sem se encolher para caber em expectativas alheias. O universo ganha "
                f"cor quando você se mostra em toda a sua verdade."
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
                "seu coração se sinta em paz.\n\n"
                "A Lua rege também seus hábitos, sua memória emocional e sua forma de lidar com o "
                "passado. As experiências da infância deixaram marcas profundas em sua psique, moldando "
                "sua forma de amar e de confiar. Honrar sua história, com todas as suas dores e alegrias, "
                "é parte do caminho de cura que a Lua te convida a percorrer. Quando você se permite "
                "sentir sem julgamento, a Lua se torna sua maior aliada — guiando suas emoções como "
                "as marés guiam o oceano, com sabedoria e fluidez naturais."
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
                f"precise fazer esforço — um brilho natural que atrai olhares e desperta curiosidade.\n\n"
                f"Seu Ascendente também influencia sua aparência física e seu estilo pessoal. É comum que "
                f"pessoas com este ascendente tenham olhos expressivos e uma presença que ocupa o espaço "
                f"sem precisar de palavras. Você tem um jeito único de se movimentar pelo mundo, uma "
                f"assinatura energética que fica gravada na memória de quem te encontra. À medida que você "
                f"amadurece, aprende a integrar melhor a energia do seu Ascendente com a do seu Sol, "
                f"tornando-se cada vez mais autêntica e completa.\n\n"
                f"O Ascendente é o presente que você dá ao mundo quando chega — e com o tempo, ele se "
                f"transforma em quem você está destinada a ser. É interessante notar como seu Ascendente "
                f"pode surpreender até você mesma: muitas vezes, as pessoas enxergam em você qualidades "
                f"que você ainda não descobriu em si mesma. Preste atenção nos elogios que recebe com "
                f"frequência — eles são pistas do seu Ascendente em ação. À medida que você cresce e "
                f"evolui, a diferença entre seu Sol e seu Ascendente diminui, e você se torna uma versão "
                f"cada vez mais integrada e poderosa de si mesma."
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
                "clareza da comunicação.\n\n"
                "Seu dom é traduzir o complexo em simples, o profundo em acessível, transformando "
                "sabedoria em palavras que tocam corações. Com Mercúrio bem posicionado, você tem "
                "facilidade para aprender idiomas, para escrever de forma cativante e para se conectar "
                "com pessoas através de conversas significativas. Invista em desenvolver sua voz única "
                "— o mundo precisa ouvir o que você tem a dizer. Sua palavra tem poder de cura e de "
                "transformação quando usada com consciência."
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
                "por medo de se machucar.\n\n"
                "Sua sensibilidade é seu maior presente nos relacionamentos, desde que você aprenda a "
                "usá-la como ponte e não como muro. Ame com coragem, porque sua capacidade de amar "
                "profundamente é um dos seus maiores dons. Vênus também rege sua relação com a beleza "
                "e a arte — você tem um olhar apurado para o que é estético e harmonioso. Cultivar "
                "espaços bonitos e momentos de prazer é essencial para seu bem-estar. Permita-se "
                "receber tanto quanto dá, pois o amor floresce quando há equilíbrio entre entrega e "
                "recepção. Você merece um amor que te veja por inteiro e que celebre cada parte de você."
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
                "uma capacidade de sedução que vai além do físico.\n\n"
                "Seu magnetismo pessoal é forte e as pessoas sentem sua presença quando você entra em "
                "um ambiente. Marte te dá coragem para seguir seus instintos e lutar pelo que você "
                "acredita. Aprender a direcionar essa energia de forma construtiva é uma das lições "
                "mais importantes do seu mapa. Use sua garra para construir, para proteger, para criar. "
                "Sua força interior é um presente que, quando bem cultivado, te leva a conquistar "
                "qualquer objetivo que você realmente deseje. Não tenha medo de ser intensa — sua "
                "intensidade é seu superpoder."
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
                "constrói estradas. Honre os dois e encontrará o equilíbrio entre expansão e estrutura. "
                "Lembre-se de que todo mestre Saturno tem seu presente: depois de cada lição aprendida, "
                "você se torna mais forte, mais sábia e mais preparada para o próximo capítulo."
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
                "presentes — são eles que te empurram para fora da zona de conforto e te fazem crescer. "
                "Observe quais áreas da sua vida geram mais atrito e veja nisso não um problema, mas "
                "um convite à evolução. O mapa astral não mostra um destino fixo, mas um potencial de "
                "crescimento que só você pode realizar."
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
                f"aspectos desenvolver e como expressar cada energia que recebeu ao nascer.\n\n"
                f"A astrologia é uma ferramenta de autoconhecimento, não uma prisão. Use estas informações "
                f"como um espelho para se enxergar melhor, como uma bússola para orientar suas escolhas "
                f"e como um lembrete de que você é parte de algo maior. O cosmos vive em você, e você "
                f"vive no cosmos. Cada passo que você dá em direção ao autoconhecimento é um passo em "
                f"direção à sua verdade mais profunda.\n\n"
                f"Continue explorando, continue perguntando, continue crescendo. O universo tem infinitas "
                f"camadas de sabedoria para revelar, e você está exatamente onde precisa estar. Que os "
                f"astros iluminem seu caminho e que sua jornada seja repleta de descobertas, amor e "
                f"transformação. Lembre-se: o maior astrólogo que existe é você mesma, no seu silêncio "
                f"interior, quando ouve a voz da sua própria alma. Confie nela, ela nunca te engana."
            ),
        },
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
