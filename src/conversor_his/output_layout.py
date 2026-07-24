# SPDX-License-Identifier: MIT
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class OutputLayout:
    root: Path
    analysis_dir: Path
    assets_dir: Path
    compatibility_manifest: Path


def build_output_layout(output_dir: Path, document_stem: str) -> OutputLayout:
    root = output_dir.resolve()
    analysis_dir = root / "analise"
    assets_dir = root / "ativos" / document_stem
    analysis_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.parent.mkdir(parents=True, exist_ok=True)
    return OutputLayout(
        root=root,
        analysis_dir=analysis_dir,
        assets_dir=assets_dir,
        compatibility_manifest=root / f"{document_stem}.manifest.json",
    )
