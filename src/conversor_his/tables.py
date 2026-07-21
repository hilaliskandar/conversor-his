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
_NUMBER_RE = re.compile(r"\d+(?:[.,/]\d+)?")
_LEGAL_PREFIX_RE = re.compile(
    r"^(?:ART\.?\s*\d+|§|PARAGRAFO\b|[IVXLCDM]+\s*[-.)]|[A-Z]\s*[.)])",
    re.IGNORECASE,
)
_EXPLICIT_TITLE_RE = re.compile(
    r"^(?:TABELA|QUADRO)\b|"
    r"^ANEXO\b.{0,140}\b(?:LISTAGEM|TABELA|QUADRO|PARAMETROS?|ZONAS?|ZEIS)\b",
    re.IGNORECASE,
)
_NOMINAL_TITLE_RE = re.compile(
    r"^(?:PARAMETROS?|INDICES?|INSTRUMENTOS?|LISTAGEM)\b.{0,140}"
    r"\b(?:ZONA|ZONAS|URBANISTICOS?|EDILICIOS?|ZEIS)\b",
    re.IGNORECASE,
)
_HEADER_GROUPS = {
    "territorial": re.compile(r"\b(?:ZONA|ZONAS|ZEIS|SETOR|AREA|MACROZONA)\b"),
    "identificador": re.compile(r"\b(?:CODIGO|NUMERO|N[Oº°]|LEI|DECRETO)\b"),
    "denominacao": re.compile(
        r"\b(?:COMUNIDADE|DENOMINACAO|LOCALIDADE|DESCRICAO|NOME)\b"
    ),
    "parametro": re.compile(
        r"\b(?:COEFICIENTE|TAXA|GABARITO|RECUO|APROVEITAMENTO|SOLO NATURAL)\b"
    ),
    "instrumento": re.compile(
        r"\b(?:INSTRUMENTOS?|OUTORGA|TRANSFERENCIA|POLITICA URBANA)\b"
    ),
    "observacao": re.compile(r"\bOBSERVACOES?\b"),
    "uso": re.compile(r"\bUSOS?\b"),
}


def _ascii_upper(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).upper()


def _cell_starts(line: str) -> list[int]:
    text = line.rstrip()
    first = re.search(r"\S", text)
    if first is None:
        return []

    starts = [first.start()]
    for gap in _INTERNAL_GAP_RE.finditer(text):
        if gap.end() < len(text):
            starts.append(gap.end())
    return sorted(set(starts))


def _stable_column_count(row_positions: list[list[int]], tolerance: int = 4) -> int:
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

    minimum_support = max(3, ceil(len(row_positions) * 0.40))
    return sum(1 for support in bins.values() if support >= minimum_support)


def _is_title_line(line: str) -> bool:
    normalized = _ascii_upper(" ".join(line.split()))
    if not normalized or len(normalized) > 180 or _LEGAL_PREFIX_RE.search(normalized):
        return False
    return bool(_EXPLICIT_TITLE_RE.search(normalized) or _NOMINAL_TITLE_RE.search(normalized))


def _header_hits(text: str) -> list[str]:
    normalized = _ascii_upper(text)
    return [name for name, pattern in _HEADER_GROUPS.items() if pattern.search(normalized)]


def _best_header_window(lines: list[str]) -> tuple[int, int, list[str]] | None:
    best: tuple[tuple[int, int, int], int, int, list[str]] | None = None

    for start in range(len(lines)):
        for width in (1, 2):
            end = start + width
            if end > len(lines):
                continue
            window_lines = lines[start:end]
            if any(_LEGAL_PREFIX_RE.search(_ascii_upper(line.strip())) for line in window_lines):
                continue
            hits = _header_hits(" ".join(window_lines))
            separators = sum(max(len(_cell_starts(line)) - 1, 0) for line in window_lines)
            if len(hits) < 3 or separators < 2:
                continue
            rank = (len(hits), separators, -start)
            if best is None or rank > best[0]:
                best = (rank, start, end, hits)

    if best is None:
        return None
    return best[1], best[2], best[3]


def _is_legal_list_line(line: str) -> bool:
    normalized = _ascii_upper(line.strip())
    return bool(_LEGAL_PREFIX_RE.search(normalized) or normalized.endswith(";"))


def assess_table(text: str) -> TableAssessment:
    """Classifica a página como não tabela, candidata ou tabela confirmada.

    A versão 0.5.1 exige cabeçalho local e linhas de dados subsequentes. Termos
    urbanísticos dispersos e recuos próprios de artigos, incisos e alíneas não são
    suficientes para alterar a rota de conversão.
    """

    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if len(lines) < 3:
        return TableAssessment(
            classification="not_table",
            suspected=False,
            score=0,
            row_count=0,
            stable_columns=0,
            header_hits=[],
            reasons=[],
        )

    header = _best_header_window(lines)
    if header is None:
        return TableAssessment(
            classification="not_table",
            suspected=False,
            score=0,
            row_count=0,
            stable_columns=0,
            header_hits=[],
            reasons=[],
        )

    header_start, header_end, header_hits = header
    title_nearby = any(
        _is_title_line(lines[index])
        for index in range(max(0, header_start - 4), header_start)
    )

    data_window = lines[header_end : header_end + 35]
    row_positions: list[list[int]] = []
    numeric_rows = 0
    legal_rows = 0

    for line in data_window:
        if _is_legal_list_line(line):
            legal_rows += 1
            continue
        starts = _cell_starts(line)
        if len(starts) < 3:
            continue
        row_positions.append(starts)
        if len(_NUMBER_RE.findall(line)) >= 1:
            numeric_rows += 1

    row_count = len(row_positions)
    stable_columns = _stable_column_count(row_positions)
    legal_list_ratio = legal_rows / max(len(data_window), 1)

    score = 0
    reasons: list[str] = []
    if title_nearby:
        score += 3
        reasons.append("titulo tabular explicito proximo ao cabecalho")
    if len(header_hits) >= 3:
        score += 3
        reasons.append("tres ou mais grupos de cabecalho em bloco local")
    if row_count >= 4:
        score += 2
        reasons.append("quatro ou mais linhas de dados candidatas")
    if 2 <= stable_columns <= 8:
        score += 2
        reasons.append("quantidade plausivel de colunas recorrentes")
    if numeric_rows >= 2:
        score += 1
        reasons.append("linhas de dados com valores ou codigos numericos")
    if legal_list_ratio <= 0.25:
        score += 1
        reasons.append("baixa predominancia de estrutura juridica enumerativa")

    candidate = (
        len(header_hits) >= 3
        and row_count >= 2
        and 2 <= stable_columns <= 8
        and legal_list_ratio < 0.50
    )
    confirmed = (
        candidate
        and row_count >= 4
        and numeric_rows >= 2
        and legal_list_ratio <= 0.35
        and (title_nearby or len(header_hits) >= 4)
    )

    if confirmed:
        classification = "confirmed"
    elif candidate:
        classification = "candidate"
    else:
        classification = "not_table"

    return TableAssessment(
        classification=classification,
        suspected=confirmed,
        score=score,
        row_count=row_count,
        stable_columns=stable_columns,
        header_hits=header_hits,
        reasons=reasons,
        header_line_index=header_start + 1,
        legal_list_ratio=round(legal_list_ratio, 4),
    )


def extract_table_title(text: str, page_number: int) -> str:
    lines = [" ".join(line.split()) for line in text.splitlines() if line.strip()]
    for line in lines:
        if _is_title_line(line):
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
