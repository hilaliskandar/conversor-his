from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

PageRoute = Literal["native", "ocr", "map", "hybrid", "manual"]
OcrQualityLevel = Literal["high", "medium", "low"]


@dataclass(slots=True)
class RepeatedGraphic:
    graphic_id: str
    sha256: str
    occurrences: int
    page_count: int
    page_ratio: