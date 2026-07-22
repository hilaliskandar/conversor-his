# SPDX-License-Identifier: MIT
"""Compatibilidade temporária com a API anterior em inglês."""

from .visual_mapa import (
    AvaliacaoVisualDeMapa as MapVisualAssessment,
    avaliar_visual_de_mapa as assess_map_visual,
)

__all__ = ["MapVisualAssessment", "assess_map_visual"]
