# SPDX-License-Identifier: MIT
"""Modelos centrais do Conversor HIS com nomenclatura em português.

Os valores categóricos permanecem estáveis para preservar a interoperabilidade
com manifestos e regras anteriores. Durante a transição para a versão 0.8, os
construtores aceitam também os nomes ingleses e propriedades de compatibilidade
permitem que consumidores da API 0.7 continuem funcionando.
"""

from __future__ import annotations

from dataclasses import MISSING, dataclass, field, fields
from pathlib import Path
from typing import Any, Literal

from .tabelas import AvaliacaoDeTabela, ClassificacaoDeTabela
from .visual_raster import AvaliacaoVisualRaster, ClasseDeConteudoVisual

RotaDePagina = Literal[
    "native",
    "ocr",
    "map",
    "structured",
    "decorative",
    "hybrid",
    "manual",
]
TipoDePagina = Literal[
    "text",
    "map",
    "map_candidate",
    "map_confirmed",
    "map_cover",
    "table",
    "table_candidate",
    "raster_table_candidate",
    "diagram_candidate",
    "coordinate_register",
    "ocr_review",
    "decorative_only",
    "back_cover",
    "unknown",
]
NivelDeQualidadeOCR = Literal["high", "medium", "low"]


def _propriedade_alias(nome_campo: str) -> property:
    def obter(instancia: Any) -> Any:
        return getattr(instancia, nome_campo)

    def definir(instancia: Any, valor: Any) -> None:
        setattr(instancia, nome_campo, valor)

    return property(obter, definir)


def _inicializar_modelo(
    instancia: Any,
    argumentos: tuple[Any, ...],
    nomeados: dict[str, Any],
    aliases: dict[str, str],
) -> None:
    campos = list(fields(instancia))
    if len(argumentos) > len(campos):
        raise TypeError(
            f"{type(instancia).__name__} recebeu argumentos posicionais em excesso"
        )

    valores = dict(nomeados)
    for nome_antigo, nome_novo in aliases.items():
        if nome_antigo not in valores:
            continue
        if nome_novo in valores:
            raise TypeError(
                f"use apenas um entre {nome_antigo!r} e {nome_novo!r}"
            )
        valores[nome_novo] = valores.pop(nome_antigo)

    for campo, valor in zip(campos, argumentos, strict=False):
        if campo.name in valores:
            raise TypeError(f"valor duplicado para {campo.name!r}")
        valores[campo.name] = valor

    nomes_validos = {campo.name for campo in campos}
    desconhecidos = sorted(set(valores) - nomes_validos)
    if desconhecidos:
        nomes = ", ".join(desconhecidos)
        raise TypeError(f"parâmetros desconhecidos: {nomes}")

    for campo in campos:
        if campo.name in valores:
            valor = valores[campo.name]
        elif campo.default is not MISSING:
            valor = campo.default
        elif campo.default_factory is not MISSING:
            valor = campo.default_factory()
        else:
            raise TypeError(f"parâmetro obrigatório ausente: {campo.name!r}")
        object.__setattr__(instancia, campo.name, valor)


@dataclass(slots=True, init=False)
class GraficoRepetido:
    id_grafico: str
    sha256: str
    ocorrencias: int
    quantidade_paginas: int
    proporcao_paginas: float
    posicao: str
    caixa_delimitadora_mediana: list[float]
    proporcao_area_maxima: float
    classificacao: str = "decorative"
    acao: str = "ignored_for_routing"

    _ALIASES = {
        "graphic_id": "id_grafico",
        "occurrences": "ocorrencias",
        "page_count": "quantidade_paginas",
        "page_ratio": "proporcao_paginas",
        "position": "posicao",
        "median_bbox": "caixa_delimitadora_mediana",
        "max_area_ratio": "proporcao_area_maxima",
        "classification": "classificacao",
        "action": "acao",
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        _inicializar_modelo(self, args, kwargs, self._ALIASES)

    graphic_id = _propriedade_alias("id_grafico")
    occurrences = _propriedade_alias("ocorrencias")
    page_count = _propriedade_alias("quantidade_paginas")
    page_ratio = _propriedade_alias("proporcao_paginas")
    position = _propriedade_alias("posicao")
    median_bbox = _propriedade_alias("caixa_delimitadora_mediana")
    max_area_ratio = _propriedade_alias("proporcao_area_maxima")
    classification = _propriedade_alias("classificacao")
    action = _propriedade_alias("acao")


@dataclass(slots=True, init=False)
class QualidadeOCR:
    quantidade_caracteres: int
    quantidade_palavras: int
    proporcao_alfanumerica: float
    confianca_media: float | None
    qualidade: NivelDeQualidadeOCR
    requer_revisao: bool
    motivos: list[str] = field(default_factory=list)

    _ALIASES = {
        "character_count": "quantidade_caracteres",
        "word_count": "quantidade_palavras",
        "alphanumeric_ratio": "proporcao_alfanumerica",
        "mean_confidence": "confianca_media",
        "quality": "qualidade",
        "requires_review": "requer_revisao",
        "reasons": "motivos",
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        _inicializar_modelo(self, args, kwargs, self._ALIASES)

    character_count = _propriedade_alias("quantidade_caracteres")
    word_count = _propriedade_alias("quantidade_palavras")
    alphanumeric_ratio = _propriedade_alias("proporcao_alfanumerica")
    mean_confidence = _propriedade_alias("confianca_media")
    quality = _propriedade_alias("qualidade")
    requires_review = _propriedade_alias("requer_revisao")
    reasons = _propriedade_alias("motivos")


@dataclass(slots=True, init=False)
class AvaliacaoDeCoordenadas:
    detectado: bool
    pontuacao: int
    quantidade_pares: int
    quantidade_coordenadas_numericas: int
    ocorrencias_palavras_chave: list[str] = field(default_factory=list)
    motivos: list[str] = field(default_factory=list)

    _ALIASES = {
        "detected": "detectado",
        "score": "pontuacao",
        "pair_count": "quantidade_pares",
        "numeric_coordinate_count": "quantidade_coordenadas_numericas",
        "keyword_hits": "ocorrencias_palavras_chave",
        "reasons": "motivos",
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        _inicializar_modelo(self, args, kwargs, self._ALIASES)

    detected = _propriedade_alias("detectado")
    score = _propriedade_alias("pontuacao")
    pair_count = _propriedade_alias("quantidade_pares")
    numeric_coordinate_count = _propriedade_alias(
        "quantidade_coordenadas_numericas"
    )
    keyword_hits = _propriedade_alias("ocorrencias_palavras_chave")
    reasons = _propriedade_alias("motivos")


@dataclass(slots=True, init=False)
class DiagnosticoDePagina:
    numero_pagina: int
    tem_texto_nativo: bool
    quantidade_caracteres: int
    quantidade_imagens: int
    quantidade_imagens_brutas: int = 0
    quantidade_imagens_decorativas: int = 0
    quantidade_imagens_de_conteudo: int = 0
    suspeita_tabela: bool = False
    suspeita_mapa: bool = False
    tipo_pagina: TipoDePagina = "unknown"
    rota: RotaDePagina = "native"
    avisos: list[str] = field(default_factory=list)
    qualidade_ocr: QualidadeOCR | None = None
    avaliacao_tabela: AvaliacaoDeTabela | None = None
    avaliacao_coordenadas: AvaliacaoDeCoordenadas | None = None
    avaliacao_visual_raster: AvaliacaoVisualRaster | None = None
    modo_extracao_nativa: str = "layout"
    quantidade_caracteres_layout: int = 0
    quantidade_caracteres_simples: int = 0
    texto_rotacionado_detectado: bool = False
    avisos_extracao: list[str] = field(default_factory=list)
    texto_visual_preservado: bool = False
    imagem_revisao_preservada: bool = False

    _ALIASES = {
        "page_number": "numero_pagina",
        "has_native_text": "tem_texto_nativo",
        "character_count": "quantidade_caracteres",
        "image_count": "quantidade_imagens",
        "raw_image_count": "quantidade_imagens_brutas",
        "decorative_image_count": "quantidade_imagens_decorativas",
        "content_image_count": "quantidade_imagens_de_conteudo",
        "suspected_table": "suspeita_tabela",
        "suspected_map": "suspeita_mapa",
        "page_type": "tipo_pagina",
        "route": "rota",
        "warnings": "avisos",
        "ocr_quality": "qualidade_ocr",
        "table_assessment": "avaliacao_tabela",
        "coordinate_assessment": "avaliacao_coordenadas",
        "raster_visual_assessment": "avaliacao_visual_raster",
        "native_extraction_mode": "modo_extracao_nativa",
        "layout_character_count": "quantidade_caracteres_layout",
        "simple_character_count": "quantidade_caracteres_simples",
        "rotated_text_detected": "texto_rotacionado_detectado",
        "extraction_warnings": "avisos_extracao",
        "preserved_visual_text": "texto_visual_preservado",
        "preserved_review_image": "imagem_revisao_preservada",
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        _inicializar_modelo(self, args, kwargs, self._ALIASES)

    page_number = _propriedade_alias("numero_pagina")
    has_native_text = _propriedade_alias("tem_texto_nativo")
    character_count = _propriedade_alias("quantidade_caracteres")
    image_count = _propriedade_alias("quantidade_imagens")
    raw_image_count = _propriedade_alias("quantidade_imagens_brutas")
    decorative_image_count = _propriedade_alias("quantidade_imagens_decorativas")
    content_image_count = _propriedade_alias("quantidade_imagens_de_conteudo")
    suspected_table = _propriedade_alias("suspeita_tabela")
    suspected_map = _propriedade_alias("suspeita_mapa")
    page_type = _propriedade_alias("tipo_pagina")
    route = _propriedade_alias("rota")
    warnings = _propriedade_alias("avisos")
    ocr_quality = _propriedade_alias("qualidade_ocr")
    table_assessment = _propriedade_alias("avaliacao_tabela")
    coordinate_assessment = _propriedade_alias("avaliacao_coordenadas")
    raster_visual_assessment = _propriedade_alias("avaliacao_visual_raster")
    native_extraction_mode = _propriedade_alias("modo_extracao_nativa")
    layout_character_count = _propriedade_alias("quantidade_caracteres_layout")
    simple_character_count = _propriedade_alias("quantidade_caracteres_simples")
    rotated_text_detected = _propriedade_alias("texto_rotacionado_detectado")
    extraction_warnings = _propriedade_alias("avisos_extracao")
    preserved_visual_text = _propriedade_alias("texto_visual_preservado")
    preserved_review_image = _propriedade_alias("imagem_revisao_preservada")


@dataclass(slots=True, init=False)
class DiagnosticoDeDocumento:
    caminho_origem: Path | str
    sha256: str
    quantidade_paginas: int
    paginas: list[DiagnosticoDePagina]
    graficos_repetidos: list[GraficoRepetido] = field(default_factory=list)

    _ALIASES = {
        "source_path": "caminho_origem",
        "page_count": "quantidade_paginas",
        "pages": "paginas",
        "repeated_graphics": "graficos_repetidos",
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        _inicializar_modelo(self, args, kwargs, self._ALIASES)

    source_path = _propriedade_alias("caminho_origem")
    page_count = _propriedade_alias("quantidade_paginas")
    pages = _propriedade_alias("paginas")
    repeated_graphics = _propriedade_alias("graficos_repetidos")


@dataclass(slots=True, init=False)
class ManifestoDeConversao:
    caminho_origem: Path | str
    sha256_origem: str
    quantidade_paginas: int
    caminho_markdown: Path
    sha256_markdown: str
    tamanho_markdown_bytes: int
    caminhos_recursos: list[Path]
    paginas_com_ocr: list[int]
    paginas_de_mapa: list[int]
    paginas_de_tabela: list[int]
    paginas_candidatas_a_tabela: list[int]
    paginas_decorativas: list[int]
    paginas_para_revisao: list[int]
    dpi: int
    versao_conversor: str
    diagnostico: DiagnosticoDeDocumento
    paginas_com_texto_rotacionado: list[int] = field(default_factory=list)
    paginas_com_texto_visual_preservado: list[int] = field(default_factory=list)
    paginas_de_tabela_raster: list[int] = field(default_factory=list)
    paginas_de_diagrama: list[int] = field(default_factory=list)
    paginas_de_registro_de_coordenadas: list[int] = field(default_factory=list)
    paginas_candidatas_a_mapa: list[int] = field(default_factory=list)
    paginas_de_capa_de_mapa: list[int] = field(default_factory=list)
    paginas_com_imagem_de_revisao_ocr: list[int] = field(default_factory=list)
    segundos_de_processamento: float | None = None

    _ALIASES = {
        "source_path": "caminho_origem",
        "source_sha256": "sha256_origem",
        "page_count": "quantidade_paginas",
        "markdown_path": "caminho_markdown",
        "markdown_sha256": "sha256_markdown",
        "markdown_size_bytes": "tamanho_markdown_bytes",
        "asset_paths": "caminhos_recursos",
        "used_ocr_pages": "paginas_com_ocr",
        "map_pages": "paginas_de_mapa",
        "table_pages": "paginas_de_tabela",
        "table_candidate_pages": "paginas_candidatas_a_tabela",
        "decorative_pages": "paginas_decorativas",
        "review_pages": "paginas_para_revisao",
        "converter_version": "versao_conversor",
        "diagnosis": "diagnostico",
        "rotated_text_pages": "paginas_com_texto_rotacionado",
        "visual_text_preserved_pages": "paginas_com_texto_visual_preservado",
        "raster_table_pages": "paginas_de_tabela_raster",
        "diagram_pages": "paginas_de_diagrama",
        "coordinate_register_pages": "paginas_de_registro_de_coordenadas",
        "map_candidate_pages": "paginas_candidatas_a_mapa",
        "map_cover_pages": "paginas_de_capa_de_mapa",
        "ocr_review_image_pages": "paginas_com_imagem_de_revisao_ocr",
        "processing_seconds": "segundos_de_processamento",
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        _inicializar_modelo(self, args, kwargs, self._ALIASES)

    source_path = _propriedade_alias("caminho_origem")
    source_sha256 = _propriedade_alias("sha256_origem")
    page_count = _propriedade_alias("quantidade_paginas")
    markdown_path = _propriedade_alias("caminho_markdown")
    markdown_sha256 = _propriedade_alias("sha256_markdown")
    markdown_size_bytes = _propriedade_alias("tamanho_markdown_bytes")
    asset_paths = _propriedade_alias("caminhos_recursos")
    used_ocr_pages = _propriedade_alias("paginas_com_ocr")
    map_pages = _propriedade_alias("paginas_de_mapa")
    table_pages = _propriedade_alias("paginas_de_tabela")
    table_candidate_pages = _propriedade_alias("paginas_candidatas_a_tabela")
    decorative_pages = _propriedade_alias("paginas_decorativas")
    review_pages = _propriedade_alias("paginas_para_revisao")
    converter_version = _propriedade_alias("versao_conversor")
    diagnosis = _propriedade_alias("diagnostico")
    rotated_text_pages = _propriedade_alias("paginas_com_texto_rotacionado")
    visual_text_preserved_pages = _propriedade_alias(
        "paginas_com_texto_visual_preservado"
    )
    raster_table_pages = _propriedade_alias("paginas_de_tabela_raster")
    diagram_pages = _propriedade_alias("paginas_de_diagrama")
    coordinate_register_pages = _propriedade_alias(
        "paginas_de_registro_de_coordenadas"
    )
    map_candidate_pages = _propriedade_alias("paginas_candidatas_a_mapa")
    map_cover_pages = _propriedade_alias("paginas_de_capa_de_mapa")
    ocr_review_image_pages = _propriedade_alias(
        "paginas_com_imagem_de_revisao_ocr"
    )
    processing_seconds = _propriedade_alias("segundos_de_processamento")


@dataclass(slots=True, init=False)
class ResultadoDeConversao:
    caminho_origem: Path | str
    diretorio_saida: Path
    caminho_markdown: Path
    caminho_manifesto: Path
    paginas_com_ocr: list[int]
    avisos: list[str] = field(default_factory=list)

    _ALIASES = {
        "source_path": "caminho_origem",
        "output_dir": "diretorio_saida",
        "markdown_path": "caminho_markdown",
        "manifest_path": "caminho_manifesto",
        "used_ocr_pages": "paginas_com_ocr",
        "warnings": "avisos",
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        _inicializar_modelo(self, args, kwargs, self._ALIASES)

    source_path = _propriedade_alias("caminho_origem")
    output_dir = _propriedade_alias("diretorio_saida")
    markdown_path = _propriedade_alias("caminho_markdown")
    manifest_path = _propriedade_alias("caminho_manifesto")
    used_ocr_pages = _propriedade_alias("paginas_com_ocr")
    warnings = _propriedade_alias("avisos")


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
