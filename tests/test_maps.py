from conversor_his.maps import classify_map_page, extract_map_title, is_map_page


def test_classifies_short_map_page_as_candidate_without_visual_confirmation() -> None:
    text = "MAPA 3 - ZONEAMENTO"

    assert classify_map_page(text, image_count=1) == "map_candidate"
    assert is_map_page(text, image_count=1) is True
    assert extract_map_title(text, page_number=68) == "MAPA 3 - ZONEAMENTO"


def test_confirms_map_with_visual_and_cartographic_evidence() -> None:
    text = "MAPA 3 - ZONEAMENTO - LEGENDA - ESCALA 1:10.000 - SIRGAS 2000"

    result = classify_map_page(text, image_count=1, visual_complexity=True)

    assert result == "map_confirmed"


def test_distinguishes_cartographic_cover() -> None:
    text = "ANEXO CARTOGRÁFICO - CADERNO DE MAPAS"

    result = classify_map_page(text, image_count=1)

    assert result == "map_cover"
    assert is_map_page(text, image_count=1) is False


def test_does_not_classify_normative_reference_as_map() -> None:
    text = (
        "Art. 23. O zoneamento municipal está representado no MAPA 3 do Anexo I. "
        "Este dispositivo contém texto normativo extenso e regras de aplicação que "
        "não devem ser substituídas por imagem. " * 8
    )

    assert classify_map_page(text, image_count=1) == "none"
    assert is_map_page(text, image_count=1) is False


def test_requires_an_image_for_map_route() -> None:
    assert classify_map_page("MAPA 2 - SISTEMA VIÁRIO", image_count=0) == "none"
    assert is_map_page("MAPA 2 - SISTEMA VIÁRIO", image_count=0) is False
