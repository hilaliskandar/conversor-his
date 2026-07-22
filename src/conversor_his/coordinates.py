# SPDX-License-Identifier: MIT
"""Compatibilidade temporária com a API anterior em inglês."""

from __future__ import annotations

from .coordenadas import (
    avaliar_registro_de_coordenadas,
    deve_classificar_como_registro_de_coordenadas,
)
from .models import CoordinateAssessment, TableAssessment


def assess_coordinate_register(text: str) -> CoordinateAssessment:
    return avaliar_registro_de_coordenadas(text)


def should_classify_coordinate_register(
    assessment: CoordinateAssessment,
    table_assessment: TableAssessment | None = None,
    *,
    visual_grid_strong: bool = False,
) -> bool:
    return deve_classificar_como_registro_de_coordenadas(
        assessment,
        table_assessment,
        grade_visual_forte=visual_grid_strong,
    )


__all__ = [
    "assess_coordinate_register",
    "should_classify_coordinate_register",
]
