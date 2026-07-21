# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
import shutil
import stat
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from . import __version__
from .converter import convert_pdf
from .hashing import sha256_file
from .manifest import write_manifest

_DRIVE_PART_RE = re.compile(r"^[A-Za-z]:$")


@dataclass(slots=True)
class BatchConversionResult:
    manifest_path: Path
    pdf_count: int
    success_count: int
    failure_count: int
    skipped_count: int


def _safe_member_path(member_name: str) -> PurePosixPath:
    normalized_name = member_name.replace("\\", "/")
    member_path = PurePosixPath(normalized_name)

    if member_path.is_absolute():
        raise ValueError("caminho absoluto nao permitido")
    if not member_path.parts:
        raise ValueError("caminho vazio")
    if any(part in {"", ".", ".."} for part in member_path.parts):
        raise ValueError("caminho relativo inseguro")
    if _DRIVE_PART_RE.match(member_path.parts[0]):
        raise ValueError("unidade de disco nao permitida")

    return member_path


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = info.external_attr >> 16
    return stat.S_IFMT(mode) == stat.S_IFLNK


def _extract_pdf_member(
    archive: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    relative_path: PurePosixPath,
    temporary_root: Path,
) -> Path:
    temporary_path = temporary_root.joinpath(*relative_path.parts)
    temporary_path.parent.mkdir(parents=True, exist_ok=True)

    with archive.open(info, "r") as source, temporary_path.open("wb") as target:
        shutil.copyfileobj(source, target, length=1024 * 1024)

    with temporary_path.open("rb") as pdf_file:
        header = pdf_file.read(1024)
    if b"%PDF-" not in header:
        temporary_path.unlink(missing_ok=True)
        raise ValueError("arquivo com extensao PDF sem assinatura PDF valida")

    return temporary_path


def convert_zip_batch(zip_path: Path, output_dir: Path, dpi: int = 300) -> BatchConversionResult:
    """Converte recursivamente PDFs de um ZIP, preservando sua arvore de diretorios.

    O ZIP original nao e alterado. Apenas membros PDF sao extraidos temporariamente,
    um por vez, e os produtos sao gravados na pasta de saida com o mesmo caminho
    relativo existente no arquivo compactado.
    """

    zip_path = zip_path.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not zipfile.is_zipfile(zip_path):
        raise ValueError(f"arquivo de entrada nao e um ZIP valido: {zip_path}")

    entries: list[dict[str, object]] = []
    seen_paths: set[str] = set()
    pdf_count = 0
    success_count = 0
    failure_count = 0
    skipped_count = 0

    with tempfile.TemporaryDirectory(prefix="conversor_his_lote_") as temporary_name:
        temporary_root = Path(temporary_name)

        with zipfile.ZipFile(zip_path, "r") as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue

                try:
                    relative_path = _safe_member_path(info.filename)
                except ValueError as exc:
                    failure_count += 1
                    entries.append(
                        {
                            "member": info.filename,
                            "status": "rejected",
                            "error": str(exc),
                        }
                    )
                    continue

                if relative_path.suffix.casefold() != ".pdf":
                    skipped_count += 1
                    continue

                pdf_count += 1
                collision_key = relative_path.as_posix().casefold()
                if collision_key in seen_paths:
                    failure_count += 1
                    entries.append(
                        {
                            "member": relative_path.as_posix(),
                            "status": "failed",
                            "error": "caminho PDF duplicado no ZIP",
                        }
                    )
                    continue
                seen_paths.add(collision_key)

                if _is_symlink(info):
                    failure_count += 1
                    entries.append(
                        {
                            "member": relative_path.as_posix(),
                            "status": "rejected",
                            "error": "link simbolico nao permitido no ZIP",
                        }
                    )
                    continue

                destination_dir = output_dir.joinpath(*relative_path.parent.parts)
                source_reference = f"{zip_path}!/{relative_path.as_posix()}"

                try:
                    temporary_pdf = _extract_pdf_member(
                        archive,
                        info,
                        relative_path,
                        temporary_root,
                    )
                    markdown_path = convert_pdf(
                        temporary_pdf,
                        destination_dir,
                        dpi=dpi,
                        source_reference=source_reference,
                    )
                    manifest_path = destination_dir / f"{relative_path.stem}.manifest.json"
                    success_count += 1
                    entries.append(
                        {
                            "member": relative_path.as_posix(),
                            "status": "success",
                            "output_directory": str(destination_dir),
                            "markdown_path": str(markdown_path),
                            "manifest_path": str(manifest_path),
                        }
                    )
                except Exception as exc:  # noqa: BLE001 - falhas devem ser isoladas por diploma
                    failure_count += 1
                    entries.append(
                        {
                            "member": relative_path.as_posix(),
                            "status": "failed",
                            "output_directory": str(destination_dir),
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        }
                    )

    batch_manifest_path = output_dir / f"{zip_path.stem}.lote.manifest.json"
    write_manifest(
        {
            "source_zip": zip_path,
            "source_zip_sha256": sha256_file(zip_path),
            "output_directory": output_dir,
            "converter_version": __version__,
            "pdf_count": pdf_count,
            "success_count": success_count,
            "failure_count": failure_count,
            "skipped_non_pdf_count": skipped_count,
            "directory_policy": "mirror_zip_structure",
            "entries": entries,
        },
        batch_manifest_path,
    )

    return BatchConversionResult(
        manifest_path=batch_manifest_path,
        pdf_count=pdf_count,
        success_count=success_count,
        failure_count=failure_count,
        skipped_count=skipped_count,
    )
