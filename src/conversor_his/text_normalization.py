# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
import unicodedata

_ZERO_WIDTH_TRANSLATION = str.maketrans(
    {
        "\u200b": None,
        "\u200c": None,
        "\u200d": None,
        "\u2060": None,
        "\ufeff": None,
    }
)
_HORIZONTAL_WHITESPACE_RE = re.compile(r"[ \t]{2,}")
_EXCESS_BLANK_LINES_RE = re.compile(r"\n{3,}")
_LONG_GAP_RE = re.compile(r" {8,}")


def clean_invisible_characters(text: str) -> str:
    """Normaliza Unicode e remove caracteres invisíveis sem valor textual."""

    return (
        unicodedata.normalize("NFC", text)
        .translate(_ZERO_WIDTH_TRANSLATION)
        .replace("\u00a0", " ")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )


def normalize_prose_text(text: str) -> str:
    """Produz texto pesquisável sem alterar a ordem das linhas.

    A normalização é destinada a prosa normativa. Ela não deve ser aplicada ao
    bloco bruto de tabelas, no qual os espaços podem representar colunas.
    """

    cleaned = clean_invisible_characters(text)
    lines: list[str] = []
    for line in cleaned.splitlines():
        normalized_line = _HORIZONTAL_WHITESPACE_RE.sub(" ", line.strip())
        lines.append(normalized_line)
    normalized = "\n".join(lines).strip()
    return _EXCESS_BLANK_LINES_RE.sub("\n\n", normalized)


def has_excessive_layout_spacing(text: str) -> bool:
    """Detecta saídas em que o modo layout usa espaços como posicionamento."""

    cleaned = clean_invisible_characters(text)
    if len(cleaned) < 120:
        return False
    spaces = cleaned.count(" ")
    long_gaps = list(_LONG_GAP_RE.finditer(cleaned))
    long_gap_characters = sum(match.end() - match.start() for match in long_gaps)
    return (
        len(long_gaps) >= 3
        and (
            spaces / max(len(cleaned), 1) >= 0.22
            or long_gap_characters / max(len(cleaned), 1) >= 0.08
        )
    )
