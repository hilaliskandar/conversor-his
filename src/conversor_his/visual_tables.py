# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from .models import TableAssessment

_MIN_HORIZONTAL_LENGTH = 20.0
_MAX_LINE_THICKNESS = 2.5
_MIN_VERTICAL_LENGTH = 8.0

_LEGAL_MARKERS = {
    "lei": re.compile(r"\bLEI\s+(?:N|NO|NUMERO)\b"),
    "artigo": re.compile(r"\bART\.?\s*\d+"),
    "prefeito": re.compile(r"\bPREFEIT[OA]\b"),
    "camara": re.compile(r"\bCAMARA\s+MUNICIPAL\b"),
    "sancao": re.compile(r"\bSANCIONA\b"),
    "vigencia": re.compile(r"\bENTRARA?\s+EM\s+VIGOR\b"),
    "revogacao": re.compile(r"\bREVOGAD[AO]S?\b"),
    "providencias": re.compile(r"\bPROVIDENCIAS\b"),
}


@dataclass(slots=True)
class VisualGridEvidence:
    detected: bool
    strong: bool
    score: int
    rectangle_count: int
    horizontal_lines: int
    vertical_lines: int
    reasons: list[str] = field(default_factory=list)


def _ascii_upper(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(
        char for char in decomposed if not unicodedata.combining(char)
    ).upper()


def assess_vector_grid(page: Any) -> VisualGridEvidence:
    """Obtém evidência de grade diretamente das operações vetoriais do PDF.

    Tabelas produzidas por editores de texto e planilhas costumam representar cada
    borda como um retângulo muito fino. A contagem é independente do texto extraído
    e evita renderizar todas as páginas apenas para localizar linhas de grade.
    """

    rectangle_count = 0
    horizontal_lines = 0
    vertical_lines = 0
    reasons: list[str] = []

    try:
        contents = page.get_contents()
        operations = [] if contents is None else getattr(contents, "operations", [])
        for operands, operator in operations:
            if operator != b"re" or len(operands) < 4:
                continue
            try:
                _, _, width, height = (float(value) for value in operands[:4])
            except (TypeError, ValueError):
                continue

            rectangle_count += 1
            abs_width = abs(width)
            abs_height = abs(height)
            if (
                abs_height <= _MAX_LINE_THICKNESS
                and abs_width >= _MIN_HORIZONTAL_LENGTH
            ):
                horizontal_lines += 1
            if (
                abs_width <= _MAX_LINE_THICKNESS
                and abs_height >= _MIN_VERTICAL_LENGTH
            ):
                vertical_lines += 1
    except Exception as exc:  # pragma: no cover - PDF corrompido ou backend incomum
        return VisualGridEvidence(
            detected=False,
            strong=False,
            score=0,
            rectangle_count=rectangle_count,
            horizontal_lines=horizontal_lines,
            vertical_lines=vertical_lines,
            reasons=[f"evidencia vetorial indisponivel: {type(exc).__name__}"],
        )

    detected = (
        rectangle_count >= 10
        and horizontal_lines >= 4
        and vertical_lines >= 3
    )
    strong = (
        rectangle_count >= 16
        and horizontal_lines >= 8
        and vertical_lines >= 6
    )

    score = 0
    if detected:
        score += 3
        reasons.append("grade vetorial com linhas horizontais e verticais")
    if strong:
        score += 3
        reasons.append("grade vetorial forte e repetitiva")
    score += min(horizontal_lines, 20) // 4
    score += min(vertical_lines, 20) // 3

    return VisualGridEvidence(
        detected=detected,
        strong=strong,
        score=score,
        rectangle_count=rectangle_count,
        horizontal_lines=horizontal_lines,
        vertical_lines=vertical_lines,
        reasons=reasons,
    )


def _legal_marker_count(text: str) -> int:
    normalized = _ascii_upper(text)
    return sum(bool(pattern.search(normalized)) for pattern in _LEGAL_MARKERS.values())


def merge_visual_table_evidence(
    assessment: TableAssessment,
    evidence: VisualGridEvidence,
    raw_text: str,
) -> TableAssessment:
    """Combina evidência textual e vetorial sem forçar certeza indevida."""

    assessment.visual_grid_detected = evidence.detected
    assessment.visual_grid_strong = evidence.strong
    assessment.visual_grid_score = evidence.score
    assessment.vector_rectangle_count = evidence.rectangle_count
    assessment.vector_horizontal_lines = evidence.horizontal_lines
    assessment.vector_vertical_lines = evidence.vertical_lines

    for reason in evidence.reasons:
        if reason not in assessment.reasons:
            assessment.reasons.append(reason)

    if evidence.detected and assessment.classification == "not_table":
        assessment.classification = "visual_candidate"
        assessment.suspected = False
        assessment.score += evidence.score
        assessment.content_profile = "visual_grid"
        return assessment

    # Emendas legais de página única podem imitar colunas por causa do modo layout.
    # Sem grade vetorial, título tabular ou vocabulário matricial, a prosa jurídica
    # deve prevalecer sobre alinhamentos artificiais.
    has_explicit_title = any("titulo tabular" in reason for reason in assessment.reasons)
    legal_prose = (
        assessment.classification == "candidate"
        and assessment.content_profile == "generic_table"
        and assessment.legal_list_ratio >= 0.20
        and len(assessment.header_hits) <= 2
        and not has_explicit_title
        and _legal_marker_count(raw_text) >= 3
    )
    if not evidence.detected and legal_prose:
        assessment.classification = "not_table"
        assessment.suspected = False
        assessment.reasons.append(
            "reclassificada como prosa juridica: sem grade vetorial e com marcadores legais"
        )
        assessment.content_profile = "legal_amendment"

    return assessment
