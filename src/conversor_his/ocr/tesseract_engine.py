from __future__ import annotations

from pathlib import Path

import fitz
from PIL import Image

from .base import OcrEngine


class TesseractEngine(OcrEngine):
    """Motor de OCR local baseado em Tesseract.

    O binding ``pytesseract`` e o executavel Tesseract sao dependencias
    opcionais. A importacao tardia permite que diagnostico, extracao nativa e
    metricas funcionem mesmo quando o extra ``ocr`` nao estiver instalado.
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
                "OCR solicitado, mas pytesseract nao esta instalado. "
                "Instale o projeto com: pip install -e '.[ocr]'"
            ) from exc

        zoom = dpi / 72
        matrix = fitz.Matrix(zoom, zoom)
        with fitz.open(pdf_path) as doc:
            page = doc[page_number - 1]
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        config = f"--psm {self.psm} --oem {self.oem}"
        return pytesseract.image_to_string(image, lang=self.lang, config=config).strip()
