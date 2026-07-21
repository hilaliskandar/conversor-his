from __future__ import annotations

from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, StreamObject

from conversor_his.diagnostic import diagnose_pdf
from conversor_his.extractors.pypdf_native import extract_native_pages
from conversor_his.ocr.render import render_pdf_page


def _write_pdf_with_text(path: Path, text: str) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)

    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font)
    resources = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
    )
    page[NameObject("/Resources")] = resources

    safe_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content = StreamObject()
    content.set_data(f"BT /F1 12 Tf 72 720 Td ({safe_text}) Tj ET".encode("latin-1"))
    page[NameObject("/Contents")] = writer._add_object(content)

    with path.open("wb") as handle:
        writer.write(handle)


def test_native_extraction_and_diagnosis(tmp_path: Path) -> None:
    pdf_path = tmp_path / "lei.pdf"
    _write_pdf_with_text(pdf_path, "Artigo 1 Teste normativo municipal")

    pages = extract_native_pages(pdf_path)
    diagnosis = diagnose_pdf(pdf_path, min_native_chars=10)

    assert "Artigo 1" in pages[1]
    assert diagnosis.page_count == 1
    assert diagnosis.pages[0].route == "native"
    assert diagnosis.pages[0].has_native_text is True


def test_blank_page_routes_to_ocr(tmp_path: Path) -> None:
    pdf_path = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with pdf_path.open("wb") as handle:
        writer.write(handle)

    diagnosis = diagnose_pdf(pdf_path)

    assert diagnosis.pages[0].route == "ocr"
    assert "pagina sem texto ou imagem detectavel" in diagnosis.pages[0].warnings


def test_pdfium_renders_page(tmp_path: Path) -> None:
    pdf_path = tmp_path / "render.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=144, height=72)
    with pdf_path.open("wb") as handle:
        writer.write(handle)

    image = render_pdf_page(pdf_path, 1, dpi=144)

    assert image.mode == "RGB"
    assert image.size == (288, 144)
