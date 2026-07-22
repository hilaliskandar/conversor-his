# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
import unicodedata

from .models import CoordinateAssessment, TableAssessment

_XY_PAIR_RE = re.compile(
    r"\bX\s*[:=]\s*-?\d{3,}(?:[.,]\d+)?\s*[,; ]+\s*Y\s*[:=]\s*-?\d{3,}(?:[.,]\d+)?",
    re.IGNORECASE,
)
_LAT_LONG_PAIR_RE = re.compile(
    r"\b(?:LAT(?:ITUDE)?|NORTE)\s*[:=]?\s*-?\d{1,3}(?:[.,]\d+)?"
    r".{0,40}?\b(?:LONG(?:ITUDE)?|LESTE)\s*[:=]?\s*-?\d{1,3}(?:[.,]\d+)?",
    re.IGNORECASE,
)
_COORDINATE_NUMBER_RE = re.compile(r"(?<!\d)-?\d{4,7}(?:[.,]\d{2,})?(?!\d)")
_KEYWORD_PATTERNS = {
    "coordenada": re.compile(r"\bCOORDENAD"),
    "vertice": re.compile(r"\bVERTICE"),
    "utm": re.compile(r"\bUTM\b"),
    "sirgas": re.compile(r"\bSIRGAS\b"),
    "azimute": re.compile(r"\bAZIMUTE\b"),
    "norte_leste": re.compile(r"\b(?:NORTE|LESTE)\b"),
    "poligono": re.compile(r"\bPOLIGONO\b"),
    "distancia": re.compile(r"\bDISTANCIA\b"),
}


def _ascii_upper(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(
        character for character in decomposed if not unicodedata.combining(character)
    ).upper()


def assess_coordinate_register(text: str) -> CoordinateAssessment:
    """Identifica memoriais e sequências estruturadas de coordenadas.

    O objetivo não é interpretar a geometria, mas separar esses registros das
    tabelas urbanísticas para que recebam preservação visual e métricas próprias.
    """

    normalized = _ascii_upper(text)
    xy_pairs = len(_XY_PAIR_RE.findall(normalized))
    lat_long_pairs = len(_LAT_LONG_PAIR_RE.findall(normalized))
    pair_count = xy_pairs + lat_long_pairs
    numeric_coordinate_count = len(_COORDINATE_NUMBER_RE.findall(normalized))
    keyword_hits = [
        label for label, pattern in _KEYWORD_PATTERNS.items() if pattern.search(normalized)
    ]

    score = 0
    reasons: list[str] = []
    if pair_count:
        score += min(pair_count, 10) * 2
        reasons.append(f"{pair_count} pares explicitos de coordenadas")
    if numeric_coordinate_count >= 8:
        score += min(numeric_coordinate_count // 4, 8)
        reasons.append("sequencia extensa de numeros com formato de coordenada")
    if keyword_hits:
        score += min(len(keyword_hits), 5)
        reasons.append("vocabulario geodesico ou de memorial descritivo")

    detected = (
        pair_count >= 4
        or (
            numeric_coordinate_count >= 12
            and len(keyword_hits) >= 2
        )
        or (
            pair_count >= 2
            and numeric_coordinate_count >= 8
            and len(keyword_hits) >= 1
        )
    )

    return CoordinateAssessment(
        detected=detected,
        score=score,
        pair_count=pair_count,
        numeric_coordinate_count=numeric_coordinate_count,
        keyword_hits=keyword_hits,
        reasons=reasons,
    )


def should_classify_coordinate_register(
    assessment: CoordinateAssessment,
    table_assessment: TableAssessment | None = None,
    *,
    visual_grid_strong: bool = False,
) -> bool:
    """Resolve conflito entre coordenadas e tabela com precedência conservadora.

    Uma sequência geodésica continua em classe própria, exceto quando a página
    apresenta grade tabular forte ou cabeçalhos e colunas suficientemente claros.
    Isso evita converter tabelas de parâmetros que apenas mencionam UTM ou
    coordenadas em memoriais descritivos.
    """

    if not assessment.detected:
        return False
    if visual_grid_strong:
        return False
    if table_assessment is None:
        return True

    if table_assessment.visual_grid_strong:
        return False

    strong_textual_table = (
        table_assessment.classification == "confirmed"
        and table_assessment.stable_columns >= 3
        and (
            len(table_assessment.header_hits) >= 2
            or len(table_assessment.urban_parameter_hits) >= 2
            or table_assessment.row_count >= 4
        )
    )
    return not strong_textual_table
