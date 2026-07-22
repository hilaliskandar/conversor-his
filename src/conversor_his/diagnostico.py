# SPDX-License-Identifier: MIT
from __future__ import annotations

from pathlib import Path

from .coordenadas import (
    avaliar_registro_de_coordenadas,
    deve_classificar_como_registro_de_coordenadas,
)
from .extractors.pypdf_native import (
    NativeTextExtraction,
    count_page_images,
    extract_page_text_detailed,
    open_pdf,
)
from .graphics import analyze_repeated_graphics
from .graphics_policy import refine_confirmed_decorative_graphics
from .hashing import sha256_file
from .mapas import classificar_pagina_de_mapa
from .modelos import DiagnosticoDeDocumento, DiagnosticoDePagina
from .tabelas import avaliar_tabela
from .visual_tables import assess_vector_grid, merge_visual_table_evidence

_CLASSES_CANDIDATAS_A_TABELA = {
    "candidate",
    "mixed_candidate",
    "continuation_candidate",
    "visual_candidate",
}


def diagnosticar_pdf(
    caminho: Path,
    minimo_caracteres_nativos: int = 40,
    extracoes_nativas: dict[int, NativeTextExtraction] | None = None,
) -> DiagnosticoDeDocumento:
    """Diagnostica cada página e define a rota inicial de conversão."""

    leitor = open_pdf(caminho)
    resumos_graficos, graficos_repetidos = analyze_repeated_graphics(leitor)
    resumos_graficos = refine_confirmed_decorative_graphics(
        leitor,
        resumos_graficos,
        graficos_repetidos,
    )
    paginas: list[DiagnosticoDePagina] = []
    quantidade_paginas = len(leitor.pages)

    for indice, pagina in enumerate(leitor.pages, start=1):
        extracao = (
            extracoes_nativas[indice]
            if extracoes_nativas is not None and indice in extracoes_nativas
            else extract_page_text_detailed(pagina)
        )
        texto = extracao.text
        texto_bruto = extracao.raw_text
        quantidade_imagens_fallback = count_page_images(pagina)
        graficos = resumos_graficos.get(indice)
        quantidade_imagens_brutas = (
            graficos.raw_image_count
            if graficos is not None
            else quantidade_imagens_fallback
        )
        quantidade_imagens_decorativas = (
            graficos.decorative_image_count if graficos is not None else 0
        )
        quantidade_imagens_de_conteudo = (
            graficos.content_image_count
            if graficos is not None
            else quantidade_imagens_fallback
        )
        quantidade_caracteres = len(texto.strip())
        classe_mapa = classificar_pagina_de_mapa(
            texto,
            quantidade_imagens_de_conteudo,
        )
        avaliacao_tabela = avaliar_tabela(texto_bruto)
        evidencia_vetorial = assess_vector_grid(pagina)
        avaliacao_tabela = merge_visual_table_evidence(
            avaliacao_tabela,
            evidencia_vetorial,
            texto_bruto,
        )
        avaliacao_coordenadas = avaliar_registro_de_coordenadas(texto_bruto)
        registro_coordenadas = deve_classificar_como_registro_de_coordenadas(
            avaliacao_coordenadas,
            avaliacao_tabela,
            grade_visual_forte=evidencia_vetorial.strong,
        )

        if registro_coordenadas:
            avaliacao_tabela.classificacao = "not_table"
            avaliacao_tabela.suspeita = False
            avaliacao_tabela.perfil_conteudo = "coordinates"

        suspeita_tabela = avaliacao_tabela.classificacao == "confirmed"
        candidata_tabela = (
            avaliacao_tabela.classificacao in _CLASSES_CANDIDATAS_A_TABELA
        )
        tem_texto_nativo = quantidade_caracteres >= minimo_caracteres_nativos
        exclusivamente_decorativa = (
            quantidade_caracteres == 0
            and quantidade_imagens_brutas > 0
            and quantidade_imagens_de_conteudo == 0
            and quantidade_imagens_brutas == quantidade_imagens_decorativas
        )

        if classe_mapa in {"map_confirmed", "map_candidate", "map_cover"}:
            rota = "map"
            tipo_pagina = classe_mapa
        elif exclusivamente_decorativa:
            rota = "decorative"
            tipo_pagina = (
                "back_cover"
                if indice == quantidade_paginas
                else "decorative_only"
            )
        elif registro_coordenadas and tem_texto_nativo:
            rota = "native"
            tipo_pagina = "coordinate_register"
        elif suspeita_tabela:
            rota = "structured"
            tipo_pagina = "table"
        elif tem_texto_nativo:
            rota = "native"
            tipo_pagina = "table_candidate" if candidata_tabela else "text"
        else:
            rota = "ocr"
            tipo_pagina = "unknown"

        avisos_pagina: list[str] = []
        if classe_mapa == "map_confirmed":
            avisos_pagina.append(
                "conteudo cartografico confirmado: preservar imagem e texto"
            )
        elif classe_mapa == "map_candidate":
            avisos_pagina.append(
                "possivel conteudo cartografico: preservar para revisao"
            )
        elif classe_mapa == "map_cover":
            avisos_pagina.append(
                "capa ou indice cartografico: preservar sem contar como mapa"
            )
        elif exclusivamente_decorativa:
            avisos_pagina.append("pagina exclusivamente decorativa: OCR dispensado")
        elif registro_coordenadas:
            avisos_pagina.append(
                "registro de coordenadas: preservar imagem e texto em classe propria"
            )
        elif suspeita_tabela:
            avisos_pagina.append(
                "estrutura tabular confirmada: preservar imagem e exigir revisao estrutural"
            )
        elif candidata_tabela:
            rotulo = avaliacao_tabela.classificacao.replace("_", " ")
            avisos_pagina.append(
                f"{rotulo}: preservar texto bruto e imagem para revisao estrutural"
            )
        elif 0 < quantidade_caracteres < minimo_caracteres_nativos:
            avisos_pagina.append("camada textual insuficiente")

        if evidencia_vetorial.detected:
            avisos_pagina.append(
                "grade vetorial detectada: bordas tabulares preservadas como evidencia"
            )
        if avaliacao_coordenadas.detectado and not registro_coordenadas:
            avisos_pagina.append(
                "evidencia de coordenadas subordinada a estrutura tabular mais forte"
            )
        if (
            quantidade_imagens_de_conteudo
            and tem_texto_nativo
            and classe_mapa == "none"
        ):
            avisos_pagina.append("pagina hibrida: texto e imagem relevante")
        if not quantidade_caracteres and not quantidade_imagens_brutas:
            avisos_pagina.append("pagina sem texto ou imagem detectavel")
        if extracao.rotated_text:
            avisos_pagina.append(
                "texto rotacionado detectado; "
                f"extracao selecionada: {extracao.selected_mode}"
            )
        if extracao.warnings:
            avisos_pagina.append("avisos da extracao nativa registrados")

        paginas.append(
            DiagnosticoDePagina(
                numero_pagina=indice,
                tem_texto_nativo=tem_texto_nativo,
                quantidade_caracteres=quantidade_caracteres,
                quantidade_imagens=quantidade_imagens_de_conteudo,
                quantidade_imagens_brutas=quantidade_imagens_brutas,
                quantidade_imagens_decorativas=quantidade_imagens_decorativas,
                quantidade_imagens_de_conteudo=quantidade_imagens_de_conteudo,
                suspeita_tabela=suspeita_tabela,
                suspeita_mapa=classe_mapa in {"map_confirmed", "map_candidate"},
                tipo_pagina=tipo_pagina,
                rota=rota,
                avisos=avisos_pagina,
                avaliacao_tabela=(
                    avaliacao_tabela
                    if avaliacao_tabela.classificacao != "not_table"
                    else None
                ),
                avaliacao_coordenadas=(
                    avaliacao_coordenadas
                    if avaliacao_coordenadas.detectado
                    else None
                ),
                modo_extracao_nativa=extracao.selected_mode,
                quantidade_caracteres_layout=extracao.layout_character_count,
                quantidade_caracteres_simples=extracao.simple_character_count,
                texto_rotacionado_detectado=extracao.rotated_text,
                avisos_extracao=extracao.warnings,
            )
        )

    return DiagnosticoDeDocumento(
        caminho_origem=caminho,
        sha256=sha256_file(caminho),
        quantidade_paginas=quantidade_paginas,
        paginas=paginas,
        graficos_repetidos=graficos_repetidos,
    )


__all__ = ["diagnosticar_pdf"]
