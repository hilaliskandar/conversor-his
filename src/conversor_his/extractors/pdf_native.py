from __future__ import annotations

from pathlib import Path

import fitz


def extract_native_pages(path: Path) -> dict[int, str]:
    output: dict[int, str] = {}
    with fitz.open(path) as doc:
        for index, page in enumerate(doc, start=1):
            output[index] = (page.get_text("text") or "").strip()
    return output
