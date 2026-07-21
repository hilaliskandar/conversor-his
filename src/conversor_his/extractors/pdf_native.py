# SPDX-License-Identifier: MIT
"""Compatibilidade para importações anteriores do extrator nativo."""

from .pypdf_native import (
    count_page_images,
    extract_native_pages,
    extract_page_text,
    open_pdf,
)

__all__ = [
    "count_page_images",
    "extract_native_pages",
    "extract_page_text",
    "open_pdf",
]
