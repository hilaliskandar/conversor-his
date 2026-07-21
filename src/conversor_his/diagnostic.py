from __future__ import annotations

from pathlib import Path

import fitz

from .hashing import sha256_file
from .models import DocumentDiagnosis, PageDiagnosis


def diagnose_pdf(path: Path, min_native_chars: int = 40) -> DocumentDiagnosis:
    pages: list[PageDiagnosis] = []
    with fitz.open(path) as doc:
        for index, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            images = page.get_images(full=True)
            char_count = len(text.strip())
            has_native = char_count >= min_native_chars
            route = "native" if has_native else "ocr"
            warnings: list[str] = []
            if 0 < char_count < min_native_chars:
                warnings.append("camada textual insuficiente")
            if images and has_native:
                warnings.append("pagina hibrida: texto e imagem")
            pages.append(
                PageDiagnosis(
                    page_number=index,
                    has_native_text=has_native,
                    character_count=char_count,
                    image_count=len(images),
                    route=route,
                    warnings=warnings,
                )
            )
        return DocumentDiagnosis(
            source_path=path,
            sha256=sha256_file(path),
            page_count=len(doc),
            pages=pages,
        )
