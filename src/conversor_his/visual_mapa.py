# SPDX-License-Identifier: MIT
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AvaliacaoVisualDeMapa:
    complexidade_visual: bool
    semelhante_a_capa: bool
    proporcao_tinta: float
    proporcao_bordas: float
    quantidade_componentes: int
    motivos: tuple[str, ...]

    # Propriedades transitórias para consumidores da API 0.7.
    @property
    def visual_complexity(self) -> bool:
        return self.complexidade_visual

    @property
    def cover_like(self) -> bool:
        return self.semelhante_a_capa

    @property
    def ink_ratio(self) -> float:
        return self.proporcao_tinta

    @property
    def edge_ratio(self) -> float:
        return self.proporcao_bordas

    @property
    def component_count(self) -> int:
        return self.quantidade_componentes

    @property
    def reasons(self) -> tuple[str, ...]:
        return self.motivos


def avaliar_visual_de_mapa(imagem: Any) -> AvaliacaoVisualDeMapa:
    """Distingue página cartográfica ocupada de capa predominantemente vazia."""

    try:
        import cv2
        import numpy as np
    except ImportError as erro:  # pragma: no cover
        raise RuntimeError(
            "A análise cartográfica requer opencv-python-headless e numpy."
        ) from erro

    matriz_rgb = np.asarray(imagem.convert("RGB"))
    tons_de_cinza = cv2.cvtColor(matriz_rgb, cv2.COLOR_RGB2GRAY)
    altura, largura = tons_de_cinza.shape

    inicio_y, fim_y = round(altura * 0.05), round(altura * 0.95)
    inicio_x, fim_x = round(largura * 0.04), round(largura * 0.96)
    nucleo = tons_de_cinza[inicio_y:fim_y, inicio_x:fim_x]

    binaria = cv2.threshold(nucleo, 225, 255, cv2.THRESH_BINARY_INV)[1]
    proporcao_tinta = float(cv2.countNonZero(binaria)) / float(max(binaria.size, 1))

    bordas = cv2.Canny(nucleo, 80, 180)
    proporcao_bordas = float(cv2.countNonZero(bordas)) / float(max(bordas.size, 1))

    quantidade, _, estatisticas, _ = cv2.connectedComponentsWithStats(
        binaria, connectivity=8
    )
    area_minima = max(8, round(binaria.size * 0.00002))
    quantidade_componentes = sum(
        int(estatisticas[indice, cv2.CC_STAT_AREA]) >= area_minima
        for indice in range(1, quantidade)
    )

    rede_densa_conectada = proporcao_tinta >= 0.045 and proporcao_bordas >= 0.025
    graficos_diversos = (
        proporcao_tinta >= 0.055
        and proporcao_bordas >= 0.012
        and quantidade_componentes >= 18
    )
    componentes_ocupados = proporcao_tinta >= 0.09 and quantidade_componentes >= 12
    complexidade_visual = (
        rede_densa_conectada or graficos_diversos or componentes_ocupados
    )

    semelhante_a_capa = not complexidade_visual and (
        proporcao_tinta <= 0.035
        or (quantidade_componentes <= 8 and proporcao_bordas <= 0.012)
        or (proporcao_tinta <= 0.05 and proporcao_bordas <= 0.010)
    )

    motivos: list[str] = []
    if rede_densa_conectada:
        motivos.append("rede gráfica densa e conectada compatível com mapa")
    elif complexidade_visual:
        motivos.append("ocupação gráfica e diversidade de componentes compatíveis com mapa")
    if semelhante_a_capa:
        motivos.append("baixa ocupação gráfica compatível com capa ou folha de abertura")

    return AvaliacaoVisualDeMapa(
        complexidade_visual=complexidade_visual,
        semelhante_a_capa=semelhante_a_capa,
        proporcao_tinta=round(proporcao_tinta, 6),
        proporcao_bordas=round(proporcao_bordas, 6),
        quantidade_componentes=quantidade_componentes,
        motivos=tuple(motivos),
    )


__all__ = ["AvaliacaoVisualDeMapa", "avaliar_visual_de_mapa"]
