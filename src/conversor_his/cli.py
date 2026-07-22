# SPDX-License-Identifier: MIT
"""Compatibilidade temporária com o módulo de linha de comando anterior."""

from .linha_comando import app, console, converter, converter_lote, diagnosticar

__all__ = ["app", "console", "converter", "converter_lote", "diagnosticar"]
