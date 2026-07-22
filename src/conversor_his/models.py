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
    "map_candidate",
    "map_confirmed",
    "map_cover",
    "table",
    "table_candidate",
    "raster_table_candidate",
    "diagram_candidate",
    "coordinate_register",
    "ocr_review",
    "decorative_only",
    "back_cover",
    "unknown",
]
TableClassification = Literal[
    "not_table",
    "candidate",
    "mixed_candidate",
    "continuation_candidate",
    "visual_candidate",
    "raster_candidate",
    "confirmed",
]
OcrQualityLevel = Literal["high", "medium", "low"]
VisualContentClass = Literal[
    "none",
    "raster_table_candidate",
    "diagram_candidate",
    "map_candidate",
]


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
class CoordinateAssessment:
    detected: bool
    score: int
    pair_count: int
    numeric_coordinate_count: int
    keyword_hits: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RasterVisualAssessment:
    classification: VisualContentClass
    detected: bool
    strong: bool
    score: int
    horizontal_lines: int
    vertical_lines: int
    intersections: int
    closed_regions: int
    structured_area_ratio: float
    arrow_like_components: int = 0
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
    prose_ratio: float = 0.0
    numeric_rows: int = 0
    compact_value_rows: int = 0
    multi_column_lines: int = 0
    urban_parameter_hits: list[str] = field(default_factory=list)
    zone_code_count: int = 0
    content_profile: str = "unknown"
    visual_grid_detected: bool = False
    visual_grid_strong: bool = False
    visual_grid_score: int = 0
    vector_rectangle_count: int = 0
    vector_horizontal_lines: int = 0
    vector_vertical_lines: int = 0


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
    coordinate_assessment: CoordinateAssessment | None = None
    raster_visual_assessment: RasterVisualAssessment | None = None
    native_extraction_mode: str = "layout"
    layout_character_count: int = 0
    simple_character_count: int = 0
    rotated_text_detected: bool = False
    extraction_warnings: list[str] = field(default_factory=list)
    preserved_visual_text: bool = False
    preserved_review_image: bool = False


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
    rotated_text_pages: list[int] = field(default_factory=list)
    visual_text_preserved_pages: list[int] = field(default_factory=list)
    raster_table_pages: list[int] = field(default_factory=list)
    diagram_pages: list[int] = field(default_factory=list)
    coordinate_register_pages: list[int] = field(default_factory=list)
    map_candidate_pages: list[int] = field(default_factory=list)
    map_cover_pages: list[int] = field(default_factory=list)
    ocr_review_image_pages: list[int] = field(default_factory=list)
    processing_seconds: float | None = None


@dataclass(slots=True)
class ConversionResult:
    source_path: Path | str
    output_dir: Path
    markdown_path: Path
    manifest_path: Path
    used_ocr_pages: list[int]
    warnings: list[str] = field(default_factory=list)
