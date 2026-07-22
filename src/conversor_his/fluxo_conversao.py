# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path

from . import __version__
from .coordenadas import (
    avaliar_registro_de_coordenadas,
    deve_classificar_como_registro_de_coordenadas,
)
from .diagnostico import diagnosticar_pdf
from .extractors.pypdf_native import extract_native_pages_detailed
from .hashing import sha256_file
from .manifesto import escrever_manifesto
from .mapas import (
    classificar_pagina_de_mapa,
    extrair_titulo_de_mapa,
    salvar_imagem_de_mapa,
)
from .modelos import (
    AvaliacaoDeCoordenadas,
    AvaliacaoDeTabela,
    AvaliacaoVisualRaster,
    DiagnosticoDeDocumento,
    ManifestoDeConversao,
    QualidadeOCR,
)
from .normalizacao_texto import (
    limpar_caracteres_invisiveis,
    normalizar_texto_de_prosa,
)
from .ocr.quality import assess_ocr_quality as avaliar_qualidade_ocr
from .ocr.render import render_pdf_page as renderizar_pagina_pdf
from .ocr.tesseract_engine import TesseractEngine as MotorTesseract
from .tabelas import (
    avaliar_tabela,
    extrair_titulo_de_tabela,
    salvar_imagem_de_tabela,
)
from .visual_mapa import AvaliacaoVisualDeMapa, avaliar_visual_de_mapa
from .visual_raster import avaliar_visual_raster

_DPI_IMAGEM_TABELA = 200
_DPI_ANALISE_RASTER = 150
_DPI_IMAGEM_DIAGRAMA = 250
_DPI_IMAGEM_REVISAO = 300
_DPI_IMAGEM_COORDENADAS = 200
_DPI_ANALISE_MAPA = 150

_MARCADOR_LEGAL_RE = re.compile(
    r"\b(?:LEI|ART\.?|ARTIGO|EMENDA|PREFEIT[OA]|CAMARA\s+MUNICIPAL|"
    r"SANCIONA|VIGOR|REVOGAD[AO]S?|ASSINATURA|DECRETO)\b",
    re.IGNORECASE,
)


@dataclass(slots=True)
class EvidenciaOCRDePagina:
    texto: str
    qualidade: QualidadeOCR
    imagem: object
    raster: AvaliacaoVisualRaster
    tabela_textual: AvaliacaoDeTabela
    coordenadas: AvaliacaoDeCoordenadas
    visual_mapa: AvaliacaoVisualDeMapa


def _imagem_markdown(texto_alternativo: str, imagem_relativa: str) -> str:
    texto_seguro = texto_alternativo.replace("[", "(").replace("]", ")")
    return f"![{texto_seguro}](<{imagem_relativa}>)"


def _salvar_imagem_revisao(
    caminho_pdf: Path,
    numero_pagina: int,
    diretorio_recursos: Path,
    *,
    dpi: int,
    sufixo: str,
) -> Path:
    diretorio_recursos.mkdir(parents=True, exist_ok=True)
    caminho_imagem = (
        diretorio_recursos / f"pagina_{numero_pagina:04d}_{sufixo}.png"
    )
    imagem = renderizar_pagina_pdf(caminho_pdf, numero_pagina, dpi=dpi)
    imagem.save(caminho_imagem, format="PNG", optimize=True)
    return caminho_imagem


def _bloco_visual(
    numero_pagina: int,
    titulo: str,
    texto: str,
    imagem_relativa: str,
    modo_origem: str,
    *,
    tipo_visual: str,
    aviso: str,
) -> str:
    texto_normalizado = normalizar_texto_de_prosa(texto)
    bloco_texto = ""
    if texto_normalizado:
        bloco_texto = (
            "\n\n> Texto associado à página visual, preservado para pesquisa e "
            "rastreabilidade. A interpretação espacial deve consultar a imagem.\n\n"
            "```text\n"
            f"{texto_normalizado}\n"
            "```\n"
        )
    return (
        f"<!-- pagina_original: {numero_pagina}; tipo: {tipo_visual}; "
        f"rota: imagem+texto:{modo_origem}; revisao: sim -->\n\n"
        f"## Página {numero_pagina} — {titulo}\n\n"
        f"> {aviso}\n\n"
        f"{_imagem_markdown(titulo, imagem_relativa)}"
        f"{bloco_texto}"
    )


def _bloco_tabela(
    numero_pagina: int,
    titulo: str,
    texto: str,
    imagem_relativa: str,
    *,
    candidata: bool,
    raster: bool,
) -> str:
    classificacao = "candidata" if candidata else "confirmada"
    origem = "raster" if raster else "nativa/vetorial"
    texto_bruto = limpar_caracteres_invisiveis(texto).strip()
    return (
        f"<!-- pagina_original: {numero_pagina}; tipo: tabela_{classificacao}; "
        f"origem: {origem}; rota: structured:preservacao; revisao: sim -->\n\n"
        f"## Página {numero_pagina} — {titulo}\n\n"
        f"> **Revisão estrutural necessária:** estrutura tabular {classificacao} "
        f"identificada em fonte {origem}. O texto linear e a imagem foram preservados; "
        "as relações entre linhas e colunas devem ser conferidas.\n\n"
        f"{_imagem_markdown(f'Página tabular {numero_pagina}', imagem_relativa)}\n\n"
        "```text\n"
        f"{texto_bruto}\n"
        "```\n"
    )


def _bloco_coordenadas(
    numero_pagina: int,
    texto: str,
    imagem_relativa: str,
) -> str:
    texto_bruto = limpar_caracteres_invisiveis(texto).strip()
    return (
        f"<!-- pagina_original: {numero_pagina}; tipo: coordinate_register; "
        "rota: structured:preservacao; revisao: sim -->\n\n"
        f"## Página {numero_pagina} — Registro de coordenadas\n\n"
        "> Sequência espacial preservada em classe própria. A imagem deve ser consultada "
        "para conferir pares, vértices, ordem e continuidade geométrica.\n\n"
        f"{_imagem_markdown(f'Registro de coordenadas da página {numero_pagina}', imagem_relativa)}\n\n"
        "```text\n"
        f"{texto_bruto}\n"
        "```\n"
    )


def _bloco_revisao_ocr(
    numero_pagina: int,
    texto: str,
    imagem_relativa: str,
    rotulo_qualidade: str,
) -> str:
    texto_normalizado = normalizar_texto_de_prosa(texto)
    return (
        f"<!-- pagina_original: {numero_pagina}; tipo: ocr_review; "
        f"qualidade: {rotulo_qualidade}; rota: ocr:tesseract+pdfium; revisao: sim -->\n\n"
        f"## Página {numero_pagina} — OCR com revisão necessária\n\n"
        "> **Revisão necessária:** o resultado do OCR apresentou qualidade baixa ou "
        "moderada. A imagem integral foi preservada e deve prevalecer em caso de dúvida.\n\n"
        f"{_imagem_markdown(f'Página {numero_pagina} para revisão de OCR', imagem_relativa)}\n\n"
        "```text\n"
        f"{texto_normalizado}\n"
        "```\n"
    )


def _bloco_decorativo(numero_pagina: int, tipo_pagina: str) -> str:
    rotulo = "contracapa" if tipo_pagina == "back_cover" else "página decorativa"
    return (
        f"<!-- pagina_original: {numero_pagina}; tipo: {tipo_pagina}; "
        "rota: decorative; revisao: nao -->\n\n"
        f"## Página {numero_pagina} — {rotulo.capitalize()}\n\n"
        "> Página sem conteúdo textual normativo detectável. Os elementos gráficos "
        "foram classificados como decorativos recorrentes; o PDF original permanece "
        "como fonte visual de referência.\n"
    )


def _bloco_ocr(numero_pagina: int, texto: str) -> str:
    return (
        f"<!-- pagina_original: {numero_pagina}; rota: ocr:tesseract+pdfium; "
        "revisao: nao -->\n\n"
        f"## Página {numero_pagina}\n\n{normalizar_texto_de_prosa(texto)}\n"
    )


def _falso_positivo_legal(
    texto: str,
    avaliacao: AvaliacaoDeTabela | None,
) -> bool:
    if avaliacao is None or avaliacao.grade_visual_detectada:
        return False
    quantidade_marcadores = len(_MARCADOR_LEGAL_RE.findall(texto))
    return (
        quantidade_marcadores >= 3
        and avaliacao.classificacao
        in {
            "candidate",
            "mixed_candidate",
            "continuation_candidate",
        }
        and len(avaliacao.ocorrencias_cabecalho) <= 2
        and len(avaliacao.ocorrencias_parametros_urbanos) <= 1
        and avaliacao.perfil_conteudo
        not in {"urban_matrix", "mixed_urban_matrix"}
    )


def _tem_contexto_tabela_adjacente(
    numero_pagina: int,
    evidencias: dict[int, EvidenciaOCRDePagina],
    paginas_diagnostico: list,
) -> bool:
    for numero_vizinha in (numero_pagina - 1, numero_pagina + 1):
        vizinha = evidencias.get(numero_vizinha)
        if (
            vizinha is not None
            and vizinha.raster.classificacao == "raster_table_candidate"
        ):
            return True
        if 1 <= numero_vizinha <= len(paginas_diagnostico):
            pagina_vizinha = paginas_diagnostico[numero_vizinha - 1]
            if pagina_vizinha.tipo_pagina in {"table", "table_candidate"}:
                return True
    return False


def _precomputar_evidencias_ocr(
    caminho: Path,
    diagnostico: DiagnosticoDeDocumento,
    motor_ocr: MotorTesseract,
    dpi: int,
) -> dict[int, EvidenciaOCRDePagina]:
    evidencias: dict[int, EvidenciaOCRDePagina] = {}
    for pagina in diagnostico.paginas:
        if pagina.rota != "ocr":
            continue
        imagem_analise = renderizar_pagina_pdf(
            caminho,
            pagina.numero_pagina,
            dpi=min(_DPI_ANALISE_RASTER, dpi),
        )
        texto, confiancas = motor_ocr.recognize_page_with_confidence(
            caminho,
            pagina.numero_pagina,
            dpi=dpi,
        )
        qualidade = avaliar_qualidade_ocr(texto, confiancas)
        raster = avaliar_visual_raster(imagem_analise, texto)
        tabela_textual = avaliar_tabela(texto)
        coordenadas = avaliar_registro_de_coordenadas(texto)
        visual_mapa = avaliar_visual_de_mapa(imagem_analise)
        evidencias[pagina.numero_pagina] = EvidenciaOCRDePagina(
            texto=texto,
            qualidade=qualidade,
            imagem=imagem_analise,
            raster=raster,
            tabela_textual=tabela_textual,
            coordenadas=coordenadas,
            visual_mapa=visual_mapa,
        )

    # Grades parciais só são promovidas junto a tabela adjacente.
    for numero_pagina, item in evidencias.items():
        if item.raster.detectado or not item.raster.grade_parcial_detectada:
            continue
        if not _tem_contexto_tabela_adjacente(
            numero_pagina,
            evidencias,
            diagnostico.paginas,
        ):
            continue
        item.raster = avaliar_visual_raster(
            item.imagem,
            item.texto,
            permitir_contexto_parcial=True,
        )
    return evidencias


def converter_pdf(
    caminho: Path,
    diretorio_saida: Path,
    dpi: int = 300,
    referencia_origem: str | None = None,
) -> Path:
    """Converte um PDF para Markdown rastreável e escreve seu manifesto."""

    inicio = time.perf_counter()
    diretorio_saida.mkdir(parents=True, exist_ok=True)
    extracoes_nativas = extract_native_pages_detailed(caminho)
    diagnostico = diagnosticar_pdf(
        caminho,
        extracoes_nativas=extracoes_nativas,
    )
    caminho_origem: Path | str = referencia_origem or caminho
    diagnostico.caminho_origem = caminho_origem
    motor_ocr = MotorTesseract()
    evidencias_ocr = _precomputar_evidencias_ocr(
        caminho,
        diagnostico,
        motor_ocr,
        dpi,
    )

    blocos: list[str] = []
    diretorio_recursos = diretorio_saida / f"{caminho.stem}_assets"
    caminhos_recursos: list[Path] = []
    paginas_com_ocr: list[int] = []
    paginas_de_mapa: list[int] = []
    paginas_candidatas_a_mapa: list[int] = []
    paginas_de_capa_de_mapa: list[int] = []
    paginas_de_tabela: list[int] = []
    paginas_candidatas_a_tabela: list[int] = []
    paginas_de_tabela_raster: list[int] = []
    paginas_de_diagrama: list[int] = []
    paginas_de_registro_de_coordenadas: list[int] = []
    paginas_com_imagem_de_revisao_ocr: list[int] = []
    paginas_decorativas: list[int] = []
    paginas_para_revisao: list[int] = []
    paginas_com_texto_rotacionado: list[int] = []
    paginas_com_texto_visual_preservado: list[int] = []

    for pagina in diagnostico.paginas:
        extracao = extracoes_nativas[pagina.numero_pagina]
        texto_nativo = extracao.text
        texto_nativo_bruto = extracao.raw_text
        pagina.modo_extracao_nativa = extracao.selected_mode
        pagina.quantidade_caracteres_layout = extracao.layout_character_count
        pagina.quantidade_caracteres_simples = extracao.simple_character_count
        pagina.texto_rotacionado_detectado = extracao.rotated_text
        pagina.avisos_extracao = extracao.warnings

        # Candidatas cartográficas nativas recebem confirmação visual antes da rota.
        if pagina.rota == "map":
            imagem_analise = renderizar_pagina_pdf(
                caminho,
                pagina.numero_pagina,
                dpi=min(_DPI_ANALISE_MAPA, dpi),
            )
            visual = avaliar_visual_de_mapa(imagem_analise)
            classe_mapa = classificar_pagina_de_mapa(
                texto_nativo,
                max(pagina.quantidade_imagens_de_conteudo, 1),
                complexidade_visual=visual.complexidade_visual,
            )
            if visual.semelhante_a_capa and classe_mapa != "map_confirmed":
                classe_mapa = "map_cover"
            pagina.tipo_pagina = classe_mapa
            titulo = extrair_titulo_de_mapa(
                texto_nativo,
                pagina.numero_pagina,
            )
            sufixo = "capa_mapa" if classe_mapa == "map_cover" else "mapa"
            caminho_imagem = salvar_imagem_de_mapa(
                caminho,
                pagina.numero_pagina,
                diretorio_recursos,
                dpi=min(dpi, 300),
                sufixo=sufixo,
            )
            caminhos_recursos.append(caminho_imagem)
            paginas_para_revisao.append(pagina.numero_pagina)
            if classe_mapa == "map_cover":
                paginas_de_capa_de_mapa.append(pagina.numero_pagina)
                aviso = (
                    "Capa ou índice cartográfico preservado sem ser contado "
                    "como mapa efetivo."
                )
            elif classe_mapa == "map_confirmed":
                paginas_de_mapa.append(pagina.numero_pagina)
                aviso = (
                    "Conteúdo cartográfico confirmado por evidência textual e visual."
                )
            else:
                paginas_candidatas_a_mapa.append(pagina.numero_pagina)
                aviso = "Possível conteúdo cartográfico preservado para revisão."
            if texto_nativo.strip():
                pagina.texto_visual_preservado = True
                paginas_com_texto_visual_preservado.append(pagina.numero_pagina)
            blocos.append(
                _bloco_visual(
                    pagina.numero_pagina,
                    titulo,
                    texto_nativo,
                    caminho_imagem.relative_to(diretorio_saida).as_posix(),
                    extracao.selected_mode,
                    tipo_visual=classe_mapa,
                    aviso=aviso,
                )
            )
            continue

        if pagina.rota == "decorative":
            paginas_decorativas.append(pagina.numero_pagina)
            blocos.append(
                _bloco_decorativo(pagina.numero_pagina, pagina.tipo_pagina)
            )
            continue

        if pagina.tipo_pagina == "coordinate_register":
            caminho_imagem = _salvar_imagem_revisao(
                caminho,
                pagina.numero_pagina,
                diretorio_recursos,
                dpi=min(dpi, _DPI_IMAGEM_COORDENADAS),
                sufixo="coordenadas",
            )
            caminhos_recursos.append(caminho_imagem)
            paginas_de_registro_de_coordenadas.append(pagina.numero_pagina)
            paginas_para_revisao.append(pagina.numero_pagina)
            blocos.append(
                _bloco_coordenadas(
                    pagina.numero_pagina,
                    texto_nativo_bruto,
                    caminho_imagem.relative_to(diretorio_saida).as_posix(),
                )
            )
            continue

        if pagina.tipo_pagina == "table_candidate" and not _falso_positivo_legal(
            texto_nativo_bruto,
            pagina.avaliacao_tabela,
        ):
            caminho_imagem = salvar_imagem_de_tabela(
                caminho,
                pagina.numero_pagina,
                diretorio_recursos,
                dpi=min(dpi, _DPI_IMAGEM_TABELA),
            )
            caminhos_recursos.append(caminho_imagem)
            paginas_candidatas_a_tabela.append(pagina.numero_pagina)
            paginas_para_revisao.append(pagina.numero_pagina)
            blocos.append(
                _bloco_tabela(
                    pagina.numero_pagina,
                    extrair_titulo_de_tabela(
                        texto_nativo_bruto,
                        pagina.numero_pagina,
                    ),
                    texto_nativo_bruto,
                    caminho_imagem.relative_to(diretorio_saida).as_posix(),
                    candidata=True,
                    raster=False,
                )
            )
            continue

        if pagina.rota == "structured":
            caminho_imagem = salvar_imagem_de_tabela(
                caminho,
                pagina.numero_pagina,
                diretorio_recursos,
                dpi=min(dpi, _DPI_IMAGEM_TABELA),
            )
            caminhos_recursos.append(caminho_imagem)
            paginas_de_tabela.append(pagina.numero_pagina)
            paginas_para_revisao.append(pagina.numero_pagina)
            blocos.append(
                _bloco_tabela(
                    pagina.numero_pagina,
                    extrair_titulo_de_tabela(
                        texto_nativo_bruto,
                        pagina.numero_pagina,
                    ),
                    texto_nativo_bruto,
                    caminho_imagem.relative_to(diretorio_saida).as_posix(),
                    candidata=False,
                    raster=False,
                )
            )
            continue

        if pagina.rota == "ocr":
            paginas_com_ocr.append(pagina.numero_pagina)
            item = evidencias_ocr[pagina.numero_pagina]
            pagina.qualidade_ocr = item.qualidade
            pagina.avaliacao_visual_raster = item.raster
            pagina.avaliacao_coordenadas = (
                item.coordenadas if item.coordenadas.detectado else None
            )

            if item.raster.classificacao == "diagram_candidate":
                caminho_imagem = _salvar_imagem_revisao(
                    caminho,
                    pagina.numero_pagina,
                    diretorio_recursos,
                    dpi=min(dpi, _DPI_IMAGEM_DIAGRAMA),
                    sufixo="diagrama",
                )
                caminhos_recursos.append(caminho_imagem)
                paginas_de_diagrama.append(pagina.numero_pagina)
                paginas_para_revisao.append(pagina.numero_pagina)
                pagina.tipo_pagina = "diagram_candidate"
                pagina.imagem_revisao_preservada = True
                blocos.append(
                    _bloco_visual(
                        pagina.numero_pagina,
                        f"Diagrama da página {pagina.numero_pagina}",
                        item.texto,
                        caminho_imagem.relative_to(diretorio_saida).as_posix(),
                        "ocr+raster",
                        tipo_visual="diagram_candidate",
                        aviso=(
                            "Estrutura visual preservada como possível fluxograma, "
                            "esquema ou desenho técnico."
                        ),
                    )
                )
                continue

            if item.raster.classificacao == "raster_table_candidate":
                caminho_imagem = _salvar_imagem_revisao(
                    caminho,
                    pagina.numero_pagina,
                    diretorio_recursos,
                    dpi=min(dpi, _DPI_IMAGEM_TABELA),
                    sufixo="tabela_raster",
                )
                caminhos_recursos.append(caminho_imagem)
                paginas_de_tabela_raster.append(pagina.numero_pagina)
                paginas_candidatas_a_tabela.append(pagina.numero_pagina)
                paginas_para_revisao.append(pagina.numero_pagina)
                pagina.tipo_pagina = "raster_table_candidate"
                pagina.imagem_revisao_preservada = True
                blocos.append(
                    _bloco_tabela(
                        pagina.numero_pagina,
                        f"Tabela raster da página {pagina.numero_pagina}",
                        item.texto,
                        caminho_imagem.relative_to(diretorio_saida).as_posix(),
                        candidata=True,
                        raster=True,
                    )
                )
                continue

            if deve_classificar_como_registro_de_coordenadas(
                item.coordenadas,
                item.tabela_textual,
                grade_visual_forte=item.raster.forte,
            ):
                caminho_imagem = _salvar_imagem_revisao(
                    caminho,
                    pagina.numero_pagina,
                    diretorio_recursos,
                    dpi=min(dpi, _DPI_IMAGEM_COORDENADAS),
                    sufixo="coordenadas",
                )
                caminhos_recursos.append(caminho_imagem)
                paginas_de_registro_de_coordenadas.append(pagina.numero_pagina)
                paginas_para_revisao.append(pagina.numero_pagina)
                pagina.tipo_pagina = "coordinate_register"
                pagina.imagem_revisao_preservada = True
                blocos.append(
                    _bloco_coordenadas(
                        pagina.numero_pagina,
                        item.texto,
                        caminho_imagem.relative_to(diretorio_saida).as_posix(),
                    )
                )
                continue

            classe_mapa = classificar_pagina_de_mapa(
                item.texto,
                max(pagina.quantidade_imagens, 1),
                complexidade_visual=item.visual_mapa.complexidade_visual,
            )
            if (
                item.visual_mapa.semelhante_a_capa
                and classe_mapa != "map_confirmed"
            ):
                classe_mapa = "map_cover"
            if classe_mapa in {"map_candidate", "map_confirmed", "map_cover"}:
                pagina.tipo_pagina = classe_mapa
                pagina.rota = "map"
                sufixo = "capa_mapa" if classe_mapa == "map_cover" else "mapa"
                caminho_imagem = salvar_imagem_de_mapa(
                    caminho,
                    pagina.numero_pagina,
                    diretorio_recursos,
                    dpi=min(dpi, 300),
                    sufixo=sufixo,
                )
                caminhos_recursos.append(caminho_imagem)
                paginas_para_revisao.append(pagina.numero_pagina)
                if classe_mapa == "map_cover":
                    paginas_de_capa_de_mapa.append(pagina.numero_pagina)
                    aviso = "Capa ou índice cartográfico preservado."
                elif classe_mapa == "map_confirmed":
                    paginas_de_mapa.append(pagina.numero_pagina)
                    aviso = (
                        "Conteúdo cartográfico confirmado por evidência textual "
                        "e visual."
                    )
                else:
                    paginas_candidatas_a_mapa.append(pagina.numero_pagina)
                    aviso = "Possível conteúdo cartográfico preservado para revisão."
                blocos.append(
                    _bloco_visual(
                        pagina.numero_pagina,
                        extrair_titulo_de_mapa(
                            item.texto,
                            pagina.numero_pagina,
                        ),
                        item.texto,
                        caminho_imagem.relative_to(diretorio_saida).as_posix(),
                        "ocr",
                        tipo_visual=classe_mapa,
                        aviso=aviso,
                    )
                )
                continue

            if item.qualidade.requer_revisao:
                caminho_imagem = _salvar_imagem_revisao(
                    caminho,
                    pagina.numero_pagina,
                    diretorio_recursos,
                    dpi=min(dpi, _DPI_IMAGEM_REVISAO),
                    sufixo="ocr_revisao",
                )
                caminhos_recursos.append(caminho_imagem)
                paginas_para_revisao.append(pagina.numero_pagina)
                paginas_com_imagem_de_revisao_ocr.append(pagina.numero_pagina)
                pagina.tipo_pagina = "ocr_review"
                pagina.imagem_revisao_preservada = True
                blocos.append(
                    _bloco_revisao_ocr(
                        pagina.numero_pagina,
                        item.texto,
                        caminho_imagem.relative_to(diretorio_saida).as_posix(),
                        item.qualidade.qualidade,
                    )
                )
                continue

            blocos.append(_bloco_ocr(pagina.numero_pagina, item.texto))
            continue

        if extracao.rotated_text:
            paginas_com_texto_rotacionado.append(pagina.numero_pagina)
            paginas_para_revisao.append(pagina.numero_pagina)
            caminho_imagem = _salvar_imagem_revisao(
                caminho,
                pagina.numero_pagina,
                diretorio_recursos,
                dpi=min(dpi, _DPI_IMAGEM_REVISAO),
                sufixo="texto_rotacionado",
            )
            caminhos_recursos.append(caminho_imagem)
            pagina.imagem_revisao_preservada = True
            blocos.append(
                _bloco_visual(
                    pagina.numero_pagina,
                    f"Texto rotacionado da página {pagina.numero_pagina}",
                    texto_nativo,
                    caminho_imagem.relative_to(diretorio_saida).as_posix(),
                    extracao.selected_mode,
                    tipo_visual="rotated_text_review",
                    aviso=(
                        "Texto rotacionado detectado; imagem preservada para conferência."
                    ),
                )
            )
            continue

        blocos.append(
            f"<!-- pagina_original: {pagina.numero_pagina}; rota: native:pypdf; "
            f"modo: {extracao.selected_mode} -->\n\n"
            f"## Página {pagina.numero_pagina}\n\n{texto_nativo}\n"
        )

    caminho_markdown = diretorio_saida / f"{caminho.stem}.md"
    caminho_manifesto = diretorio_saida / f"{caminho.stem}.manifest.json"
    markdown_temporario = caminho_markdown.with_suffix(".md.tmp")
    markdown_temporario.write_text("\n\n".join(blocos), encoding="utf-8")
    markdown_temporario.replace(caminho_markdown)

    manifesto = ManifestoDeConversao(
        caminho_origem=caminho_origem,
        sha256_origem=diagnostico.sha256,
        quantidade_paginas=diagnostico.quantidade_paginas,
        caminho_markdown=caminho_markdown,
        sha256_markdown=sha256_file(caminho_markdown),
        tamanho_markdown_bytes=caminho_markdown.stat().st_size,
        caminhos_recursos=caminhos_recursos,
        paginas_com_ocr=paginas_com_ocr,
        paginas_de_mapa=sorted(set(paginas_de_mapa)),
        paginas_de_tabela=sorted(set(paginas_de_tabela)),
        paginas_candidatas_a_tabela=sorted(set(paginas_candidatas_a_tabela)),
        paginas_decorativas=sorted(set(paginas_decorativas)),
        paginas_para_revisao=sorted(set(paginas_para_revisao)),
        dpi=dpi,
        versao_conversor=__version__,
        diagnostico=diagnostico,
        paginas_com_texto_rotacionado=sorted(
            set(paginas_com_texto_rotacionado)
        ),
        paginas_com_texto_visual_preservado=sorted(
            set(paginas_com_texto_visual_preservado)
        ),
        paginas_de_tabela_raster=sorted(set(paginas_de_tabela_raster)),
        paginas_de_diagrama=sorted(set(paginas_de_diagrama)),
        paginas_de_registro_de_coordenadas=sorted(
            set(paginas_de_registro_de_coordenadas)
        ),
        paginas_candidatas_a_mapa=sorted(set(paginas_candidatas_a_mapa)),
        paginas_de_capa_de_mapa=sorted(set(paginas_de_capa_de_mapa)),
        paginas_com_imagem_de_revisao_ocr=sorted(
            set(paginas_com_imagem_de_revisao_ocr)
        ),
        segundos_de_processamento=round(time.perf_counter() - inicio, 3),
    )
    escrever_manifesto(manifesto, caminho_manifesto)
    return caminho_markdown


__all__ = ["EvidenciaOCRDePagina", "converter_pdf", "_imagem_markdown"]
