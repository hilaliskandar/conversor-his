from PIL import Image, ImageDraw

from conversor_his.raster_visual import assess_raster_visual


def test_detects_regular_raster_table() -> None:
    image = Image.new("RGB", (900, 1200), "white")
    draw = ImageDraw.Draw(image)

    for y in range(250, 751, 80):
        draw.line((120, y, 780, y), fill="black", width=4)
    for x in range(120, 781, 110):
        draw.line((x, 250, x, 750), fill="black", width=4)

    result = assess_raster_visual(image)

    assert result.classification == "raster_table_candidate"
    assert result.detected is True
    assert result.horizontal_lines >= 4
    assert result.vertical_lines >= 3
    assert result.intersections >= 6


def test_detects_box_diagram_without_regular_grid() -> None:
    image = Image.new("RGB", (900, 1200), "white")
    draw = ImageDraw.Draw(image)

    boxes = [
        (100, 150, 320, 260),
        (580, 150, 800, 260),
        (340, 480, 560, 590),
        (100, 820, 320, 930),
    ]
    for box in boxes:
        draw.rectangle(box, outline="black", width=5)
    draw.line((320, 205, 580, 205), fill="black", width=4)
    draw.line((450, 260, 450, 480), fill="black", width=4)
    draw.line((340, 535, 210, 535), fill="black", width=4)
    draw.line((210, 535, 210, 820), fill="black", width=4)

    result = assess_raster_visual(image)

    assert result.classification in {"diagram_candidate", "raster_table_candidate"}
    assert result.detected is True


def test_ignores_plain_scanned_text_page() -> None:
    image = Image.new("RGB", (900, 1200), "white")
    draw = ImageDraw.Draw(image)
    for y in range(150, 1000, 45):
        draw.line((120, y, 760, y), fill="black", width=2)

    result = assess_raster_visual(image)

    assert result.classification == "none"
    assert result.detected is False
