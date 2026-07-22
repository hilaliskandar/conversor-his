# SPDX-License-Identifier: MIT
"""Compatibilidade temporária com a API anterior em inglês."""

from __future__ import annotations

from pathlib import Path

from .diagnostico import diagnosticar_pdf as _diagnosticar_pdf
from .extractors.pypdf_native import NativeTextExtraction
from .models import DocumentDiagnosis


def diagnose_pdf(
    path: Path,
    min_native_chars: int = 40,
    native_extractions: dict[int, NativeTextExtraction] | None = None,
) -> DocumentDiagnosis:
    return _diagnosticar_pdf(
        path,
        minimo_caracteres_nativos=min_native_chars,
        extracoes_nativas=native_extractions,
    )


__all__ = ["diagnose_pdf"]
