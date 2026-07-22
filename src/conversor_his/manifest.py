# SPDX-License-Identifier: MIT
"""Compatibilidade temporária com a API anterior em inglês."""

from .manifesto import escrever_manifesto, ler_manifesto


def write_manifest(content, output_path, *, compatibility_mode: bool = True) -> None:
    escrever_manifesto(
        content,
        output_path,
        modo_compatibilidade=compatibility_mode,
    )


def read_manifest(path, *, normalize_fields: bool = False):
    return ler_manifesto(path, normalizar_campos=normalize_fields)


__all__ = ["read_manifest", "write_manifest"]
