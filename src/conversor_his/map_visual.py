# SPDX-License-Identifier: MIT
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class MapVisualAssessment:
    visual_complexity: bool
    cover_like: bool
    ink_ratio: float
    edge_ratio: float
    component_count: int
    reasons: tuple[str, ...]


def assess_map_visual(image: Any) -> MapVisualAssessment:
    """Distingue página cartográfica ocupada de capa predominantemente vazia.

    A função não interpreta o mapa. Ela mede ocupação, bordas e componentes para
    apoiar a separação entre mapa efetivo e página de abertura de anexo.
    """

    try:
        import cv2
        import numpy as np
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "A análise cartográfica requer opencv-python-headless e numpy."
        ) from exc

    rgb = np.asarray(image.convert("RGB"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    height, width = gray.shape

    # Ignora faixa periférica, onde cabeçalhos e números de página predominam.
    y0, y1 = round(height * 0.05), round(height * 0.95)
    x0, x1 = round(width * 0.04), round(width * 0.96)
    core = gray[y0:y1, x0:x1]

    binary = cv2.threshold(core, 225, 255, cv2.THRESH_BINARY_INV)[1]
    ink_ratio = float(cv2.countNonZero(binary)) / float(max(binary.size, 1))

    edges = cv2.Canny(core, 80, 180)
    edge_ratio = float(cv2.countNonZero(edges)) / float(max(edges.size, 1))

    count, _, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    minimum_area = max(8, round(binary.size * 0.00002))
    component_count = sum(
        int(stats[index, cv2.CC_STAT_AREA]) >= minimum_area
        for index in range(1, count)
    )

    visual_complexity = (
        ink_ratio >= 0.055
        and edge_ratio >= 0.012
        and component_count >= 18
    ) or (
        ink_ratio >= 0.09
        and component_count >= 12
    )
    cover_like = (
        ink_ratio <= 0.035
        or component_count <= 8
        or (ink_ratio <= 0.05 and edge_ratio <= 0.010)
    )

    reasons: list[str] = []
    if visual_complexity:
        reasons.append("ocupação gráfica e diversidade de componentes compatíveis com mapa")
    if cover_like:
        reasons.append("baixa ocupação gráfica compatível com capa ou folha de abertura")

    return MapVisualAssessment(
        visual_complexity=visual_complexity,
        cover_like=cover_like,
        ink_ratio=round(ink_ratio, 6),
        edge_ratio=round(edge_ratio, 6),
        component_count=component_count,
        reasons=tuple(reasons),
    )
