from PIL import Image, ImageDraw

from conversor_his.map_visual import assess_map_visual


def test_identifies_sparse_title_page_as_cover_like() -> None:
    image = Image.new("RGB", (1000, 1400), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((320, 620, 680, 720), outline="black", width=3)

    result = assess_map_visual(image)

    assert result.cover_like is True
    assert result.visual_complexity is False


def test_identifies_dense_cartographic_page_as_visually_complex() -> None:
    image = Image.new("RGB", (1000, 1400), "white")
    draw = ImageDraw.Draw(image)
    for x in range(100, 901, 55):
        draw.line((x, 120, 950 - x // 4, 1260), fill="black", width=2)
    for y in range(140, 1261, 45):
        draw.line((80, y, 920, y + (y % 90)), fill="black", width=2)
    for index in range(20):
        x = 100 + (index % 5) * 160
        y = 200 + (index // 5) * 250
        draw.rectangle((x, y, x + 90, y + 60), outline="black", width=2)

    result = assess_map_visual(image)

    assert result.visual_complexity is True
    assert result.cover_like is False
