# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
import unicodedata

from .modelos import AvaliacaoDeCoordenadas, AvaliacaoDeTabela

_PAR_XY_RE = re.compile(
    r"\bX\s*[:=]\s*-?\d{3,}(?:[.,]\d+)?\s*[,; ]+\s*Y\s*[:=]\s*-?\d{3,}(?:[.,]\d+)?",
    re.IGNORECASE,
)
_PAR_LAT_LONG_RE = re.compile(
    r"\b(?:LAT(?:ITUDE)?|NORTE)\s*[:=]?\s*-?\d{1,3}(?:[.,]\d+)?"
    r".{0,40}?\b(?:LONG(?:ITUDE)?|LESTE)\s*[:=]?\s*-?\d{1,3}(?:[.,]\d+)?",
    re.IGNORECASE,
)
_NUMERO_COORDENADA_RE = re.compile(r"(?<!\d)-?\d{4,7}(?:[.,]\d{2,})?(?!\d)")
_PADROES_PALAVRAS_CHAVE = {
    "coordenada": re.compile(r"\bCOORDENAD"),
    "vertice": re.compile(r"\bVERTICE"),
    "utm": re.compile(r"\bUTM\b"),
    "sirgas": re.compile(r"\bSIRGAS\b"),
    "azimute": re.compile(r"\bAZIMUTE\b"),
    "norte_leste": re.compile(r"\b(?:NORTE|LESTE)\b"),
    "poligono": re.compile(r"\bPOLIGONO\b"),
    "distancia": re.compile(r"\bDISTANCIA\b"),
}


def _maiusculas_sem_acentos(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(
        caractere
        for caractere in decomposto
        if not unicodedata.combining(caractere)
    ).upper()


def avaliar_registro_de_coordenadas(texto: str) -> AvaliacaoDeCoordenadas:
    """Identifica memoriais e sequências estruturadas de coordenadas."""

    texto_normalizado = _maiusculas_sem_acentos(texto)
    pares_xy = len(_PAR_XY_RE.findall(texto_normalizado))
    pares_lat_long = len(_PAR_LAT_LONG_RE.findall(texto_normalizado))
    quantidade_pares = pares_xy + pares_lat_long
    quantidade_numeros = len(_NUMERO_COORDENADA_RE.findall(texto_normalizado))
    palavras_encontradas = [
        rotulo
        for rotulo, padrao in _PADROES_PALAVRAS_CHAVE.items()
        if padrao.search(texto_normalizado)
    ]

    pontuacao = 0
    motivos: list[str] = []
    if quantidade_pares:
        pontuacao += min(quantidade_pares, 10) * 2
        motivos.append(f"{quantidade_pares} pares explícitos de coordenadas")
    if quantidade_numeros >= 8:
        pontuacao += min(quantidade_numeros // 4, 8)
        motivos.append("sequência extensa de números com formato de coordenada")
    if palavras_encontradas:
        pontuacao += min(len(palavras_encontradas), 5)
        motivos.append("vocabulário geodésico ou de memorial descritivo")

    detectado = (
        quantidade_pares >= 4
        or (quantidade_numeros >= 12 and len(palavras_encontradas) >= 2)
        or (
            quantidade_pares >= 2
            and quantidade_numeros >= 8
            and len(palavras_encontradas) >= 1
        )
    )

    return AvaliacaoDeCoordenadas(
        detected=detectado,
        score=pontuacao,
        pair_count=quantidade_pares,
        numeric_coordinate_count=quantidade_numeros,
        keyword_hits=palavras_encontradas,
        reasons=motivos,
    )


def deve_classificar_como_registro_de_coordenadas(
    avaliacao: AvaliacaoDeCoordenadas,
    avaliacao_de_tabela: AvaliacaoDeTabela | None = None,
    *,
    grade_visual_forte: bool = False,
) -> bool:
    """Resolve conflito entre coordenadas e tabela com precedência conservadora."""

    if not avaliacao.detected:
        return False
    if grade_visual_forte:
        return False
    if avaliacao_de_tabela is None:
        return True
    if avaliacao_de_tabela.visual_grid_strong:
        return False

    tabela_textual_forte = (
        avaliacao_de_tabela.classification == "confirmed"
        and avaliacao_de_tabela.stable_columns >= 3
        and (
            len(avaliacao_de_tabela.header_hits) >= 2
            or len(avaliacao_de_tabela.urban_parameter_hits) >= 2
            or avaliacao_de_tabela.row_count >= 4
        )
    )
    return not tabela_textual_forte


__all__ = [
    "avaliar_registro_de_coordenadas",
    "deve_classificar_como_registro_de_coordenadas",
]
