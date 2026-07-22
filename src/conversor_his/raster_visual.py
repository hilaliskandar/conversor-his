# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
import unicodedata
from typing import Any

from .models import RasterVisualAssessment

_DIAGRAM_TEXT_RE = re.compile(
    r"\b(?:FLUXOGRAMA|ORGANOGRAMA|DIAGRAMA|ESQUEMA|REPRESENTACAO\s+GRAFICA|"
    r"CORTE|ELEVACAO|DETALHE|PLANTA\s+BAIXA|GRAFICO)\b"
)
_TABLE_TEXT_RE = re.compile(
    r"\b(?:TABELA|QUADRO|PARAMETROS?|INDICES?|COLUNA|LINHA|TOTAL|SUBTOTAL|CONTINUACAO)\b"
)


def _ascii_upper(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(
        character for character in decomposed if not unicodedata.combining(character)
    ).upper()


def _load_cv_stack() -> tuple[Any, Any]:
    try:
        import cv2
        import numpy as np
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "A análise visual raster requer opencv-python-headless e numpy. "
            "Reinstale o projeto com: pip install -e '.[dev,ocr]'"
        ) from exc
    return cv2, np


def _component_count(mask: Any, cv2: Any, min_area: int = 3) -> int:
    count, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if count <= 1:
        return 0
    return sum(int(stats[index, cv2.CC_STAT_AREA]) >= min_area for index in range(1, count))


def assess_raster_visual(
    image: Any,
    text: str = "",
    *,
    allow_partial_context: bool = False,
    mask_page_edges: bool = True,
) -> RasterVisualAssessment:
    """Detecta tabelas e diagramas em páginas rasterizadas.

    Grades parciais são apenas evidência latente. Elas somente viram tabela quando
    ``allow_partial_context`` é ativado pelo pipeline após verificar uma página
    tabular adjacente. O mascaramento periférico reduz molduras, cabeçalhos e
    rodapés recorrentes sem alterar a imagem preservada no produto.
    """

    cv2, np = _load_cv_stack()
    rgb = np.asarray(image.convert("RGB"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    normalized_text = _ascii_upper(text)

    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        15,
    )

    height, width = binary.shape
    recurrent_mask_applied = False
    if mask_page_edges and height >= 200 and width >= 200:
        top_bottom = max(8, round(height * 0.055))
        left_right = max(8, round(width * 0.035))
        binary[:top_bottom, :] = 0
        binary[height - top_bottom :, :] = 0
        binary[:, :left_right] = 0
        binary[:, width - left_right :] = 0
        recurrent_mask_applied = True

    horizontal_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (max(20, width // 30), 1),
    )
    vertical_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (1, max(12, height // 45)),
    )

    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
    grid = cv2.bitwise_or(horizontal, vertical)
    intersections_mask = cv2.bitwise_and(horizontal, vertical)

    horizontal_lines = _component_count(horizontal, cv2, min_area=max(12, width // 80))
    vertical_lines = _component_count(vertical, cv2, min_area=max(12, height // 100))
    intersections = _component_count(intersections_mask, cv2, min_area=2)

    contours, _ = cv2.findContours(grid, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    page_area = float(max(width * height, 1))
    closed_regions = 0
    structured_area = 0.0
    box_like_regions = 0
    for contour in contours:
        _, _, box_width, box_height = cv2.boundingRect(contour)
        area = box_width * box_height
        if area < page_area * 0.0005 or area > page_area * 0.90:
            continue
        perimeter = cv2.arcLength(contour, True)
        polygon = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(polygon) == 4:
            closed_regions += 1
            structured_area += area
            if box_width >= width * 0.04 and box_height >= height * 0.025:
                box_like_regions += 1

    structured_area_ratio = min(structured_area / page_area, 1.0)
    has_diagram_text = bool(_DIAGRAM_TEXT_RE.search(normalized_text))
    has_table_text = bool(_TABLE_TEXT_RE.search(normalized_text))

    line_total = max(horizontal_lines + vertical_lines, 1)
    intersection_density = intersections / line_total
    regular_grid = intersection_density >= 1.15 and intersections >= 8

    full_table_candidate = (
        horizontal_lines >= 4
        and vertical_lines >= 3
        and intersections >= 6
        and structured_area_ratio >= 0.04
        and (regular_grid or has_table_text)
    )
    partial_grid_detected = (
        horizontal_lines >= 3
        and vertical_lines >= 2
        and intersections >= 4
        and closed_regions >= 2
        and structured_area_ratio >= 0.02
        and not has_diagram_text
    )
    contextual_partial_table = partial_grid_detected and allow_partial_context
    table_candidate = full_table_candidate or contextual_partial_table

    strong_table = (
        horizontal_lines >= 8
        and vertical_lines >= 6
        and intersections >= 20
        and structured_area_ratio >= 0.08
        and regular_grid
    )

    diagram_candidate = (
        box_like_regions >= 2
        and (horizontal_lines + vertical_lines) >= 4
        and 0.008 <= structured_area_ratio <= 0.60
        and (
            has_diagram_text
            or not regular_grid
            or intersections < max(12, box_like_regions * 4)
        )
        and not strong_table
    )

    score = 0
    reasons: list[str] = []
    classification = "none"
    detected = False
    strong = False

    if diagram_candidate and (has_diagram_text or not table_candidate):
        classification = "diagram_candidate"
        detected = True
        score = 4 + min(box_like_regions, 10)
        if has_diagram_text:
            score += 3
            reasons.append("vocabulário explícito de diagrama ou representação gráfica")
        reasons.append("caixas e conectores sem regularidade suficiente de grade tabular")
    elif table_candidate:
        classification = "raster_table_candidate"
        detected = True
        strong = strong_table
        score = 4
        score += min(horizontal_lines, 20) // 4
        score += min(vertical_lines, 20) // 3
        score += min(intersections, 40) // 8
        if has_table_text:
            score += 2
        if strong_table:
            score += 4
            reasons.append("grade raster forte com linhas e cruzamentos regulares")
        elif contextual_partial_table and not full_table_candidate:
            reasons.append("grade raster parcial promovida por continuidade contextual")
        else:
            reasons.append("grade raster candidata com estrutura celular")
    elif partial_grid_detected:
        reasons.append("grade raster parcial mantida como evidência latente sem contexto adjacente")

    return RasterVisualAssessment(
        classification=classification,
        detected=detected,
        strong=strong,
        score=score,
        horizontal_lines=horizontal_lines,
        vertical_lines=vertical_lines,
        intersections=intersections,
        closed_regions=closed_regions,
        structured_area_ratio=round(structured_area_ratio, 6),
        arrow_like_components=0,
        partial_grid_detected=partial_grid_detected,
        contextual_continuation=contextual_partial_table,
        recurrent_mask_applied=recurrent_mask_applied,
        table_text_evidence=has_table_text,
        diagram_text_evidence=has_diagram_text,
        reasons=reasons,
    )
