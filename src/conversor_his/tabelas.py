# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from math import ceil
from pathlib import Path
from typing import Literal

from .ocr.render import render_pdf_page

ClassificacaoDeTabela = Literal[
    "not_table",
    "candidate",
    "mixed_candidate",
    "continuation_candidate",
    "visual_candidate",
    "raster_candidate",
    "confirmed",
]

_LACUNA_INTERNA_RE = re.compile(r"(?<=\S) {2,}(?=\S)")
_NUMERO_RE = re.compile(r"\d+(?:[.,/]\d+)?")
_CODIGO_ZONA_RE = re.compile(
    r"\b(?:ZEIS|ZRU\d*|ZEC|ZAI|ZUR|ZPRA|SOU|SEI|CCSB|NUAR|NUR\d*|"
    r"Z[A-Z]{1,4}\d*|MZ\d+)\b",
    re.IGNORECASE,
)
_PREFIXO_LEGAL_RE = re.compile(
    r"^(?:ART\.?\s*\d+|§|PARAGRAFO\b|[IVXLCDM]+\s*[-.)]|[A-Z]\s*[.)])",
    re.IGNORECASE,
)
_DEFINICAO_LEGAL_RE = re.compile(
    r"^(?:[IVXLCDM]+\s*[-.)]|[A-Z]\s*[.)])\s+.{20,}:|^§\s*\d+",
    re.IGNORECASE,
)
_COORDENADA_RE = re.compile(r"\b[XY]\s*=\s*\d", re.IGNORECASE)
_TITULO_EXPLICITO_RE = re.compile(
    r"^(?:TABELA|QUADRO)\b|"
    r"^ANEXO\b.{0,180}\b(?:LISTAGEM|TABELA|QUADRO|PARAMETROS?|ZONAS?|ZEIS|"
    r"USOS?|INSTRUMENTOS?)\b",
    re.IGNORECASE,
)
_TITULO_NOMINAL_RE = re.compile(
    r"^(?:PARAMETROS?|INDICES?|INSTRUMENTOS?|LISTAGEM|REQUISITOS?)\b.{0,180}"
    r"\b(?:ZONA|ZONAS|URBANISTICOS?|EDILICIOS?|ZEIS|USOS?)\b",
    re.IGNORECASE,
)
_GRUPOS_CABECALHO = {
    "territorial": re.compile(r"\b(?:ZONA|ZONAS|ZEIS|SETOR|AREA|MACROZONA)\b"),
    "identificador": re.compile(r"\b(?:CODIGO|NUMERO|N[Oº°]|LEI|DECRETO)\b"),
    "denominacao": re.compile(
        r"\b(?:COMUNIDADE|DENOMINACAO|LOCALIDADE|DESCRICAO|NOME)\b"
    ),
    "parametro": re.compile(
        r"\b(?:COEFICIENTE|TAXA|GABARITO|RECUO|APROVEITAMENTO|SOLO NATURAL|"
        r"TESTADA|LOTE MINIMO|AREA MINIMA|TO|TSN|CA|GM|LM|TM)\b"
    ),
    "instrumento": re.compile(
        r"\b(?:INSTRUMENTOS?|OUTORGA|TRANSFERENCIA|POLITICA URBANA)\b"
    ),
    "observacao": re.compile(r"\b(?:OBSERVACOES?|REQUISITOS? ESPECIAIS)\b"),
    "uso": re.compile(
        r"\b(?:USOS?|HABITACIONAL|RESIDENCIAL|NAO HABITACIONAL|MISTO)\b"
    ),
    "dimensao": re.compile(r"\b(?:M2|M²|METROS?|PAVTOS?|PAVIMENTOS?)\b"),
}
_PADROES_PARAMETROS_URBANOS = {
    "lote": re.compile(r"\b(?:LOTE|LM|AREA MINIMA)\b"),
    "testada": re.compile(r"\b(?:TESTADA|TM)\b"),
    "recuo": re.compile(r"\b(?:RECUO|FRONT|LATERAL|FUNDOS?|LAT|FUND)\b"),
    "ocupacao": re.compile(r"\b(?:TO|TAXA DE OCUPACAO)\b"),
    "solo_natural": re.compile(r"\b(?:TSN|SOLO NATURAL)\b"),
    "gabarito": re.compile(r"\b(?:GM|GABARITO|PAVTOS?|PAVIMENTOS?)\b"),
    "aproveitamento": re.compile(r"\b(?:CA|COEFICIENTE DE APROVEITAMENTO)\b"),
    "uso": re.compile(r"\b(?:USO|HABITACIONAL|RESIDENCIAL|MISTO|INDUSTRIAL)\b"),
}


@dataclass(slots=True)
class AvaliacaoDeTabela:
    classificacao: ClassificacaoDeTabela
    suspeita: bool
    pontuacao: int
    quantidade_linhas: int
    colunas_estaveis: int
    ocorrencias_cabecalho: list[str] = field(default_factory=list)
    motivos: list[str] = field(default_factory=list)
    indice_linha_cabecalho: int | None = None
    proporcao_lista_legal: float = 0.0
    proporcao_prosa: float = 0.0
    linhas_numericas: int = 0
    linhas_valores_compactos: int = 0
    linhas_multicoluna: int = 0
    ocorrencias_parametros_urbanos: list[str] = field(default_factory=list)
    quantidade_codigos_zona: int = 0
    perfil_conteudo: str = "unknown"
    grade_visual_detectada: bool = False
    grade_visual_forte: bool = False
    pontuacao_grade_visual: int = 0
    quantidade_retangulos_vetoriais: int = 0
    linhas_vetoriais_horizontais: int = 0
    linhas_vetoriais_verticais: int = 0

    # Propriedades transitórias para consumidores da API 0.7.
    @property
    def classification(self) -> ClassificacaoDeTabela:
        return self.classificacao

    @property
    def suspected(self) -> bool:
        return self.suspeita

    @property
    def score(self) -> int:
        return self.pontuacao

    @property
    def row_count(self) -> int:
        return self.quantidade_linhas

    @property
    def stable_columns(self) -> int:
        return self.colunas_estaveis

    @property
    def header_hits(self) -> list[str]:
        return self.ocorrencias_cabecalho

    @property
    def reasons(self) -> list[str]:
        return self.motivos

    @property
    def header_line_index(self) -> int | None:
        return self.indice_linha_cabecalho

    @property
    def legal_list_ratio(self) -> float:
        return self.proporcao_lista_legal

    @property
    def prose_ratio(self) -> float:
        return self.proporcao_prosa

    @property
    def numeric_rows(self) -> int:
        return self.linhas_numericas

    @property
    def compact_value_rows(self) -> int:
        return self.linhas_valores_compactos

    @property
    def multi_column_lines(self) -> int:
        return self.linhas_multicoluna

    @multi_column_lines.setter
    def multi_column_lines(self, valor: int) -> None:
        self.linhas_multicoluna = valor

    @property
    def urban_parameter_hits(self) -> list[str]:
        return self.ocorrencias_parametros_urbanos

    @property
    def zone_code_count(self) -> int:
        return self.quantidade_codigos_zona

    @property
    def content_profile(self) -> str:
        return self.perfil_conteudo

    @property
    def visual_grid_detected(self) -> bool:
        return self.grade_visual_detectada

    @visual_grid_detected.setter
    def visual_grid_detected(self, valor: bool) -> None:
        self.grade_visual_detectada = valor

    @property
    def visual_grid_strong(self) -> bool:
        return self.grade_visual_forte

    @visual_grid_strong.setter
    def visual_grid_strong(self, valor: bool) -> None:
        self.grade_visual_forte = valor

    @property
    def visual_grid_score(self) -> int:
        return self.pontuacao_grade_visual

    @visual_grid_score.setter
    def visual_grid_score(self, valor: int) -> None:
        self.pontuacao_grade_visual = valor

    @property
    def vector_rectangle_count(self) -> int:
        return self.quantidade_retangulos_vetoriais

    @vector_rectangle_count.setter
    def vector_rectangle_count(self, valor: int) -> None:
        self.quantidade_retangulos_vetoriais = valor

    @property
    def vector_horizontal_lines(self) -> int:
        return self.linhas_vetoriais_horizontais

    @vector_horizontal_lines.setter
    def vector_horizontal_lines(self, valor: int) -> None:
        self.linhas_vetoriais_horizontais = valor

    @property
    def vector_vertical_lines(self) -> int:
        return self.linhas_vetoriais_verticais

    @vector_vertical_lines.setter
    def vector_vertical_lines(self, valor: int) -> None:
        self.linhas_vetoriais_verticais = valor


def _maiusculas_sem_acentos(texto: str) -> str:
    texto_decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(
        caractere
        for caractere in texto_decomposto
        if not unicodedata.combining(caractere)
    ).upper()


def _inicios_celulas(linha: str) -> list[int]:
    texto = linha.rstrip()
    primeiro = re.search(r"\S", texto)
    if primeiro is None:
        return []
    inicios = [primeiro.start()]
    for lacuna in _LACUNA_INTERNA_RE.finditer(texto):
        if lacuna.end() < len(texto):
            inicios.append(lacuna.end())
    return sorted(set(inicios))


def _contar_colunas_estaveis(
    posicoes_linhas: list[list[int]],
    tolerancia: int = 4,
) -> int:
    if not posicoes_linhas:
        return 0
    faixas: Counter[int] = Counter()
    for posicoes in posicoes_linhas:
        vistas: set[int] = set()
        for posicao in posicoes:
            faixa = round(posicao / tolerancia)
            if faixa not in vistas:
                faixas[faixa] += 1
                vistas.add(faixa)
    suporte_minimo = max(3, ceil(len(posicoes_linhas) * 0.35))
    return sum(1 for suporte in faixas.values() if suporte >= suporte_minimo)


def _linha_e_titulo(linha: str) -> bool:
    texto_normalizado = _maiusculas_sem_acentos(" ".join(linha.split()))
    if (
        not texto_normalizado
        or len(texto_normalizado) > 220
        or _PREFIXO_LEGAL_RE.search(texto_normalizado)
    ):
        return False
    return bool(
        _TITULO_EXPLICITO_RE.search(texto_normalizado)
        or _TITULO_NOMINAL_RE.search(texto_normalizado)
    )


def _ocorrencias_cabecalho(texto: str) -> list[str]:
    texto_normalizado = _maiusculas_sem_acentos(texto)
    return [
        nome
        for nome, padrao in _GRUPOS_CABECALHO.items()
        if padrao.search(texto_normalizado)
    ]


def _ocorrencias_parametros_urbanos(texto: str) -> list[str]:
    texto_normalizado = _maiusculas_sem_acentos(texto)
    return [
        nome
        for nome, padrao in _PADROES_PARAMETROS_URBANOS.items()
        if padrao.search(texto_normalizado)
    ]


def _melhor_janela_cabecalho(
    linhas: list[str],
) -> tuple[int, int, list[str]] | None:
    melhor: tuple[tuple[int, int, int], int, int, list[str]] | None = None
    for inicio in range(len(linhas)):
        for largura in (1, 2, 3):
            fim = inicio + largura
            if fim > len(linhas):
                continue
            linhas_janela = linhas[inicio:fim]
            if any(
                _PREFIXO_LEGAL_RE.search(_maiusculas_sem_acentos(linha.strip()))
                for linha in linhas_janela
            ):
                continue
            combinado = " ".join(linhas_janela)
            ocorrencias = _ocorrencias_cabecalho(combinado)
            parametros = _ocorrencias_parametros_urbanos(combinado)
            separadores = sum(
                max(len(_inicios_celulas(linha)) - 1, 0)
                for linha in linhas_janela
            )
            if len(ocorrencias) < 2 or separadores < 2:
                continue
            classificacao = (
                len(ocorrencias) + len(parametros),
                separadores,
                -inicio,
            )
            if melhor is None or classificacao > melhor[0]:
                melhor = (classificacao, inicio, fim, ocorrencias)
    if melhor is None:
        return None
    return melhor[1], melhor[2], melhor[3]


def _linha_e_lista_legal(linha: str) -> bool:
    texto_normalizado = _maiusculas_sem_acentos(linha.strip())
    return bool(
        _PREFIXO_LEGAL_RE.search(texto_normalizado)
        or _DEFINICAO_LEGAL_RE.search(texto_normalizado)
        or texto_normalizado.endswith(";")
    )


def _linha_tem_valores_compactos(linha: str) -> bool:
    inicios = _inicios_celulas(linha)
    if len(inicios) < 3:
        return False
    texto_normalizado = _maiusculas_sem_acentos(linha)
    quantidade_numeros = len(_NUMERO_RE.findall(linha))
    return len(linha.split()) <= 24 and (
        quantidade_numeros >= 2 or bool(_CODIGO_ZONA_RE.search(texto_normalizado))
    )


def _tem_assinatura_local_cabecalho(linhas: list[str]) -> bool:
    return any(
        len(_inicios_celulas(linha)) >= 3
        and len(_ocorrencias_cabecalho(linha)) >= 2
        for linha in linhas
    )


def _avaliacao_vazia(perfil: str = "prose") -> AvaliacaoDeTabela:
    return AvaliacaoDeTabela(
        classificacao="not_table",
        suspeita=False,
        pontuacao=0,
        quantidade_linhas=0,
        colunas_estaveis=0,
        perfil_conteudo=perfil,
    )


def avaliar_tabela(texto: str) -> AvaliacaoDeTabela:
    """Classifica estrutura tabular com regras calibradas para legislação urbana."""

    linhas = [linha.rstrip() for linha in texto.splitlines() if linha.strip()]
    if len(linhas) < 3:
        return _avaliacao_vazia()

    pagina_normalizada = _maiusculas_sem_acentos("\n".join(linhas))
    linhas_coordenadas = sum(bool(_COORDENADA_RE.search(linha)) for linha in linhas)
    total_linhas_legais = sum(_linha_e_lista_legal(linha) for linha in linhas)
    proporcao_legal = total_linhas_legais / max(len(linhas), 1)
    linhas_multicoluna = sum(len(_inicios_celulas(linha)) >= 3 for linha in linhas)
    linhas_valores_alinhados = sum(
        _linha_tem_valores_compactos(linha) for linha in linhas
    )
    linhas_numericas_alinhadas = sum(
        len(_inicios_celulas(linha)) >= 3 and len(_NUMERO_RE.findall(linha)) >= 2
        for linha in linhas
    )
    quantidade_codigos_zona = len(_CODIGO_ZONA_RE.findall(pagina_normalizada))
    parametros_pagina = _ocorrencias_parametros_urbanos(pagina_normalizada)
    evidencia_titulo_explicito = any(_linha_e_titulo(linha) for linha in linhas[:8])

    if (
        linhas_coordenadas >= max(4, len(linhas) // 3)
        and not _TITULO_EXPLICITO_RE.search(pagina_normalizada)
    ):
        resultado = _avaliacao_vazia("coordinates")
        resultado.linhas_multicoluna = linhas_multicoluna
        return resultado

    sinal_continuacao = (
        linhas_valores_alinhados >= 3
        and quantidade_codigos_zona >= 2
        and (len(parametros_pagina) >= 2 or linhas_valores_alinhados >= 4)
        and proporcao_legal <= 0.25
        and not evidencia_titulo_explicito
        and not _tem_assinatura_local_cabecalho(linhas)
    )
    if sinal_continuacao:
        return AvaliacaoDeTabela(
            classificacao="continuation_candidate",
            suspeita=False,
            pontuacao=7,
            quantidade_linhas=linhas_multicoluna,
            colunas_estaveis=0,
            motivos=["possivel continuacao de matriz urbanistica sem cabecalho local"],
            proporcao_lista_legal=round(proporcao_legal, 4),
            linhas_numericas=linhas_numericas_alinhadas,
            linhas_valores_compactos=linhas_valores_alinhados,
            linhas_multicoluna=linhas_multicoluna,
            ocorrencias_parametros_urbanos=parametros_pagina,
            quantidade_codigos_zona=quantidade_codigos_zona,
            perfil_conteudo="urban_matrix_continuation",
        )

    cabecalho = _melhor_janela_cabecalho(linhas)
    if cabecalho is None:
        perfil = "legal_list" if total_linhas_legais >= len(linhas) * 0.3 else "prose"
        return _avaliacao_vazia(perfil)

    inicio_cabecalho, fim_cabecalho, ocorrencias_cabecalho = cabecalho
    titulo_proximo = any(
        _linha_e_titulo(linhas[indice])
        for indice in range(max(0, inicio_cabecalho - 5), inicio_cabecalho)
    )
    titulo_no_cabecalho = any(
        _linha_e_titulo(linha)
        for linha in linhas[inicio_cabecalho:fim_cabecalho]
    )
    evidencia_titulo = (
        evidencia_titulo_explicito or titulo_proximo or titulo_no_cabecalho
    )
    texto_cabecalho = " ".join(linhas[inicio_cabecalho:fim_cabecalho])
    parametros_urbanos = sorted(
        set(parametros_pagina + _ocorrencias_parametros_urbanos(texto_cabecalho))
    )

    janela_dados = linhas[fim_cabecalho : fim_cabecalho + 45]
    posicoes_linhas: list[list[int]] = []
    linhas_numericas = 0
    linhas_valores_compactos = 0
    linhas_legais = 0
    linhas_prosa = 0

    for linha in janela_dados:
        if _linha_e_lista_legal(linha):
            linhas_legais += 1
            continue
        inicios = _inicios_celulas(linha)
        quantidade_palavras = len(linha.split())
        quantidade_numeros = len(_NUMERO_RE.findall(linha))
        if len(inicios) < 3:
            if quantidade_palavras >= 14:
                linhas_prosa += 1
            continue
        posicoes_linhas.append(inicios)
        if quantidade_numeros >= 1:
            linhas_numericas += 1
        if _linha_tem_valores_compactos(linha):
            linhas_valores_compactos += 1

    quantidade_linhas = len(posicoes_linhas)
    colunas_estaveis = _contar_colunas_estaveis(posicoes_linhas)
    proporcao_lista_legal = linhas_legais / max(len(janela_dados), 1)
    proporcao_prosa = linhas_prosa / max(len(janela_dados), 1)
    vocabulario_matriz = len(parametros_urbanos) >= 4 or (
        "territorial" in ocorrencias_cabecalho
        and "uso" in ocorrencias_cabecalho
        and len(parametros_urbanos) >= 2
    )

    pontuacao = 0
    motivos: list[str] = []
    if evidencia_titulo:
        pontuacao += 3
        motivos.append("titulo tabular explicito associado ao cabecalho")
    if len(ocorrencias_cabecalho) >= 3:
        pontuacao += 3
        motivos.append("grupos semanticos de cabecalho em bloco local")
    elif len(ocorrencias_cabecalho) == 2 and vocabulario_matriz:
        pontuacao += 2
        motivos.append("cabecalho urbanistico especializado")
    if quantidade_linhas >= 4:
        pontuacao += 2
        motivos.append("quatro ou mais linhas alinhadas")
    if 2 <= colunas_estaveis <= 14:
        pontuacao += 2
        motivos.append("colunas recorrentes em quantidade plausivel")
    if linhas_numericas >= 2:
        pontuacao += 1
        motivos.append("linhas com valores ou codigos numericos")
    if linhas_valores_compactos >= 3:
        pontuacao += 2
        motivos.append("linhas compactas tipicas de matriz de parametros")
    if vocabulario_matriz:
        pontuacao += 3
        motivos.append("vocabulario convergente de matriz urbanistica")
    if quantidade_codigos_zona >= 2:
        pontuacao += 2
        motivos.append("codigos de zonas recorrentes")
    if proporcao_lista_legal >= 0.30:
        pontuacao -= 4
        motivos.append("penalizacao por estrutura juridica enumerativa")
    if proporcao_prosa >= 0.30:
        pontuacao -= 2
        motivos.append("penalizacao por paragrafos extensos")

    matriz_urbana_forte = (
        vocabulario_matriz
        and quantidade_linhas >= 3
        and linhas_valores_compactos >= 2
        and (quantidade_codigos_zona >= 1 or linhas_numericas >= 3)
        and proporcao_lista_legal <= 0.30
    )
    listagem_estruturada = (
        evidencia_titulo
        and len(ocorrencias_cabecalho) >= 3
        and quantidade_linhas >= 4
        and linhas_numericas >= 3
        and proporcao_lista_legal <= 0.20
        and proporcao_prosa <= 0.25
    )
    evidencia_alinhamento = (
        2 <= colunas_estaveis <= 14
        or matriz_urbana_forte
        or listagem_estruturada
        or (linhas_multicoluna >= 5 and quantidade_codigos_zona >= 2)
    )
    candidata = (
        quantidade_linhas >= 3
        and evidencia_alinhamento
        and proporcao_lista_legal <= 0.35
        and proporcao_prosa <= 0.35
        and (evidencia_titulo or linhas_numericas >= 2 or matriz_urbana_forte)
        and (len(ocorrencias_cabecalho) >= 2 or matriz_urbana_forte)
    )
    confirmada = candidata and (
        listagem_estruturada
        or (
            quantidade_linhas >= 4
            and linhas_valores_compactos >= 3
            and proporcao_lista_legal <= 0.20
            and proporcao_prosa <= 0.25
            and (
                evidencia_titulo
                or len(ocorrencias_cabecalho) >= 3
                or matriz_urbana_forte
            )
        )
    )

    pagina_mista = candidata and (
        inicio_cabecalho >= 10 or proporcao_prosa > 0.20
    )
    if confirmada and not pagina_mista:
        classificacao: ClassificacaoDeTabela = "confirmed"
    elif candidata and pagina_mista:
        classificacao = "mixed_candidate"
    elif candidata:
        classificacao = "candidate"
    else:
        classificacao = "not_table"

    return AvaliacaoDeTabela(
        classificacao=classificacao,
        suspeita=classificacao == "confirmed",
        pontuacao=pontuacao,
        quantidade_linhas=quantidade_linhas,
        colunas_estaveis=colunas_estaveis,
        ocorrencias_cabecalho=ocorrencias_cabecalho,
        motivos=motivos,
        indice_linha_cabecalho=inicio_cabecalho + 1,
        proporcao_lista_legal=round(proporcao_lista_legal, 4),
        proporcao_prosa=round(proporcao_prosa, 4),
        linhas_numericas=linhas_numericas,
        linhas_valores_compactos=linhas_valores_compactos,
        linhas_multicoluna=linhas_multicoluna,
        ocorrencias_parametros_urbanos=parametros_urbanos,
        quantidade_codigos_zona=quantidade_codigos_zona,
        perfil_conteudo=(
            "mixed_urban_matrix"
            if pagina_mista
            else "urban_matrix"
            if vocabulario_matriz
            else "generic_table"
        ),
    )


def extrair_titulo_de_tabela(texto: str, numero_pagina: int) -> str:
    linhas = [" ".join(linha.split()) for linha in texto.splitlines() if linha.strip()]
    for linha in linhas:
        if _linha_e_titulo(linha):
            return linha[:180].strip(" .;:-")
    return f"Tabela ou quadro da página {numero_pagina}"


def salvar_imagem_de_tabela(
    caminho_pdf: Path,
    numero_pagina: int,
    diretorio_recursos: Path,
    dpi: int = 200,
) -> Path:
    """Preserva a página tabular integral como imagem para conferência visual."""

    diretorio_recursos.mkdir(parents=True, exist_ok=True)
    caminho_imagem = diretorio_recursos / f"pagina_{numero_pagina:04d}_tabela.png"
    imagem = render_pdf_page(caminho_pdf, numero_pagina, dpi=dpi)
    imagem.save(caminho_imagem, format="PNG", optimize=True)
    return caminho_imagem


__all__ = [
    "AvaliacaoDeTabela",
    "ClassificacaoDeTabela",
    "avaliar_tabela",
    "extrair_titulo_de_tabela",
    "salvar_imagem_de_tabela",
]
