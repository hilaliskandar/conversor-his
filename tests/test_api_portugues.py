from __future__ import annotations

from conversor_his.coordenadas import avaliar_registro_de_coordenadas
from conversor_his.diagnostico import diagnosticar_pdf
from conversor_his.lote import converter_lote_zip
from conversor_his.manifesto import escrever_manifesto
from conversor_his.mapas import classificar_pagina_de_mapa
from conversor_his.modelos import AvaliacaoDeCoordenadas, ManifestoDeConversao
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
