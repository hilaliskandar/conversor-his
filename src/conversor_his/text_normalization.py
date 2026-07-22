# SPDX-License-Identifier: MIT
"""Compatibilidade temporária com a API anterior em inglês."""

from .normalizacao_texto import (
    limpar_caracteres_invisiveis as clean_invisible_characters,
    normalizar_texto_de_prosa as normalize_prose_text,
    tem_espacamento_excessivo_de_layout as has_excessive_layout_spacing,
)

__all__ = [
    "clean_invisible_characters",
    "has_excessive_layout_spacing",
    "normalize_prose_text",
]
