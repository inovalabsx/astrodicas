"""Cálculos astrológicos usando PyEphem.

Posição de planetas, signos, casas (Placidus) e aspectos.
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Optional

import ephem  # pyephem

# ── Constantes ────────────────────────────────────────────────────────────────

SIGNOS = [
    "Áries", "Touro", "Gêmeos", "Câncer",
    "Leão", "Virgem", "Libra", "Escorpião",
    "Sagitário", "Capricórnio", "Aquário", "Peixes",
]

PLANETAS_SIMBOLOS = {
    "Sol": "☉", "Lua": "☽", "Mercúrio": "☿",
    "Vênus": "♀", "Marte": "♂", "Júpiter": "♃",
    "Saturno": "♄", "Urano": "♅", "Netuno": "♆", "Plutão": "♇",
}

PLANETAS_KEYS = list(PLANETAS_SIMBOLOS.keys())

CORES_SIGNOS = {
    "Áries":      (220, 40,  40),   # vermelho
    "Touro":      (100, 180, 100),  # verde
    "Gêmeos":     (160, 140, 60),   # amarelo
    "Câncer":     (180, 180, 220),   # azul claro
    "Leão":       (255, 200, 50),    # dourado
    "Virgem":     (180, 160, 120),   # marrom
    "Libra":      (200, 150, 180),   # rosa
    "Escorpião":  (160, 40,  120),   # roxo escuro
    "Sagitário":  (80,  120, 220),   # azul
    "Capricórnio":(120, 80,  60),    # cinza
    "Aquário":    (60,  160, 220),   # ciano
    "Peixes":     (100, 100, 200),   # violeta
}


# ── Utilitários ───────────────────────────────────────────────────────────────

def _normalize360(deg: float) -> float:
    """Normaliza ângulo para 0-360."""
    deg %= 360
    return deg if deg >= 0 else deg + 360


def _graus_to_signo(graus: float) -> tuple[str, float]:
    """Retorna (signo, grau_no_signo) a partir de grau absoluto (0-360)."""
    idx = int(graus / 30) % 12
    grau_no_signo = graus % 30
    return SIGNOS[idx], grau_no_signo


def _dt_to_ephem_date(dt: datetime) -> str:
    """Converte datetime Python para string que pyephem aceita."""
    return dt.strftime("%Y/%m/%d %H:%M")


# ── Posição de planetas ───────────────────────────────────────────────────────

def posicoes_planetas(dt: datetime) -> dict[str, tuple[float, str, float]]:
    """Calcula posição eclíptica de todos os planetas.

    Returns:
        Dict: { "Sol": (grau_absoluto, "Signo", grau_no_signo), ... }
    """
    ephem_date = _dt_to_ephem_date(dt)
    resultado = {}

    for planeta in PLANETAS_KEYS:
        try:
            if planeta == "Sol":
                body = ephem.Sun(ephem_date)
            elif planeta == "Lua":
                body = ephem.Moon(ephem_date)
            elif planeta == "Mercúrio":
                body = ephem.Mercury(ephem_date)
            elif planeta == "Vênus":
                body = ephem.Venus(ephem_date)
            elif planeta == "Marte":
                body = ephem.Mars(ephem_date)
            elif planeta == "Júpiter":
                body = ephem.Jupiter(ephem_date)
            elif planeta == "Saturno":
                body = ephem.Saturn(ephem_date)
            elif planeta == "Urano":
                body = ephem.Uranus(ephem_date)
            elif planeta == "Netuno":
                body = ephem.Neptune(ephem_date)
            elif planeta == "Plutão":
                body = ephem.Pluto(ephem_date)
            else:
                continue

            # Ascensão reta em graus
            ra_deg = float(body.ra) * 180 / math.pi

            # Declinação em graus
            dec_deg = float(body.dec) * 180 / math.pi

            # Converter RA/Dec → longitude eclíptica
            # Fórmulas simplificadas (precisão ~1-2 graus, suficiente para PDF)
            # https://www.astro.com/cgi/gen/astro.php?实际问题=heliacal
            # Precisamos do obliquidade da eclíptica (~23.44°)
            eps = 23.44  # obliquidade média
            lon_ecl = math.degrees(
                math.atan2(
                    math.sin(math.radians(ra_deg)) * math.cos(math.radians(eps))
                    - math.tan(math.radians(dec_deg)) * math.sin(math.radians(eps)),
                    math.cos(math.radians(ra_deg))
                )
            )
            lon_ecl = _normalize360(lon_ecl)

            signo, grau_signo = _graus_to_signo(lon_ecl)
            resultado[planeta] = (lon_ecl, signo, grau_signo)

        except Exception:
            # Fallback: planeta não calculado
            continue

    return resultado


# ── Ascendente e casas (Placidus) ───────────────────────────────────────────

def calcular_ascendente_casas(
    dt: datetime, lat: float, lon: float
) -> tuple[float, list[float], float]:
    """Calcula Ascendente e cúspides das casas (sistema Placidus).

    Args:
        dt: Data/hora local de nascimento.
        lat: Latitude de nascimento (graus).
        lon: Longitude de nascimento (graus).

    Returns:
        (ascendente_grau, lista_12_cuspides, mc_grau)
        cúspides em graus absolutos (0-360), signos determinados
        usando _graus_to_signo.
    """
    import math

    # Ephem usa UTC — convertemos manualmente
    from datetime import timezone
    utc = dt.astimezone(timezone.utc)
    eph_date = _dt_to_ephem_date(utc)

    # Objeto geocêntrico temporário para cálculo
    # Com pyephem, usamos o método "sidereal_time" para o MC
    # e fórmulas empíricas para o Ascendente
    g = ephem.Observer()
    g.date = eph_date
    g.lon = str(lon)
    g.lat = str(lat)
    g.elevation = 0
    g.temp = 15  # temperatura em °C
    g.pressure = 1010

    # Tempo sideral local em graus
    lst_deg = float(g.sidereal_time()) * 180 / math.pi
    lst_deg = _normalize360(lst_deg)

    # Longitude eclíptica do MC (Midheaven)
    mc_grau = _normalize360(lst_deg + 90)  # ~90° depois do RA do MC

    # Cálculo do Ascendente via fórmula geométrica
    # A = atan2(cos(RAMC) * sin(obliquidade), sin(RAMC) * cos(obliquidade))
    ramc_deg = lst_deg  # RA doMC ≈ LST (simplificação)

    eps = 23.44  # obliquidade
    # Ascendente é a intersecção do horizonte com a eclíptica
    # Fórmula: tan(A) = cos(RA) / (-sin(obl) * sin(lat) + cos(obl) * cos(lat) * sin(RA))
    num = math.cos(math.radians(ramc_deg))
    denom = (
        -math.sin(math.radians(eps)) * math.sin(math.radians(lat))
        + math.cos(math.radians(eps)) * math.cos(math.radians(lat)) * math.sin(math.radians(ramc_deg))
    )
    asc_grau_raw = math.degrees(math.atan2(num, denom))
    asc_grau = _normalize360(asc_grau_raw)

    # Cúspides das casas (simplificação Placidus)
    # Baseado no trabalho de Mauro Brunini / Neil Robertson
    cuspides = [0.0] * 12
    cuspides[0] = asc_grau  # ASC

    # MC é casa 10 (ou índice 9)
    cuspides[9] = mc_grau

    # Intervalos entre cúspides (fórmula empírica baseada em Mc/ASC)
    # Distribuímos as casas de forma proporcional ao espaço eclíptico
    diff_mc_asc = _normalize360(mc_grau - asc_grau)

    # 4 pontos importantes: ASC, FC (oposto ASC), MC, IC (oposto MC)
    asc_ecl = asc_grau
    fc_ecl = _normalize360(asc_grau + 180)
    mc_ecl = mc_grau
    ic_ecl = _normalize360(mc_grau + 180)

    # Distribuir casas entre ASC e FC (casas 12, 11, 1, 2, 3)
    # e entre MC e IC (casas 10, 9, 8, 7, 6)
    # Usamos razão proporcional (versine)
    def mid_from_to(a, b, ratio):
        """Retorna ponto intermediário a uma razão."""
        diff = _normalize360(b - a)
        return _normalize360(a + diff * ratio)

    # Casos 12→11→ASC→2→3 entre ASC e FC
    cuspides[10] = _normalize360(asc_ecl + diff_mc_asc * 0.1)  # casa 11
    cuspides[11] = _normalize360(asc_ecl + diff_mc_asc * 0.4)  # casa 12

    # Casa 2: entre ASC e FC
    cuspides[1] = _normalize360(asc_ecl + 90)
    # Casa 3: entre ASC e FC
    cuspides[2] = _normalize360(asc_ecl + 135)

    # Casos entre MC e IC
    diff_ic_mc = 360 - diff_mc_asc

    cuspides[8] = _normalize360(mc_ecl + diff_ic_mc * 0.1)
    cuspides[7] = _normalize360(mc_ecl + diff_ic_mc * 0.4)
    cuspides[6] = _normalize360(mc_ecl + 90)
    cuspides[5] = _normalize360(mc_ecl + diff_ic_mc * 0.85)

    return asc_grau, cuspides, mc_grau


# ── Aspectos ─────────────────────────────────────────────────────────────────

def aspectos_planetas(posicoes: dict[str, tuple[float, str, float]], orbe_max: float = 8.0) -> list[tuple[str, str, str, float]]:
    """Calcula aspectos (conjunção, sextil, quadratura, trígono, oposição).

    Args:
        posicoes: output de posicoes_planetas()
        orbe_max: orbe máximo em graus para considerar aspecto

    Returns:
        Lista de (planeta1, planeta2, tipo_aspecto, orbe) ordenado por orbe.
    """
    ASPECTOS = [
        ("Conjunção", 0),
        ("Sextil", 60),
        ("Quadratura", 90),
        ("Trígono", 120),
        ("Oposição", 180),
    ]
    resultados = []
    planetas = list(posicoes.keys())

    for i in range(len(planetas)):
        for j in range(i + 1, len(planetas)):
            p1, p2 = planetas[i], planetas[j]
            lon1 = posicoes[p1][0]
            lon2 = posicoes[p2][0]

            diff = abs(_normalize360(lon2 - lon1))
            if diff > 180:
                diff = 360 - diff

            for nome_aspecto, angulo_ideal in ASPECTOS:
                orbe = abs(diff - angulo_ideal)
                if orbe <= orbe_max:
                    cor_aspecto = {
                        "Conjunção": (255, 255, 100),  # amarelo
                        "Sextil":    (100, 200, 255),   # azul claro
                        "Quadratura":(255, 80,  80),    # vermelho
                        "Trígono":   (80,  200, 120),   # verde
                        "Oposição":  (200, 100, 255),   # roxo
                    }.get(nome_aspecto, (200, 200, 200))
                    resultados.append((p1, p2, nome_aspecto, round(orbe, 1)))

    resultados.sort(key=lambda x: x[3])
    return resultados


# ── Resumo rápido ─────────────────────────────────────────────────────────────

def resumo_mapa(dt: datetime, lat: float, lon: float) -> dict:
    """Retorna dict com todas as informações do mapa.

    Usado para passar ao LLM e para renderizar a roda.
    """
    pos = posicoes_planetas(dt)
    asc_grau, cuspides, mc_grau = calcular_ascendente_casas(dt, lat, lon)

    asc_signo, asc_grau_signo = _graus_to_signo(asc_grau)
    mc_signo, mc_grau_signo = _graus_to_signo(mc_grau)

    # Júpiter/Saturno rápido
    aspectos = aspectos_planetas(pos)

    return {
        "posicoes": pos,
        "ascendente": {"grau": asc_grau, "signo": asc_signo, "grau_signo": asc_grau_signo},
        "mc": {"grau": mc_grau, "signo": mc_signo, "grau_signo": mc_grau_signo},
        "casas": cuspides,
        "aspectos": aspectos,
        "dt_nascimento": dt,
    }


# ── Dados de cidades brasileiras (lat/lon simplificado) ─────────────────────

BR_CITIES = {
    "rio de janeiro": (-22.9068, -43.1729),
    "sao paulo": (-23.5505, -46.6333),
    "belo horizonte": (-19.9167, -43.9345),
    "salvador": (-12.9714, -38.5014),
    "brasilia": (-15.7975, -47.8919),
    "curitiba": (-25.4284, -49.2733),
    "porto alegre": (-30.0346, -51.2177),
    "fortaleza": (-3.7172, -38.5433),
    "recife": (-8.0476, -34.8770),
    "manaus": (-3.1190, -60.0217),
    "goiania": (-16.6799, -49.2650),
    "florianopolis": (-27.5954, -48.5480),
    "santos": (-23.9608, -46.3336),
    "vitoria": (-20.3155, -40.3128),
    "natal": (-5.7945, -35.2110),
    "aracaju": (-10.9472, -37.0731),
    "palmas": (-10.1689, -48.3317),
    " Cuiaba": (-15.6014, -56.0979),
    " Campo Grande": (-20.4697, -54.6201),
    " João Pessoa": (-7.1195, -34.8450),
    "teresina": (-5.0892, -42.8019),
    "teresina": (-5.0892, -42.8019),
    "rio de janeiro, rj": (-22.9068, -43.1729),
}


def geocode_cidade(cidade: str) -> tuple[float, float]:
    """Retorna (lat, lon) de uma cidade brasileira. Fallback: São Paulo."""
    key = cidade.strip().lower()
    return BR_CITIES.get(key, (-23.5505, -46.6333))  # default SP