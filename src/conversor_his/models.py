from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

PageRoute = Literal["native", "ocr", "map", "hybrid", "manual"]


@dataclass(slots=True)
class RepeatedGraphic:
    graphic_id: str
    sha256: str
    occurrences: int
    page_count: int
    page_ratio: float
    position: str
    median_bbox: list[float]
    max_area_ratio: float
    classification: str = "decorative"
    action: str = "ignored_for_routing"


@dataclass(slots=True)
class PageDiagnosis:
    page_number: int
    has_native_text: bool
    character_count: int
    image_count: int
    raw_image_count: int = 0
    decorative_image_count: int = 0
    content_image_count: int = 0
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
    repeated_graphics: list[RepeatedGraphic] = field(default_factory=list)


@dataclass(slots=True)
class ConversionResult:
    source_path: Path
    output_dir: Path
    markdown_path: Path
    manifest_path: Path
    used_ocr_pages: list[int]
    warnings: list[str] = field(default_factory=list)
