from __future__ import annotations

from dataclasses import dataclass

from conversor_his.models import TableAssessment
from conversor_his.visual_tables import (
    assess_vector_grid,
    merge_visual_table_evidence,
)


@dataclass
class _FakeContents:
    operations: list[tuple[list[float], bytes]]


@dataclass
class _FakePage:
    operations: list[tuple[list[float], bytes]]

    def get_contents(self) -> _FakeContents:
        return _FakeContents(self.operations)


def _rectangle(width: float, height: float) -> tuple[list[float], bytes]:
    return ([0.0, 0.0, width, height], b"re")


def _empty_assessment() -> TableAssessment:
    return TableAssessment(
        classification="not_table",
        suspected=False,
        score=0,
        row_count=0,
        stable_columns=0,
    )


def test_detects_vector_grid_from_thin_rectangles() -> None:
    operations = [
        *[_rectangle(400.0, 0.5) for _ in range(12)],
        *[_rectangle(0.5, 40.0) for _ in range(9)],
    ]

    evidence = assess_vector_grid(_FakePage(operations))

    assert evidence.detected is True
    assert evidence.strong is True
    assert evidence.horizontal_lines == 12
    assert evidence.vertical_lines == 9


def test_promotes_textual_negative_when_vector_grid_is_present() -> None:
    operations = [
        *[_rectangle(300.0, 0.5) for _ in range(8)],
        *[_rectangle(0.5, 30.0) for _ in range(6)],
    ]
    evidence = assess_vector_grid(_FakePage(operations))

    result = merge_visual_table_evidence(
        _empty_assessment(),
        evidence,
        "Quadro de vias, descrição e intervenções",
    )

    assert result.classification == "visual_candidate"
    assert result.visual_grid_detected is True
    assert result.vector_horizontal_lines == 8
    assert result.vector_vertical_lines == 6


def test_does_not_detect_page_border_as_table_grid() -> None:
    operations = [
        _rectangle(500.0, 0.5),
        _rectangle(0.5, 700.0),
        _rectangle(500.0, 0.5),
        _rectangle(0.5, 700.0),
    ]

    evidence = assess_vector_grid(_FakePage(operations))

    assert evidence.detected is False
    assert evidence.strong is False


def test_rejects_legal_amendment_without_vector_grid() -> None:
    assessment = TableAssessment(
        classification="candidate",
        suspected=False,
        score=7,
        row_count=4,
        stable_columns=6,
        header_hits=["identificador", "uso"],
        legal_list_ratio=0.25,
        numeric_rows=2,
        compact_value_rows=2,
        multi_column_lines=11,
        urban_parameter_hits=["uso"],
        zone_code_count=4,
        content_profile="generic_table",
    )
    evidence = assess_vector_grid(_FakePage([]))
    text = """
LEI Nº 916, DE 25 DE OUTUBRO DE 2013.
Altera o Art. 70 da Lei Municipal nº 650/2008 e dá outras providências.
O Prefeito faz saber que a Câmara Municipal aprovou e ele sanciona a seguinte lei:
Art. 1º O artigo passa a vigorar com a seguinte redação.
Art. 2º Esta Lei entra em vigor na data de sua publicação.
"""

    result = merge_visual_table_evidence(assessment, evidence, text)

    assert result.classification == "not_table"
    assert result.content_profile == "legal_amendment"
    assert result.visual_grid_detected is False
