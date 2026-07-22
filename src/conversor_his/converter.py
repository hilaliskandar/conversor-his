# SPDX-License-Identifier: MIT
"""Interface pública do conversor.

A implementação ativa fica em ``pipeline_v072`` para manter a evolução do fluxo
isolada e auditável sem alterar os comandos CLI, o processamento em lote e os
imports de compatibilidade usados pelos testes existentes.
"""

from .pipeline_v072 import _markdown_image, convert_pdf

__all__ = ["convert_pdf", "_markdown_image"]
