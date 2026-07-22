# SPDX-License-Identifier: MIT
"""Detecção e preservação de tabelas com API pública em português."""

from .tables import (
    assess_table as avaliar_tabela,
    extract_table_title as extrair_titulo_de_tabela,
    save_table_image as salvar_imagem_de_tabela,
)

__all__ = [
    "avaliar_tabela",
    "extrair_titulo_de_tabela",
    "salvar_imagem_de_tabela",
]
