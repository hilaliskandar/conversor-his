from __future__ import annotations

from PIL import Image, ImageDraw

from conversor_his.coordenadas import avaliar_registro_de_coordenadas
from conversor_his.diagnostico import diagnosticar_pdf
from conversor_his.lote import converter_lote_zip
from conversor_his.manifesto import escrever_manifesto
from conversor_his.mapas import classificar_pagina_de_mapa
from conversor_his.modelos import (
    AvaliacaoDeCoordenadas,
    AvaliacaoDeTabela,
    AvaliacaoVisualRaster,
    ManifestoDeConversao,
)
from conversor_his.normalizacao_texto import normalizar_texto_de_prosa
from conversor_his.tabelas import avaliar_tabela
from conversor_his.visual_mapa import avaliar_visual_de_mapa
from conversor_his.visual_raster import avaliar_visual_raster


def test_api_publica_em_portugues_esta_disponivel() -> None:
    assert callable(avaliar_registro_de_coordenadas)
    assert callable(avaliar_tabela)
    assert callable(avaliar_visual_de_mapa)
    assert callable(avaliar_visual_raster)
    assert callable(classificar_pagina_de_mapa)
    assert callable(converter_lote_zip)
    assert callable(diagnosticar_pdf)
    assert callable(escrever_manifesto)
    assert callable(normalizar_texto_de_prosa)
    assert AvaliacaoDeCoordenadas.__name__ == "CoordinateAssessment"
    assert AvaliacaoDeTabela.__name__ == "AvaliacaoDeTabela"
    assert AvaliacaoVisualRaster.__name__ == "AvaliacaoVisualRaster"
    assert ManifestoDeConversao.__name__ == "ConversionManifest"


def test_funcoes_portuguesas_preservam_comportamento() -> None:
    texto = "Art.     1º\u200b     Esta     Lei"
    assert normalizar_texto_de_prosa(texto) == "Art. 1º Esta Lei"

    coordenadas = avaliar_registro_de_coordenadas(
        "COORDENADAS UTM X=278626.4, Y=9096236.6; "
        "X=278544.8, Y=9091389.3; X=278895.1, Y=9096096.0; "
        "X=278520.6, Y=9091329.4"
    )
    assert coordenadas.detected is True

    assert classificar_pagina_de_mapa("MAPA DE ZONEAMENTO", 1) == "map_candidate"


def test_resultados_tabular_e_raster_usam_campos_em_portugues() -> None:
    avaliacao_tabela = avaliar_tabela(
        """
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
    )
    assert isinstance(avaliacao_tabela, AvaliacaoDeTabela)
    assert avaliacao_tabela.classificacao == "confirmed"
    assert avaliacao_tabela.classification == avaliacao_tabela.classificacao

    imagem = Image.new("RGB", (900, 1200), "white")
    desenho = ImageDraw.Draw(imagem)
    for y in (300, 450, 600, 750, 900):
        desenho.line((150, y, 750, y), fill="black", width=4)
    for x in (150, 350, 550, 750):
        desenho.line((x, 300, x, 900), fill="black", width=4)

    avaliacao_raster = avaliar_visual_raster(imagem, texto="TABELA")
    assert isinstance(avaliacao_raster, AvaliacaoVisualRaster)
    assert avaliacao_raster.classificacao == "raster_table_candidate"
    assert avaliacao_raster.classification == avaliacao_raster.classificacao
