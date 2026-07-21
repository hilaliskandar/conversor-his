# SPDX-License-Identifier: MIT
from __future__ import annotations

import logging
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pypdf import PdfReader

_LEGAL_MARKER_RE = re.compile(
    r"\b(?:ART\.?|ARTIGO|PAR[AÁ]GRAFO|INCISO|LEI|DECRETO|RESOLU[CÇ][AÃ]O)\b",
    re.IGNORECASE,
)


@dataclass(slots=True)
class NativeTextExtraction:
    text: str
    selected_mode: str
    layout_character_count: int
    simple_character_count: int
    rotated_text: bool = False
    warnings: list[str] = field(default_factory=list)


class _MessageHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def _text_score(text: str) -> float:
    normalized = text.strip()
    if not normalized:
        return 0.0
    alphanumeric = sum(char.isalnum() for char in normalized)
    words = len(normalized.split())
    legal_markers = len(_LEGAL_MARKER_RE.findall(normalized))
    replacement_penalty = normalized.count("\ufffd") * 8
    return max(0.0, alphanumeric + words * 0.5 + legal_markers * 12 - replacement_penalty)


def _extract_layout_with_messages(page: Any) -> tuple[str, list[str]]:
    handler = _MessageHandler()
    logger = logging.getLogger("pypdf")
    previous_propagate = logger.propagate
    logger.addHandler(handler)
    logger.propagate = False

    captured: list[str] = []
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            text = page.extract_text(
                extraction_mode="layout",
                layout_mode_space_vertically=False,
            )
        captured.extend(str(item.message) for item in caught)
        captured.extend(handler.messages)
        return (text or "").strip(), captured
    finally:
        logger.removeHandler(handler)
        logger.propagate = previous_propagate


def extract_page_text_detailed(page: Any) -> NativeTextExtraction:
    """Extrai texto e registra limitações da camada textual da página.

    O modo ``layout`` é preferido. Quando o pypdf sinaliza texto rotacionado,
    quando a saída fica vazia ou muito curta, a extração simples também é
    executada e as duas alternativas são comparadas por completude textual.
    """

    layout_text = ""
    messages: list[str] = []
    try:
        layout_text, messages = _extract_layout_with_messages(page)
    except (TypeError, ValueError, KeyError) as exc:
        messages.append(f"layout_extraction_failed: {type(exc).__name__}: {exc}")

    rotated_text = any("rotated text" in message.casefold() for message in messages)
    should_try_simple = rotated_text or len(layout_text) < 40
    simple_text = ""
    if should_try_simple:
        try:
            simple_text = (page.extract_text() or "").strip()
        except (TypeError, ValueError, KeyError) as exc:
            messages.append(f"simple_extraction_failed: {type(exc).__name__}: {exc}")

    selected_mode = "layout"
    selected_text = layout_text
    layout_score = _text_score(layout_text)
    simple_score = _text_score(simple_text)

    if simple_text and (
        not layout_text
        or simple_score > layout_score * 1.15
        or (rotated_text and simple_score >= layout_score * 0.95)
    ):
        selected_mode = "simple"
        selected_text = simple_text

    normalized_messages = list(dict.fromkeys(message.strip() for message in messages if message.strip()))
    return NativeTextExtraction(
        text=selected_text,
        selected_mode=selected_mode,
        layout_character_count=len(layout_text),
        simple_character_count=len(simple_text),
        rotated_text=rotated_text,
        warnings=normalized_messages,
    )


def extract_page_text(page: Any, preserve_layout: bool = True) -> str:
    """Extrai o melhor texto disponível, preservando compatibilidade da API."""

    if preserve_layout:
        return extract_page_text_detailed(page).text
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


def extract_native_pages_detailed(path: Path) -> dict[int, NativeTextExtraction]:
    reader = open_pdf(path)
    return {
        index: extract_page_text_detailed(page)
        for index, page in enumerate(reader.pages, start=1)
    }


def extract_native_pages(path: Path, preserve_layout: bool = True) -> dict[int, str]:
    reader = open_pdf(path)
    if preserve_layout:
        return {
            index: extract_page_text_detailed(page).text
            for index, page in enumerate(reader.pages, start=1)
        }
    return {
        index: extract_page_text(page, preserve_layout=False)
        for index, page in enumerate(reader.pages, start=1)
    }
