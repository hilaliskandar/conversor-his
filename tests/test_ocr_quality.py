from conversor_his.ocr.quality import assess_ocr_quality


def test_short_noisy_ocr_requires_review() -> None:
    result = assess_ocr_quality(
        'E "Eu JABOATAO DOS GUARARAPES',
        confidences=[22.0, 31.0, 48.0, 53.0],
    )

    assert result.quality == "low"
    assert result.requires_review is True
    assert "texto OCR muito curto" in result.reasons
    assert "confianca media OCR baixa" in result.reasons


def test_long_high_confidence_ocr_is_accepted() -> None:
    text = (
        "Art. 1 O municipio estabelece diretrizes urbanisticas para garantir "
        "moradia adequada, infraestrutura, mobilidade e protecao ambiental. "
        "O dispositivo devera ser observado no licenciamento municipal."
    )
    result = assess_ocr_quality(text, confidences=[91.0] * 28)

    assert result.quality == "high"
    assert result.requires_review is False
    assert result.reasons == []


def test_moderate_confidence_requires_review() -> None:
    text = (
        "Art. 2 Este texto possui quantidade suficiente de palavras e caracteres "
        "para ser avaliado, mas a confianca media do reconhecimento permanece "
        "moderada e por isso exige verificacao humana antes do uso normativo."
    )
    result = assess_ocr_quality(text, confidences=[68.0] * 30)

    assert result.quality == "medium"
    assert result.requires_review is True
