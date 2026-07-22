# SPDX-License-Identifier: MIT
"""Interface pública do conversor.

A implementação ativa fica em ``pipeline_v072`` para manter a evolução do fluxo
isolada e auditável sem alterar os comandos CLI e o processamento em lote.
"""

from .pipeline_v072 import convert_pdf

__all__ = ["convert_pdf"]
