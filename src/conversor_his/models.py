from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

PageRoute = Literal[
    "native",
    "ocr",
    "map",
    "structured",
    "decorative",
    "hybrid",
    "manual",
]
PageType = Literal[
    "text",
    "map",
    "table",
    "table_candidate",
    "decorative_only",
    "back_cover",
    "unknown",
]
TableClassification = Literal["not_table", "candidate", "confirmed"]
OcrQualityLevel = Literal["high", "medium", "low"]


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
class OcrQuality:
    character_count: int
    word_count: int
    alphanumeric_ratio: float
    mean_confidence: float | None
    quality: OcrQualityLevel
    requires_review: bool
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class TableAssessment:
    classification: TableClassification
    suspected: bool
    score: int
    row_count: int
    stable_columns: int
    header_hits: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    header_line_index: int | None = None
    legal_list_ratio: float = 0.0


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
    page_type: PageType = "unknown"
    route: PageRoute = "native"
    warnings: list[str] = field(default_factory=list)
    ocr_quality: OcrQuality | None = None
    table_assessment: TableAssessment | None = None


@dataclass(slots=True)
class DocumentDiagnosis:
    source_path: Path | str
    sha256: str
    page_count: int
    pages: list[PageDiagnosis]
    repeated_graphics: list[RepeatedGraphic] = field(default_factory=list)


@dataclass(slots=True)
class ConversionManifest:
    source_path: Path | str
    source_sha256: str
    page_count: int
    markdown_path: Path
    markdown_sha256: str
    markdown_size_bytes: int
    asset_paths: list[Path]
    used_ocr_pages: list[int]
    map_pages: list[int]
    table_pages: list[int]
    table_candidate_pages: list[int]
    decorative_pages: list[int]
    review_pages: list[int]
    dpi: int
    converter_version: str
    diagnosis: DocumentDiagnosis


@dataclass(slots=True)
class ConversionResult:
    source_path: Path | str
    output_dir: Path
    markdown_path: Path
    manifest_path: Path
    used_ocr_pages: list[int]
    warnings: list[str] = field(default_factory=list)
