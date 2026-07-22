# SPDX-License-Identifier: MIT
"""Compatibilidade temporária com o processamento em lote da API 0.7."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path, PurePosixPath

from .converter import convert_pdf
from .lote import (
    ResultadoDeConversaoEmLote as BatchConversionResult,
    _caminho_seguro_do_membro,
    _raiz_comum,
    converter_lote_zip,
)


def _safe_member_path(member_name: str) -> PurePosixPath:
    return _caminho_seguro_do_membro(member_name)


def _common_root(paths: list[PurePosixPath]) -> str | None:
    return _raiz_comum(paths)


def convert_zip_batch(
    zip_path: Path,
    output_dir: Path,
    dpi: int = 300,
    document_limit: int = 0,
    resume: bool = False,
    remove_common_root: bool = True,
    progress: Callable[[str], None] | None = None,
) -> BatchConversionResult:
    """Preserva a assinatura pública da versão 0.7."""

    def converter_compatibilidade(
        caminho: Path,
        diretorio_saida: Path,
        *,
        dpi: int,
        referencia_origem: str,
    ) -> Path:
        return convert_pdf(
            caminho,
            diretorio_saida,
            dpi=dpi,
            source_reference=referencia_origem,
        )

    return converter_lote_zip(
        caminho_zip=zip_path,
        diretorio_saida=output_dir,
        dpi=dpi,
        limite_documentos=document_limit,
        retomar=resume,
        remover_raiz_comum=remove_common_root,
        progresso=progress,
        conversor_pdf=converter_compatibilidade,
    )


__all__ = [
    "BatchConversionResult",
    "convert_zip_batch",
    "_common_root",
    "_safe_member_path",
]
