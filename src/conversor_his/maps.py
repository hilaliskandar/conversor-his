# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from .ocr.render import render_pdf_page

MapTextClass = Literal["none", "map_candidate", "map_confirmed", "map_cover"]

_MAP_WORD_RE = re.compile(r"\b(?:MAPA|MAPAS|PLANTA|PLANTAS|CARTA|CARTAS|CROQUI)\b", re.IGNORECASE)
_MAP_TITLE_RE = re.compile(
    r"\b(?:MAPA|PLANTA|CARTA|CROQUI)\b(?:\s+(?:N[º°.]?\s*)?[A-Z0-9IVXLCDM.-]+)?"
    r"(?:\s*[-–—:]\s*[^\n]{1,150})?",
    re.IGNORECASE,
)
_SPATIAL_RE = re.compile(
    r"\b(?:ZONEAMENTO|MACROZONEAMENTO|SISTEMA\s+VI[ÁA]RIO|PER[ÍI]METRO\s+URBANO|"
    r"USO\s+E\s+OCUPA[CÇ][AÃ]O|[ÁA]REAS?\s+DE\s+RISCO)\b",
    re.IGNORECASE,
)
_CARTOGRAPHIC_EVIDENCE_RE = re.compile(
    r"\b(?:LEGENDA|ESCALA|NORTE|SIRGAS|UTM|COORDENADAS?|PROJE[CÇ][AÃ]O|DATUM|"
    r"MERIDIANO|FUSO|FONTE\s+CARTOGR[ÁA]FICA)\b",
    re.IGNORECASE,
)
_COVER_RE = re.compile(
    r"\b(?:ANEXO\s+(?:CARTOGR[ÁA]FICO|DE\s+MAPAS?)|CADERNO\s+DE\s+MAPAS?|"
    r"[ÍI]NDICE\s+(?:DE\s+)?MAPAS?|RELA[CÇ][AÃ]O\s+DE\s+MAPAS?|"
    r"LISTA\s+DE\s+MAPAS?|MAPAS?\s+ANEXOS?|ANEXOS?\s+[-–—:]?\s*MAPAS?)\b",
    re.IGNORECASE,
)
_COVER_LAYOUT_RE = re.compile(
    r"^(?:ANEXO|AP[EÊ]NDICE|CADERNO|MAPA|PLANTA)\b.{0,180}$",
    re.IGNORECASE,
)


def classify_map_page(
    text: str,
    image_count: int,
    *,
    visual_complexity: bool = False,
    max_text_chars: int = 700,
) -> MapTextClass:
    """Classifica evidência cartográfica sem confundir capa e mapa efetivo."""

    normalized = " ".join(text.split())
    if image_count < 1 or len(normalized) > max_text_chars:
        return "none"

    has_map_word = bool(
        _MAP_WORD_RE.search(normalized) or _SPATIAL_RE.search(normalized)
    )
    if not has_map_word:
        return "none"

    has_cartographic_evidence = bool(_CARTOGRAPHIC_EVIDENCE_RE.search(normalized))
    cover_signal = bool(_COVER_RE.search(normalized))
    short_title_page = (
        len(normalized) <= 180
        and bool(_COVER_LAYOUT_RE.search(normalized))
        and not has_cartographic_evidence
    )
    if (cover_signal or short_title_page) and not visual_complexity:
        return "map_cover"

    evidence_count = sum(
        (
            bool(_MAP_WORD_RE.search(normalized)),
            bool(_SPATIAL_RE.search(normalized)),
            has_cartographic_evidence,
            visual_complexity,
        )
    )

    # Legenda, escala, datum ou coordenadas constituem evidência cartográfica
    # forte mesmo quando a complexidade visual ainda não foi calculada.
    if has_cartographic_evidence and evidence_count >= 2:
        return "map_confirmed"
    if evidence_count >= 2 and visual_complexity:
        return "map_confirmed"
    return "map_candidate"


def is_map_page(text: str, image_count: int, max_text_chars: int = 700) -> bool:
    """Compatibilidade: indica mapa confirmado ou candidato, não capa."""

    return classify_map_page(
        text,
        image_count,
        max_text_chars=max_text_chars,
    ) in {"map_candidate", "map_confirmed"}


def extract_map_title(text: str, page_number: int) -> str:
    """Extrai um título curto e estável para a referência cartográfica."""

    lines = [" ".join(line.split()) for line in text.splitlines() if line.strip()]
    for line in lines:
        match = _MAP_TITLE_RE.search(line)
        if match:
            return match.group(0).strip(" .;:-")
    for line in lines:
        if _SPATIAL_RE.search(line):
            return line[:160].strip(" .;:-")
    return f"Mapa da página {page_number}"


def save_map_image(
    pdf_path: Path,
    page_number: int,
    assets_dir: Path,
    dpi: int = 200,
    suffix: str = "mapa",
) -> Path:
    """Renderiza e salva a página cartográfica integralmente como PNG."""

    assets_dir.mkdir(parents=True, exist_ok=True)
    image_path = assets_dir / f"pagina_{page_number:04d}_{suffix}.png"
    image = render_pdf_page(pdf_path, page_number, dpi=dpi)
    image.save(image_path, format="PNG", optimize=True)
    return image_path
