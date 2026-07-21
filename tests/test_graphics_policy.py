from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
    NumberObject,
)

from conversor_his.graphics import analyze_repeated_graphics
from conversor_his.graphics_policy import refine_confirmed_decorative_graphics


def _write_pdf(path: Path, central_exception: bool = False) -> None:
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

    for page_number in range(1, 23):
        page = writer.add_blank_page(width=600, height=800)
        page[NameObject("/Resources")] = DictionaryObject(
            {
                NameObject("/XObject"): DictionaryObject(
                    {NameObject("/ImHeader"): image_ref}
                )
            }
        )
        if page_number == 11:
            if central_exception:
                command = b"q 120 0 0 120 240 340 cm /ImHeader Do Q"
            else:
                command = b"q 20 0 0 20 290 10 cm /ImHeader Do Q"
        else:
            command = b"q 20 0 0 20 290 760 cm /ImHeader Do Q"
        content = DecodedStreamObject()
        content.set_data(command)
        page[NameObject("/Contents")] = writer._add_object(content)

    with path.open("wb") as handle:
        writer.write(handle)


def test_confirmed_graphic_can_move_to_another_edge(tmp_path: Path) -> None:
    pdf_path = tmp_path / "edge-variation.pdf"
    _write_pdf(pdf_path)
    reader = PdfReader(str(pdf_path))

    summaries, repeated = analyze_repeated_graphics(reader)
    refined = refine_confirmed_decorative_graphics(reader, summaries, repeated)

    assert repeated
    assert summaries[11].content_image_count == 1
    assert refined[11].decorative_image_count == 1
    assert refined[11].content_image_count == 0


def test_central_enlarged_occurrence_remains_content(tmp_path: Path) -> None:
    pdf_path = tmp_path / "central-exception.pdf"
    _write_pdf(pdf_path, central_exception=True)
    reader = PdfReader(str(pdf_path))

    summaries, repeated = analyze_repeated_graphics(reader)
    refined = refine_confirmed_decorative_graphics(reader, summaries, repeated)

    assert repeated
    assert refined[11].decorative_image_count == 0
    assert refined[11].content_image_count == 1
