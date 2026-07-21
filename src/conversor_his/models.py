from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

PageRoute = Literal["native", "ocr", "hybrid", "manual"]


@dataclass(slots=True)
class PageDiagnosis:
    page_number: int
    has_native_text: bool
    character_count: int
    image_count: int
    suspected_table: bool = False
    suspected_map: bool = False
    route: PageRoute = "native"
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DocumentDiagnosis:
    source_path: Path
    sha256: str
    page_count: int
    pages: list[PageDiagnosis]


@dataclass(slots=True)
class ConversionResult:
    source_path: Path
    output_dir: Path
    markdown_path: Path
    manifest_path: Path
    used_ocr_pages: list[int]
    warnings: list[str] = field(default_factory=list)
