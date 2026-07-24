# SPDX-License-Identifier: MIT
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .base import OcrEngine
from .render import render_pdf_page


@dataclass(frozen=True, slots=True)
class OcrToken:
    text: str
    confidence: float | None
    page_number: int
    block_number: int
    paragraph_number: int
    line_number: int
    word_number: int
    left: int
    top: int
    width: int
    height: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
        text, _, _ = self.recognize_page_with_tokens(pdf_path, page_number, dpi=dpi)
        return text

    def recognize_page_with_confidence(
        self,
        pdf_path: Path,
        page_number: int,
        dpi: int = 300,
    ) -> tuple[str, list[float]]:
        text, confidences, _ = self.recognize_page_with_tokens(
            pdf_path,
            page_number,
            dpi=dpi,
        )
        return text, confidences

    def recognize_page_with_tokens(
        self,
        pdf_path: Path,
        page_number: int,
        dpi: int = 300,
    ) -> tuple[str, list[float], list[OcrToken]]:
        pytesseract = self._load_pytesseract()
        image = render_pdf_page(pdf_path, page_number, dpi=dpi)
        config = f"--psm {self.psm} --oem {self.oem}"
        data = pytesseract.image_to_data(
            image,
            lang=self.lang,
            config=config,
            output_type=pytesseract.Output.DICT,
        )
        tokens: list[OcrToken] = []
        confidences: list[float] = []
        size = len(data.get("text", []))
        for index in range(size):
            cleaned = str(data.get("text", [""])[index]).strip()
            if not cleaned:
                continue
            raw_confidence = data.get("conf", [None] * size)[index]
            try:
                parsed = float(raw_confidence)
                confidence = parsed if parsed >= 0 else None
            except (TypeError, ValueError):
                confidence = None
            if confidence is not None:
                confidences.append(confidence)
            tokens.append(
                OcrToken(
                    text=cleaned,
                    confidence=confidence,
                    page_number=page_number,
                    block_number=int(data.get("block_num", [0] * size)[index] or 0),
                    paragraph_number=int(data.get("par_num", [0] * size)[index] or 0),
                    line_number=int(data.get("line_num", [0] * size)[index] or 0),
                    word_number=int(data.get("word_num", [0] * size)[index] or 0),
                    left=int(data.get("left", [0] * size)[index] or 0),
                    top=int(data.get("top", [0] * size)[index] or 0),
                    width=int(data.get("width", [0] * size)[index] or 0),
                    height=int(data.get("height", [0] * size)[index] or 0),
                )
            )
        return " ".join(token.text for token in tokens).strip(), confidences, tokens


__all__ = ["OcrToken", "TesseractEngine"]
