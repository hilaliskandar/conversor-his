# SPDX-License-Identifier: MIT
"""Detecção de registros de coordenadas com API em português."""

from .coordinates import (
    assess_coordinate_register as avaliar_registro_de_coordenadas,
    should_classify_coordinate_register as deve_classificar_como_registro_de_coordenadas,
)

__all__ = [
    "avaliar_registro_de_coordenadas",
    "deve_classificar_como_registro_de_coordenadas",
]
