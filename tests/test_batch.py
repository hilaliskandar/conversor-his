from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from conversor_his.batch import _safe_member_path, convert_zip_batch


def test_safe_member_path_preserves_subdirectories() -> None:
    result = _safe_member_path("municipio/plano_diretor/lei.pdf")
    assert result.as_posix() == "municipio/plano_diretor/lei.pdf"


@pytest.mark.parametrize(
    "name",
    ["../lei.pdf", "/absoluto/lei.pdf", "C:/lei.pdf", "pasta/../../lei.pdf"],
)
def test_safe_member_path_rejects_unsafe_paths(name: str) -> None:
    with pytest.raises(ValueError):
        _safe_member_path(name)


def test_batch_rejects_duplicate_pdf_paths_case_insensitive(tmp_path: Path) -> None:
    zip_path = tmp_path / "municipio.zip"
    output_dir = tmp_path / "saida"

    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("leis/Plano.pdf", b"%PDF-1.4\n")
        archive.writestr("leis/plano.PDF", b"%PDF-1.4\n")

    result = convert_zip_batch(zip_path, output_dir)

    assert result.pdf_count == 2
    assert result.failure_count >= 1
    assert result.manifest_path.exists()
