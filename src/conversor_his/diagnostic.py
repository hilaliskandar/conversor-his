# SPDX-License-Identifier: MIT
from __future__ import annotations

from pathlib import Path

from .coordinates import assess_coordinate_register
from .extractors.pypdf_native import (
    NativeTextExtraction,
    count_page_images,
    extract_page_text_detailed,
    open_pdf,
)
from .graphics import analyze_repeated_graphics
from .graphics_policy import refine_confirmed_decorative_graphics
from .hashing import sha256_file
from .maps import classify_map_page
from .models import DocumentDiagnosis, PageDiagnosis
from .tables import assess_table
from .visual_tables import assess_vector_grid, merge_visual_table_evidence

_TABLE_CANDIDATE_CLASSES = {
    "candidate",
    "mixed_candidate",
    "continuation_candidate",
    "visual_candidate",
}


def diagnose_pdf(
    path: Path,
    min_native_chars: int = 40,
    native_extractions: dict[int, NativeTextExtraction] | None = None,
) -> DocumentDiagnosis:
    reader = open_pdf(path)
    graphic_summaries, repeated_graphics = analyze_repeated_graphics(reader)
    graphic_summaries = refine_confirmed_decorative_graphics(
        reader,
        graphic_summaries,
        repeated_graphics,
    )
    pages: list[PageDiagnosis] = []
    page_count = len(reader.pages)

    for index, page in enumerate(reader.pages, start=1):
        extraction = (
            native_extractions[index]
            if native_extractions is not None and index in native_extractions
            else extract_page_text_detailed(page)
        )
        text = extraction.text
        raw_text = extraction.raw_text
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
        map_class = classify_map_page(text, content_image_count)
        coordinate_assessment = assess_coordinate_register(raw_text)
        table_assessment = assess_table(raw_text)
        vector_evidence = assess_vector_grid(page)
        table_assessment = merge_visual_table_evidence(
            table_assessment,
            vector_evidence,
            raw_text,
        )

        # Registros de coordenadas são preservados, mas não entram na métrica tabular.
        if coordinate_assessment.detected:
            table_assessment.classification = "not_table"
            table_assessment.suspected = False
            table_assessment.content_profile = "coordinates"

        suspected_table = table_assessment.classification == "confirmed"
        table_candidate = table_assessment.classification in _TABLE_CANDIDATE_CLASSES
        has_native = char_count >= min_native_chars
        decorative_only = (
            char_count == 0
            and raw_image_count > 0
            and content_image_count == 0
            and raw_image_count == decorative_image_count
        )

        if map_class in {"map_confirmed", "map_candidate", "map_cover"}:
            route = "map"
            page_type = map_class
        elif decorative_only:
            route = "decorative"
            page_type = "back_cover" if index == page_count else "decorative_only"
        elif coordinate_assessment.detected and has_native:
            route = "native"
            page_type = "coordinate_register"
        elif suspected_table:
            route = "structured"
            page_type = "table"
        elif has_native:
            route = "native"
            page_type = "table_candidate" if table_candidate else "text"
        else:
            route = "ocr"
            page_type = "unknown"

        page_warnings: list[str] = []
        if map_class == "map_confirmed":
            page_warnings.append("conteudo cartografico confirmado: preservar imagem e texto")
        elif map_class == "map_candidate":
            page_warnings.append("possivel conteudo cartografico: preservar para revisao")
        elif map_class == "map_cover":
            page_warnings.append("capa ou indice cartografico: preservar sem contar como mapa")
        elif decorative_only:
            page_warnings.append("pagina exclusivamente decorativa: OCR dispensado")
        elif coordinate_assessment.detected:
            page_warnings.append(
                "registro de coordenadas: preservar imagem e texto em classe propria"
            )
        elif suspected_table:
            page_warnings.append(
                "estrutura tabular confirmada: preservar imagem e exigir revisao estrutural"
            )
        elif table_candidate:
            label = table_assessment.classification.replace("_", " ")
            page_warnings.append(
                f"{label}: preservar texto bruto e imagem para revisao estrutural"
            )
        elif 0 < char_count < min_native_chars:
            page_warnings.append("camada textual insuficiente")
        if vector_evidence.detected:
            page_warnings.append(
                "grade vetorial detectada: bordas tabulares preservadas como evidencia"
            )
        if content_image_count and has_native and map_class == "none":
            page_warnings.append("pagina hibrida: texto e imagem relevante")
        if not char_count and not raw_image_count:
            page_warnings.append("pagina sem texto ou imagem detectavel")
        if extraction.rotated_text:
            page_warnings.append(
                f"texto rotacionado detectado; extracao selecionada: {extraction.selected_mode}"
            )
        if extraction.warnings:
            page_warnings.append("avisos da extracao nativa registrados")

        pages.append(
            PageDiagnosis(
                page_number=index,
                has_native_text=has_native,
                character_count=char_count,
                image_count=content_image_count,
                raw_image_count=raw_image_count,
                decorative_image_count=decorative_image_count,
                content_image_count=content_image_count,
                suspected_table=suspected_table,
                suspected_map=map_class in {"map_confirmed", "map_candidate"},
                page_type=page_type,
                route=route,
                warnings=page_warnings,
                table_assessment=(
                    table_assessment
                    if table_assessment.classification != "not_table"
                    else None
                ),
                coordinate_assessment=(
                    coordinate_assessment if coordinate_assessment.detected else None
                ),
                native_extraction_mode=extraction.selected_mode,
                layout_character_count=extraction.layout_character_count,
                simple_character_count=extraction.simple_character_count,
                rotated_text_detected=extraction.rotated_text,
                extraction_warnings=extraction.warnings,
            )
        )

    return DocumentDiagnosis(
        source_path=path,
        sha256=sha256_file(path),
        page_count=page_count,
        pages=pages,
        repeated_graphics=repeated_graphics,
    )
