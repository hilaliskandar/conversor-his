# SPDX-License-Identifier: MIT
from __future__ import annotations

from pathlib import Path

from PIL import Image


def render_pdf_page(pdf_path: Path, page_number: int, dpi: int = 300) -> Image.Image:
    """Renderiza uma página PDF em imagem usando PDFium.

    ``page_number`` é baseado em 1 para manter coerência com a numeração
    apresentada nos manifestos e arquivos Markdown.
    """

    if page_number < 1:
        raise ValueError("page_number deve ser maior ou igual a 1")
    if dpi <= 0:
        raise ValueError("dpi deve ser positivo")

    try:
        import pypdfium2 as pdfium
    except ImportError as exc:  # pragma: no cover - dependência do núcleo
        raise RuntimeError("pypdfium2 não está instalado") from exc

    document = pdfium.PdfDocument(str(pdf_path))
    page = None
    bitmap = None
    try:
        if page_number > len(document):
            raise IndexError(
                f"pagina {page_number} fora do intervalo; documento possui {len(document)} paginas"
            )
        page = document[page_number - 1]
        bitmap = page.render(scale=dpi / 72.0)
        image = bitmap.to_pil().copy()
        return image.convert("RGB") if image.mode != "RGB" else image
    finally:
        if bitmap is not None and hasattr(bitmap, "close"):
            bitmap.close()
        if page is not None and hasattr(page, "close"):
            page.close()
        if hasattr(document, "close"):
            document.close()
