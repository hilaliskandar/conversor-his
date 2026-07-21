# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from math import ceil
from pathlib import Path

from .models import TableAssessment
from .ocr.render import render_pdf_page

_INTERNAL_GAP_RE = re.compile(r"(?<=\S) {2,}(?=\S)")
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
_STRONG_TITLE_RE = re.compile(
    r"\b(?:TABELA|QUADRO)\b|"
    r"\bPARAMETROS?\b.*\b(?:ZONA|URBANISTICOS?|EDILICIOS?)\b",
    re.IGNORECASE,
)
_HEADER_PATTERNS = {
    "zona": re.compile(r"\bZONA\b", re.IGNORECASE),
    "coeficiente": re.compile(r"\bCOEFICIENTE\b", re.IGNORECASE),
    "taxa": re.compile(r"\bTAXA\b", re.IGNORECASE),
    "aproveitamento": re.compile(r"\bAPROVEITAMENTO\b", re.IGNORECASE),
    "instrumentos": re.compile(r"\bINSTRUMENTOS?\b", re.IGNORECASE),
    "observacoes": re.compile(r"\bOBSERVACOES?\b", re.IGNORECASE),
    "uso": re.compile(r"\bUSOS?\b", re.IGNORECASE),
    "parametro": re.compile(r"\bPARAMETROS?\b", re.IGNORECASE),
}


def _ascii_upper(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).upper()


def _gap_positions(line: str) -> list[int]:
    return [match.start() for match in _INTERNAL_GAP_RE.finditer(line.rstrip())]


def _stable_column_count(row_positions: list[list[int]], tolerance: int = 3) -> int:
    if not row_positions:
        return 0

    bins: Counter[int] = Counter()
    for positions in row_positions:
        seen: set[int] = set()
        for position in positions:
            bucket = round(position / tolerance)
            if bucket not in seen:
                bins[bucket] += 1
                seen.add(bucket)

    minimum_support = max(3, ceil(len(row_positions) * 0.25))
    return sum(1 for support in bins.values() if support >= minimum_support)


def assess_table(text: str) -> TableAssessment:
    """Avalia sinais de estrutura tabular sem reconstruir células automaticamente.

    A heurística combina evidência semântica e alinhamento de colunas. Espaçamento
    isolado ou listas numéricas, como memoriais de coordenadas, não são suficientes.
    """

    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    normalized = _ascii_upper("\n".join(lines))
    if len(lines) < 3:
        return TableAssessment(
            suspected=False,
            score=0,
            row_count=0,
            stable_columns=0,
            header_hits=[],
            reasons=[],
        )

    header_hits = [
        name for name, pattern in _HEADER_PATTERNS.items() if pattern.search(normalized)
    ]
    strong_title = bool(_STRONG_TITLE_RE.search(normalized))

    row_positions: list[list[int]] = []
    numeric_rows = 0
    for line in lines:
        positions = _gap_positions(line)
        if len(positions) >= 2:
            row_positions.append(positions)
            if len(_NUMBER_RE.findall(line)) >= 2:
                numeric_rows += 1

    row_count = len(row_positions)
    stable_columns = _stable_column_count(row_positions)
    layout_ratio = row_count / len(lines)

    score = 0
    reasons: list[str] = []

    if strong_title:
        score += 4
        reasons.append("titulo ou identificador explicito de tabela/quadro")
    if len(header_hits) >= 2:
        score += 2
        reasons.append("cabecalhos semanticos tabulares identificados")
    if row_count >= 5 and layout_ratio >= 0.20:
        score += 2
        reasons.append("multiplas linhas com separadores de coluna")
    if stable_columns >= 2:
        score += 2
        reasons.append("posicoes de coluna recorrentes")
    if numeric_rows >= 4:
        score += 1
        reasons.append("linhas numericas compativeis com tabela")

    semantic_evidence = strong_title or len(header_hits) >= 2
    suspected = semantic_evidence and score >= 5

    return TableAssessment(
        suspected=suspected,
        score=score,
        row_count=row_count,
        stable_columns=stable_columns,
        header_hits=header_hits,
        reasons=reasons,
    )


def extract_table_title(text: str, page_number: int) -> str:
    lines = [" ".join(line.split()) for line in text.splitlines() if line.strip()]
    for line in lines:
        normalized = _ascii_upper(line)
        if _STRONG_TITLE_RE.search(normalized):
            return line[:180].strip(" .;:-")
    return f"Tabela ou quadro da página {page_number}"


def save_table_image(
    pdf_path: Path,
    page_number: int,
    assets_dir: Path,
    dpi: int = 200,
) -> Path:
    """Preserva a página tabular integral como imagem para conferência visual."""

    assets_dir.mkdir(parents=True, exist_ok=True)
    image_path = assets_dir / f"pagina_{page_number:04d}_tabela.png"
    image = render_pdf_page(pdf_path, page_number, dpi=dpi)
    image.save(image_path, format="PNG", optimize=True)
    return image_path
