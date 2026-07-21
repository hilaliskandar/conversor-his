# SPDX-License-Identifier: MIT
from __future__ import annotations

from pathlib import Path

from .extractors.pypdf_native import count_page_images, extract_page_text, open_pdf
from .hashing import sha256_file
from .models import DocumentDiagnosis, PageDiagnosis


def diagnose_pdf(path: Path, min_native_chars: int = 40) -> DocumentDiagnosis:
    reader = open_pdf(path)
    pages: list[PageDiagnosis] = []

    for index, page in enumerate(reader.pages, start=1):
        text = extract_page_text(page)
        image_count = count_page_images(page)
        char_count = len(text.strip())
        has_native = char_count >= min_native_chars
        route = "native" if has_native else "ocr"
        warnings: list[str] = []

        if 0 < char_count < min_native_chars:
            warnings.append("camada textual insuficiente")
        if image_count and has_native:
            warnings.append("pagina hibrida: texto e imagem")
        if not char_count and not image_count:
            warnings.append("pagina sem texto ou imagem detectavel")

        pages.append(
            PageDiagnosis(
                page_number=index,
                has_native_text=has_native,
                character_count=char_count,
                image_count=image_count,
                route=route,
                warnings=warnings,
            )
        )

    return DocumentDiagnosis(
        source_path=path,
        sha256=sha256_file(path),
        page_count=len(reader.pages),
        pages=pages,
    )
