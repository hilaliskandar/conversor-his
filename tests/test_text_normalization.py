from __future__ import annotations

from conversor_his.converter import _markdown_image
from conversor_his.text_normalization import (
    clean_invisible_characters,
    has_excessive_layout_spacing,
    normalize_prose_text,
)


def test_normalize_prose_collapses_layout_spacing_and_zero_width() -> None:
    text = "Art.     1º\u200b     Esta     Lei\n\n\nParágrafo     único."

    normalized = normalize_prose_text(text)

    assert normalized == "Art. 1º Esta Lei\n\nParágrafo único."
    assert "\u200b" not in normalized


def test_detects_excessive_layout_spacing() -> None:
    text = (
        "Art.             1º             Esta             Lei             estabelece "
        "normas             urbanísticas             para             o             Município."
    )
    assert has_excessive_layout_spacing(text) is True


def test_clean_invisible_characters_preserves_accents() -> None:
    assert clean_invisible_characters("Habitação\ufeff de Interesse Social") == (
        "Habitação de Interesse Social"
    )


def test_markdown_image_wraps_target_with_spaces() -> None:
    result = _markdown_image(
        "Página tabular 2",
        "Lei Municipal_assets/pagina_0002_tabela.png",
    )
    assert result == (
        "![Página tabular 2](<Lei Municipal_assets/pagina_0002_tabela.png>)"
    )
