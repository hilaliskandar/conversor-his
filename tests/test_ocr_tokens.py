from pathlib import Path
from types import SimpleNamespace

from conversor_his.ocr.tesseract_engine import TesseractEngine


class FakePytesseract:
    class Output:
        DICT = object()

    @staticmethod
    def image_to_data(image, lang, config, output_type):
        return {
            "text": ["", "Art.", "70-A"],
            "conf": ["-1", "96.5", "88"],
            "block_num": [0, 1, 1],
            "par_num": [0, 1, 1],
            "line_num": [0, 1, 1],
            "word_num": [0, 1, 2],
            "left": [0, 10, 55],
            "top": [0, 20, 20],
            "width": [0, 40, 45],
            "height": [0, 15, 15],
        }


def test_tesseract_preserves_token_positions(monkeypatch) -> None:
    engine = TesseractEngine()
    monkeypatch.setattr(engine, "_load_pytesseract", lambda: FakePytesseract)
    monkeypatch.setattr(
        "conversor_his.ocr.tesseract_engine.render_pdf_page",
        lambda *args, **kwargs: SimpleNamespace(),
    )
    text, confidences, tokens = engine.recognize_page_with_tokens(Path("lei.pdf"), 3)
    assert text == "Art. 70-A"
    assert confidences == [96.5, 88.0]
    assert tokens[1].page_number == 3
    assert tokens[1].left == 55
