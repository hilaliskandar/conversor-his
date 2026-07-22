# SPDX-License-Identifier: MIT
from __future__ import annotations

import time
from pathlib import Path

from . import __version__
from .coordinates import assess_coordinate_register
from .diagnostic import diagnose_pdf
from .extractors.pypdf_native import extract_native_pages_detailed
from .hashing import sha256_file
from .manifest import write_manifest
from .maps import classify_map_page, extract_map_title, save_map_image
from .models import ConversionManifest
from .ocr.quality import assess_ocr_quality
from .ocr.render import render_pdf_page
from .ocr.tesseract_engine import TesseractEngine
from .raster_visual import assess_raster_visual
from .tables import extract_table_title, save_table_image
from .text_normalization import clean_invisible_characters, normalize_prose_text

_TABLE_IMAGE_DPI = 200
_RASTER_ANALYSIS_DPI = 150
_DIAGRAM_IMAGE_DPI = 250
_REVIEW_IMAGE_DPI = 300
_COORDINATE_IMAGE_DPI = 200


def _markdown_image(alt_text: str, relative_image: str) -> str:
    safe_alt = alt_text.replace("[", "(").replace("]", ")")
    return f"![{safe_alt}](<{relative_image}>)"


def _save_review_image(
    pdf_path: Path,
    page_number: int,
    assets_dir: Path,
    *,
    dpi: int,
    suffix: str,
) -> Path:
    assets_dir.mkdir(parents=True, exist_ok=True)
    image_path = assets_dir / f"pagina_{page_number:04d}_{suffix}.png"
    image = render_pdf_page(pdf_path, page_number, dpi=dpi)
    image.save(image_path, format="PNG", optimize=True)
    return image_path


def _visual_chunk(
    page_number: int,
    title: str,
    text: str,
    relative_image: str,
    source_mode: str,
    visual_type: str = "visual_cartografico",
    notice: str | None = None,
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
    message = notice or (
        "Conteúdo visual preservado integralmente. A classificação e as relações "
        "espaciais devem ser conferidas na imagem."
    )
    return (
        f"<!-- pagina_original: {page_number}; tipo: {visual_type}; "
        f"rota: imagem+texto:{source_mode}; revisao: sim -->\n\n"
        f"## Página {page_number} — {title}\n\n"
        f"> {message}\n\n"
        f"{_markdown_image(title, relative_image)}"
        f"{text_block}"
    )


def _table_chunk(
    page_number: int,
    title: str,
    text: str,
    relative_image: str,
    candidate: bool = False,
    raster: bool = False,
) -> str:
    classification = "candidata" if candidate else "confirmada"
    source = "raster" if raster else "nativa/vetorial"
    raw_text = clean_invisible_characters(text).strip()
    return (
        f"<!-- pagina_original: {page_number}; tipo: tabela_{classification}; "
        f"origem: {source}; rota: structured:preservacao; revisao: sim -->\n\n"
        f"## Página {page_number} — {title}\n\n"
        f"> **Revisão estrutural necessária:** estrutura tabular {classification} "
        f"identificada em fonte {source}. O texto linear e a imagem foram preservados; "
        "as relações entre linhas e colunas devem ser conferidas.\n\n"
        f"{_markdown_image(f'Página tabular {page_number}', relative_image)}\n\n"
        "```text\n"
        f"{raw_text}\n"
        "```\n"
    )


def _coordinate_chunk(
    page_number: int,
    text: str,
    relative_image: str,
) -> str:
    raw_text = clean_invisible_characters(text).strip()
    return (
        f"<!-- pagina_original: {page_number}; tipo: coordinate_register; "
        "rota: structured:preservacao; revisao: sim -->\n\n"
        f"## Página {page_number} — Registro de coordenadas\n\n"
        "> Sequência espacial preservada em classe própria. A imagem deve ser consultada "
        "para conferir pares, vértices, ordem e continuidade geométrica.\n\n"
        f"{_markdown_image(f'Registro de coordenadas da página {page_number}', relative_image)}\n\n"
        "```text\n"
        f"{raw_text}\n"
        "```\n"
    )


def _ocr_review_chunk(
    page_number: int,
    text: str,
    relative_image: str,
    quality_label: str,
) -> str:
    normalized_text = normalize_prose_text(text)
    return (
        f"<!-- pagina_original: {page_number}; tipo: ocr_review; "
        f"qualidade: {quality_label}; rota: ocr:tesseract+pdfium; revisao: sim -->\n\n"
        f"## Página {page_number} — OCR com revisão necessária\n\n"
        "> **Revisão necessária:** o resultado do OCR apresentou qualidade baixa ou "
        "moderada. A imagem integral foi preservada e deve prevalecer em caso de dúvida.\n\n"
        f"{_markdown_image(f'Página {page_number} para revisão de OCR', relative_image)}\n\n"
        "```text\n"
        f"{normalized_text}\n"
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


def _ocr_chunk(page_number: int, text: str) -> str:
    normalized_text = normalize_prose_text(text)
    return (
        f"<!-- pagina_original: {page_number}; rota: ocr:tesseract+pdfium; "
        "revisao: nao -->\n\n"
        f"## Página {page_number}\n\n{normalized_text}\n"
    )


def convert_pdf(
    path: Path,
    output_dir: Path,
    dpi: int = 300,
    source_reference: str | None = None,
) -> Path:
    started = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    native = extract_native_pages_detailed(path)
    diagnosis = diagnose_pdf(path, native_extractions=native)
    source_path: Path | str = source_reference or path
    diagnosis.source_path = source_path
    ocr = TesseractEngine()
    chunks: list[str] = []
    assets_dir = output_dir / f"{path.stem}_assets"
    asset_paths: list[Path] = []
    used_ocr_pages: list[int] = []
    map_pages: list[int] = []
    map_candidate_pages: list[int] = []
    map_cover_pages: list[int] = []
    table_pages: list[int] = []
    table_candidate_pages: list[int] = []
    raster_table_pages: list[int] = []
    diagram_pages: list[int] = []
    coordinate_register_pages: list[int] = []
    ocr_review_image_pages: list[int] = []
    decorative_pages: list[int] = []
    review_pages: list[int] = []
    rotated_text_pages: list[int] = []
    visual_text_preserved_pages: list[int] = []

    for page in diagnosis.pages:
        extraction = native[page.page_number]
        native_text = extraction.text
        raw_native_text = extraction.raw_text
        page.native_extraction_mode = extraction.selected_mode
        page.layout_character_count = extraction.layout_character_count
        page.simple_character_count = extraction.simple_character_count
        page.rotated_text_detected = extraction.rotated_text
        page.extraction_warnings = extraction.warnings

        if page.page_type == "coordinate_register":
            image_path = _save_review_image(
                path,
                page.page_number,
                assets_dir,
                dpi=min(dpi, _COORDINATE_IMAGE_DPI),
                suffix="coordenadas",
            )
            asset_paths.append(image_path)
            coordinate_register_pages.append(page.page_number)
            review_pages.append(page.page_number)
            chunks.append(
                _coordinate_chunk(
                    page.page_number,
                    raw_native_text,
                    image_path.relative_to(output_dir).as_posix(),
                )
            )
            continue

        if page.page_type == "table_candidate":
            table_candidate_pages.append(page.page_number)
            image_path = save_table_image(
                path,
                page.page_number,
                assets_dir,
                dpi=min(dpi, _TABLE_IMAGE_DPI),
            )
            asset_paths.append(image_path)
            review_pages.append(page.page_number)
            title = extract_table_title(raw_native_text, page.page_number)
            chunks.append(
                _table_chunk(
                    page.page_number,
                    title,
                    raw_native_text,
                    image_path.relative_to(output_dir).as_posix(),
                    candidate=True,
                )
            )
            continue

        if page.route == "map":
            title = extract_map_title(native_text, page.page_number)
            suffix = "mapa"
            visual_type = "map_candidate"
            notice = "Possível conteúdo cartográfico preservado para revisão."
            if page.page_type == "map_cover":
                suffix = "capa_mapa"
                visual_type = "map_cover"
                notice = "Capa ou índice cartográfico preservado sem ser contado como mapa efetivo."
                map_cover_pages.append(page.page_number)
            elif page.page_type == "map_candidate":
                map_candidate_pages.append(page.page_number)
            else:
                map_pages.append(page.page_number)
                visual_type = "map_confirmed"
                notice = "Conteúdo cartográfico confirmado e preservado integralmente."
            image_path = save_map_image(
                path,
                page.page_number,
                assets_dir,
                dpi=min(dpi, 300),
                suffix=suffix,
            )
            asset_paths.append(image_path)
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
                    visual_type=visual_type,
                    notice=notice,
                )
            )
            continue

        if page.route == "decorative":
            decorative_pages.append(page.page_number)
            chunks.append(_decorative_chunk(page.page_number, page.page_type))
            continue

        if page.route == "structured":
            title = extract_table_title(raw_native_text, page.page_number)
            image_path = save_table_image(
                path,
                page.page_number,
                assets_dir,
                dpi=min(dpi, _TABLE_IMAGE_DPI),
            )
            asset_paths.append(image_path)
            table_pages.append(page.page_number)
            review_pages.append(page.page_number)
            chunks.append(
                _table_chunk(
                    page.page_number,
                    title,
                    raw_native_text,
                    image_path.relative_to(output_dir).as_posix(),
                )
            )
            continue

        if page.route == "ocr":
            used_ocr_pages.append(page.page_number)
            analysis_image = render_pdf_page(
                path,
                page.page_number,
                dpi=min(_RASTER_ANALYSIS_DPI, dpi),
            )
            raster_assessment = assess_raster_visual(analysis_image)
            page.raster_visual_assessment = raster_assessment

            text, confidences = ocr.recognize_page_with_confidence(
                path,
                page.page_number,
                dpi=dpi,
            )
            quality = assess_ocr_quality(text, confidences)
            page.ocr_quality = quality
            coordinate_assessment = assess_coordinate_register(text)
            page.coordinate_assessment = (
                coordinate_assessment if coordinate_assessment.detected else None
            )

            if coordinate_assessment.detected:
                image_path = _save_review_image(
                    path,
                    page.page_number,
                    assets_dir,
                    dpi=min(dpi, _COORDINATE_IMAGE_DPI),
                    suffix="coordenadas",
                )
                asset_paths.append(image_path)
                coordinate_register_pages.append(page.page_number)
                review_pages.append(page.page_number)
                page.page_type = "coordinate_register"
                page.preserved_review_image = True
                chunks.append(
                    _coordinate_chunk(
                        page.page_number,
                        text,
                        image_path.relative_to(output_dir).as_posix(),
                    )
                )
                continue

            if raster_assessment.classification == "raster_table_candidate":
                image_path = _save_review_image(
                    path,
                    page.page_number,
                    assets_dir,
                    dpi=min(dpi, _TABLE_IMAGE_DPI),
                    suffix="tabela_raster",
                )
                asset_paths.append(image_path)
                raster_table_pages.append(page.page_number)
                table_candidate_pages.append(page.page_number)
                review_pages.append(page.page_number)
                page.page_type = "raster_table_candidate"
                page.preserved_review_image = True
                chunks.append(
                    _table_chunk(
                        page.page_number,
                        f"Tabela raster da página {page.page_number}",
                        text,
                        image_path.relative_to(output_dir).as_posix(),
                        candidate=True,
                        raster=True,
                    )
                )
                continue

            if raster_assessment.classification == "diagram_candidate":
                image_path = _save_review_image(
                    path,
                    page.page_number,
                    assets_dir,
                    dpi=min(dpi, _DIAGRAM_IMAGE_DPI),
                    suffix="diagrama",
                )
                asset_paths.append(image_path)
                diagram_pages.append(page.page_number)
                review_pages.append(page.page_number)
                page.page_type = "diagram_candidate"
                page.preserved_review_image = True
                chunks.append(
                    _visual_chunk(
                        page.page_number,
                        f"Diagrama da página {page.page_number}",
                        text,
                        image_path.relative_to(output_dir).as_posix(),
                        "ocr+raster",
                        visual_type="diagram_candidate",
                        notice=(
                            "Estrutura de caixas e conectores preservada como possível "
                            "fluxograma, organograma ou esquema."
                        ),
                    )
                )
                continue

            map_class = classify_map_page(
                text,
                max(page.image_count, 1),
                visual_complexity=False,
            )
            if map_class in {"map_candidate", "map_confirmed", "map_cover"}:
                page.suspected_map = map_class != "map_cover"
                page.page_type = map_class
                page.route = "map"
                page.preserved_visual_text = bool(text.strip())
                suffix = "mapa" if map_class != "map_cover" else "capa_mapa"
                image_path = save_map_image(
                    path,
                    page.page_number,
                    assets_dir,
                    dpi=min(dpi, 300),
                    suffix=suffix,
                )
                asset_paths.append(image_path)
                review_pages.append(page.page_number)
                if map_class == "map_cover":
                    map_cover_pages.append(page.page_number)
                elif map_class == "map_candidate":
                    map_candidate_pages.append(page.page_number)
                else:
                    map_pages.append(page.page_number)
                if text.strip():
                    visual_text_preserved_pages.append(page.page_number)
                chunks.append(
                    _visual_chunk(
                        page.page_number,
                        extract_map_title(text, page.page_number),
                        text,
                        image_path.relative_to(output_dir).as_posix(),
                        "ocr",
                        visual_type=map_class,
                        notice=(
                            "Capa ou índice cartográfico preservado."
                            if map_class == "map_cover"
                            else "Possível conteúdo cartográfico preservado para revisão."
                        ),
                    )
                )
                continue

            if quality.requires_review:
                image_path = _save_review_image(
                    path,
                    page.page_number,
                    assets_dir,
                    dpi=min(dpi, _REVIEW_IMAGE_DPI),
                    suffix="ocr_revisao",
                )
                asset_paths.append(image_path)
                review_pages.append(page.page_number)
                ocr_review_image_pages.append(page.page_number)
                page.page_type = "ocr_review"
                page.preserved_review_image = True
                page.warnings.append(
                    "resultado OCR requer revisao: " + "; ".join(quality.reasons)
                )
                chunks.append(
                    _ocr_review_chunk(
                        page.page_number,
                        text,
                        image_path.relative_to(output_dir).as_posix(),
                        quality.quality,
                    )
                )
                continue

            chunks.append(_ocr_chunk(page.page_number, text))
            continue

        if extraction.rotated_text:
            rotated_text_pages.append(page.page_number)
            review_pages.append(page.page_number)
            image_path = _save_review_image(
                path,
                page.page_number,
                assets_dir,
                dpi=min(dpi, _REVIEW_IMAGE_DPI),
                suffix="texto_rotacionado",
            )
            asset_paths.append(image_path)
            page.preserved_review_image = True
            chunks.append(
                _visual_chunk(
                    page.page_number,
                    f"Texto rotacionado da página {page.page_number}",
                    native_text,
                    image_path.relative_to(output_dir).as_posix(),
                    extraction.selected_mode,
                    visual_type="rotated_text_review",
                    notice=(
                        "Texto rotacionado detectado. A imagem foi preservada para "
                        "conferência da ordem e orientação da leitura."
                    ),
                )
            )
            continue

        chunks.append(
            f"<!-- pagina_original: {page.page_number}; rota: native:pypdf; "
            f"modo: {extraction.selected_mode} -->\n\n"
            f"## Página {page.page_number}\n\n{native_text}\n"
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
        raster_table_pages=sorted(set(raster_table_pages)),
        diagram_pages=sorted(set(diagram_pages)),
        coordinate_register_pages=sorted(set(coordinate_register_pages)),
        map_candidate_pages=sorted(set(map_candidate_pages)),
        map_cover_pages=sorted(set(map_cover_pages)),
        ocr_review_image_pages=sorted(set(ocr_review_image_pages)),
        processing_seconds=round(time.perf_counter() - started, 3),
    )
    write_manifest(conversion_manifest, manifest_path)
    return markdown_path
