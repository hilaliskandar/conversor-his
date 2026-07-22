# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from .ocr.render import render_pdf_page

ClasseTextualDeMapa = Literal["none", "map_candidate", "map_confirmed", "map_cover"]

_PALAVRA_MAPA_RE = re.compile(
    r"\b(?:MAPA|MAPAS|PLANTA|PLANTAS|CARTA|CARTAS|CROQUI)\b",
    re.IGNORECASE,
)
_TITULO_MAPA_RE = re.compile(
    r"\b(?:MAPA|PLANTA|CARTA|CROQUI)\b(?:\s+(?:N[º°.]?\s*)?[A-Z0-9IVXLCDM.-]+)?"
    r"(?:\s*[-–—:]\s*[^\n]{1,150})?",
    re.IGNORECASE,
)
_EVIDENCIA_ESPACIAL_RE = re.compile(
    r"\b(?:ZONEAMENTO|MACROZONEAMENTO|SISTEMA\s+VI[ÁA]RIO|PER[ÍI]METRO\s+URBANO|"
    r"USO\s+E\s+OCUPA[CÇ][AÃ]O|[ÁA]REAS?\s+DE\s+RISCO)\b",
    re.IGNORECASE,
)
_EVIDENCIA_CARTOGRAFICA_RE = re.compile(
    r"\b(?:LEGENDA|ESCALA|NORTE|SIRGAS|UTM|COORDENADAS?|PROJE[CÇ][AÃ]O|DATUM|"
    r"MERIDIANO|FUSO|FONTE\s+CARTOGR[ÁA]FICA)\b",
    re.IGNORECASE,
)
_CAPA_RE = re.compile(
    r"\b(?:ANEXO\s+(?:CARTOGR[ÁA]FICO|DE\s+MAPAS?)|CADERNO\s+DE\s+MAPAS?|"
    r"[ÍI]NDICE\s+(?:DE\s+)?MAPAS?|RELA[CÇ][AÃ]O\s+DE\s+MAPAS?|"
    r"LISTA\s+DE\s+MAPAS?|MAPAS?\s+ANEXOS?|ANEXOS?\s+[-–—:]?\s*MAPAS?)\b",
    re.IGNORECASE,
)
_LAYOUT_CAPA_RE = re.compile(
    r"^(?:ANEXO|AP[EÊ]NDICE|CADERNO)\b.{0,180}$",
    re.IGNORECASE,
)


def classificar_pagina_de_mapa(
    texto: str,
    quantidade_imagens: int,
    *,
    complexidade_visual: bool = False,
    maximo_caracteres_texto: int = 700,
) -> ClasseTextualDeMapa:
    """Classifica evidência cartográfica sem confundir capa e mapa efetivo."""

    texto_normalizado = " ".join(texto.split())
    if quantidade_imagens < 1 or len(texto_normalizado) > maximo_caracteres_texto:
        return "none"

    tem_palavra_mapa = bool(
        _PALAVRA_MAPA_RE.search(texto_normalizado)
        or _EVIDENCIA_ESPACIAL_RE.search(texto_normalizado)
    )
    if not tem_palavra_mapa:
        return "none"

    tem_evidencia_cartografica = bool(
        _EVIDENCIA_CARTOGRAFICA_RE.search(texto_normalizado)
    )
    sinal_de_capa = bool(_CAPA_RE.search(texto_normalizado))
    pagina_curta_de_titulo = (
        len(texto_normalizado) <= 180
        and bool(_LAYOUT_CAPA_RE.search(texto_normalizado))
        and not tem_evidencia_cartografica
    )
    if (sinal_de_capa or pagina_curta_de_titulo) and not complexidade_visual:
        return "map_cover"

    quantidade_evidencias = sum(
        (
            bool(_PALAVRA_MAPA_RE.search(texto_normalizado)),
            bool(_EVIDENCIA_ESPACIAL_RE.search(texto_normalizado)),
            tem_evidencia_cartografica,
            complexidade_visual,
        )
    )

    if tem_evidencia_cartografica and quantidade_evidencias >= 2:
        return "map_confirmed"
    if quantidade_evidencias >= 2 and complexidade_visual:
        return "map_confirmed"
    return "map_candidate"


def pagina_e_mapa(
    texto: str,
    quantidade_imagens: int,
    maximo_caracteres_texto: int = 700,
) -> bool:
    """Indica mapa confirmado ou candidato, sem incluir capa cartográfica."""

    return classificar_pagina_de_mapa(
        texto,
        quantidade_imagens,
        maximo_caracteres_texto=maximo_caracteres_texto,
    ) in {"map_candidate", "map_confirmed"}


def extrair_titulo_de_mapa(texto: str, numero_pagina: int) -> str:
    """Extrai um título curto e estável para a referência cartográfica."""

    linhas = [" ".join(linha.split()) for linha in texto.splitlines() if linha.strip()]
    for linha in linhas:
        ocorrencia = _TITULO_MAPA_RE.search(linha)
        if ocorrencia:
            return ocorrencia.group(0).strip(" .;:-")
    for linha in linhas:
        if _EVIDENCIA_ESPACIAL_RE.search(linha):
            return linha[:160].strip(" .;:-")
    return f"Mapa da página {numero_pagina}"


def salvar_imagem_de_mapa(
    caminho_pdf: Path,
    numero_pagina: int,
    diretorio_recursos: Path,
    dpi: int = 200,
    sufixo: str = "mapa",
) -> Path:
    """Renderiza e salva a página cartográfica integralmente como PNG."""

    diretorio_recursos.mkdir(parents=True, exist_ok=True)
    caminho_imagem = diretorio_recursos / f"pagina_{numero_pagina:04d}_{sufixo}.png"
    imagem = render_pdf_page(caminho_pdf, numero_pagina, dpi=dpi)
    imagem.save(caminho_imagem, format="PNG", optimize=True)
    return caminho_imagem


__all__ = [
    "ClasseTextualDeMapa",
    "classificar_pagina_de_mapa",
    "extrair_titulo_de_mapa",
    "pagina_e_mapa",
    "salvar_imagem_de_mapa",
]
