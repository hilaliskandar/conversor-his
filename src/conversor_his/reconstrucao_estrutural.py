# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from statistics import fmean
from typing import Literal

from .ocr.tesseract_engine import OcrToken

TipoLinha = Literal[
    "titulo",
    "capitulo",
    "secao",
    "subsecao",
    "artigo",
    "paragrafo",
    "inciso",
    "alinea",
    "item",
    "texto",
]

_PADROES_LINHA: tuple[tuple[TipoLinha, re.Pattern[str]], ...] = (
    ("titulo", re.compile(r"^TITULO\s+(?:[IVXLCDM]+|\d+)(?:\b|\s)", re.IGNORECASE)),
    ("capitulo", re.compile(r"^CAPITULO\s+(?:[IVXLCDM]+|\d+)(?:\b|\s)", re.IGNORECASE)),
    ("subsecao", re.compile(r"^SUBSECAO\s+(?:[IVXLCDM]+|\d+)(?:\b|\s)", re.IGNORECASE)),
    ("secao", re.compile(r"^SECAO\s+(?:[IVXLCDM]+|\d+)(?:\b|\s)", re.IGNORECASE)),
    (
        "artigo",
        re.compile(
            r"^ART(?:IGO)?\.?\s*\d+[Oº°]?(?:\s*-\s*[A-Z])?(?:\b|[.\-—–])",
            re.IGNORECASE,
        ),
    ),
    (
        "paragrafo",
        re.compile(
            r"^(?:§\s*\d+[Oº°]?|PARAGRAFO\s+(?:UNICO|\d+[Oº°]?))"
            r"(?:\b|[.\-—–])",
            re.IGNORECASE,
        ),
    ),
    ("inciso", re.compile(r"^[IVXLCDM]+\s*[\-—–.]\s*", re.IGNORECASE)),
    ("alinea", re.compile(r"^[A-Z]\s*\)\s*", re.IGNORECASE)),
    ("item", re.compile(r"^\d+\s*[.)\-—–]\s*")),
)

_SEM_ESPACO_ANTES = frozenset(".,;:!?%)]}º°")
_SEM_ESPACO_DEPOIS = frozenset("([{§")


@dataclass(frozen=True, slots=True)
class LinhaReconstruida:
    pagina: int
    bloco_origem: int
    paragrafo_origem: int
    linha_origem: int
    ordem: int
    coluna: int
    texto: str
    tipo: TipoLinha
    confianca_media: float | None
    quantidade_tokens: int
    esquerda: int
    topo: int
    direita: int
    base: int


@dataclass(frozen=True, slots=True)
class BlocoReconstruido:
    pagina: int
    ordem: int
    coluna: int
    bloco_origem: int
    paragrafo_origem: int
    tipo_predominante: TipoLinha
    texto: str
    confianca_media: float | None
    quantidade_linhas: int
    esquerda: int
    topo: int
    direita: int
    base: int
    linhas: list[LinhaReconstruida]


def _sem_acentos(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(
        caractere
        for caractere in decomposto
        if not unicodedata.combining(caractere)
    ).upper()


def classificar_linha(texto: str) -> TipoLinha:
    base = _sem_acentos(texto.strip())
    for tipo, padrao in _PADROES_LINHA:
        if padrao.match(base):
            return tipo
    return "texto"


def juntar_tokens(tokens: Iterable[OcrToken]) -> str:
    partes: list[str] = []
    for token in tokens:
        atual = token.text.strip()
        if not atual:
            continue
        if not partes:
            partes.append(atual)
            continue
        anterior = partes[-1]
        if atual in {"-", "–", "—"}:
            partes.append(atual)
        elif (
            atual[0] in _SEM_ESPACO_ANTES
            or anterior[-1] in _SEM_ESPACO_DEPOIS
            or anterior.endswith("/")
        ):
            partes[-1] = anterior + atual
        else:
            partes.append(atual)
    return " ".join(partes)


def _media_confianca(tokens: Iterable[OcrToken]) -> float | None:
    valores = [token.confidence for token in tokens if token.confidence is not None]
    return round(fmean(valores), 3) if valores else None


def reconstruir_linhas(tokens: Iterable[OcrToken]) -> list[LinhaReconstruida]:
    grupos: dict[tuple[int, int, int, int], list[OcrToken]] = defaultdict(list)
    for token in tokens:
        grupos[
            (
                token.page_number,
                token.block_number,
                token.paragraph_number,
                token.line_number,
            )
        ].append(token)

    linhas: list[LinhaReconstruida] = []
    for chave, itens in grupos.items():
        pagina, bloco, paragrafo, linha = chave
        ordenados = sorted(itens, key=lambda item: (item.left, item.word_number))
        direita = max(item.left + item.width for item in ordenados)
        base = max(item.top + item.height for item in ordenados)
        texto = juntar_tokens(ordenados)
        linhas.append(
            LinhaReconstruida(
                pagina=pagina,
                bloco_origem=bloco,
                paragrafo_origem=paragrafo,
                linha_origem=linha,
                ordem=0,
                coluna=1,
                texto=texto,
                tipo=classificar_linha(texto),
                confianca_media=_media_confianca(ordenados),
                quantidade_tokens=len(ordenados),
                esquerda=min(item.left for item in ordenados),
                topo=min(item.top for item in ordenados),
                direita=direita,
                base=base,
            )
        )

    resultado: list[LinhaReconstruida] = []
    por_pagina: dict[int, list[LinhaReconstruida]] = defaultdict(list)
    for linha in linhas:
        por_pagina[linha.pagina].append(linha)
    for pagina in sorted(por_pagina):
        ordenadas = sorted(
            por_pagina[pagina],
            key=lambda item: (
                item.topo,
                item.esquerda,
                item.bloco_origem,
                item.linha_origem,
            ),
        )
        com_colunas = _atribuir_colunas(ordenadas)
        com_colunas.sort(
            key=lambda item: (
                item.topo,
                0 if item.coluna == 0 else item.coluna,
                item.esquerda,
            )
        )
        resultado.extend(
            replace(item, ordem=ordem)
            for ordem, item in enumerate(com_colunas, start=1)
        )
    return resultado


def _sobreposicao_vertical(
    esquerda: list[LinhaReconstruida],
    direita: list[LinhaReconstruida],
) -> float:
    topo = max(min(item.topo for item in esquerda), min(item.topo for item in direita))
    base = min(max(item.base for item in esquerda), max(item.base for item in direita))
    if base <= topo:
        return 0.0
    altura_esquerda = max(item.base for item in esquerda) - min(
        item.topo for item in esquerda
    )
    altura_direita = max(item.base for item in direita) - min(
        item.topo for item in direita
    )
    menor_altura = min(altura_esquerda, altura_direita)
    return (base - topo) / menor_altura if menor_altura > 0 else 0.0


def _atribuir_colunas(linhas: list[LinhaReconstruida]) -> list[LinhaReconstruida]:
    if len(linhas) < 6:
        return linhas
    pagina_esquerda = min(item.esquerda for item in linhas)
    pagina_direita = max(item.direita for item in linhas)
    largura_pagina = pagina_direita - pagina_esquerda
    if largura_pagina <= 0:
        return linhas

    candidatas = [
        item
        for item in linhas
        if (item.direita - item.esquerda) <= largura_pagina * 0.72
    ]
    if len(candidatas) < 6:
        return linhas
    candidatas_ordenadas = sorted(
        candidatas,
        key=lambda item: (
            (item.esquerda + item.direita) / 2,
            item.topo,
            item.esquerda,
        ),
    )
    centros = [
        ((item.esquerda + item.direita) / 2, item)
        for item in candidatas_ordenadas
    ]
    melhor: tuple[float, int] | None = None
    for indice in range(2, len(centros) - 2):
        lacuna = centros[indice][0] - centros[indice - 1][0]
        if melhor is None or lacuna > melhor[0]:
            melhor = (lacuna, indice)
    if melhor is None or melhor[0] < largura_pagina * 0.18:
        return linhas

    indice = melhor[1]
    grupo_esquerdo = [item for _, item in centros[:indice]]
    grupo_direito = [item for _, item in centros[indice:]]
    if len(grupo_esquerdo) < 3 or len(grupo_direito) < 3:
        return linhas
    if _sobreposicao_vertical(grupo_esquerdo, grupo_direito) < 0.35:
        return linhas

    corte = (centros[indice - 1][0] + centros[indice][0]) / 2
    resultado: list[LinhaReconstruida] = []
    for item in linhas:
        largura = item.direita - item.esquerda
        if largura > largura_pagina * 0.72:
            coluna = 0
        else:
            centro = (item.esquerda + item.direita) / 2
            coluna = 1 if centro <= corte else 2
        resultado.append(replace(item, coluna=coluna))
    return resultado


def reconstruir_blocos(tokens: Iterable[OcrToken]) -> list[BlocoReconstruido]:
    linhas = reconstruir_linhas(tokens)
    grupos: dict[tuple[int, int, int, int], list[LinhaReconstruida]] = defaultdict(list)
    for linha in linhas:
        grupos[
            (
                linha.pagina,
                linha.coluna,
                linha.bloco_origem,
                linha.paragrafo_origem,
            )
        ].append(linha)

    blocos: list[BlocoReconstruido] = []
    ordem_por_pagina: dict[int, int] = defaultdict(int)
    chaves = sorted(
        grupos,
        key=lambda chave: (
            chave[0],
            min(item.topo for item in grupos[chave]),
            chave[1],
            min(item.esquerda for item in grupos[chave]),
        ),
    )
    for chave in chaves:
        pagina, coluna, bloco, paragrafo = chave
        itens = sorted(grupos[chave], key=lambda item: (item.topo, item.esquerda))
        ordem_por_pagina[pagina] += 1
        confiancas = [
            item.confianca_media
            for item in itens
            if item.confianca_media is not None
        ]
        tipos = [item.tipo for item in itens if item.tipo != "texto"]
        tipo_predominante: TipoLinha = tipos[0] if tipos else "texto"
        blocos.append(
            BlocoReconstruido(
                pagina=pagina,
                ordem=ordem_por_pagina[pagina],
                coluna=coluna,
                bloco_origem=bloco,
                paragrafo_origem=paragrafo,
                tipo_predominante=tipo_predominante,
                texto="\n".join(item.texto for item in itens),
                confianca_media=round(fmean(confiancas), 3) if confiancas else None,
                quantidade_linhas=len(itens),
                esquerda=min(item.esquerda for item in itens),
                topo=min(item.topo for item in itens),
                direita=max(item.direita for item in itens),
                base=max(item.base for item in itens),
                linhas=itens,
            )
        )
    return blocos


def carregar_tokens_jsonl(caminho: Path) -> list[OcrToken]:
    tokens: list[OcrToken] = []
    for numero_linha, linha in enumerate(
        caminho.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if not linha.strip():
            continue
        registro = json.loads(linha)
        try:
            tokens.append(OcrToken(**registro))
        except TypeError as exc:
            raise ValueError(
                f"token OCR inválido na linha {numero_linha} de {caminho}"
            ) from exc
    return tokens


def gravar_estrutura_ocr(tokens: Iterable[OcrToken], caminho: Path) -> Path:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_suffix(caminho.suffix + ".tmp")
    with temporario.open("w", encoding="utf-8") as fluxo:
        for bloco in reconstruir_blocos(tokens):
            registro = asdict(bloco)
            registro["tipo_registro"] = "bloco_ocr"
            fluxo.write(json.dumps(registro, ensure_ascii=False) + "\n")
    temporario.replace(caminho)
    return caminho


__all__ = [
    "BlocoReconstruido",
    "LinhaReconstruida",
    "TipoLinha",
    "carregar_tokens_jsonl",
    "classificar_linha",
    "gravar_estrutura_ocr",
    "juntar_tokens",
    "reconstruir_blocos",
    "reconstruir_linhas",
]
