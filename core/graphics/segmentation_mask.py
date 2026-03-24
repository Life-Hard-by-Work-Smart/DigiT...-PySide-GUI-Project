"""Segmentation mask overlay renderer for vertebral polygons.

Standalone module — no imports from ui/. Can be enabled/disabled
via ENABLE_SEGMENTATION_MASK in config.py.
"""

from PySide6.QtGui import QPainter, QColor, QPolygon
from PySide6.QtCore import QPoint, Qt

from core.models.data_structures import VertebralPoints


def _classify_point(label: str) -> str:
    """Return corner abbreviation from a full point label.

    Examples:
        "C2 top left"     -> "TL"
        "C3 bottom right" -> "BR"
        "C4 centroid"     -> "C"
    """
    upper = label.upper()
    if "TOP" in upper and "LEFT" in upper:
        return "TL"
    if "TOP" in upper and "RIGHT" in upper:
        return "TR"
    if "BOTTOM" in upper and "LEFT" in upper:
        return "BL"
    if "BOTTOM" in upper and "RIGHT" in upper:
        return "BR"
    return "C"


def draw_segmentation_masks(
    painter: QPainter,
    vertebral_groups: list,
    zoom_level: float,
    pan_offset: QPoint,
    colors: list,
    alpha: int,
) -> None:
    """Draw filled semi-transparent polygons for each vertebra.

    Each vertebra's TL/TR/BR/BL corner points are connected in clockwise
    order to form a quadrilateral. Vertebrae missing fewer than 3 corners
    are silently skipped.

    Args:
        painter:          Active QPainter on the canvas widget.
        vertebral_groups: list[VertebralPoints] — one entry per vertebra.
        zoom_level:       Current canvas zoom (float).
        pan_offset:       Current pan offset (QPoint).
        colors:           list[QColor] — one color per vertebra, cycles if needed.
        alpha:            Fill transparency 0–255 (80 ≈ 31 % opacity).
    """
    if not vertebral_groups or not colors:
        return

    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)

    for i, vertebral in enumerate(vertebral_groups):
        # Build corner dict: abbreviation -> Point
        corners: dict = {}
        for point in vertebral.points:
            abbr = _classify_point(point.label)
            if abbr in ("TL", "TR", "BL", "BR"):
                corners[abbr] = point

        # Need at least 3 corners to form a visible polygon
        if len(corners) < 3:
            continue

        # Clockwise order: TL -> TR -> BR -> BL
        poly_points = []
        for abbr in ("TL", "TR", "BR", "BL"):
            if abbr in corners:
                p = corners[abbr]
                cx = int(p.x * zoom_level + pan_offset.x())
                cy = int(p.y * zoom_level + pan_offset.y())
                poly_points.append(QPoint(cx, cy))

        if len(poly_points) < 3:
            continue

        # Build polygon and draw
        polygon = QPolygon(poly_points)
        color = QColor(colors[i % len(colors)])
        color.setAlpha(alpha)
        painter.setBrush(color)
        painter.drawPolygon(polygon)

    painter.restore()
