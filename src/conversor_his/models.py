# SPDX-License-Identifier: MIT
"""Compatibilidade temporária com os modelos da API 0.7."""

from .modelos import (
    AvaliacaoDeCoordenadas as CoordinateAssessment,
    AvaliacaoDeTabela as TableAssessment,
    AvaliacaoVisualRaster as RasterVisualAssessment,
    ClasseDeConteudoVisual as VisualContentClass,
    ClassificacaoDeTabela as TableClassification,
    DiagnosticoDeDocumento as DocumentDiagnosis,
    DiagnosticoDePagina as PageDiagnosis,
    GraficoRepetido as RepeatedGraphic,
    ManifestoDeConversao as ConversionManifest,
    NivelDeQualidadeOCR as OcrQualityLevel,
    QualidadeOCR as OcrQuality,
    ResultadoDeConversao as ConversionResult,
    RotaDePagina as PageRoute,
    TipoDePagina as PageType,
)

__all__ = [
    "ConversionManifest",
    "ConversionResult",
    "CoordinateAssessment",
    "DocumentDiagnosis",
    "OcrQuality",
    "OcrQualityLevel",
    "PageDiagnosis",
    "PageRoute",
    "PageType",
    "RasterVisualAssessment",
    "RepeatedGraphic",
    "TableAssessment",
    "TableClassification",
    "VisualContentClass",
]
