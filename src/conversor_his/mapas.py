# SPDX-License-Identifier: MIT
"""Classificação cartográfica com API pública em português."""

from .maps import (
    MapTextClass as ClasseTextualDeMapa,
    classify_map_page as classificar_pagina_de_mapa,
    extract_map_title as extrair_titulo_de_mapa,
    is_map_page as pagina_e_mapa,
    save_map_image as salvar_imagem_de_mapa,
)

__all__ = [
    "ClasseTextualDeMapa",
    "classificar_pagina_de_mapa",
    "extrair_titulo_de_mapa",
    "pagina_e_mapa",
    "salvar_imagem_de_mapa",
]
