# SPDX-License-Identifier: MIT
from __future__ import annotations

from pathlib import Path

from .extractors.pypdf_native import count_page_images, extract_page_text, open_pdf
from .graphics import analyze_repeated_graphics
from .hashing import sha256_file
from .maps import is_map_page
from .models import DocumentDiagnosis, PageDiagnosis


def diagnose_pdf(path: Path, min_native_chars: int = 40) -> DocumentDiagnosis:
    reader = open_pdf(path)
    graphic_summaries, repeated_graphics = analyze_repeated_graphics(reader)
    pages: list[PageDiagnosis] = []

    for index, page in enumerate(reader.pages, start=1):
        text = extract_page_text(page)
        fallback_image_count = count_page_images(page)
        graphics = graphic_summaries.get(index)
        raw_image_count = (
            graphics.raw_image_count if graphics is not None else fallback_image_count
        )
        decorative_image_count = (
            graphics.decorative_image_count if graphics is not None else 0
        )
        content_image_count = (
            graphics.content_image_count if graphics is not None else fallback_image_count
        )
        char_count = len(text.strip())
        suspected_map = is_map_page(text, content_image_count)
        has_native = char_count >= min_native_chars
        route = "map" if suspected_map else ("native" if has_native else "ocr")
        warnings: list[str] = []

        if suspected_map:
            warnings.append("conteudo cartografico: preservar como imagem")
        elif 0 < char_count < min_native_chars:
            warnings.append("camada textual insuficiente")
        if content_image_count and has_native and not suspected_map:
            warnings.append("pagina hibrida: texto e imagem relevante")
        if not char_count and not raw_image_count:
            warnings.append("pagina sem texto ou imagem detectavel")

        pages.append(
            PageDiagnosis(
                page_number=index,
                has_native_text=has_native,
                character_count=char_count,
                image_count=content_image_count,
                raw_image_count=raw_image_count,
                decorative_image_count=decorative_image_count,
                content_image_count=content_image_count,
                suspected_map=suspected_map,
                route=route,
                warnings=warnings,
            )
        )

    return DocumentDiagnosis(
        source_path=path,
        sha256=sha256_file(path),
        page_count=len(reader.pages),
        pages=pages,
        repeated_graphics=repeated_graphics,
    )
