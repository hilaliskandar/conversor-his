import zipfile
from pathlib import Path

from conversor_his.packaging import create_analysis_zip


def test_analysis_zip_excludes_images_and_keeps_light_files(tmp_path: Path) -> None:
    (tmp_path / "analise").mkdir()
    (tmp_path / "ativos" / "lei").mkdir(parents=True)
    (tmp_path / "analise" / "lei.md").write_text("texto", encoding="utf-8")
    (tmp_path / "analise" / "dados.csv").write_text("a,b", encoding="utf-8")
    (tmp_path / "ativos" / "lei" / "pagina.png").write_bytes(b"png")
    target = tmp_path / "pacote.zip"

    create_analysis_zip(tmp_path, target)

    with zipfile.ZipFile(target) as archive:
        names = set(archive.namelist())
    assert "analise/lei.md" in names
    assert "analise/dados.csv" in names
    assert not any(name.endswith(".png") for name in names)
