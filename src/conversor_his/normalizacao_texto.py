# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
import unicodedata

_TRADUCAO_CARACTERES_INVISIVEIS = str.maketrans(
    {
        "\u200b": None,
        "\u200c": None,
        "\u200d": None,
        "\u2060": None,
        "\ufeff": None,
    }
)
_ESPACOS_HORIZONTAIS_RE = re.compile(r"[ \t]{2,}")
_LINHAS_EM_BRANCO_EXCEDENTES_RE = re.compile(r"\n{3,}")
_LACUNA_LONGA_RE = re.compile(r" {8,}")


def limpar_caracteres_invisiveis(texto: str) -> str:
    """Normaliza Unicode e remove caracteres invisíveis sem valor textual."""

    return (
        unicodedata.normalize("NFC", texto)
        .translate(_TRADUCAO_CARACTERES_INVISIVEIS)
        .replace("\u00a0", " ")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )


def normalizar_texto_de_prosa(texto: str) -> str:
    """Produz texto pesquisável sem alterar a ordem das linhas.

    A normalização é destinada a prosa normativa. Ela não deve ser aplicada ao
    bloco bruto de tabelas, no qual os espaços podem representar colunas.
    """

    texto_limpo = limpar_caracteres_invisiveis(texto)
    linhas: list[str] = []
    for linha in texto_limpo.splitlines():
        linha_normalizada = _ESPACOS_HORIZONTAIS_RE.sub(" ", linha.strip())
        linhas.append(linha_normalizada)
    texto_normalizado = "\n".join(linhas).strip()
    return _LINHAS_EM_BRANCO_EXCEDENTES_RE.sub("\n\n", texto_normalizado)


def tem_espacamento_excessivo_de_layout(texto: str) -> bool:
    """Detecta saídas em que o modo layout usa espaços como posicionamento."""

    texto_limpo = limpar_caracteres_invisiveis(texto)
    if len(texto_limpo) < 120:
        return False
    quantidade_espacos = texto_limpo.count(" ")
    lacunas_longas = list(_LACUNA_LONGA_RE.finditer(texto_limpo))
    caracteres_em_lacunas = sum(
        ocorrencia.end() - ocorrencia.start() for ocorrencia in lacunas_longas
    )
    return (
        len(lacunas_longas) >= 3
        and (
            quantidade_espacos / max(len(texto_limpo), 1) >= 0.22
            or caracteres_em_lacunas / max(len(texto_limpo), 1) >= 0.08
        )
    )


__all__ = [
    "limpar_caracteres_invisiveis",
    "normalizar_texto_de_prosa",
    "tem_espacamento_excessivo_de_layout",
]
