# SPDX-License-Identifier: MIT
"""Interface pública do conversor com organização leve/pesada da saída."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .ocr.tesseract_engine import OcrToken, TesseractEngine
from .output_layout import build_output_layout
from .pipeline_v072 import _markdown_image
from .pipeline_v072 import convert_pdf as _pipeline_convert_pdf
from .reconstrucao_estrutural import gravar_estrutura_ocr


def _write_ocr_tokens(
    pdf_path: Path,
    pages: list[int],
    target: Path,
    *,
    dpi: int,
) -> list[OcrToken]:
    engine = TesseractEngine()
    tokens_acumulados: list[OcrToken] = []
    temporary = target.with_suffix(".jsonl.tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        for page_number in sorted(set(pages)):
            _, _, tokens = engine.recognize_page_with_tokens(
                pdf_path,
                page_number,
                dpi=dpi,
            )
            tokens_acumulados.extend(tokens)
            for token in tokens:
                stream.write(json.dumps(token.to_dict(), ensure_ascii=False) + "\n")
    temporary.replace(target)
    return tokens_acumulados


def convert_pdf(
    path: Path,
    output_dir: Path,
    dpi: int = 300,
    source_reference: str | None = None,
) -> Path:
    """Converte e separa artefatos leves de imagens e outros ativos pesados.

    Um manifesto de compatibilidade permanece na raiz para não quebrar a
    retomada de lotes produzidos pela série 0.7.x.
    """

    output_dir = output_dir.resolve()
    layout = build_output_layout(output_dir, path.stem)
    staging = output_dir / ".conversor_his_staging" / path.stem
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)

    staged_markdown = _pipeline_convert_pdf(
        path,
        staging,
        dpi=dpi,
        source_reference=source_reference,
    )
    staged_manifest = staging / f"{path.stem}.manifest.json"
    staged_assets = staging / f"{path.stem}_assets"

    markdown_path = layout.analysis_dir / f"{path.stem}.md"
    manifest_path = layout.analysis_dir / f"{path.stem}.manifest.json"
    token_path = layout.analysis_dir / f"{path.stem}.ocr_tokens.jsonl"
    structure_path = layout.analysis_dir / f"{path.stem}.estrutura_ocr.jsonl"

    if layout.assets_dir.exists():
        shutil.rmtree(layout.assets_dir)
    if staged_assets.exists():
        shutil.move(str(staged_assets), str(layout.assets_dir))
    else:
        layout.assets_dir.mkdir(parents=True, exist_ok=True)

    markdown = staged_markdown.read_text(encoding="utf-8")
    markdown = markdown.replace(
        f"{path.stem}_assets/",
        f"../ativos/{path.stem}/",
    )
    markdown_path.write_text(markdown, encoding="utf-8")

    manifest = json.loads(staged_manifest.read_text(encoding="utf-8"))
    used_ocr_pages = [int(value) for value in manifest.get("used_ocr_pages", [])]
    tokens = _write_ocr_tokens(path, used_ocr_pages, token_path, dpi=dpi)
    gravar_estrutura_ocr(tokens, structure_path)

    manifest["markdown_path"] = str(markdown_path)
    manifest["manifest_path"] = str(manifest_path)
    manifest["ocr_tokens_path"] = str(token_path)
    manifest["ocr_structure_path"] = str(structure_path)
    manifest["ocr_structure"] = {
        "schema_version": "1.0",
        "source": "ocr_tokens",
        "conservative": True,
        "replaces_markdown": False,
    }
    manifest["output_layout"] = {
        "analysis_directory": str(layout.analysis_dir),
        "assets_directory": str(layout.assets_dir),
        "lightweight_extensions": [".md", ".csv", ".json", ".jsonl"],
    }
    manifest["asset_paths"] = [
        str(layout.assets_dir / Path(value).name)
        for value in manifest.get("asset_paths", [])
    ]
    serialized = json.dumps(manifest, ensure_ascii=False, indent=2, default=str)
    manifest_path.write_text(serialized, encoding="utf-8")
    layout.compatibility_manifest.write_text(serialized, encoding="utf-8")

    shutil.rmtree(staging, ignore_errors=True)
    if staging.parent.exists() and not any(staging.parent.iterdir()):
        staging.parent.rmdir()
    return markdown_path


__all__ = ["_markdown_image", "convert_pdf"]
