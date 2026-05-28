"""Vendas Bot — Geração de Mapa Astral em PDF.

Usa a LLM (OmniRoute) para gerar a interpretação astrológica
e fpdf2 para gerar o PDF final.

NOTA: Implementação inicial — versão simplificada. A geração real
completa (casas, aspectos, planetas) será refinada em versões futuras.
"""
import json
import logging
import os
import tempfile
from datetime import date, datetime
from typing import Optional
from urllib import request as urllib_request

from src.vendas_bot.settings import settings

logger = logging.getLogger(__name__)


def _gerar_interpretacao_llm(
    nome: str,
    signo: str,
    data_nascimento: date,
    hora_nascimento: str,
    cidade: str,
    tipo: str = "astral",
) -> str:
    """Gera a interpretação astrológica via LLM OmniRoute."""
    tipo_nome = {
        "astral": "Mapa Astral Completo",
        "sinastria": "Sinastria (Amor)",
        "carreira": "Mapa da Carreira",
        "revolucao": "Revolução Solar",
    }.get(tipo, "Mapa Astral")

    prompt = (
        f"Você é um astrólogo profissional brasileiro. Gere um {tipo_nome} "
        f"personalizado e completo em português do Brasil para:\n\n"
        f"Nome: {nome}\n"
        f"Signo: {signo}\n"
        f"Data de nascimento: {data_nascimento.strftime('%d/%m/%Y')}\n"
        f"Hora: {hora_nascimento}\n"
        f"Cidade: {cidade}\n\n"
        f"Formato do documento:\n"
        f"- Título: {tipo_nome} de {nome}\n"
        f"- Introdução personalizada (2-3 parágrafos)\n"
        f"- Para cada planeta/ aspecto relevante, um parágrafo explicando\n"
        f"- Linguagem acolhedora e mística, mas com conteúdo real\n"
        f"- Incluir: Sol, Lua, Ascendente, Mercúrio, Vênus, Marte, Júpiter, Saturno\n"
        f"- Fechamento com mensagem de empoderamento\n"
        f"- Entre 3.000 e 5.000 caracteres\n\n"
        f"IMPORTANTE: Retorne APENAS o texto do mapa astral, sem formatação especial."
    )

    payload = json.dumps({
        "model": settings.llm_model_text,
        "messages": [
            {
                "role": "system",
                "content": "Você é um astrólogo profissional que gera mapas astrais detalhados e precisos.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 2048,
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
            result = json.loads(resp.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            return content.strip()
    except Exception as e:
        logger.error(f"Erro ao gerar mapa astral via LLM: {e}")
        return (
            f"✨ {tipo_nome} de {nome} ✨\n\n"
            f"Olá, {nome}! Seu mapa astral está sendo preparado com todo carinho.\n\n"
            f"Esta é uma prévia do seu {tipo_nome}. A versão completa será enviada "
            f"em breve após a confirmação do pagamento.\n\n"
            f"A AstroDicas agradece sua confiança! 🌟"
        )


def gerar_mapa_pdf(
    nome: str,
    signo: str,
    data_nascimento: date,
    hora_nascimento: str,
    cidade: str,
    tipo: str = "astral",
) -> Optional[str]:
    """Gera o PDF do mapa astral e retorna o caminho do arquivo.

    Retorna None em caso de erro.
    """
    try:
        from fpdf import FPDF

        # Gerar conteúdo
        conteudo = _gerar_interpretacao_llm(
            nome=nome,
            signo=signo,
            data_nascimento=data_nascimento,
            hora_nascimento=hora_nascimento,
            cidade=cidade,
            tipo=tipo,
        )

        # Criar PDF
        pdf = FPDF()
        pdf.add_page()

        # Fonte
        pdf.add_font("DejaVu", "", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", uni=True)
        pdf.add_font("DejaVu", "B", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", uni=True)

        # Título
        tipo_nome = {
            "astral": "Mapa Astral Completo",
            "sinastria": "Sinastria (Amor)",
            "carreira": "Mapa da Carreira",
            "revolucao": "Revolução Solar",
        }.get(tipo, "Mapa Astral")

        pdf.set_font("DejaVu", "B", 18)
        pdf.cell(0, 15, f"{tipo_nome}", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_font("DejaVu", "", 12)
        pdf.cell(0, 10, f"de {nome}", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(10)

        # Info
        pdf.set_font("DejaVu", "", 10)
        pdf.cell(0, 7, f"Signo: {signo}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 7, f"Nascimento: {data_nascimento.strftime('%d/%m/%Y')} às {hora_nascimento}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 7, f"Cidade: {cidade}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(10)

        # Conteúdo
        pdf.set_font("DejaVu", "", 11)
        # Quebrar em parágrafos
        paragrafos = conteudo.split("\n")
        for par in paragrafos:
            par = par.strip()
            if par:
                # Verificar se tem negrito (**texto**)
                if par.startswith("**") and par.endswith("**"):
                    par = par.strip("*")
                    pdf.set_font("DejaVu", "B", 12)
                    pdf.cell(0, 8, par, new_x="LMARGIN", new_y="NEXT")
                    pdf.set_font("DejaVu", "", 11)
                else:
                    pdf.multi_cell(0, 6, par)
                pdf.ln(2)

        # Footer
        pdf.ln(10)
        pdf.set_font("DejaVu", "", 8)
        pdf.cell(0, 5, "Gerado por AstroDicas - astrodicas.inovalabx.com.br", new_x="LMARGIN", new_y="NEXT", align="C")

        # Salvar
        os.makedirs("/tmp/mapas_astrais", exist_ok=True)
        filename = f"/tmp/mapas_astrais/mapa_{nome.lower().replace(' ', '_')}_{date.today().isoformat()}.pdf"
        pdf.output(filename)
        logger.info(f"📄 PDF gerado: {filename}")
        return filename

    except ImportError:
        logger.warning("fpdf2 não instalado — pulando geração de PDF")
        return None
    except Exception as e:
        logger.error(f"Erro ao gerar PDF: {e}")
        return None
