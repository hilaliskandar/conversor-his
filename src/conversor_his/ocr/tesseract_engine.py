# SPDX-License-Identifier: MIT
from __future__ import annotations

from pathlib import Path

from .base import OcrEngine
from .render import render_pdf_page


class TesseractEngine(OcrEngine):
    """Motor de OCR local baseado em Tesseract e renderização por PDFium."""

    def __init__(self, lang: str = "por", psm: int = 6, oem: int = 1) -> None:
        self.lang = lang
        self.psm = psm
        self.oem = oem

    def _load_pytesseract(self):
        try:
            import pytesseract
        except ImportError as exc:
            raise RuntimeError(
                "OCR solicitado, mas pytesseract não está instalado. "
                "Instale o projeto com: pip install -e '.[ocr]'"
            ) from exc
        return pytesseract

    def recognize_page(self, pdf_path: Path, page_number: int, dpi: int = 300) -> str:
        text, _ = self.recognize_page_with_confidence(pdf_path, page_number, dpi=dpi)
        return text

    def recognize_page_with_confidence(
        self,
        pdf_path: Path,
        page_number: int,
        dpi: int = 300,
    ) -> tuple[str, list[float]]:
        pytesseract = self._load_pytesseract()
        image = render_pdf_page(pdf_path, page_number, dpi=dpi)
        config = f"--psm {self.psm} --oem {self.oem}"
        data = pytesseract.image_to_data(
            image,
            lang=self.lang,
            config=config,
            output_type=pytesseract.Output.DICT,
        )
        tokens: list[str] = []
        confidences: list[float] = []
        for token, confidence in zip(data.get("text", []), data.get("conf", [])):
            cleaned = str(token).strip()
            if not cleaned:
                continue
            tokens.append(cleaned)
            try:
                numeric_confidence = float(confidence)
            except (TypeError, ValueError):
                continue
            if numeric_confidence >= 0:
                confidences.append(numeric_confidence)
        return " ".join(tokens).strip(), confidences
