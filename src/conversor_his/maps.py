# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
from pathlib import Path

from .ocr.render import render_pdf_page

_MAP_WORD_RE = re.compile(r"\b(?:MAPA|PLANTA|CARTA|CROQUI)\b", re.IGNORECASE)
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


def is_map_page(text: str, image_count: int, max_text_chars: int = 700) -> bool:
    """Indica se a página deve ser tratada como conteúdo cartográfico.

    A heurística exige imagem e combina vocabulário cartográfico com uma camada
    textual curta. Isso evita classificar como mapa páginas normativas que apenas
    fazem referência a anexos cartográficos.
    """

    normalized = " ".join(text.split())
    if image_count < 1 or len(normalized) > max_text_chars:
        return False
    return bool(_MAP_WORD_RE.search(normalized) or _SPATIAL_RE.search(normalized))


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
) -> Path:
    """Renderiza e salva a página cartográfica integralmente como PNG."""

    assets_dir.mkdir(parents=True, exist_ok=True)
    image_path = assets_dir / f"pagina_{page_number:04d}_mapa.png"
    image = render_pdf_page(pdf_path, page_number, dpi=dpi)
    image.save(image_path, format="PNG", optimize=True)
    return image_path
