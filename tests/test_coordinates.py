from conversor_his.coordinates import (
    assess_coordinate_register,
    should_classify_coordinate_register,
)
from conversor_his.models import TableAssessment


def test_detects_explicit_xy_coordinate_register() -> None:
    text = """
    POLIGONO 01 - COORDENADAS UTM SIRGAS 2000
    V1 X=278626.4005, Y=9096236.6289
    V2 X=278544.8185, Y=9091389.3200
    V3 X=278895.1132, Y=9096096.0164
    V4 X=278520.6786, Y=9091329.4602
    """

    result = assess_coordinate_register(text)

    assert result.detected is True
    assert result.pair_count == 4
    assert "utm" in result.keyword_hits
    assert "sirgas" in result.keyword_hits
    assert should_classify_coordinate_register(result) is True


def test_does_not_classify_ordinary_legal_numbers_as_coordinates() -> None:
    text = """
    Lei nº 916, de 25 de outubro de 2013.
    Art. 1º Fica alterado o artigo 70 da Lei Municipal nº 650/2008.
    Art. 2º Esta Lei entra em vigor na data de sua publicação.
    """

    result = assess_coordinate_register(text)

    assert result.detected is False
    assert result.pair_count == 0


def test_strong_table_precedes_coordinate_vocabulary() -> None:
    coordinates = assess_coordinate_register(
        "COORDENADAS UTM SIRGAS 2000 X=278626.4, Y=9096236.6; "
        "X=278544.8, Y=9091389.3; X=278895.1, Y=9096096.0; "
        "X=278520.6, Y=9091329.4"
    )
    table = TableAssessment(
        classification="confirmed",
        suspected=True,
        score=15,
        row_count=8,
        stable_columns=5,
        header_hits=["identificador", "denominacao"],
        visual_grid_detected=True,
        visual_grid_strong=True,
    )

    assert should_classify_coordinate_register(
        coordinates,
        table,
        visual_grid_strong=True,
    ) is False
