# SPDX-License-Identifier: MIT
"""Compatibilidade temporária com o fluxo de conversão da versão 0.7."""

from __future__ import annotations

from pathlib import Path

from .fluxo_conversao import (
    EvidenciaOCRDePagina as OcrPageEvidence,
    _imagem_markdown,
    converter_pdf,
)


def _markdown_image(alt_text: str, relative_image: str) -> str:
    return _imagem_markdown(alt_text, relative_image)


def convert_pdf(
    path: Path,
    output_dir: Path,
    dpi: int = 300,
    source_reference: str | None = None,
) -> Path:
    return converter_pdf(
        caminho=path,
        diretorio_saida=output_dir,
        dpi=dpi,
        referencia_origem=source_reference,
    )


__all__ = ["OcrPageEvidence", "convert_pdf", "_markdown_image"]
