"""Gerador da Roda Astrológica (astrological wheel) em PNG.

Usa matplotlib para desenhar o círculo com:
- 12 casas astrológicas (cúspides)
- 12 signos com cores e símbolos
- Planetas com símbolos
- Aspectos (linhas coloridas entre planetas)
"""
from __future__ import annotations

import math
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Arc
import matplotlib.transforms as transforms
import numpy as np

# Importar do módulo de cálculos
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from astro_math import (
    SIGNOS, CORES_SIGNOS, PLANETAS_SIMBOLOS,
    _graus_to_signo, _normalize360, posicoes_planetas,
    calcular_ascendente_casas, aspectos_planetas,
)


# ── Símbolos astrológicos (Unicode) ────────────────────────────────────────────

SIMBOLOS_SIGNOS = {
    "Áries": "♈", "Touro": "♉", "Gêmeos": "♊", "Câncer": "♋",
    "Leão": "♌", "Virgem": "♍", "Libra": "♎", "Escorpião": "♏",
    "Sagitário": "♐", "Capricórnio": "♑", "Aquário": "♒", "Peixes": "♓",
}

COR_TIPO_PLANETA = {
    "Sol": (255, 220, 50),
    "Lua": (200, 200, 200),
    "Mercúrio": (180, 180, 80),
    "Vênus": (255, 150, 180),
    "Marte": (230, 50, 50),
    "Júpiter": (255, 180, 80),
    "Saturno": (150, 120, 80),
    "Urano": (80, 200, 255),
    "Netuno": (50, 100, 200),
    "Plutão": (140, 60, 140),
}


def _grau_to_xy(grau: float, raio: float, cx: float, cy: float) -> tuple[float, float]:
    """Converte grau (0 = leste, clockwise) → (x, y)."""
    rad = math.radians(grau - 90)  # 0 no topo
    return cx + raio * math.cos(rad), cy + raio * math.sin(rad)


def _grau_to_xy_no_cx(grau: float, raio: float) -> tuple[float, float]:
    """Mesmo mas retorna (x, y) relativo ao centro (0,0)."""
    rad = math.radians(grau - 90)
    return raio * math.cos(rad), raio * math.sin(rad)


def _plot_zodiac_symbol(ax, angle_deg: float, radius: float, color: tuple, symbol: str):
    """Plota um símbolo zodiacal na posição angular."""
    rad = math.radians(angle_deg - 90)
    x = radius * math.cos(rad)
    y = radius * math.sin(rad)
    ax.text(x, y, symbol, fontsize=18, ha='center', va='center',
            color=color, fontfamily='DejaVu Sans')


def _grau_to_rad(grau: float) -> float:
    """Grau → radiano (0° = leste, horário)."""
    return math.radians(grau - 90)


def gerar_roda_astrologica(
    dt_nasc: datetime,
    lat: float,
    lon: float,
    posicoes: dict = None,
    casas: list = None,
    asc_grau: float = None,
    aspectos: list = None,
    tamanho: int = 1200,
    bg_color: str = '#0d0d1a',
) -> np.ndarray:
    """Gera a imagem da roda astrológica como array numpy (RGB).

    Args:
        dt_nasc: data/hora de nascimento
        lat/lon: coordenadas geográficas
        posicoes: dict de posicoes_planetas() (opcional, calcula se None)
        casas: lista de 12 cúspides em graus (opcional)
        asc_grau: grau do ascendente (opcional)
        aspectos: lista de aspectos (opcional)
        tamanho: resolução em pixels (quadrado)

    Returns:
        np.ndarray shape (H, W, 3) em RGB uint8
    """
    DPI = 150
    SIZE_IN = tamanho / DPI

    fig, ax = plt.subplots(figsize=(SIZE_IN, SIZE_IN), dpi=DPI)
    ax.set_aspect('equal')
    ax.axis('off')

    cx, cy = 0, 0
    R = 0.88  # raio normalizado (0-1)

    # Fundo escuro elegante
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)

    # ── Anel externo (borda decorativa) ─────────────────────────────────────
    outer_ring = plt.Circle((cx, cy), R + 0.04, color='#3a3a5c', zorder=1)
    ax.add_patch(outer_ring)
    inner_ring = plt.Circle((cx, cy), R - 0.02, color=bg_color, zorder=1)
    ax.add_patch(inner_ring)

    # ── Calcular posições se não fornecidas ────────────────────────────────
    if posicoes is None:
        posicoes = posicoes_planetas(dt_nasc)
    if casas is None or asc_grau is None:
        asc_grau_calc, casas_calc, mc_grau = calcular_ascendente_casas(dt_nasc, lat, lon)
        if casas is None:
            casas = casas_calc
        if asc_grau is None:
            asc_grau = asc_grau_calc

    # ── Desenhar signos no anel externo ───────────────────────────────────
    for i in range(12):
        grau_central = i * 30 + 15  # centro do signo
        signo_nome = SIGNOS[i]
        cor = CORES_SIGNOS[signo_nome]
        cor_hex = '#%02x%02x%02x' % cor

        # Arco do signo
        theta1 = _grau_to_rad(grau_central - 14.5)
        theta2 = _grau_to_rad(grau_central + 14.5)
        arc = Arc((cx, cy), 2 * (R + 0.03), 2 * (R + 0.03),
                  angle=0, theta1=math.degrees(theta1), theta2=math.degrees(theta2),
                  color=cor_hex, linewidth=4, zorder=3)
        ax.add_patch(arc)

        # Símbolo do signo
        r_sym = R + 0.075
        x_sym, y_sym = _grau_to_xy_no_cx(grau_central, r_sym)
        ax.text(x_sym, y_sym, SIMBOLOS_SIGNOS[signo_nome],
                fontsize=22, ha='center', va='center',
                color=cor_hex, fontweight='bold', zorder=5)

    # ── Linha do zodíaco (anel decorativo interno) ─────────────────────────
    for i in range(12):
        signo = SIGNOS[i]
        cor = CORES_SIGNOS[signo]
        cor_hex = '#%02x%02x%02x' % cor
        ang1 = i * 30
        ang2 = (i + 1) * 30
        wedge = mpatches.Wedge((cx, cy), R - 0.005, math.degrees(_grau_to_rad(ang1)),
                                math.degrees(_grau_to_rad(ang2)),
                                facecolor=cor_hex, alpha=0.07, zorder=2, linewidth=0)
        ax.add_patch(wedge)

    # ── Casas (cúspides) ───────────────────────────────────────────────────
    casas_por_signo = []
    for i, cusp_grau in enumerate(casas):
        signo, _ = _graus_to_signo(cusp_grau)
        casas_por_signo.append(signo)

    R_in = R - 0.04

    # Linhas das cúspides (do centro até a borda)
    for i in range(12):
        grau = casas[i]
        x1, y1 = _grau_to_xy_no_cx(grau, 0.10)
        x2, y2 = _grau_to_xy_no_cx(grau, R_in)
        ax.plot([x1, x2], [y1, y2], color='#6060a0', linewidth=1.0, zorder=4)

    # Números das casas
    for i, cusp_grau in enumerate(casas):
        r_num = (0.10 + R_in) / 2
        # Evitar sobreposição: se casa i está perto de i-1, avança
        x, y = _grau_to_xy_no_cx(cusp_grau, r_num)
        ax.text(x, y, str(i + 1), fontsize=9, ha='center', va='center',
                color='#c0c0e0', fontweight='bold', zorder=6)

    # ── Planetas (pontos + símbolos) ───────────────────────────────────────
    R_planet = R - 0.055

    posicoes_sorted = sorted(posicoes.items(), key=lambda x: x[1][0])

    for planeta, (grau_abs, signo, grau_signo) in posicoes_sorted:
        cor = COR_TIPO_PLANETA.get(planeta, (200, 200, 200))
        cor_hex = '#%02x%02x%02x' % cor

        x, y = _grau_to_xy_no_cx(grau_abs, R_planet)

        # Ponto do planeta
        ax.plot(x, y, 'o', color=cor_hex, markersize=8, zorder=7)

        # Símbolo do planeta
        symbol = PLANETAS_SIMBOLOS.get(planeta, "?")
        r_label = R_planet - 0.035
        xl, yl = _grau_to_xy_no_cx(grau_abs, r_label)
        ax.text(xl, yl, symbol, fontsize=14, ha='center', va='center',
                color=cor_hex, fontweight='bold', zorder=8)

        # Nome do planeta perto do símbolo
        # Tenta colocar o nome fora do círculo
        r_name = R_planet - 0.065
        xn, yn = _grau_to_xy_no_cx(grau_abs, r_name)
        ax.text(xn, yn, planeta, fontsize=7, ha='center', va='center',
                color='#a0a0c0', zorder=8)

    # ── Aspectos (linhas entre planetas) ───────────────────────────────────
    if aspectos:
        pontos_planetas = {p: posicoes[p][0] for p in posicoes}
        COR_ASPECTO = {
            "Conjunção": '#ffff66',
            "Sextil":    '#66ccff',
            "Quadratura": '#ff5050',
            "Trígono":   '#50cc80',
            "Oposição":  '#cc66ff',
        }
        for p1, p2, tipo_aspecto, orbe in aspectos:
            if p1 not in pontos_planetas or p2 not in pontos_planetas:
                continue
            if orbe > 6:  # orbe máximo visual
                continue

            g1 = pontos_planetas[p1]
            g2 = pontos_planetas[p2]
            cor_linha = COR_ASPECTO.get(tipo_aspecto, '#888888')

            x1, y1 = _grau_to_xy_no_cx(g1, R_planet)
            x2, y2 = _grau_to_xy_no_cx(g2, R_planet)

            ax.plot([x1, x2], [y1, y2], color=cor_linha,
                    linewidth=1.2, alpha=0.6, zorder=3, linestyle='-')

    # ── Centro decorativo ───────────────────────────────────────────────────
    center = plt.Circle((cx, cy), 0.08, color='#1a1a30', zorder=10)
    ax.add_patch(center)
    asc_signo, asc_g = _graus_to_signo(asc_grau)
    ax.text(0, 0.03, f"ASC {asc_signo}", fontsize=10, ha='center', va='center',
            color='#c0c0ff', fontweight='bold', zorder=11)
    ax.text(0, -0.03, "ASTRODICAS", fontsize=8, ha='center', va='center',
            color='#6060a0', zorder=11)

    # ── Configurar limites ─────────────────────────────────────────────────
    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)
    ax.set_box_aspect('1')

    plt.tight_layout(pad=0)
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

    # Converter para numpy array — matplotlib 3.10+
    import io
    fig.savefig(io.BytesIO(), format='png')  # força renderização
    buf = np.asarray(fig.canvas.buffer_rgba())
    # RGB only
    buf = buf[:, :, :3]

    plt.close(fig)
    return buf


def salvar_roda(
    dt_nasc: datetime,
    lat: float,
    lon: float,
    caminho: str,
    posicoes: dict = None,
    casas: list = None,
    asc_grau: float = None,
    aspectos: list = None,
    tamanho: int = 1200,
    bg_color: str = '#0d0d1a',
) -> str:
    """Salva a roda astrológica como PNG e retorna o caminho."""
    from PIL import Image
    import os
    os.makedirs(os.path.dirname(caminho) or '.', exist_ok=True)
    buf = gerar_roda_astrologica(dt_nasc, lat, lon, posicoes, casas, asc_grau, aspectos, tamanho, bg_color)
    img = Image.fromarray(buf)
    img.save(caminho, 'PNG')
    return caminho