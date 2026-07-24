# SPDX-License-Identifier: MIT
from __future__ import annotations

import zipfile
from pathlib import Path

_LIGHT_EXTENSIONS = {".md", ".csv", ".json", ".jsonl", ".txt", ".yaml", ".yml"}
_EXCLUDED_PARTS = {"ativos", ".conversor_his_staging", "__pycache__"}


def create_analysis_zip(source_dir: Path, zip_path: Path) -> Path:
    """Compacta apenas artefatos leves, excluindo imagens e outros binários."""

    source_dir = source_dir.resolve()
    zip_path = zip_path.resolve()
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(source_dir)
            if any(part in _EXCLUDED_PARTS for part in relative.parts):
                continue
            if path.suffix.casefold() not in _LIGHT_EXTENSIONS:
                continue
            if path.resolve() == zip_path:
                continue
            archive.write(path, relative.as_posix())
    return zip_path


__all__ = ["create_analysis_zip"]
