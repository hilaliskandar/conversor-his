# SPDX-License-Identifier: MIT
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .graphics import PageGraphicSummary, list_page_graphics
from .models import RepeatedGraphic


def refine_confirmed_decorative_graphics(
    reader: Any,
    summaries: dict[int, PageGraphicSummary],
    repeated_graphics: list[RepeatedGraphic],
    *,
    max_area_ratio: float = 0.05,
    edge_band: float = 0.15,
) -> dict[int, PageGraphicSummary]:
    """Aceita variação geométrica apenas para fingerprints já confirmados.

    Depois de um gráfico ter passado pela regra rigorosa de recorrência e
    estabilidade, ocorrências do mesmo conteúdo continuam decorativas quando
    permanecem pequenas e periféricas, mesmo em páginas rotacionadas ou com
    CropBox/layout diferentes. Objetos ampliados ou movidos para o interior
    continuam sendo tratados como conteúdo.
    """

    confirmed = {item.sha256 for item in repeated_graphics}
    if not confirmed:
        return summaries

    refined = dict(summaries)
    for page_number, page in enumerate(reader.pages, start=1):
        occurrences = list_page_graphics(page, page_number, edge_band=edge_band)
        groups: dict[str, list] = defaultdict(list)
        for occurrence in occurrences:
            groups[occurrence.fingerprint].append(occurrence)

        raw_count = sum(
            max(item.image_weight for item in group) for group in groups.values()
        )
        decorative_count = 0
        for fingerprint, group in groups.items():
            if fingerprint not in confirmed:
                continue
            if any(
                item.position != "interior" and item.area_ratio <= max_area_ratio
                for item in group
            ):
                decorative_count += max(item.image_weight for item in group)

        previous = summaries.get(page_number)
        if previous is not None:
            raw_count = max(raw_count, previous.raw_image_count)
            decorative_count = max(
                decorative_count,
                previous.decorative_image_count,
            )

        refined[page_number] = PageGraphicSummary(
            raw_image_count=raw_count,
            decorative_image_count=min(decorative_count, raw_count),
            content_image_count=max(raw_count - decorative_count, 0),
        )

    return refined
