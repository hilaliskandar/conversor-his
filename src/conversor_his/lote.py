# SPDX-License-Identifier: MIT
"""Processamento de lotes com API pública em português."""

from .batch import (
    BatchConversionResult as ResultadoDeConversaoEmLote,
    convert_zip_batch as converter_lote_zip,
)

__all__ = ["ResultadoDeConversaoEmLote", "converter_lote_zip"]
