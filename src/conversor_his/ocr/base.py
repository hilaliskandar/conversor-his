from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class OcrEngine(ABC):
    @abstractmethod
    def recognize_page(self, pdf_path: Path, page_number: int, dpi: int = 300) -> str:
        raise NotImplementedError
