# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import re
import shutil
import stat
import tempfile
import time
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
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
    duplicate_count: int = 0
    pending_count: int = 0


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


def _common_root(paths: list[PurePosixPath]) -> str | None:
    if not paths:
        return None
    first_parts = {path.parts[0].casefold() for path in paths if len(path.parts) > 1}
    if len(first_parts) != 1 or any(len(path.parts) == 1 for path in paths):
        return None
    return paths[0].parts[0]


def _strip_root(path: PurePosixPath, root: str | None) -> PurePosixPath:
    if root and path.parts and path.parts[0].casefold() == root.casefold():
        return PurePosixPath(*path.parts[1:])
    return path


def _load_existing_entries(manifest_path: Path) -> dict[str, dict[str, object]]:
    if not manifest_path.exists():
        return {}
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    entries = data.get("entries", [])
    if not isinstance(entries, list):
        return {}
    return {
        str(entry.get("member")): entry
        for entry in entries
        if isinstance(entry, dict) and entry.get("member")
    }


def _is_completed_entry(
    entry: dict[str, object] | None,
    source_hash: str,
    dpi: int,
) -> bool:
    if not entry or entry.get("status") not in {"success", "duplicate"}:
        return False
    if entry.get("source_sha256") != source_hash:
        return False
    if entry.get("dpi") != dpi or entry.get("converter_version") != __version__:
        return False
    if entry.get("status") == "duplicate":
        return True
    markdown_path = Path(str(entry.get("markdown_path", "")))
    manifest_path = Path(str(entry.get("manifest_path", "")))
    return markdown_path.exists() and manifest_path.exists()


def convert_zip_batch(
    zip_path: Path,
    output_dir: Path,
    dpi: int = 300,
    document_limit: int = 0,
    resume: bool = False,
    remove_common_root: bool = True,
    progress: Callable[[str], None] | None = None,
) -> BatchConversionResult:
    """Converte PDFs de um ZIP com limite, retomada e manifesto incremental."""

    if document_limit < 0:
        raise ValueError("document_limit deve ser zero ou positivo")

    zip_path = zip_path.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not zipfile.is_zipfile(zip_path):
        raise ValueError(f"arquivo de entrada nao e um ZIP valido: {zip_path}")

    batch_manifest_path = output_dir / f"{zip_path.stem}.lote.manifest.json"
    source_zip_hash = sha256_file(zip_path)
    existing_entries = _load_existing_entries(batch_manifest_path) if resume else {}

    entries: list[dict[str, object]] = []
    ignored_entries: list[dict[str, str]] = []
    seen_paths: set[str] = set()
    seen_hashes: dict[str, str] = {}
    success_count = 0
    failure_count = 0
    skipped_count = 0
    duplicate_count = 0
    processed_count = 0
    started_perf = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat()

    def emit(message: str) -> None:
        if progress is not None:
            progress(message)

    def persist(
        status: str,
        total_pdf_count: int,
        pending_count: int,
        completed: bool = False,
    ) -> None:
        payload: dict[str, object] = {
            "source_zip": zip_path,
            "source_zip_sha256": source_zip_hash,
            "output_directory": output_dir,
            "converter_version": __version__,
            "dpi": dpi,
            "document_limit": document_limit,
            "resume_enabled": resume,
            "status": status,
            "started_at": started_at,
            "pdf_count": total_pdf_count,
            "processed_count": processed_count,
            "success_count": success_count,
            "failure_count": failure_count,
            "duplicate_count": duplicate_count,
            "skipped_non_pdf_count": skipped_count,
            "pending_count": pending_count,
            "directory_policy": "mirror_zip_structure",
            "common_root_removed": remove_common_root,
            "processing_seconds": round(time.perf_counter() - started_perf, 3),
            "ignored_entries": ignored_entries,
            "entries": entries,
            "generated_at": started_at,
        }
        if completed:
            payload["completed_at"] = datetime.now(timezone.utc).isoformat()
        write_manifest(payload, batch_manifest_path)

    total_pdf_count = 0
    pending_count = 0
    with tempfile.TemporaryDirectory(prefix="conversor_his_lote_") as temporary_name:
        temporary_root = Path(temporary_name)

        with zipfile.ZipFile(zip_path, "r") as archive:
            candidates: list[tuple[zipfile.ZipInfo, PurePosixPath]] = []
            for info in archive.infolist():
                if info.is_dir():
                    continue
                try:
                    path = _safe_member_path(info.filename)
                except ValueError as exc:
                    failure_count += 1
                    entries.append(
                        {"member": info.filename, "status": "rejected", "error": str(exc)}
                    )
                    continue
                if path.suffix.casefold() != ".pdf":
                    skipped_count += 1
                    ignored_entries.append(
                        {
                            "member": path.as_posix(),
                            "status": "ignored",
                            "reason": "extensao diferente de PDF",
                        }
                    )
                    continue
                candidates.append((info, path))

            candidates.sort(key=lambda item: item[1].as_posix().casefold())
            total_pdf_count = len(candidates)
            root = _common_root([path for _, path in candidates]) if remove_common_root else None
            selected_candidates = (
                candidates if document_limit == 0 else candidates[:document_limit]
            )
            pending_count = total_pdf_count - len(selected_candidates)
            persist("running", total_pdf_count, pending_count)

            for position, (info, original_path) in enumerate(selected_candidates, start=1):
                relative_path = _strip_root(original_path, root)
                member_name = original_path.as_posix()
                collision_key = relative_path.as_posix().casefold()

                if collision_key in seen_paths:
                    failure_count += 1
                    entries.append(
                        {
                            "member": member_name,
                            "output_relative_path": relative_path.as_posix(),
                            "status": "failed",
                            "error": "caminho PDF duplicado no ZIP",
                        }
                    )
                    persist("running", total_pdf_count, pending_count)
                    continue
                seen_paths.add(collision_key)

                if _is_symlink(info):
                    failure_count += 1
                    entries.append(
                        {
                            "member": member_name,
                            "status": "rejected",
                            "error": "link simbolico nao permitido no ZIP",
                        }
                    )
                    persist("running", total_pdf_count, pending_count)
                    continue

                destination_dir = output_dir.joinpath(*relative_path.parent.parts)
                source_reference = f"{zip_path}!/{member_name}"
                emit(f"[{position}/{len(selected_candidates)}] {member_name}")

                try:
                    temporary_pdf = _extract_pdf_member(
                        archive, info, original_path, temporary_root
                    )
                    source_hash = sha256_file(temporary_pdf)
                    existing = existing_entries.get(member_name)
                    if resume and _is_completed_entry(existing, source_hash, dpi):
                        resumed = dict(existing)
                        resumed["status"] = "success"
                        resumed["resumed_without_processing"] = True
                        entries.append(resumed)
                        success_count += 1
                        processed_count += 1
                        emit("  já concluído; reutilizado pelo modo de retomada")
                        persist("running", total_pdf_count, pending_count)
                        continue

                    duplicate_of = seen_hashes.get(source_hash)
                    if duplicate_of:
                        duplicate_count += 1
                        processed_count += 1
                        entries.append(
                            {
                                "member": member_name,
                                "output_relative_path": relative_path.as_posix(),
                                "status": "duplicate",
                                "duplicate_of": duplicate_of,
                                "source_sha256": source_hash,
                                "dpi": dpi,
                                "converter_version": __version__,
                            }
                        )
                        emit(f"  duplicado exato de {duplicate_of}; conversão dispensada")
                        persist("running", total_pdf_count, pending_count)
                        continue
                    seen_hashes[source_hash] = member_name

                    current_entry: dict[str, object] = {
                        "member": member_name,
                        "output_relative_path": relative_path.as_posix(),
                        "status": "processing",
                        "source_sha256": source_hash,
                        "output_directory": str(destination_dir),
                        "dpi": dpi,
                        "converter_version": __version__,
                    }
                    entries.append(current_entry)
                    persist("running", total_pdf_count, pending_count)

                    document_started = time.perf_counter()
                    markdown_path = convert_pdf(
                        temporary_pdf,
                        destination_dir,
                        dpi=dpi,
                        source_reference=source_reference,
                    )
                    manifest_path = destination_dir / f"{relative_path.stem}.manifest.json"
                    current_entry.update(
                        {
                            "status": "success",
                            "markdown_path": str(markdown_path),
                            "manifest_path": str(manifest_path),
                            "processing_seconds": round(
                                time.perf_counter() - document_started, 3
                            ),
                        }
                    )
                    success_count += 1
                    processed_count += 1
                except KeyboardInterrupt:
                    if entries and entries[-1].get("status") == "processing":
                        entries[-1]["status"] = "interrupted"
                        entries[-1]["error"] = "processamento interrompido pelo usuario"
                    persist("interrupted", total_pdf_count, pending_count)
                    raise
                except Exception as exc:  # noqa: BLE001
                    failure_count += 1
                    processed_count += 1
                    if entries and entries[-1].get("status") == "processing":
                        current_entry = entries[-1]
                    else:
                        current_entry = {
                            "member": member_name,
                            "output_relative_path": relative_path.as_posix(),
                        }
                        entries.append(current_entry)
                    current_entry.update(
                        {
                            "status": "failed",
                            "output_directory": str(destination_dir),
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                        }
                    )
                persist("running", total_pdf_count, pending_count)

    if failure_count:
        final_status = "completed_with_failures"
    elif pending_count:
        final_status = "completed_with_limit"
    else:
        final_status = "completed"
    persist(final_status, total_pdf_count, pending_count, completed=True)

    return BatchConversionResult(
        manifest_path=batch_manifest_path,
        pdf_count=total_pdf_count,
        success_count=success_count,
        failure_count=failure_count,
        skipped_count=skipped_count,
        duplicate_count=duplicate_count,
        pending_count=pending_count,
    )
