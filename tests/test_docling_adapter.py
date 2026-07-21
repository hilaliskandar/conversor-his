from __future__ import annotations

from pathlib import Path

import pytest

from conversor_his.extractors.docling_structured import convert_with_docling


def test_docling_extra_has_clear_error_when_missing(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="rota estruturada requer Docling"):
        convert_with_docling(tmp_path / "missing.pdf", tmp_path / "out.md")
