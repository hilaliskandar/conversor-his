# SPDX-License-Identifier: MIT
"""Modelos públicos com nomenclatura em português.

Durante a migração para a versão 0.8, os tipos antigos continuam disponíveis em
``models.py``. Este módulo define a API principal em português e mantém
identidade de classe com os modelos existentes para não alterar a serialização.
"""

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
    RasterVisualAssessment as AvaliacaoVisualRaster,
    RepeatedGraphic as GraficoRepetido,
    TableAssessment as AvaliacaoDeTabela,
    TableClassification as ClassificacaoDeTabela,
    VisualContentClass as ClasseDeConteudoVisual,
)

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
