# SPDX-License-Identifier: MIT
from __future__ import annotations

from pathlib import Path

from .diagnostic import diagnose_pdf
from .extractors.pypdf_native import extract_native_pages
from .manifest import write_manifest
from .maps import extract_map_title, is_map_page, save_map_image
from .ocr.tesseract_engine import TesseractEngine


def _map_chunk(page_number: int, title: str, relative_image: str) -> str:
    return (
        f"<!-- pagina_original: {page_number}; tipo: mapa; rota: imagem:pdfium -->\n\n"
        f"## Página {page_number} — {title}\n\n"
        "> Conteúdo cartográfico preservado como imagem. A interpretação territorial "
        "deve consultar a representação visual original.\n\n"
        f"![{title}]({relative_image})\n"
    )


def convert_pdf(path: Path, output_dir: Path, dpi: int = 300) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    diagnosis = diagnose_pdf(path)
    native = extract_native_pages(path)
    ocr = TesseractEngine()
    chunks: list[str] = []
    assets_dir = output_dir / f"{path.stem}_assets"

    for page in diagnosis.pages:
        native_text = native[page.page_number]

        if page.route == "map":
            title = extract_map_title(native_text, page.page_number)
            image_path = save_map_image(path, page.page_number, assets_dir, dpi=min(dpi, 300))
            chunks.append(_map_chunk(page.page_number, title, image_path.relative_to(output_dir).as_posix()))
            continue

        if page.route == "ocr":
            text = ocr.recognize_page(path, page.page_number, dpi=dpi)
            if is_map_page(text, max(page.image_count, 1)):
                page.suspected_map = True
                page.route = "map"
                page.warnings.append("mapa identificado apos OCR; texto substituido por imagem")
                title = extract_map_title(text, page.page_number)
                image_path = save_map_image(path, page.page_number, assets_dir, dpi=min(dpi, 300))
                chunks.append(
                    _map_chunk(page.page_number, title, image_path.relative_to(output_dir).as_posix())
                )
                continue
            route = "ocr:tesseract+pdfium"
        else:
            text = native_text
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
