# SPDX-License-Identifier: MIT
"""Análise visual cartográfica com API pública em português."""

from .map_visual import (
    MapVisualAssessment as AvaliacaoVisualDeMapa,
    assess_map_visual as avaliar_visual_de_mapa,
)

__all__ = ["AvaliacaoVisualDeMapa", "avaliar_visual_de_mapa"]
