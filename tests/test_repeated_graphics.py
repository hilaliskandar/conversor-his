from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NumberObject,
)

from conversor_his.diagnostic import diagnose_pdf
from conversor_his.graphics import analyze_repeated_graphics


def _write_pdf_with_repeated_footer(path: Path, page_count: int = 8) -> None:
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
                    {NameObject("/ImFooter"): image_ref}
                )
            }
        )
        content = DecodedStreamObject()
        content.set_data(b"q 20 0 0 20 10 10 cm /ImFooter Do Q")
        page[NameObject("/Contents")] = writer._add_object(content)

    with path.open("wb") as handle:
        writer.write(handle)


def test_repeated_small_footer_is_decorative(tmp_path: Path) -> None:
    pdf_path = tmp_path / "repeated-footer.pdf"
    _write_pdf_with_repeated_footer(pdf_path)

    reader = PdfReader(str(pdf_path))
    summaries, repeated = analyze_repeated_graphics(reader)

    assert len(repeated) == 1
    assert repeated[0].classification == "decorative"
    assert repeated[0].position == "bottom"
    assert summaries[2].raw_image_count == 1
    assert summaries[2].decorative_image_count == 1
    assert summaries[2].content_image_count == 0


def test_decorative_footer_does_not_create_hybrid_warning(tmp_path: Path) -> None:
    pdf_path = tmp_path / "repeated-footer.pdf"
    _write_pdf_with_repeated_footer(pdf_path)

    diagnosis = diagnose_pdf(pdf_path)

    assert diagnosis.repeated_graphics
    assert all(page.content_image_count == 0 for page in diagnosis.pages)
    assert all(
        "pagina hibrida: texto e imagem relevante" not in page.warnings
        for page in diagnosis.pages
    )
