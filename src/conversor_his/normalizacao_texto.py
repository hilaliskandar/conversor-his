# SPDX-License-Identifier: MIT
"""Normalização de texto com API pública em português."""

from .text_normalization import (
    clean_invisible_characters as limpar_caracteres_invisiveis,
    has_excessive_layout_spacing as tem_espacamento_excessivo_de_layout,
    normalize_prose_text as normalizar_texto_de_prosa,
)

__all__ = [
    "limpar_caracteres_invisiveis",
    "normalizar_texto_de_prosa",
    "tem_espacamento_excessivo_de_layout",
]
