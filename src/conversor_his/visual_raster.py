# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Literal

ClasseDeConteudoVisual = Literal[
    "none",
    "raster_table_candidate",
    "diagram_candidate",
    "map_candidate",
]

_TEXTO_DIAGRAMA_RE = re.compile(
    r"\b(?:FLUXOGRAMA|ORGANOGRAMA|DIAGRAMA|ESQUEMA|REPRESENTACAO\s+GRAFICA|"
    r"CORTE|ELEVACAO|DETALHE|PLANTA\s+BAIXA|GRAFICO)\b"
)
_TEXTO_TABELA_RE = re.compile(
    r"\b(?:TABELA|QUADRO|PARAMETROS?|INDICES?|COLUNA|LINHA|TOTAL|SUBTOTAL|CONTINUACAO)\b"
)


@dataclass(slots=True)
class AvaliacaoVisualRaster:
    classificacao: ClasseDeConteudoVisual
    detectado: bool
    forte: bool
    pontuacao: int
    linhas_horizontais: int
    linhas_verticais: int
    intersecoes: int
    regioes_fechadas: int
    proporcao_area_estruturada: float
    componentes_semelhantes_a_seta: int = 0
    grade_parcial_detectada: bool = False
    continuacao_contextual: bool = False
    mascara_recorrente_aplicada: bool = False
    evidencia_textual_tabela: bool = False
    evidencia_textual_diagrama: bool = False
    motivos: list[str] = field(default_factory=list)

    # Propriedades transitórias para consumidores da API 0.7.
    @property
    def classification(self) -> ClasseDeConteudoVisual:
        return self.classificacao

    @property
    def detected(self) -> bool:
        return self.detectado

    @property
    def strong(self) -> bool:
        return self.forte

    @property
    def score(self) -> int:
        return self.pontuacao

    @property
    def horizontal_lines(self) -> int:
        return self.linhas_horizontais

    @property
    def vertical_lines(self) -> int:
        return self.linhas_verticais

    @property
    def intersections(self) -> int:
        return self.intersecoes

    @property
    def closed_regions(self) -> int:
        return self.regioes_fechadas

    @property
    def structured_area_ratio(self) -> float:
        return self.proporcao_area_estruturada

    @property
    def arrow_like_components(self) -> int:
        return self.componentes_semelhantes_a_seta

    @property
    def partial_grid_detected(self) -> bool:
        return self.grade_parcial_detectada

    @property
    def contextual_continuation(self) -> bool:
        return self.continuacao_contextual

    @property
    def recurrent_mask_applied(self) -> bool:
        return self.mascara_recorrente_aplicada

    @property
    def table_text_evidence(self) -> bool:
        return self.evidencia_textual_tabela

    @property
    def diagram_text_evidence(self) -> bool:
        return self.evidencia_textual_diagrama

    @property
    def reasons(self) -> list[str]:
        return self.motivos


def _maiusculas_sem_acentos(texto: str) -> str:
    texto_decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(
        caractere
        for caractere in texto_decomposto
        if not unicodedata.combining(caractere)
    ).upper()


def _carregar_bibliotecas_visuais() -> tuple[Any, Any]:
    try:
        import cv2
        import numpy as np
    except ImportError as erro:  # pragma: no cover
        raise RuntimeError(
            "A análise visual raster requer opencv-python-headless e numpy. "
            "Reinstale o projeto com: pip install -e '.[dev,ocr]'"
        ) from erro
    return cv2, np


def _contar_componentes(
    mascara: Any,
    cv2: Any,
    area_minima: int = 3,
) -> int:
    quantidade, _, estatisticas, _ = cv2.connectedComponentsWithStats(
        mascara,
        connectivity=8,
    )
    if quantidade <= 1:
        return 0
    return sum(
        int(estatisticas[indice, cv2.CC_STAT_AREA]) >= area_minima
        for indice in range(1, quantidade)
    )


def avaliar_visual_raster(
    imagem: Any,
    texto: str = "",
    *,
    permitir_contexto_parcial: bool = False,
    mascarar_bordas_da_pagina: bool = True,
) -> AvaliacaoVisualRaster:
    """Detecta tabelas e diagramas em páginas rasterizadas.

    Grades parciais são apenas evidência latente. Elas somente viram tabela quando
    ``permitir_contexto_parcial`` é ativado após a verificação de uma página
    tabular adjacente. O mascaramento periférico reduz molduras, cabeçalhos e
    rodapés recorrentes sem alterar a imagem preservada no produto.
    """

    cv2, np = _carregar_bibliotecas_visuais()
    matriz_rgb = np.asarray(imagem.convert("RGB"))
    tons_de_cinza = cv2.cvtColor(matriz_rgb, cv2.COLOR_RGB2GRAY)
    texto_normalizado = _maiusculas_sem_acentos(texto)

    binaria = cv2.adaptiveThreshold(
        tons_de_cinza,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        15,
    )

    altura, largura = binaria.shape
    mascara_recorrente_aplicada = False
    if mascarar_bordas_da_pagina and altura >= 200 and largura >= 200:
        margem_superior_inferior = max(8, round(altura * 0.055))
        margem_esquerda_direita = max(8, round(largura * 0.035))
        binaria[:margem_superior_inferior, :] = 0
        binaria[altura - margem_superior_inferior :, :] = 0
        binaria[:, :margem_esquerda_direita] = 0
        binaria[:, largura - margem_esquerda_direita :] = 0
        mascara_recorrente_aplicada = True

    nucleo_horizontal = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (max(20, largura // 30), 1),
    )
    nucleo_vertical = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (1, max(12, altura // 45)),
    )

    horizontal = cv2.morphologyEx(binaria, cv2.MORPH_OPEN, nucleo_horizontal)
    vertical = cv2.morphologyEx(binaria, cv2.MORPH_OPEN, nucleo_vertical)
    grade = cv2.bitwise_or(horizontal, vertical)
    mascara_intersecoes = cv2.bitwise_and(horizontal, vertical)

    linhas_horizontais = _contar_componentes(
        horizontal,
        cv2,
        area_minima=max(12, largura // 80),
    )
    linhas_verticais = _contar_componentes(
        vertical,
        cv2,
        area_minima=max(12, altura // 100),
    )
    intersecoes = _contar_componentes(mascara_intersecoes, cv2, area_minima=2)

    contornos, _ = cv2.findContours(grade, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    area_pagina = float(max(largura * altura, 1))
    regioes_fechadas = 0
    area_estruturada = 0.0
    regioes_semelhantes_a_caixa = 0
    for contorno in contornos:
        _, _, largura_caixa, altura_caixa = cv2.boundingRect(contorno)
        area = largura_caixa * altura_caixa
        if area < area_pagina * 0.0005 or area > area_pagina * 0.90:
            continue
        perimetro = cv2.arcLength(contorno, True)
        poligono = cv2.approxPolyDP(contorno, 0.02 * perimetro, True)
        if len(poligono) == 4:
            regioes_fechadas += 1
            area_estruturada += area
            if largura_caixa >= largura * 0.04 and altura_caixa >= altura * 0.025:
                regioes_semelhantes_a_caixa += 1

    proporcao_area_estruturada = min(area_estruturada / area_pagina, 1.0)
    tem_texto_de_diagrama = bool(_TEXTO_DIAGRAMA_RE.search(texto_normalizado))
    tem_texto_de_tabela = bool(_TEXTO_TABELA_RE.search(texto_normalizado))

    total_linhas = max(linhas_horizontais + linhas_verticais, 1)
    densidade_intersecoes = intersecoes / total_linhas
    grade_regular = densidade_intersecoes >= 1.15 and intersecoes >= 8

    candidata_tabela_completa = (
        linhas_horizontais >= 4
        and linhas_verticais >= 3
        and intersecoes >= 6
        and proporcao_area_estruturada >= 0.04
        and (grade_regular or tem_texto_de_tabela)
    )
    grade_parcial_detectada = (
        linhas_horizontais >= 3
        and linhas_verticais >= 2
        and intersecoes >= 4
        and regioes_fechadas >= 2
        and proporcao_area_estruturada >= 0.02
        and not tem_texto_de_diagrama
    )
    tabela_parcial_contextual = (
        grade_parcial_detectada and permitir_contexto_parcial
    )
    candidata_tabela = candidata_tabela_completa or tabela_parcial_contextual

    tabela_forte = (
        linhas_horizontais >= 8
        and linhas_verticais >= 6
        and intersecoes >= 20
        and proporcao_area_estruturada >= 0.08
        and grade_regular
    )

    candidato_diagrama = (
        regioes_semelhantes_a_caixa >= 2
        and (linhas_horizontais + linhas_verticais) >= 4
        and 0.008 <= proporcao_area_estruturada <= 0.60
        and (
            tem_texto_de_diagrama
            or (
                not grade_parcial_detectada
                and (
                    not grade_regular
                    or intersecoes < max(12, regioes_semelhantes_a_caixa * 4)
                )
            )
        )
        and not tabela_forte
    )

    pontuacao = 0
    motivos: list[str] = []
    classificacao: ClasseDeConteudoVisual = "none"
    detectado = False
    forte = False

    if candidato_diagrama and (tem_texto_de_diagrama or not candidata_tabela):
        classificacao = "diagram_candidate"
        detectado = True
        pontuacao = 4 + min(regioes_semelhantes_a_caixa, 10)
        if tem_texto_de_diagrama:
            pontuacao += 3
            motivos.append(
                "vocabulário explícito de diagrama ou representação gráfica"
            )
        motivos.append(
            "caixas e conectores sem regularidade suficiente de grade tabular"
        )
    elif candidata_tabela:
        classificacao = "raster_table_candidate"
        detectado = True
        forte = tabela_forte
        pontuacao = 4
        pontuacao += min(linhas_horizontais, 20) // 4
        pontuacao += min(linhas_verticais, 20) // 3
        pontuacao += min(intersecoes, 40) // 8
        if tem_texto_de_tabela:
            pontuacao += 2
        if tabela_forte:
            pontuacao += 4
            motivos.append("grade raster forte com linhas e cruzamentos regulares")
        elif tabela_parcial_contextual and not candidata_tabela_completa:
            motivos.append("grade raster parcial promovida por continuidade contextual")
        else:
            motivos.append("grade raster candidata com estrutura celular")
    elif grade_parcial_detectada:
        motivos.append(
            "grade raster parcial mantida como evidência latente sem contexto adjacente"
        )

    return AvaliacaoVisualRaster(
        classificacao=classificacao,
        detectado=detectado,
        forte=forte,
        pontuacao=pontuacao,
        linhas_horizontais=linhas_horizontais,
        linhas_verticais=linhas_verticais,
        intersecoes=intersecoes,
        regioes_fechadas=regioes_fechadas,
        proporcao_area_estruturada=round(proporcao_area_estruturada, 6),
        componentes_semelhantes_a_seta=0,
        grade_parcial_detectada=grade_parcial_detectada,
        continuacao_contextual=tabela_parcial_contextual,
        mascara_recorrente_aplicada=mascara_recorrente_aplicada,
        evidencia_textual_tabela=tem_texto_de_tabela,
        evidencia_textual_diagrama=tem_texto_de_diagrama,
        motivos=motivos,
    )


__all__ = [
    "AvaliacaoVisualRaster",
    "ClasseDeConteudoVisual",
    "avaliar_visual_raster",
]
