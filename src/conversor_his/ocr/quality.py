# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
from statistics import mean

from ..models import OcrQuality

_WORD_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9]+", re.UNICODE)


def assess_ocr_quality(
    text: str,
    confidences: list[float] | None = None,
    *,
    min_characters: int = 80,
    min_words: int = 15,
    low_confidence: float = 55.0,
    medium_confidence: float = 75.0,
) -> OcrQuality:
    """Avalia se o texto OCR é utilizável e se exige revisão humana.

    A decisão combina volume textual, proporção de caracteres alfanuméricos e,
    quando disponível, confiança média do Tesseract. O texto nunca é descartado
    automaticamente: resultados fracos são preservados e marcados para revisão.
    """

    stripped = text.strip()
    character_count = len(stripped)
    words = _WORD_RE.findall(stripped)
    alphanumeric = sum(character.isalnum() for character in stripped)
    non_space = sum(not character.isspace() for character in stripped)
    alphanumeric_ratio = alphanumeric / non_space if non_space else 0.0

    valid_confidences = [value for value in (confidences or []) if value >= 0]
    mean_confidence = mean(valid_confidences) if valid_confidences else None
    reasons: list[str] = []

    if character_count < min_characters:
        reasons.append("texto OCR muito curto")
    if len(words) < min_words:
        reasons.append("poucas palavras reconhecidas")
    if alphanumeric_ratio < 0.60:
        reasons.append("alta proporcao de simbolos ou ruido")
    if mean_confidence is not None and mean_confidence < low_confidence:
        reasons.append("confianca media OCR baixa")

    severe = bool(reasons)
    if severe:
        quality = "low"
        requires_review = True
    elif mean_confidence is not None and mean_confidence < medium_confidence:
        quality = "medium"
        requires_review = True
        reasons.append("confianca media OCR moderada")
    else:
        quality = "high"
        requires_review = False

    return OcrQuality(
        character_count=character_count,
        word_count=len(words),
        alphanumeric_ratio=round(alphanumeric_ratio, 6),
        mean_confidence=(round(mean_confidence, 3) if mean_confidence is not None else None),
        quality=quality,
        requires_review=requires_review,
        reasons=reasons,
    )
