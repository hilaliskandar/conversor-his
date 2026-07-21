from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from conversor_his.batch import _common_root, _safe_member_path, convert_zip_batch


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


def test_common_root_requires_one_shared_directory() -> None:
    paths = [
        _safe_member_path("raiz/a/lei.pdf"),
        _safe_member_path("raiz/b/decreto.pdf"),
    ]
    assert _common_root(paths) == "raiz"
    assert _common_root([_safe_member_path("lei.pdf")]) is None


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


def test_document_limit_zero_means_all_and_positive_limit_leaves_pending(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    zip_path = tmp_path / "municipio.zip"
    output_dir = tmp_path / "saida"

    with zipfile.ZipFile(zip_path, "w") as archive:
        for index in range(3):
            archive.writestr(f"raiz/cidade/lei_{index}.pdf", b"%PDF-1.4\n")
        archive.writestr("raiz/cidade/notas.txt", "ignorar")

    def fake_convert_pdf(path: Path, output: Path, dpi: int, source_reference: str) -> Path:
        output.mkdir(parents=True, exist_ok=True)
        markdown = output / f"{path.stem}.md"
        manifest = output / f"{path.stem}.manifest.json"
        markdown.write_text("ok", encoding="utf-8")
        manifest.write_text("{}", encoding="utf-8")
        return markdown

    monkeypatch.setattr("conversor_his.batch.convert_pdf", fake_convert_pdf)

    limited = convert_zip_batch(zip_path, output_dir, document_limit=2)
    assert limited.success_count == 2
    assert limited.pending_count == 1

    manifest = json.loads(limited.manifest_path.read_text(encoding="utf-8"))
    assert manifest["document_limit"] == 2
    assert manifest["pending_count"] == 1
    assert manifest["status"] == "completed_with_limit"
    assert manifest["started_at"] == manifest["generated_at"]
    assert "completed_at" in manifest
    assert manifest["ignored_entries"][0]["member"].endswith("notas.txt")
    assert all(
        "raiz" not in str(entry.get("output_relative_path", ""))
        for entry in manifest["entries"]
    )


def test_exact_duplicate_content_is_not_converted_twice(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    zip_path = tmp_path / "municipio.zip"
    output_dir = tmp_path / "saida"
    calls: list[str] = []

    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("cidade/a.pdf", b"%PDF-1.4\nmesmo")
        archive.writestr("cidade/b.pdf", b"%PDF-1.4\nmesmo")

    def fake_convert_pdf(path: Path, output: Path, dpi: int, source_reference: str) -> Path:
        calls.append(source_reference)
        output.mkdir(parents=True, exist_ok=True)
        markdown = output / f"{path.stem}.md"
        manifest = output / f"{path.stem}.manifest.json"
        markdown.write_text("ok", encoding="utf-8")
        manifest.write_text("{}", encoding="utf-8")
        return markdown

    monkeypatch.setattr("conversor_his.batch.convert_pdf", fake_convert_pdf)
    result = convert_zip_batch(zip_path, output_dir)

    assert len(calls) == 1
    assert result.success_count == 1
    assert result.duplicate_count == 1
