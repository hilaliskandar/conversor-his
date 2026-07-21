from conversor_his.maps import extract_map_title, is_map_page


def test_detects_short_map_page_with_image() -> None:
    text = "MAPA 3 - ZONEAMENTO"

    assert is_map_page(text, image_count=1) is True
    assert extract_map_title(text, page_number=68) == "MAPA 3 - ZONEAMENTO"


def test_does_not_classify_normative_reference_as_map() -> None:
    text = (
        "Art. 23. O zoneamento municipal está representado no MAPA 3 do Anexo I. "
        "Este dispositivo contém texto normativo extenso e regras de aplicação que "
        "não devem ser substituídas por imagem. " * 8
    )

    assert is_map_page(text, image_count=1) is False


def test_requires_an_image_for_map_route() -> None:
    assert is_map_page("MAPA 2 - SISTEMA VIÁRIO", image_count=0) is False
