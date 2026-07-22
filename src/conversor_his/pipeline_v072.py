# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path

from . import __version__
from .coordinates import assess_coordinate_register, should_classify_coordinate_register
from .diagnostic import diagnose_pdf
from .extractors.pypdf_native import extract_native_pages_detailed
from .hashing import sha256_file
from .manifest import write_manifest
from .map_visual import MapVisualAssessment, assess_map_visual
from .maps import classify_map_page, extract_map_title, save_map_image
from .models import ConversionManifest, OcrQuality, RasterVisualAssessment, TableAssessment
from .ocr.quality import assess_ocr_quality
from .ocr.render import render_pdf_page
from .ocr.tesseract_engine import TesseractEngine
from .raster_visual import assess_raster_visual
from .tables import assess_table, extract_table_title, save_table_image
from .text_normalization import clean_invisible_characters, normalize_prose_text

_TABLE_IMAGE_DPI = 200
_RASTER_ANALYSIS_DPI = 150
_DIAGRAM_IMAGE_DPI = 250
_REVIEW_IMAGE_DPI = 300
_COORDINATE_IMAGE_DPI = 200
_MAP_ANALYSIS_DPI = 150

_LEGAL_MARKER_RE = re.compile(
    r"\b(?:LEI|ART\.?|ARTIGO|EMENDA|PREFEIT[OA]|CAMARA\s+MUNICIPAL|"
    r"SANCIONA|VIGOR|REVOGAD[AO]S?|ASSINATURA|DECRETO)\b",
    re.IGNORECASE,
)


@dataclass(slots=True)
class OcrPageEvidence:
    text: str
    quality: OcrQuality
    image: object
    raster: RasterVisualAssessment
    textual_table: TableAssessment
    coordinate: object
    map_visual: MapVisualAssessment


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
    *,
    visual_type: str,
    notice: str,
) -> str:
    normalized_text = normalize_prose_text(text)
    text_block = ""
    if normalized_text:
        text_block = (
            "\n\n> Texto associado à página visual, preservado para pesquisa e "
            "rastreabilidade. A interpretação espacial deve consultar a imagem.\n\n"
            "```text\n"
            f"{normalized_text}\n"
            "```\n"
        )
    return (
        f"<!-- pagina_original: {page_number}; tipo: {visual_type}; "
        f"rota: imagem+texto:{source_mode}; revisao: sim -->\n\n"
        f"## Página {page_number} — {title}\n\n"
        f"> {notice}\n\n"
        f"{_markdown_image(title, relative_image)}"
        f"{text_block}"
    )


def _table_chunk(
    page_number: int,
    title: str,
    text: str,
    relative_image: str,
    *,
    candidate: bool,
    raster: bool,
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


def _coordinate_chunk(page_number: int, text: str, relative_image: str) -> str:
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
        "foram classificados como decorativos recorrentes; o PDF original permanece "
        "como fonte visual de referência.\n"
    )


def _ocr_chunk(page_number: int, text: str) -> str:
    return (
        f"<!-- pagina_original: {page_number}; rota: ocr:tesseract+pdfium; "
        "revisao: nao -->\n\n"
        f"## Página {page_number}\n\n{normalize_prose_text(text)}\n"
    )


def _legal_false_positive(text: str, assessment: TableAssessment | None) -> bool:
    if assessment is None or assessment.visual_grid_detected:
        return False
    markers = len(_LEGAL_MARKER_RE.findall(text))
    return (
        markers >= 3
        and assessment.classification in {
            "candidate",
            "mixed_candidate",
            "continuation_candidate",
        }
        and len(assessment.header_hits) <= 2
        and len(assessment.urban_parameter_hits) <= 1
        and assessment.content_profile not in {"urban_matrix", "mixed_urban_matrix"}
    )


def _adjacent_table_context(
    page_number: int,
    evidence: dict[int, OcrPageEvidence],
    diagnosis_pages: list,
) -> bool:
    for neighbor_number in (page_number - 1, page_number + 1):
        neighbor = evidence.get(neighbor_number)
        if neighbor is not None and neighbor.raster.classification == "raster_table_candidate":
            return True
        if 1 <= neighbor_number <= len(diagnosis_pages):
            neighbor_page = diagnosis_pages[neighbor_number - 1]
            if neighbor_page.page_type in {"table", "table_candidate"}:
                return True
    return False


def _precompute_ocr_evidence(
    path: Path,
    diagnosis,
    ocr: TesseractEngine,
    dpi: int,
) -> dict[int, OcrPageEvidence]:
    evidence: dict[int, OcrPageEvidence] = {}
    for page in diagnosis.pages:
        if page.route != "ocr":
            continue
        analysis_image = render_pdf_page(
            path,
            page.page_number,
            dpi=min(_RASTER_ANALYSIS_DPI, dpi),
        )
        text, confidences = ocr.recognize_page_with_confidence(
            path,
            page.page_number,
            dpi=dpi,
        )
        quality = assess_ocr_quality(text, confidences)
        raster = assess_raster_visual(analysis_image, text)
        textual_table = assess_table(text)
        coordinate = assess_coordinate_register(text)
        map_visual = assess_map_visual(analysis_image)
        evidence[page.page_number] = OcrPageEvidence(
            text=text,
            quality=quality,
            image=analysis_image,
            raster=raster,
            textual_table=textual_table,
            coordinate=coordinate,
            map_visual=map_visual,
        )

    # Segunda passagem: grades parciais só são promovidas junto a tabela adjacente.
    for page_number, item in evidence.items():
        if item.raster.detected or not item.raster.partial_grid_detected:
            continue
        if not _adjacent_table_context(page_number, evidence, diagnosis.pages):
            continue
        item.raster = assess_raster_visual(
            item.image,
            item.text,
            allow_partial_context=True,
        )
    return evidence


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
    ocr_evidence = _precompute_ocr_evidence(path, diagnosis, ocr, dpi)

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

        # Candidatas cartográficas nativas recebem confirmação visual antes da rota.
        if page.route == "map":
            analysis_image = render_pdf_page(
                path,
                page.page_number,
                dpi=min(_MAP_ANALYSIS_DPI, dpi),
            )
            visual = assess_map_visual(analysis_image)
            map_class = classify_map_page(
                native_text,
                max(page.content_image_count, 1),
                visual_complexity=visual.visual_complexity,
            )
            if visual.cover_like and map_class != "map_confirmed":
                map_class = "map_cover"
            page.page_type = map_class
            title = extract_map_title(native_text, page.page_number)
            suffix = "capa_mapa" if map_class == "map_cover" else "mapa"
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
                notice = "Capa ou índice cartográfico preservado sem ser contado como mapa efetivo."
            elif map_class == "map_confirmed":
                map_pages.append(page.page_number)
                notice = "Conteúdo cartográfico confirmado por evidência textual e visual."
            else:
                map_candidate_pages.append(page.page_number)
                notice = "Possível conteúdo cartográfico preservado para revisão."
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
                    visual_type=map_class,
                    notice=notice,
                )
            )
            continue

        if page.route == "decorative":
            decorative_pages.append(page.page_number)
            chunks.append(_decorative_chunk(page.page_number, page.page_type))
            continue

        if page.page_type == "coordinate_register":
            # Na rota nativa, a precedência já foi resolvida no diagnóstico.
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

        if page.page_type == "table_candidate" and not _legal_false_positive(
            raw_native_text,
            page.table_assessment,
        ):
            image_path = save_table_image(
                path,
                page.page_number,
                assets_dir,
                dpi=min(dpi, _TABLE_IMAGE_DPI),
            )
            asset_paths.append(image_path)
            table_candidate_pages.append(page.page_number)
            review_pages.append(page.page_number)
            chunks.append(
                _table_chunk(
                    page.page_number,
                    extract_table_title(raw_native_text, page.page_number),
                    raw_native_text,
                    image_path.relative_to(output_dir).as_posix(),
                    candidate=True,
                    raster=False,
                )
            )
            continue

        if page.route == "structured":
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
                    extract_table_title(raw_native_text, page.page_number),
                    raw_native_text,
                    image_path.relative_to(output_dir).as_posix(),
                    candidate=False,
                    raster=False,
                )
            )
            continue

        if page.route == "ocr":
            used_ocr_pages.append(page.page_number)
            item = ocr_evidence[page.page_number]
            page.ocr_quality = item.quality
            page.raster_visual_assessment = item.raster
            page.coordinate_assessment = item.coordinate if item.coordinate.detected else None

            # Diagrama e tabela são decididos após OCR, para usar vocabulário explícito.
            if item.raster.classification == "diagram_candidate":
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
                        item.text,
                        image_path.relative_to(output_dir).as_posix(),
                        "ocr+raster",
                        visual_type="diagram_candidate",
                        notice="Estrutura visual preservada como possível fluxograma, esquema ou desenho técnico.",
                    )
                )
                continue

            if item.raster.classification == "raster_table_candidate":
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
                        item.text,
                        image_path.relative_to(output_dir).as_posix(),
                        candidate=True,
                        raster=True,
                    )
                )
                continue

            if should_classify_coordinate_register(
                item.coordinate,
                item.textual_table,
                visual_grid_strong=item.raster.strong,
            ):
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
                        item.text,
                        image_path.relative_to(output_dir).as_posix(),
                    )
                )
                continue

            map_class = classify_map_page(
                item.text,
                max(page.image_count, 1),
                visual_complexity=item.map_visual.visual_complexity,
            )
            if item.map_visual.cover_like and map_class != "map_confirmed":
                map_class = "map_cover"
            if map_class in {"map_candidate", "map_confirmed", "map_cover"}:
                page.page_type = map_class
                page.route = "map"
                suffix = "capa_mapa" if map_class == "map_cover" else "mapa"
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
                    notice = "Capa ou índice cartográfico preservado."
                elif map_class == "map_confirmed":
                    map_pages.append(page.page_number)
                    notice = "Conteúdo cartográfico confirmado por evidência textual e visual."
                else:
                    map_candidate_pages.append(page.page_number)
                    notice = "Possível conteúdo cartográfico preservado para revisão."
                chunks.append(
                    _visual_chunk(
                        page.page_number,
                        extract_map_title(item.text, page.page_number),
                        item.text,
                        image_path.relative_to(output_dir).as_posix(),
                        "ocr",
                        visual_type=map_class,
                        notice=notice,
                    )
                )
                continue

            if item.quality.requires_review:
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
                chunks.append(
                    _ocr_review_chunk(
                        page.page_number,
                        item.text,
                        image_path.relative_to(output_dir).as_posix(),
                        item.quality.quality,
                    )
                )
                continue

            chunks.append(_ocr_chunk(page.page_number, item.text))
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
                    notice="Texto rotacionado detectado; imagem preservada para conferência.",
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
