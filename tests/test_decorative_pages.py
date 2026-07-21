from __future__ import annotations

from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import (
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NumberObject,
)

from conversor_his.diagnostic import diagnose_pdf


def _write_decorative_only_pdf(path: Path, page_count: int = 8) -> None:
    writer = PdfWriter()
    image = DecodedStreamObject()
    image.set_data(b"\x00")
    image.update(
        {
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Image"),
            NameObject("/Width"): NumberObject(1),
            NameObject("/Height"): NumberObject(1),
            NameObject("/ColorSpace"): NameObject("/DeviceGray"),
            NameObject("/BitsPerComponent"): NumberObject(8),
        }
    )
    image_ref = writer._add_object(image)

    for _ in range(page_count):
        page = writer.add_blank_page(width=600, height=800)
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/XObject"): DictionaryObject(
                    {NameObject("/ImHeader"): image_ref}
                )
            }
        )
        content = DecodedStreamObject()
        content.set_data(b"q 30 0 0 30 280 750 cm /ImHeader Do Q")
        page[NameObject("/Contents")] = writer._add_object(content)

    with path.open("wb") as handle:
        writer.write(handle)


def test_last_decorative_only_page_is_back_cover(tmp_path: Path) -> None:
    pdf_path = tmp_path / "decorative-only.pdf"
    _write_decorative_only_pdf(pdf_path)

    diagnosis = diagnose_pdf(pdf_path)
    last_page = diagnosis.pages[-1]

    assert last_page.route == "decorative"
    assert last_page.page_type == "back_cover"
    assert last_page.content_image_count == 0
    assert "pagina exclusivamente decorativa: OCR dispensado" in last_page.warnings
