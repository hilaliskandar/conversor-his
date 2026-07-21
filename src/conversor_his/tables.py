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
_ZONE_CODE_RE = re.compile(
    r"\b(?:ZEIS|ZRU\d*|ZEC|ZAI|ZUR|ZPRA|SOU|SEI|CCSB|NUAR|NUR\d*|"
    r"Z[A-Z]{1,4}\d*|MZ\d+)\b",
    re.IGNORECASE,
)
_LEGAL_PREFIX_RE = re.compile(
    r"^(?:ART\.?\s*\d+|§|PARAGRAFO\b|[IVXLCDM]+\s*[-.)]|[A-Z]\s*[.)])",
    re.IGNORECASE,
)
_LEGAL_DEFINITION_RE = re.compile(
    r"^(?:[IVXLCDM]+\s*[-.)]|[A-Z]\s*[.)])\s+.{20,}:|^§\s*\d+",
    re.IGNORECASE,
)
_COORDINATE_RE = re.compile(r"\b[XY]\s*=\s*\d", re.IGNORECASE)
_EXPLICIT_TITLE_RE = re.compile(
    r"^(?:TABELA|QUADRO)\b|"
    r"^ANEXO\b.{0,180}\b(?:LISTAGEM|TABELA|QUADRO|PARAMETROS?|ZONAS?|ZEIS|"
    r"USOS?|INSTRUMENTOS?)\b",
    re.IGNORECASE,
)
_NOMINAL_TITLE_RE = re.compile(
    r"^(?:PARAMETROS?|INDICES?|INSTRUMENTOS?|LISTAGEM|REQUISITOS?)\b.{0,180}"
    r"\b(?:ZONA|ZONAS|URBANISTICOS?|EDILICIOS?|ZEIS|USOS?)\b",
    re.IGNORECASE,
)
_HEADER_GROUPS = {
    "territorial": re.compile(r"\b(?:ZONA|ZONAS|ZEIS|SETOR|AREA|MACROZONA)\b"),
    "identificador": re.compile(r"\b(?:CODIGO|NUMERO|N[Oº°]|LEI|DECRETO)\b"),
    "denominacao": re.compile(
        r"\b(?:COMUNIDADE|DENOMINACAO|LOCALIDADE|DESCRICAO|NOME)\b"
    ),
    "parametro": re.compile(
        r"\b(?:COEFICIENTE|TAXA|GABARITO|RECUO|APROVEITAMENTO|SOLO NATURAL|"
        r"TESTADA|LOTE MINIMO|AREA MINIMA|TO|TSN|CA|GM|LM|TM)\b"
    ),
    "instrumento": re.compile(
        r"\b(?:INSTRUMENTOS?|OUTORGA|TRANSFERENCIA|POLITICA URBANA)\b"
    ),
    "observacao": re.compile(r"\b(?:OBSERVACOES?|REQUISITOS? ESPECIAIS)\b"),
    "uso": re.compile(
        r"\b(?:USOS?|HABITACIONAL|RESIDENCIAL|NAO HABITACIONAL|MISTO)\b"
    ),
    "dimensao": re.compile(r"\b(?:M2|M²|METROS?|PAVTOS?|PAVIMENTOS?)\b"),
}
_URBAN_PARAMETER_PATTERNS = {
    "lote": re.compile(r"\b(?:LOTE|LM|AREA MINIMA)\b"),
    "testada": re.compile(r"\b(?:TESTADA|TM)\b"),
    "recuo": re.compile(r"\b(?:RECUO|FRONT|LATERAL|FUNDOS?|LAT|FUND)\b"),
    "ocupacao": re.compile(r"\b(?:TO|TAXA DE OCUPACAO)\b"),
    "solo_natural": re.compile(r"\b(?:TSN|SOLO NATURAL)\b"),
    "gabarito": re.compile(r"\b(?:GM|GABARITO|PAVTOS?|PAVIMENTOS?)\b"),
    "aproveitamento": re.compile(r"\b(?:CA|COEFICIENTE DE APROVEITAMENTO)\b"),
    "uso": re.compile(r"\b(?:USO|HABITACIONAL|RESIDENCIAL|MISTO|INDUSTRIAL)\b"),
}


def _ascii_upper(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(
        char for char in decomposed if not unicodedata.combining(char)
    ).upper()


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


def _stable_column_count(
    row_positions: list[list[int]],
    tolerance: int = 4,
) -> int:
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
    minimum_support = max(3, ceil(len(row_positions) * 0.35))
    return sum(1 for support in bins.values() if support >= minimum_support)


def _is_title_line(line: str) -> bool:
    normalized = _ascii_upper(" ".join(line.split()))
    if not normalized or len(normalized) > 220 or _LEGAL_PREFIX_RE.search(normalized):
        return False
    return bool(
        _EXPLICIT_TITLE_RE.search(normalized) or _NOMINAL_TITLE_RE.search(normalized)
    )


def _header_hits(text: str) -> list[str]:
    normalized = _ascii_upper(text)
    return [
        name for name, pattern in _HEADER_GROUPS.items() if pattern.search(normalized)
    ]


def _urban_parameter_hits(text: str) -> list[str]:
    normalized = _ascii_upper(text)
    return [
        name
        for name, pattern in _URBAN_PARAMETER_PATTERNS.items()
        if pattern.search(normalized)
    ]


def _best_header_window(lines: list[str]) -> tuple[int, int, list[str]] | None:
    best: tuple[tuple[int, int, int], int, int, list[str]] | None = None
    for start in range(len(lines)):
        for width in (1, 2, 3):
            end = start + width
            if end > len(lines):
                continue
            window_lines = lines[start:end]
            if any(
                _LEGAL_PREFIX_RE.search(_ascii_upper(line.strip()))
                for line in window_lines
            ):
                continue
            combined = " ".join(window_lines)
            hits = _header_hits(combined)
            urban_hits = _urban_parameter_hits(combined)
            separators = sum(
                max(len(_cell_starts(line)) - 1, 0) for line in window_lines
            )
            if len(hits) < 2 or separators < 2:
                continue
            rank = (len(hits) + len(urban_hits), separators, -start)
            if best is None or rank > best[0]:
                best = (rank, start, end, hits)
    if best is None:
        return None
    return best[1], best[2], best[3]


def _is_legal_list_line(line: str) -> bool:
    normalized = _ascii_upper(line.strip())
    return bool(
        _LEGAL_PREFIX_RE.search(normalized)
        or _LEGAL_DEFINITION_RE.search(normalized)
        or normalized.endswith(";")
    )


def _line_has_compact_values(line: str) -> bool:
    starts = _cell_starts(line)
    if len(starts) < 3:
        return False
    normalized = _ascii_upper(line)
    numbers = len(_NUMBER_RE.findall(line))
    return len(line.split()) <= 24 and (
        numbers >= 2 or bool(_ZONE_CODE_RE.search(normalized))
    )


def _empty_assessment(profile: str = "prose") -> TableAssessment:
    return TableAssessment(
        classification="not_table",
        suspected=False,
        score=0,
        row_count=0,
        stable_columns=0,
        content_profile=profile,
    )


def assess_table(text: str) -> TableAssessment:
    """Classifica estrutura tabular com regras calibradas para legislação urbana.

    A análise recebe o texto bruto em modo ``layout``. O detector combina cabeçalhos,
    posições recorrentes, códigos de zona, parâmetros urbanísticos e linhas compactas.
    Incisos, definições e coordenadas recebem penalização específica.
    """

    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if len(lines) < 3:
        return _empty_assessment()

    normalized_page = _ascii_upper("\n".join(lines))
    coordinate_lines = sum(bool(_COORDINATE_RE.search(line)) for line in lines)
    legal_lines_total = sum(_is_legal_list_line(line) for line in lines)
    multi_column_lines = sum(len(_cell_starts(line)) >= 3 for line in lines)
    aligned_value_lines = sum(_line_has_compact_values(line) for line in lines)
    numeric_aligned_lines = sum(
        len(_cell_starts(line)) >= 3 and len(_NUMBER_RE.findall(line)) >= 2
        for line in lines
    )
    zone_code_count = len(_ZONE_CODE_RE.findall(normalized_page))
    page_urban_hits = _urban_parameter_hits(normalized_page)

    if (
        coordinate_lines >= max(4, len(lines) // 3)
        and not _EXPLICIT_TITLE_RE.search(normalized_page)
    ):
        result = _empty_assessment("coordinates")
        result.multi_column_lines = multi_column_lines
        return result

    header = _best_header_window(lines)
    if header is None:
        legal_ratio = legal_lines_total / max(len(lines), 1)
        continuation_signal = (
            aligned_value_lines >= 3
            and zone_code_count >= 2
            and (len(page_urban_hits) >= 2 or aligned_value_lines >= 4)
            and legal_ratio <= 0.25
        )
        if continuation_signal:
            return TableAssessment(
                classification="continuation_candidate",
                suspected=False,
                score=7,
                row_count=multi_column_lines,
                stable_columns=0,
                reasons=[
                    "possivel continuacao de matriz urbanistica sem cabecalho local"
                ],
                legal_list_ratio=round(legal_ratio, 4),
                numeric_rows=numeric_aligned_lines,
                compact_value_rows=aligned_value_lines,
                multi_column_lines=multi_column_lines,
                urban_parameter_hits=page_urban_hits,
                zone_code_count=zone_code_count,
                content_profile="urban_matrix_continuation",
            )
        profile = "legal_list" if legal_lines_total >= len(lines) * 0.3 else "prose"
        return _empty_assessment(profile)

    header_start, header_end, header_hits = header
    title_nearby = any(
        _is_title_line(lines[index])
        for index in range(max(0, header_start - 5), header_start)
    )
    title_in_header = any(_is_title_line(line) for line in lines[header_start:header_end])
    title_evidence = title_nearby or title_in_header
    header_text = " ".join(lines[header_start:header_end])
    urban_hits = sorted(set(page_urban_hits + _urban_parameter_hits(header_text)))

    data_window = lines[header_end : header_end + 45]
    row_positions: list[list[int]] = []
    numeric_rows = 0
    compact_value_rows = 0
    legal_rows = 0
    prose_rows = 0

    for line in data_window:
        if _is_legal_list_line(line):
            legal_rows += 1
            continue
        starts = _cell_starts(line)
        word_count = len(line.split())
        numbers = len(_NUMBER_RE.findall(line))
        if len(starts) < 3:
            if word_count >= 14:
                prose_rows += 1
            continue
        row_positions.append(starts)
        if numbers >= 1:
            numeric_rows += 1
        if _line_has_compact_values(line):
            compact_value_rows += 1

    row_count = len(row_positions)
    stable_columns = _stable_column_count(row_positions)
    legal_list_ratio = legal_rows / max(len(data_window), 1)
    prose_ratio = prose_rows / max(len(data_window), 1)
    matrix_vocabulary = len(urban_hits) >= 4 or (
        "territorial" in header_hits
        and "uso" in header_hits
        and len(urban_hits) >= 2
    )

    score = 0
    reasons: list[str] = []
    if title_evidence:
        score += 3
        reasons.append("titulo tabular explicito associado ao cabecalho")
    if len(header_hits) >= 3:
        score += 3
        reasons.append("grupos semanticos de cabecalho em bloco local")
    elif len(header_hits) == 2 and matrix_vocabulary:
        score += 2
        reasons.append("cabecalho urbanistico especializado")
    if row_count >= 4:
        score += 2
        reasons.append("quatro ou mais linhas alinhadas")
    if 2 <= stable_columns <= 14:
        score += 2
        reasons.append("colunas recorrentes em quantidade plausivel")
    if numeric_rows >= 2:
        score += 1
        reasons.append("linhas com valores ou codigos numericos")
    if compact_value_rows >= 3:
        score += 2
        reasons.append("linhas compactas tipicas de matriz de parametros")
    if matrix_vocabulary:
        score += 3
        reasons.append("vocabulario convergente de matriz urbanistica")
    if zone_code_count >= 2:
        score += 2
        reasons.append("codigos de zonas recorrentes")
    if legal_list_ratio >= 0.30:
        score -= 4
        reasons.append("penalizacao por estrutura juridica enumerativa")
    if prose_ratio >= 0.30:
        score -= 2
        reasons.append("penalizacao por paragrafos extensos")

    strong_urban_matrix = (
        matrix_vocabulary
        and row_count >= 3
        and compact_value_rows >= 2
        and (zone_code_count >= 1 or numeric_rows >= 3)
        and legal_list_ratio <= 0.30
    )
    structured_listing = (
        title_evidence
        and len(header_hits) >= 3
        and row_count >= 4
        and numeric_rows >= 3
        and legal_list_ratio <= 0.20
        and prose_ratio <= 0.25
    )
    alignment_evidence = (
        2 <= stable_columns <= 14
        or strong_urban_matrix
        or structured_listing
        or (multi_column_lines >= 5 and zone_code_count >= 2)
    )
    candidate = (
        row_count >= 3
        and alignment_evidence
        and legal_list_ratio <= 0.35
        and prose_ratio <= 0.35
        and (title_evidence or numeric_rows >= 2 or strong_urban_matrix)
        and (len(header_hits) >= 2 or strong_urban_matrix)
    )
    confirmed = candidate and (
        structured_listing
        or (
            row_count >= 4
            and compact_value_rows >= 3
            and legal_list_ratio <= 0.20
            and prose_ratio <= 0.25
            and (title_evidence or len(header_hits) >= 3 or strong_urban_matrix)
        )
    )

    page_mixed = candidate and (header_start >= 10 or prose_ratio > 0.20)
    if confirmed and not page_mixed:
        classification = "confirmed"
    elif candidate and page_mixed:
        classification = "mixed_candidate"
    elif candidate:
        classification = "candidate"
    else:
        classification = "not_table"

    return TableAssessment(
        classification=classification,
        suspected=classification == "confirmed",
        score=score,
        row_count=row_count,
        stable_columns=stable_columns,
        header_hits=header_hits,
        reasons=reasons,
        header_line_index=header_start + 1,
        legal_list_ratio=round(legal_list_ratio, 4),
        prose_ratio=round(prose_ratio, 4),
        numeric_rows=numeric_rows,
        compact_value_rows=compact_value_rows,
        multi_column_lines=multi_column_lines,
        urban_parameter_hits=urban_hits,
        zone_code_count=zone_code_count,
        content_profile=(
            "mixed_urban_matrix"
            if page_mixed
            else "urban_matrix"
            if matrix_vocabulary
            else "generic_table"
        ),
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
