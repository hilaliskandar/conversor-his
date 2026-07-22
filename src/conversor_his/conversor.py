# SPDX-License-Identifier: MIT
"""Interface pública de conversão com nomenclatura em português."""

from .converter import _markdown_image as _imagem_markdown
from .converter import convert_pdf as converter_pdf

__all__ = ["converter_pdf", "_imagem_markdown"]
