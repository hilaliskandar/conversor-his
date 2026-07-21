# SPDX-License-Identifier: MIT
from __future__ import annotations

from pathlib import Path
from typing import Any

from pypdf import PdfReader


def extract_page_text(page: Any, preserve_layout: bool = True) -> str:
    """Extrai o texto de uma página PDF.

    O modo ``layout`` é preferido porque conserva melhor a posição horizontal
    e a ordem visual. Há fallback para o modo simples para PDFs incompatíveis
    com esse recurso.
    """

    if preserve_layout:
        try:
            text = page.extract_text(
                extraction_mode="layout",
                layout_mode_space_vertically=False,
            )
            return (text or "").strip()
        except (TypeError, ValueError, KeyError):
            pass

    return (page.extract_text() or "").strip()


def _resolve_pdf_object(value: Any) -> Any:
    return value.get_object() if hasattr(value, "get_object") else value


def _count_images_in_resources(resources: Any, visited: set[int]) -> int:
    resources = _resolve_pdf_object(resources)
    if not resources:
        return 0

    xobjects = _resolve_pdf_object(resources.get("/XObject"))
    if not xobjects:
        return 0

    count = 0
    for reference in xobjects.values():
        obj = _resolve_pdf_object(reference)
        object_id = id(obj)
        if object_id in visited:
            continue
        visited.add(object_id)

        subtype = obj.get("/Subtype") if hasattr(obj, "get") else None
        if subtype == "/Image":
            count += 1
        elif subtype == "/Form" and hasattr(obj, "get"):
            count += _count_images_in_resources(obj.get("/Resources"), visited)
    return count


def count_page_images(page: Any) -> int:
    """Conta imagens XObject, inclusive em Form XObjects aninhados."""

    return _count_images_in_resources(page.get("/Resources"), set())


def open_pdf(path: Path) -> PdfReader:
    """Abre um PDF com tolerância a pequenas inconformidades estruturais."""

    return PdfReader(str(path), strict=False)


def extract_native_pages(path: Path, preserve_layout: bool = True) -> dict[int, str]:
    reader = open_pdf(path)
    return {
        index: extract_page_text(page, preserve_layout=preserve_layout)
        for index, page in enumerate(reader.pages, start=1)
    }
