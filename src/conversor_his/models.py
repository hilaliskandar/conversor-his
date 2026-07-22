# SPDX-License-Identifier: MIT
"""Compatibilidade temporária com os modelos da API 0.7."""

from typing import Any

from .modelos import (
    AvaliacaoDeCoordenadas as CoordinateAssessment,
    AvaliacaoDeTabela,
    AvaliacaoVisualRaster,
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


class TableAssessment(AvaliacaoDeTabela):
    """Adaptador construtivo para a classe tabular da API 0.7."""

    def __init__(
        self,
        classification: TableClassification,
        suspected: bool,
        score: int,
        row_count: int,
        stable_columns: int,
        header_hits: list[str] | None = None,
        reasons: list[str] | None = None,
        header_line_index: int | None = None,
        legal_list_ratio: float = 0.0,
        prose_ratio: float = 0.0,
        numeric_rows: int = 0,
        compact_value_rows: int = 0,
        multi_column_lines: int = 0,
        urban_parameter_hits: list[str] | None = None,
        zone_code_count: int = 0,
        content_profile: str = "unknown",
        visual_grid_detected: bool = False,
        visual_grid_strong: bool = False,
        visual_grid_score: int = 0,
        vector_rectangle_count: int = 0,
        vector_horizontal_lines: int = 0,
        vector_vertical_lines: int = 0,
    ) -> None:
        super().__init__(
            classificacao=classification,
            suspeita=suspected,
            pontuacao=score,
            quantidade_linhas=row_count,
            colunas_estaveis=stable_columns,
            ocorrencias_cabecalho=[] if header_hits is None else header_hits,
            motivos=[] if reasons is None else reasons,
            indice_linha_cabecalho=header_line_index,
            proporcao_lista_legal=legal_list_ratio,
            proporcao_prosa=prose_ratio,
            linhas_numericas=numeric_rows,
            linhas_valores_compactos=compact_value_rows,
            linhas_multicoluna=multi_column_lines,
            ocorrencias_parametros_urbanos=(
                [] if urban_parameter_hits is None else urban_parameter_hits
            ),
            quantidade_codigos_zona=zone_code_count,
            perfil_conteudo=content_profile,
            grade_visual_detectada=visual_grid_detected,
            grade_visual_forte=visual_grid_strong,
            pontuacao_grade_visual=visual_grid_score,
            quantidade_retangulos_vetoriais=vector_rectangle_count,
            linhas_vetoriais_horizontais=vector_horizontal_lines,
            linhas_vetoriais_verticais=vector_vertical_lines,
        )

    @property
    def classification(self) -> TableClassification:
        return self.classificacao

    @classification.setter
    def classification(self, value: TableClassification) -> None:
        self.classificacao = value

    @property
    def suspected(self) -> bool:
        return self.suspeita

    @suspected.setter
    def suspected(self, value: bool) -> None:
        self.suspeita = value

    @property
    def score(self) -> int:
        return self.pontuacao

    @score.setter
    def score(self, value: int) -> None:
        self.pontuacao = value

    @property
    def reasons(self) -> list[str]:
        return self.motivos

    @reasons.setter
    def reasons(self, value: list[str]) -> None:
        self.motivos = value

    @property
    def content_profile(self) -> str:
        return self.perfil_conteudo

    @content_profile.setter
    def content_profile(self, value: str) -> None:
        self.perfil_conteudo = value


class RasterVisualAssessment(AvaliacaoVisualRaster):
    """Adaptador construtivo para a avaliação raster da API 0.7."""

    def __init__(
        self,
        classification: VisualContentClass,
        detected: bool,
        strong: bool,
        score: int,
        horizontal_lines: int,
        vertical_lines: int,
        intersections: int,
        closed_regions: int,
        structured_area_ratio: float,
        arrow_like_components: int = 0,
        partial_grid_detected: bool = False,
        contextual_continuation: bool = False,
        recurrent_mask_applied: bool = False,
        table_text_evidence: bool = False,
        diagram_text_evidence: bool = False,
        reasons: list[str] | None = None,
        **_: Any,
    ) -> None:
        super().__init__(
            classificacao=classification,
            detectado=detected,
            forte=strong,
            pontuacao=score,
            linhas_horizontais=horizontal_lines,
            linhas_verticais=vertical_lines,
            intersecoes=intersections,
            regioes_fechadas=closed_regions,
            proporcao_area_estruturada=structured_area_ratio,
            componentes_semelhantes_a_seta=arrow_like_components,
            grade_parcial_detectada=partial_grid_detected,
            continuacao_contextual=contextual_continuation,
            mascara_recorrente_aplicada=recurrent_mask_applied,
            evidencia_textual_tabela=table_text_evidence,
            evidencia_textual_diagrama=diagram_text_evidence,
            motivos=[] if reasons is None else reasons,
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
