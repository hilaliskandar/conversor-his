from conversor_his.validation.metrics import cer, wer


def test_cer_identical() -> None:
    assert cer("artigo", "artigo") == 0.0


def test_cer_one_substitution() -> None:
    assert cer("abc", "adc") == 1 / 3


def test_wer_identical() -> None:
    assert wer("artigo primeiro", "artigo primeiro") == 0.0
