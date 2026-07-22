# SPDX-License-Identifier: MIT
"""Compatibilidade temporária com a API anterior em inglês."""

from .mapas import (
    ClasseTextualDeMapa as MapTextClass,
    classificar_pagina_de_mapa as _classificar_pagina_de_mapa,
    extrair_titulo_de_mapa as _extrair_titulo_de_mapa,
    pagina_e_mapa as _pagina_e_mapa,
    salvar_imagem_de_mapa as _salvar_imagem_de_mapa,
)


def classify_map_page(
    text: str,
    image_count: int,
    *,
    visual_complexity: bool = False,
    max_text_chars: int = 700,
) -> MapTextClass:
    return _classificar_pagina_de_mapa(
        text,
        image_count,
        complexidade_visual=visual_complexity,
        maximo_caracteres_texto=max_text_chars,
    )


def is_map_page(text: str, image_count: int, max_text_chars: int = 700) -> bool:
    return _pagina_e_mapa(
        text,
        image_count,
        maximo_caracteres_texto=max_text_chars,
    )


def extract_map_title(text: str, page_number: int) -> str:
    """Preserva a assinatura pública da versão 0.7."""

    return _extrair_titulo_de_mapa(text, numero_pagina=page_number)


def save_map_image(
    pdf_path,
    page_number: int,
    assets_dir,
    dpi: int = 200,
    suffix: str = "mapa",
):
    return _salvar_imagem_de_mapa(
        pdf_path,
        page_number,
        assets_dir,
        dpi=dpi,
        sufixo=suffix,
    )


__all__ = [
    "MapTextClass",
    "classify_map_page",
    "extract_map_title",
    "is_map_page",
    "save_map_image",
]
