# SPDX-License-Identifier: MIT
"""Compatibilidade temporária com a API visual raster anterior em inglês."""

from .visual_raster import (
    AvaliacaoVisualRaster as RasterVisualAssessment,
    avaliar_visual_raster as _avaliar_visual_raster,
)


def assess_raster_visual(
    image,
    text: str = "",
    *,
    allow_partial_context: bool = False,
    mask_page_edges: bool = True,
) -> RasterVisualAssessment:
    return _avaliar_visual_raster(
        image,
        text,
        permitir_contexto_parcial=allow_partial_context,
        mascarar_bordas_da_pagina=mask_page_edges,
    )


__all__ = ["RasterVisualAssessment", "assess_raster_visual"]
