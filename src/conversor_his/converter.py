# SPDX-License-Identifier: MIT
from __future__ import annotations

from pathlib import Path

from .diagnostic import diagnose_pdf
from .extractors.pypdf_native import extract_native_pages
from .manifest import write_manifest
from .ocr.tesseract_engine import TesseractEngine


def convert_pdf(path: Path, output_dir: Path, dpi: int = 300) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    diagnosis = diagnose_pdf(path)
    native = extract_native_pages(path)
    ocr = TesseractEngine()
    chunks: list[str] = []

    for page in diagnosis.pages:
        if page.route == "ocr":
            text = ocr.recognize_page(path, page.page_number, dpi=dpi)
            route = "ocr:tesseract+pdfium"
        else:
            text = native[page.page_number]
            route = "native:pypdf"
        chunks.append(
            f"<!-- pagina_original: {page.page_number}; rota: {route} -->\n\n"
            f"## Página {page.page_number}\n\n{text}\n"
        )

    markdown_path = output_dir / f"{path.stem}.md"
    manifest_path = output_dir / f"{path.stem}.manifest.json"
    markdown_path.write_text("\n\n".join(chunks), encoding="utf-8")
    write_manifest(diagnosis, manifest_path)
    return markdown_path
