# SPDX-License-Identifier: MIT
"""Compatibilidade temporária com a API anterior em inglês."""

from .tabelas import (
    AvaliacaoDeTabela as TableAssessment,
    ClassificacaoDeTabela as TableClassification,
    avaliar_tabela as _avaliar_tabela,
    extrair_titulo_de_tabela as _extrair_titulo_de_tabela,
    salvar_imagem_de_tabela as _salvar_imagem_de_tabela,
)


def assess_table(text: str) -> TableAssessment:
    return _avaliar_tabela(text)


def extract_table_title(text: str, page_number: int) -> str:
    return _extrair_titulo_de_tabela(text, numero_pagina=page_number)


def save_table_image(
    pdf_path,
    page_number: int,
    assets_dir,
    dpi: int = 200,
):
    return _salvar_imagem_de_tabela(
        pdf_path,
        page_number,
        assets_dir,
        dpi=dpi,
    )


__all__ = [
    "TableAssessment",
    "TableClassification",
    "assess_table",
    "extract_table_title",
    "save_table_image",
]
