from __future__ import annotations

from conversor_his.tables import assess_table


def test_detects_explicit_urban_parameters_table() -> None:
    text = """
ANEXO VI
PARAMETROS E INSTRUMENTOS URBANISTICOS POR ZONA
ZONA                  coeficiente de              taxa de solo          instrumentos da             observacoes
                      aproveitamento              natural (%)           politica urbana
ZAA                              3,0                        25            DP, PEUC, IP                 1, 2, 3, 4
ZAM                              2,5                        25            DP, PEUC, IP                 1, 2, 3, 4
ZAB                              1,5                        30            DP, PEUC, IP                 1, 2, 3, 4
ZAR                              1,5                        30            DP, OUC, OO                  1, 2, 3, 4
ZIP 1                            1,2                        20            OUC, OO                     1, 2, 3, 4
"""

    result = assess_table(text)

    assert result.suspected is True
    assert result.score >= 5
    assert result.stable_columns >= 2
    assert "zona" in result.header_hits


def test_coordinate_list_is_not_table_without_semantic_evidence() -> None:
    text = """
Zona de Expansao Urbana - ZEU
POLIGONO 01
X=278626.4005, Y=9096236.6289;       X=278544.8185, Y=9091389.3200;
X=278895.1132, Y=9096096.0164;       X=278520.6786, Y=9091329.4602;
X=279013.9179, Y=9095979.2113;       X=278453.6552, Y=9091212.6406;
X=278994.3980, Y=9095935.8071;       X=278397.0989, Y=9091190.3000;
X=278950.1000, Y=9095800.2000;       X=278300.1000, Y=9091100.2000;
"""

    result = assess_table(text)

    assert result.suspected is False
