# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
from pathlib import Path


def convert_with_docling(
    source: Path,
    markdown_path: Path,
    json_path: Path | None = None,
) -> Path:
    """Converte um documento com Docling, carregado como extra opcional."""

    try:
        from docling.document_converter import DocumentConverter
    except ImportError as exc:
        raise RuntimeError(
            "A rota estruturada requer Docling. "
            "Instale o projeto com: pip install -e '.[structured]'"
        ) from exc

    result = DocumentConverter().convert(source)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(result.document.export_to_markdown(), encoding="utf-8")

    if json_path is not None:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(result.document.export_to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return markdown_path
