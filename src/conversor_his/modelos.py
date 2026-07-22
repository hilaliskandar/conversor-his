# SPDX-License-Identifier: MIT
"""Modelos públicos com nomenclatura em português."""

from .models import (
    ConversionManifest as ManifestoDeConversao,
    ConversionResult as ResultadoDeConversao,
    CoordinateAssessment as AvaliacaoDeCoordenadas,
    DocumentDiagnosis as DiagnosticoDeDocumento,
    OcrQuality as QualidadeOCR,
    OcrQualityLevel as NivelDeQualidadeOCR,
    PageDiagnosis as DiagnosticoDePagina,
    PageRoute as RotaDePagina,
    PageType as TipoDePagina,
    RepeatedGraphic as GraficoRepetido,
)
from .tabelas import AvaliacaoDeTabela, ClassificacaoDeTabela
from .visual_raster import AvaliacaoVisualRaster, ClasseDeConteudoVisual

__all__ = [
    "AvaliacaoDeCoordenadas",
    "AvaliacaoDeTabela",
    "AvaliacaoVisualRaster",
    "ClasseDeConteudoVisual",
    "ClassificacaoDeTabela",
    "DiagnosticoDeDocumento",
    "DiagnosticoDePagina",
    "GraficoRepetido",
    "ManifestoDeConversao",
    "NivelDeQualidadeOCR",
    "QualidadeOCR",
    "ResultadoDeConversao",
    "RotaDePagina",
    "TipoDePagina",
]
