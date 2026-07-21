# SPDX-License-Identifier: MIT
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import sha256
from math import ceil
from statistics import median
from typing import Any

from .models import RepeatedGraphic


@dataclass(frozen=True, slots=True)
class GraphicOccurrence:
    page_number: int
    fingerprint: str
    bbox: tuple[float, float, float, float]
    area_ratio: float
    position: str
    image_weight: int


@dataclass(frozen=True, slots=True)
class PageGraphicSummary:
    raw_image_count: int
    decorative_image_count: int
    content_image_count: int


def _resolve(value: Any) -> Any:
    return value.get_object() if hasattr(value, "get_object") else value


def _count_images_in_object(obj: Any, visited: set[int] | None = None) -> int:
    visited = visited or set()
    obj = _resolve(obj)
    object_id = id(obj)
    if object_id in visited:
        return 0
    visited.add(object_id)

    subtype = obj.get("/Subtype") if hasattr(obj, "get") else None
    if subtype == "/Image":
        return 1
    if subtype != "/Form" or not hasattr(obj, "get"):
        return 0

    resources = _resolve(obj.get("/Resources"))
    xobjects = _resolve(resources.get("/XObject")) if resources else None
    if not xobjects:
        return 0
    return sum(_count_images_in_object(ref, visited) for ref in xobjects.values())


def _update_stream_digest(digest: Any, obj: Any) -> None:
    obj = _resolve(obj)
    for key in (
        "/Subtype",
        "/Width",
        "/Height",
        "/BitsPerComponent",
        "/ColorSpace",
        "/BBox",
        "/Matrix",
    ):
        digest.update(repr(obj.get(key) if hasattr(obj, "get") else None).encode())
        digest.update(b"\0")

    raw = getattr(obj, "_data", None)
    if raw is None and hasattr(obj, "get_data"):
        try:
            raw = obj.get_data()
        except Exception:  # pragma: no cover - PDF estruturalmente problemático
            raw = b""
    digest.update(bytes(raw or b""))

    if not hasattr(obj, "get") or obj.get("/Subtype") != "/Form":
        return
    resources = _resolve(obj.get("/Resources"))
    xobjects = _resolve(resources.get("/XObject")) if resources else None
    if not xobjects:
        return
    for name, reference in sorted(xobjects.items(), key=lambda item: str(item[0])):
        digest.update(str(name).encode())
        _update_stream_digest(digest, reference)


def _stream_fingerprint(obj: Any) -> str:
    digest = sha256()
    _update_stream_digest(digest, obj)
    return digest.hexdigest()


def _apply_matrix(
    matrix: list[float] | tuple[float, ...],
    x: float,
    y: float,
) -> tuple[float, float]:
    a, b, c, d, e, f = (float(value) for value in matrix[:6])
    return (a * x + c * y + e, b * x + d * y + f)


def _matrix_multiply(left: list[float], right: list[float]) -> list[float]:
    a1, b1, c1, d1, e1, f1 = left
    a2, b2, c2, d2, e2, f2 = right
    return [
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    ]


def _normalized_bbox(
    page: Any,
    obj: Any,
    cm: list[float],
) -> tuple[float, float, float, float] | None:
    width = float(page.mediabox.width)
    height = float(page.mediabox.height)
    if width <= 0 or height <= 0:
        return None

    obj = _resolve(obj)
    subtype = obj.get("/Subtype") if hasattr(obj, "get") else None
    if subtype == "/Form":
        bbox = obj.get("/BBox") or [0, 0, 1, 1]
        form_matrix = [
            float(value)
            for value in (obj.get("/Matrix") or [1, 0, 0, 1, 0, 0])
        ]
        matrix = _matrix_multiply(cm, form_matrix)
        x0, y0, x1, y1 = (float(value) for value in bbox)
    else:
        matrix = cm
        x0, y0, x1, y1 = 0.0, 0.0, 1.0, 1.0

    points = [
        _apply_matrix(matrix, x0, y0),
        _apply_matrix(matrix, x0, y1),
        _apply_matrix(matrix, x1, y0),
        _apply_matrix(matrix, x1, y1),
    ]
    xs = [point[0] / width for point in points]
    ys = [point[1] / height for point in points]
    nx0, nx1 = max(0.0, min(xs)), min(1.0, max(xs))
    ny0, ny1 = max(0.0, min(ys)), min(1.0, max(ys))
    if nx1 <= nx0 or ny1 <= ny0:
        return None
    return (nx0, ny0, nx1, ny1)


def _position(
    bbox: tuple[float, float, float, float],
    edge_band: float,
) -> str:
    x0, y0, x1, y1 = bbox
    if y1 <= edge_band:
        return "bottom"
    if y0 >= 1.0 - edge_band:
        return "top"
    if x1 <= edge_band:
        return "left"
    if x0 >= 1.0 - edge_band:
        return "right"
    return "interior"


def list_page_graphics(
    page: Any,
    page_number: int,
    edge_band: float = 0.12,
) -> list[GraphicOccurrence]:
    """Inventaria XObjects gráficos e sua posição normalizada na página."""

    resources = _resolve(page.get("/Resources"))
    xobjects = _resolve(resources.get("/XObject")) if resources else None
    if not xobjects:
        return []

    occurrences: list[GraphicOccurrence] = []

    def visitor(
        operator: bytes,
        operands: list[Any],
        cm: list[float],
        _tm: list[float],
    ) -> None:
        if operator != b"Do" or not operands:
            return
        reference = xobjects.get(operands[0])
        if reference is None:
            return
        obj = _resolve(reference)
        image_weight = _count_images_in_object(obj)
        if image_weight < 1:
            return
        bbox = _normalized_bbox(page, obj, cm)
        if bbox is None:
            return
        x0, y0, x1, y1 = bbox
        occurrences.append(
            GraphicOccurrence(
                page_number=page_number,
                fingerprint=_stream_fingerprint(obj),
                bbox=bbox,
                area_ratio=(x1 - x0) * (y1 - y0),
                position=_position(bbox, edge_band),
                image_weight=image_weight,
            )
        )

    try:
        page.extract_text(visitor_operand_before=visitor)
    except Exception:  # pragma: no cover - fallback conservador
        return []

    unique: dict[tuple[str, tuple[float, ...]], GraphicOccurrence] = {}
    for occurrence in occurrences:
        key = (
            occurrence.fingerprint,
            tuple(round(value, 6) for value in occurrence.bbox),
        )
        unique[key] = occurrence
    return list(unique.values())


def _median_bbox(
    occurrences: list[GraphicOccurrence],
) -> tuple[float, float, float, float]:
    values = tuple(
        median(item.bbox[index] for item in occurrences) for index in range(4)
    )
    return (values[0], values[1], values[2], values[3])


def _bbox_close(
    bbox: tuple[float, float, float, float],
    reference: tuple[float, float, float, float],
    tolerance: float,
) -> bool:
    return all(
        abs(value - expected) <= tolerance
        for value, expected in zip(bbox, reference)
    )


def analyze_repeated_graphics(
    reader: Any,
    *,
    min_page_ratio: float = 0.70,
    max_area_ratio: float = 0.05,
    edge_band: float = 0.12,
    position_tolerance: float = 0.025,
    min_pages: int = 5,
) -> tuple[dict[int, PageGraphicSummary], list[RepeatedGraphic]]:
    """Detecta elementos gráficos periféricos repetidos sem alterar o PDF.

    A classificação exige simultaneamente recorrência documental, área pequena,
    posição periférica e estabilidade geométrica. A ação resultante é apenas
    lógica: o elemento deixa de influenciar rotas e alertas, mas permanece no
    original e é registrado no manifesto.
    """

    page_count = len(reader.pages)
    all_occurrences: list[GraphicOccurrence] = []
    page_occurrences: dict[int, list[GraphicOccurrence]] = {}

    for page_number, page in enumerate(reader.pages, start=1):
        occurrences = list_page_graphics(page, page_number, edge_band=edge_band)
        page_occurrences[page_number] = occurrences
        all_occurrences.extend(occurrences)

    groups: dict[str, list[GraphicOccurrence]] = defaultdict(list)
    for occurrence in all_occurrences:
        groups[occurrence.fingerprint].append(occurrence)

    decorative_rules: dict[
        str,
        tuple[str, tuple[float, float, float, float]],
    ] = {}
    repeated_graphics: list[RepeatedGraphic] = []
    core_denominator = max(page_count - 2, 1)
    required_pages = max(min_pages, ceil(core_denominator * min_page_ratio))

    for fingerprint, occurrences in groups.items():
        core = [item for item in occurrences if 1 < item.page_number < page_count]
        unique_core_pages = {item.page_number for item in core}
        if len(unique_core_pages) < required_pages:
            continue

        positions = Counter(item.position for item in core)
        position, position_count = positions.most_common(1)[0]
        if position == "interior" or position_count / len(core) < 0.95:
            continue

        eligible = [
            item
            for item in core
            if item.position == position and item.area_ratio <= max_area_ratio
        ]
        if len(eligible) / len(core) < 0.95:
            continue

        reference_bbox = _median_bbox(eligible)
        stable = [
            item
            for item in eligible
            if _bbox_close(item.bbox, reference_bbox, position_tolerance)
        ]
        if len(stable) / len(core) < 0.95:
            continue

        decorative_rules[fingerprint] = (position, reference_bbox)
        all_pages = {item.page_number for item in occurrences}
        repeated_graphics.append(
            RepeatedGraphic(
                graphic_id=f"graphic-{fingerprint[:12]}",
                sha256=fingerprint,
                occurrences=len(occurrences),
                page_count=len(all_pages),
                page_ratio=round(len(all_pages) / max(page_count, 1), 6),
                position=position,
                median_bbox=[round(value, 6) for value in reference_bbox],
                max_area_ratio=max_area_ratio,
            )
        )

    summaries: dict[int, PageGraphicSummary] = {}
    for page_number, occurrences in page_occurrences.items():
        by_fingerprint: dict[str, list[GraphicOccurrence]] = defaultdict(list)
        for occurrence in occurrences:
            by_fingerprint[occurrence.fingerprint].append(occurrence)

        raw_count = sum(
            max(item.image_weight for item in group)
            for group in by_fingerprint.values()
        )
        decorative_count = 0
        for fingerprint, group in by_fingerprint.items():
            rule = decorative_rules.get(fingerprint)
            if rule is None:
                continue
            position, reference_bbox = rule
            if any(
                item.position == position
                and item.area_ratio <= max_area_ratio
                and _bbox_close(item.bbox, reference_bbox, position_tolerance)
                for item in group
            ):
                decorative_count += max(item.image_weight for item in group)

        summaries[page_number] = PageGraphicSummary(
            raw_image_count=raw_count,
            decorative_image_count=decorative_count,
            content_image_count=max(raw_count - decorative_count, 0),
        )

    return summaries, repeated_graphics
