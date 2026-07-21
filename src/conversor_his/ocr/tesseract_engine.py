# SPDX-License-Identifier: MIT
from __future__ import annotations

from pathlib import Path

from .base import OcrEngine
from .render import render_pdf_page


class TesseractEngine(OcrEngine):
    """Motor de OCR local baseado em Tesseract e renderização por PDFium.

    O binding ``pytesseract`` e o executável Tesseract são opcionais. A
    importação tardia permite que diagnóstico, extração nativa e métricas
    funcionem quando o extra ``ocr`` não estiver instalado.
    """

    def __init__(self, lang: str = "por", psm: int = 6, oem: int = 1) -> None:
        self.lang = lang
        self.psm = psm
        self.oem = oem

    def recognize_page(self, pdf_path: Path, page_number: int, dpi: int = 300) -> str:
        try:
            import pytesseract
        except ImportError as exc:
            raise RuntimeError(
                "OCR solicitado, mas pytesseract não está instalado. "
                "Instale o projeto com: pip install -e '.[ocr]'"
            ) from exc

        image = render_pdf_page(pdf_path, page_number, dpi=dpi)
        config = f"--psm {self.psm} --oem {self.oem}"
        return pytesseract.image_to_string(image, lang=self.lang, config=config).strip()
