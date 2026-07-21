# SPDX-License-Identifier: MIT
from __future__ import annotations

import time
from pathlib import Path

from . import __version__
from .diagnostic import diagnose_pdf
from .extractors.pypdf_native import extract_native_pages_detailed
from .hashing import sha256_file
from .manifest import write_manifest
from .maps import extract_map_title, is_map_page, save_map_image
from .models import ConversionManifest
from .ocr.quality import assess_ocr_quality
from .ocr.tesseract_engine import TesseractEngine
from .tables import extract_table_title, save_table_image
from .text_normalization import clean_invisible_characters, normalize_prose_text


def _markdown_image(alt_text: str, relative_image: str) -> str:
    """Gera referência de imagem válida mesmo quando o caminho contém espaços."""

    safe_alt = alt_text.replace("[", "(").replace("]", ")")
    return f"![{safe_alt}](<{relative_image}>)"


def _visual_chunk(
    page_number: int,
    title: str,
    text: str,
    relative_image: str,
    source_mode: str,
) -> str:
    text_block = ""
    normalized_text = normalize_prose_text(text)
    if normalized_text:
        text_block = (
            "\n\n> Texto associado à página visual, preservado para pesquisa e "
            "rastreabilidade. A interpretação espacial deve consultar a imagem.\n\n"
            "```text\n"
            f"{normalized_text}\n"
            "```\n"
        )
    return (
        f"<!-- pagina_original: {page_number}; tipo: visual_cartografico; "
        f"rota: imagem+texto:{source_mode}; revisao: sim -->\n\n"
        f"## Página {page_number} — {title}\n\n"
        "> Conteúdo visual possivelmente cartográfico preservado integralmente. "
        "A classificação deve ser conferida quando a página não representar mapa ou planta.\n\n"
        f"{_markdown_image(title, relative_image)}"
        f"{text_block}"
    )


def _table_chunk(
    page_number: int,
    title: str,
    text: str,
    relative_image: str,
    candidate: bool = False,
) -> str:
    classification = "candidata" if candidate else "confirmada"
    raw_text = clean_invisible_characters(text).strip()
    return (
        f"<!-- pagina_original: {page_number}; tipo: tabela_{classification}; "
        "rota: structured:preservacao; revisao: sim -->\n\n"
        f"## Página {page_number} — {title}\n\n"
        f"> **Revisão estrutural necessária:** estrutura tabular {classification}. "
        "O texto linear e a imagem foram preservados; as relações entre linhas e colunas "
        "devem ser conferidas.\n\n"
        f"{_markdown_image(f'Página tabular {page_number}', relative_image)}\n\n"
        "```text\n"
        f"{raw_text}\n"
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
    normalized_text = normalize_prose_text(text)
    return (
        f"<!-- pagina_original: {page_number}; rota: ocr:tesseract+pdfium; "
        f"revisao: {'sim' if requires_review else 'nao'} -->\n\n"
        f"## Página {page_number}\n\n{notice}{normalized_text}\n"
    )


def convert_pdf(
    path: Path,
    output_dir: Path,
    dpi: int = 300,
    source_reference: str | None = None,
) -> Path:
    started = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    diagnosis = diagnose_pdf(path)
    source_path: Path | str = source_reference or path
    diagnosis.source_path = source_path
    native = extract_native_pages_detailed(path)
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
    rotated_text_pages: list[int] = []
    visual_text_preserved_pages: list[int] = []

    for page in diagnosis.pages:
        extraction = native[page.page_number]
        native_text = extraction.text
        page.native_extraction_mode = extraction.selected_mode
        page.layout_character_count = extraction.layout_character_count
        page.simple_character_count = extraction.simple_character_count
        page.rotated_text_detected = extraction.rotated_text
        page.extraction_warnings = extraction.warnings
        if extraction.rotated_text:
            rotated_text_pages.append(page.page_number)
            if page.page_number not in review_pages:
                review_pages.append(page.page_number)

        if page.page_type == "table_candidate":
            table_candidate_pages.append(page.page_number)
            image_path = save_table_image(
                path, page.page_number, assets_dir, dpi=min(dpi, 300)
            )
            asset_paths.append(image_path)
            review_pages.append(page.page_number)
            title = extract_table_title(native_text, page.page_number)
            chunks.append(
                _table_chunk(
                    page.page_number,
                    title,
                    native_text,
                    image_path.relative_to(output_dir).as_posix(),
                    candidate=True,
                )
            )
            continue

        if page.route == "map":
            title = extract_map_title(native_text, page.page_number)
            image_path = save_map_image(
                path, page.page_number, assets_dir, dpi=min(dpi, 300)
            )
            asset_paths.append(image_path)
            map_pages.append(page.page_number)
            review_pages.append(page.page_number)
            if native_text.strip():
                page.preserved_visual_text = True
                visual_text_preserved_pages.append(page.page_number)
            chunks.append(
                _visual_chunk(
                    page.page_number,
                    title,
                    native_text,
                    image_path.relative_to(output_dir).as_posix(),
                    extraction.selected_mode,
                )
            )
            continue

        if page.route == "decorative":
            decorative_pages.append(page.page_number)
            chunks.append(_decorative_chunk(page.page_number, page.page_type))
            continue

        if page.route == "structured":
            title = extract_table_title(native_text, page.page_number)
            image_path = save_table_image(
                path, page.page_number, assets_dir, dpi=min(dpi, 300)
            )
            asset_paths.append(image_path)
            table_pages.append(page.page_number)
            review_pages.append(page.page_number)
            chunks.append(
                _table_chunk(
                    page.page_number,
                    title,
                    native_text,
                    image_path.relative_to(output_dir).as_posix(),
                )
            )
            continue

        if page.route == "ocr":
            used_ocr_pages.append(page.page_number)
            text, confidences = ocr.recognize_page_with_confidence(
                path, page.page_number, dpi=dpi
            )
            quality = assess_ocr_quality(text, confidences)
            page.ocr_quality = quality
            if is_map_page(text, max(page.image_count, 1)):
                page.suspected_map = True
                page.page_type = "map"
                page.route = "map"
                page.preserved_visual_text = bool(text.strip())
                page.warnings.append(
                    "conteudo visual identificado apos OCR; texto OCR preservado com imagem"
                )
                title = extract_map_title(text, page.page_number)
                image_path = save_map_image(
                    path, page.page_number, assets_dir, dpi=min(dpi, 300)
                )
                asset_paths.append(image_path)
                map_pages.append(page.page_number)
                review_pages.append(page.page_number)
                if text.strip():
                    visual_text_preserved_pages.append(page.page_number)
                chunks.append(
                    _visual_chunk(
                        page.page_number,
                        title,
                        text,
                        image_path.relative_to(output_dir).as_posix(),
                        "ocr",
                    )
                )
                continue
            if quality.requires_review:
                review_pages.append(page.page_number)
                page.warnings.append(
                    "resultado OCR requer revisao: " + "; ".join(quality.reasons)
                )
            chunks.append(_ocr_chunk(page.page_number, text, quality.requires_review))
            continue

        review_notice = ""
        if extraction.rotated_text:
            review_notice = (
                "> **Revisão recomendada:** havia texto rotacionado; o conversor comparou "
                f"os modos de extração e selecionou `{extraction.selected_mode}`.\n\n"
            )
        chunks.append(
            f"<!-- pagina_original: {page.page_number}; rota: native:pypdf; "
            f"modo: {extraction.selected_mode} -->\n\n"
            f"## Página {page.page_number}\n\n{review_notice}{normalize_prose_text(native_text)}\n"
        )

    markdown_path = output_dir / f"{path.stem}.md"
    manifest_path = output_dir / f"{path.stem}.manifest.json"
    temporary_markdown = markdown_path.with_suffix(".md.tmp")
    temporary_markdown.write_text("\n\n".join(chunks), encoding="utf-8")
    temporary_markdown.replace(markdown_path)

    conversion_manifest = ConversionManifest(
        source_path=source_path,
        source_sha256=diagnosis.sha256,
        page_count=diagnosis.page_count,
        markdown_path=markdown_path,
        markdown_sha256=sha256_file(markdown_path),
        markdown_size_bytes=markdown_path.stat().st_size,
        asset_paths=asset_paths,
        used_ocr_pages=used_ocr_pages,
        map_pages=sorted(set(map_pages)),
        table_pages=sorted(set(table_pages)),
        table_candidate_pages=sorted(set(table_candidate_pages)),
        decorative_pages=sorted(set(decorative_pages)),
        review_pages=sorted(set(review_pages)),
        dpi=dpi,
        converter_version=__version__,
        diagnosis=diagnosis,
        rotated_text_pages=sorted(set(rotated_text_pages)),
        visual_text_preserved_pages=sorted(set(visual_text_preserved_pages)),
        processing_seconds=round(time.perf_counter() - started, 3),
    )
    write_manifest(conversion_manifest, manifest_path)
    return markdown_path
