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
    assert result.classification == "confirmed"
    assert result.suspected is True
    assert 2 <= result.stable_columns <= 14
    assert "territorial" in result.header_hits


def test_detects_realistic_abreu_e_lima_parameter_matrix() -> None:
    text = """
ZRU3      Habitacional   Unifamiliar   ou   Multifamiliar          200         10,00      5,00      1,50      1,50      40     30       2           0,3    D, I, J, K
          Misto                                                    200         10,00      5,00      1,50      1,50      50     30       2           0,5    D, I, J, K, Z
ZAI       Não Residencial (Industrial)                             20.000      100,00     20,00     10,00     5,00      70     20       -           1,0    P, S
ZUR       Empreendimentos de Lazer/Recreação                       Análise Especial                                                                        O
                                                                                   Recuo
 ZONA                          USO                         LM (m²)     TM (m²)     Mínimo           TO (%)         TSN (%)        GM (pavto)       CA       Requisitos Especiais
                                                                                Front     Lat     Fund.
MACROZONA RURAL ALDEIA - MZ2
NUAR         Habitacional Unifamiliar ou Multifamiliar             200         10,00      5,00      1,50      1,50      50     30       2           0,5    D, I, J, K
NUR21        Empreendimentos de Lazer e Turismo Rural               Análise Especial                                                                        O
"""
    result = assess_table(text)
    assert result.classification in {"confirmed", "mixed_candidate", "candidate"}
    assert result.classification != "not_table"
    assert len(result.urban_parameter_hits) >= 4
    assert result.zone_code_count >= 2


def test_detects_urban_matrix_continuation_without_repeated_header() -> None:
    text = """
132/150
NUR21        Misto                                       200        10,00     5,00     1,50    1,50      50         30          2            0,5       D, I, J, K, Z
ZLPF         Uso habitacional condicionado               1.000      20,00     10,00    5,00    5,00      20         70          2            0,0       W
ZPPF         Empreendimentos de lazer                     Análise Especial                                                        O
Parâmetros de lote, testada, recuo, TO, TSN, gabarito GM e coeficiente CA permanecem os mesmos.
"""
    result = assess_table(text)
    assert result.classification == "continuation_candidate"
    assert result.content_profile == "urban_matrix_continuation"


def test_preserves_zeis_listing_as_table_candidate() -> None:
    text = """
ANEXO V - LISTAGEM DAS ZEIS INSTITUIDAS EM LEIS ANTERIORES
ZEIS         COMUNIDADE                         LEI             DECRETO
1            Aritana                            114/91          068/91
2            N.S. do Carmo                      114/91          069/91
3            Santa Fe                           114/91          078/91
4            Carolinas                          114/91          072/91
5            Lagoa Azul                         114/91          080/91
"""
    result = assess_table(text)
    assert result.classification in {"candidate", "confirmed"}
    assert result.classification != "not_table"
    assert "territorial" in result.header_hits
    assert "denominacao" in result.header_hits
    assert "identificador" in result.header_hits
    assert result.row_count >= 3


def test_legal_directives_are_not_table() -> None:
    text = """
Art. 31. A Zona de Adensamento Construtivo Baixo corresponde aos assentamentos.
I- promocao da estruturacao de novas ocupacoes mediante saneamento ambiental;
II- estabelecimento de parametros urbanisticos compativeis com as caracteristicas;
III- eliminacao da situacao de risco de alagamentos;
IV- priorizacao dos investimentos para melhoria da infraestrutura;
V- normatizacao do uso e ocupacao do solo nos morros;
VI- promocao da gestao integrada das areas de morros.
"""
    result = assess_table(text)
    assert result.classification == "not_table"
    assert result.suspected is False


def test_legal_definitions_with_tabular_words_are_not_table() -> None:
    text = """
Art. 4º Tem-se, para efeitos desta Lei, as seguintes definições:
TERRITORIAL       IDENTIFICADOR       USO
I - núcleo urbano: assentamento humano destinado a uso urbano, ainda que situado em área rural;
II - núcleo urbano informal: aquele clandestino ou irregular, no qual não foi possível a titulação;
III - núcleo urbano consolidado: aquele de difícil reversão, considerados o tempo da ocupação;
IV - núcleo urbano de uso não residencial: assentamento caracterizado pelo parcelamento irregular;
V - núcleo urbano de vinculação: áreas ocupadas ou vazias destinadas à provisão habitacional;
§ 1º A regularização somente poderá ser aplicada aos núcleos comprovadamente existentes.
"""
    result = assess_table(text)
    assert result.classification == "not_table"
    assert result.suspected is False


def test_coordinate_list_is_not_table_without_local_header() -> None:
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
    assert result.classification == "not_table"
    assert result.suspected is False
    assert result.content_profile == "coordinates"
