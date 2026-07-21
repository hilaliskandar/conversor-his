# SPDX-License-Identifier: MIT
from __future__ import annotations

from pathlib import Path

from . import __version__
from .diagnostic import diagnose_pdf
from .extractors.pypdf_native import extract_native_pages
from .hashing import sha256_file
from .manifest import write_manifest
from .maps import extract_map_title, is_map_page, save_map_image
from .models import ConversionManifest
from .ocr.quality import assess_ocr_quality
from .ocr.tesseract_engine import TesseractEngine
from .tables import extract_table_title, save_table_image


def _map_chunk(page_number: int, title: str, relative_image: str) -> str:
    return (
        f"<!-- pagina_original: {page_number}; tipo: mapa; rota: imagem:pdfium -->\n\n"
        f"## Página {page_number} — {title}\n\n"
        "> Conteúdo cartográfico preservado como imagem. A interpretação territorial "
        "deve consultar a representação visual original.\n\n"
        f"![{title}]({relative_image})\n"
    )


def _table_chunk(page_number: int, title: str, text: str, relative_image: str) -> str:
    return (
        f"<!-- pagina_original: {page_number}; tipo: tabela; "
        "rota: structured:preservacao; revisao: sim -->\n\n"
        f"## Página {page_number} — {title}\n\n"
        "> **Revisão estrutural necessária:** foi confirmada estrutura de tabela ou quadro. "
        "O texto abaixo preserva a extração linear, mas as relações entre linhas e colunas "
        "devem ser conferidas na imagem da página.\n\n"
        f"![Página tabular {page_number}]({relative_image})\n\n"
        "```text\n"
        f"{text}\n"
        "```\n"
    )


def _decorative_chunk(page_number: int, page_type: str) -> str:
    label = "contracapa" if page_type == "back_cover" else "página decorativa"
    return (
        f"<!-- pagina_original: {page_number}; tipo: {page_type}; "
        "rota: decorative; revisao: nao -->\n\n"
        f"## Página {page_number} — {label.capitalize()}\n\n"
        "> Página sem conteúdo textual normativo detectável. Os elementos gráficos "
        "foram classificados como decorativos recorrentes; o arquivo PDF original "
        "permanece como fonte visual de referência.\n"
    )


def _ocr_chunk(page_number: int, text: str, requires_review: bool) -> str:
    notice = ""
    if requires_review:
        notice = (
            "> **Revisão necessária:** o resultado do OCR apresentou baixa ou moderada "
            "qualidade e não deve ser tratado como transcrição normativa confiável.\n\n"
        )
    return (
        f"<!-- pagina_original: {page_number}; rota: ocr:tesseract+pdfium; "
        f"revisao: {'sim' if requires_review else 'nao'} -->\n\n"
        f"## Página {page_number}\n\n{notice}{text}\n"
    )


def convert_pdf(
    path: Path,
    output_dir: Path,
    dpi: int = 300,
    source_reference: str | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    diagnosis = diagnose_pdf(path)
    source_path: Path | str = source_reference or path
    diagnosis.source_path = source_path
    native = extract_native_pages(path)
    ocr = TesseractEngine()
    chunks: list[str] = []
    assets_dir = output_dir / f"{path.stem}_assets"
    asset_paths: list[Path] = []
    used_ocr_pages: list[int] = []
    map_pages: list[int] = []
    table_pages: list[int] = []
    table_candidate_pages: list[int] = []
    decorative_pages: list[int] = []
    review_pages: list[int] = []

    for page in diagnosis.pages:
        native_text = native[page.page_number]
        if page.page_type == "table_candidate":
            table_candidate_pages.append(page.page_number)
        if page.route == "map":
            title = extract_map_title(native_text, page.page_number)
            image_path = save_map_image(path, page.page_number, assets_dir, dpi=min(dpi, 300))
            asset_paths.append(image_path)
            map_pages.append(page.page_number)
            chunks.append(_map_chunk(page.page_number, title, image_path.relative_to(output_dir).as_posix()))
            continue
        if page.route == "decorative":
            decorative_pages.append(page.page_number)
            chunks.append(_decorative_chunk(page.page_number, page.page_type))
            continue
        if page.route == "structured":
            title = extract_table_title(native_text, page.page_number)
            image_path = save_table_image(path, page.page_number, assets_dir, dpi=min(dpi, 300))
            asset_paths.append(image_path)
            table_pages.append(page.page_number)
            review_pages.append(page.page_number)
            chunks.append(_table_chunk(page.page_number, title, native_text, image_path.relative_to(output_dir).as_posix()))
            continue
        if page.route == "ocr":
            used_ocr_pages.append(page.page_number)
            text, confidences = ocr.recognize_page_with_confidence(path, page.page_number, dpi=dpi)
            quality = assess_ocr_quality(text, confidences)
            page.ocr_quality = quality
            if is_map_page(text, max(page.image_count, 1)):
                page.suspected_map = True
                page.page_type = "map"
                page.route = "map"
                page.warnings.append("mapa identificado apos OCR; texto substituido por imagem")
                title = extract_map_title(text, page.page_number)
                image_path = save_map_image(path, page.page_number, assets_dir, dpi=min(dpi, 300))
                asset_paths.append(image_path)
                map_pages.append(page.page_number)
                chunks.append(_map_chunk(page.page_number, title, image_path.relative_to(output_dir).as_posix()))
                continue
            if quality.requires_review:
                review_pages.append(page.page_number)
                page.warnings.append("resultado OCR requer revisao: " + "; ".join(quality.reasons))
            chunks.append(_ocr_chunk(page.page_number, text, quality.requires_review))
            continue
        chunks.append(
            f"<!-- pagina_original: {page.page_number}; rota: native:pypdf -->\n\n"
            f"## Página {page.page_number}\n\n{native_text}\n"
        )

    markdown_path = output_dir / f"{path.stem}.md"
    manifest_path = output_dir / f"{path.stem}.manifest.json"
    markdown_path.write_text("\n\n".join(chunks), encoding="utf-8")
    conversion_manifest = ConversionManifest(
        source_path=source_path,
        source_sha256=diagnosis.sha256,
        page_count=diagnosis.page_count,
        markdown_path=markdown_path,
        markdown_sha256=sha256_file(markdown_path),
        markdown_size_bytes=markdown_path.stat().st_size,
        asset_paths=asset_paths,
        used_ocr_pages=used_ocr_pages,
        map_pages=map_pages,
        table_pages=table_pages,
        table_candidate_pages=table_candidate_pages,
        decorative_pages=decorative_pages,
        review_pages=review_pages,
        dpi=dpi,
        converter_version=__version__,
        diagnosis=diagnosis,
    )
    write_manifest(conversion_manifest, manifest_path)
    return markdown_path
