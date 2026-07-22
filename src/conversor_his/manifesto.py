# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ALIASES_DE_CAMPOS = {
    "generated_at": "gerado_em",
    "updated_at": "atualizado_em",
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
    "pages": "paginas",
    "repeated_graphics": "graficos_repetidos",
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
    "graphic_id": "id_grafico",
    "occurrences": "ocorrencias",
    "page_ratio": "proporcao_paginas",
    "position": "posicao",
    "median_bbox": "caixa_delimitadora_mediana",
    "max_area_ratio": "proporcao_area_maxima",
    "action": "acao",
    "word_count": "quantidade_palavras",
    "alphanumeric_ratio": "proporcao_alfanumerica",
    "mean_confidence": "confianca_media",
    "quality": "qualidade",
    "requires_review": "requer_revisao",
    "detected": "detectado",
    "score": "pontuacao",
    "pair_count": "quantidade_pares",
    "numeric_coordinate_count": "quantidade_coordenadas_numericas",
    "keyword_hits": "ocorrencias_palavras_chave",
    "classification": "classificacao",
    "suspected": "suspeita",
    "row_count": "quantidade_linhas",
    "stable_columns": "colunas_estaveis",
    "header_hits": "ocorrencias_cabecalho",
    "reasons": "motivos",
    "header_line_index": "indice_linha_cabecalho",
    "legal_list_ratio": "proporcao_lista_legal",
    "prose_ratio": "proporcao_prosa",
    "numeric_rows": "linhas_numericas",
    "compact_value_rows": "linhas_valores_compactos",
    "multi_column_lines": "linhas_multicoluna",
    "urban_parameter_hits": "ocorrencias_parametros_urbanos",
    "zone_code_count": "quantidade_codigos_zona",
    "content_profile": "perfil_conteudo",
    "visual_grid_detected": "grade_visual_detectada",
    "visual_grid_strong": "grade_visual_forte",
    "visual_grid_score": "pontuacao_grade_visual",
    "vector_rectangle_count": "quantidade_retangulos_vetoriais",
    "vector_horizontal_lines": "linhas_vetoriais_horizontais",
    "vector_vertical_lines": "linhas_vetoriais_verticais",
    "strong": "forte",
    "horizontal_lines": "linhas_horizontais",
    "vertical_lines": "linhas_verticais",
    "intersections": "intersecoes",
    "closed_regions": "regioes_fechadas",
    "structured_area_ratio": "proporcao_area_estruturada",
    "arrow_like_components": "componentes_semelhantes_a_seta",
    "partial_grid_detected": "grade_parcial_detectada",
    "contextual_continuation": "continuacao_contextual",
    "recurrent_mask_applied": "mascara_recorrente_aplicada",
    "table_text_evidence": "evidencia_textual_tabela",
    "diagram_text_evidence": "evidencia_textual_diagrama",
}


def _preparar_para_json(valor: Any) -> Any:
    if is_dataclass(valor):
        return _preparar_para_json(asdict(valor))
    if isinstance(valor, Path):
        return str(valor)
    if isinstance(valor, dict):
        return {chave: _preparar_para_json(item) for chave, item in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_preparar_para_json(item) for item in valor]
    return valor


def _normalizar_campos(valor: Any) -> Any:
    if isinstance(valor, list):
        return [_normalizar_campos(item) for item in valor]
    if not isinstance(valor, dict):
        return valor

    resultado = {
        chave: _normalizar_campos(item)
        for chave, item in valor.items()
        if chave not in _ALIASES_DE_CAMPOS
    }
    for nome_antigo, nome_novo in _ALIASES_DE_CAMPOS.items():
        if nome_antigo in valor and nome_novo not in valor:
            resultado[nome_novo] = _normalizar_campos(valor[nome_antigo])
    return resultado


def ler_manifesto(
    caminho: Path,
    *,
    normalizar_campos: bool = True,
) -> Any:
    """Lê um manifesto e, por padrão, converte campos da API 0.7 para português."""

    dados = json.loads(caminho.read_text(encoding="utf-8"))
    return _normalizar_campos(dados) if normalizar_campos else dados


def escrever_manifesto(
    conteudo: Any,
    caminho_saida: Path,
    *,
    modo_compatibilidade: bool = False,
) -> None:
    """Escreve o manifesto em JSON de forma atômica.

    O modo de compatibilidade conserva os metadados temporais da API 0.7 e deve
    ser usado apenas por adaptadores ou por manifestos de lote que precisam ser
    retomados por versões anteriores.
    """

    dados = _preparar_para_json(conteudo)
    agora = datetime.now(timezone.utc).isoformat()
    if isinstance(dados, dict):
        if modo_compatibilidade:
            dados.setdefault("generated_at", agora)
            dados["updated_at"] = agora
        else:
            dados.setdefault("gerado_em", agora)
            dados["atualizado_em"] = agora

    caminho_saida.parent.mkdir(parents=True, exist_ok=True)
    caminho_temporario = caminho_saida.with_suffix(caminho_saida.suffix + ".tmp")
    caminho_temporario.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    caminho_temporario.replace(caminho_saida)


__all__ = ["escrever_manifesto", "ler_manifesto"]
