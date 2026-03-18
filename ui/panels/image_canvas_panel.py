"""Interactive canvas pro zobrazení a editaci vertebrálních bodů na obrázku"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea
from PySide6.QtCore import Qt, Signal, QSize, QRect, QPoint
from PySide6.QtGui import (
    QPixmap,
    QPainter,
    QColor,
    QPen,
    QFont,
    QImage,
    QTransform,
)

from core.models import VertebralPoints, Point
from config import (
    POINT_COLORS,
    POINT_RADIUS,
    POINT_SELECTED_RADIUS,
    POINT_CLICK_RADIUS,
    SHOW_POINT_LABELS,
    ZOOM_STEP,
    AUTO_FIT_IMAGE,
    ALLOW_POINTS_OUTSIDE_IMAGE,
)
from logger import logger


class PointsOverlay(QWidget):
    """Custom widget pro kreslení a manipulaci s body na obrázku"""

    # Signals
    pointSelected = Signal(str)  # point_id
    pointMoved = Signal(str, float, float)  # point_id, x, y

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)

        # Data
        self.vertebral_points: dict[str, Point] = {}  # point_id -> Point
        self.image: QPixmap = None
        self.selected_point_id: str = None
        self.dragging = False
        self.drag_start_pos = None

        # Zoom & Pan
        self.zoom_level = 1.0
        self.pan_offset = QPoint(0, 0)
        self.space_pressed = False
        self.pan_start_pos = None
        self.min_zoom_level = 1.0  # Minimální zoom = auto-fit při načtení (nastaví se v _auto_fit_image)

        # Point colors palette (lze změnit per-model)
        self.point_colors = POINT_COLORS.copy()

        # Visual
        self.setStyleSheet("background-color: #ffffff;")
        # DŮLEŽITÉ: Expanduj na dostupný prostor!
        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def sizeHint(self):
        """Vrátí doporučenou velikost - co největší"""
        from PySide6.QtCore import QSize
        return QSize(2000, 2000)  # Velké číslo aby se expandoval

    def minimumSizeHint(self):
        """Minimum velikost"""
        from PySide6.QtCore import QSize
        return QSize(100, 100)

    def set_image(self, pixmap: QPixmap):
        """Nastav obrázek na pozadí"""
        if pixmap.isNull():
            logger.warning("ImageCanvasPanel: received null pixmap")
            return

        self.image = pixmap
        logger.info(f"ImageCanvasPanel: loaded image {pixmap.width()}x{pixmap.height()}")

        # Auto-fit image do canvas (pokud je zapnuté)
        if AUTO_FIT_IMAGE:
            self._auto_fit_image()

        self.update()

    def set_point_colors(self, colors_dict):
        """Nastav novou paletu barev pro body (per-model)"""
        self.point_colors = colors_dict.copy()
        logger.debug(f"Canvas: barvy bodů změněny")
        self.update()

    def _auto_fit_image(self):
        """Auto-center a zoom image aby se vešel do canvas"""
        if self.image is None:
            return

        canvas_size = self.size()
        image_size = self.image.size()

        # Vypočítej zoom aby se obrázek vešel do celé canvas plochy
        zoom_x = canvas_size.width() / image_size.width()
        zoom_y = canvas_size.height() / image_size.height()
        self.zoom_level = min(zoom_x, zoom_y)  # Vešel se celý obrázek do canvas (bez limitu 1:1)

        # IMPORTANT: Nastav minimální zoom na aktuální zoom - nesmí se oddálit níž!
        self.min_zoom_level = self.zoom_level

        # Centr obrázek
        scaled_w = int(image_size.width() * self.zoom_level)
        scaled_h = int(image_size.height() * self.zoom_level)
        offset_x = (canvas_size.width() - scaled_w) // 2
        offset_y = (canvas_size.height() - scaled_h) // 2
        self.pan_offset = QPoint(offset_x, offset_y)

        logger.debug(f"Auto-fit: zoom={self.zoom_level:.2f}, offset=({offset_x}, {offset_y}), min_zoom={self.min_zoom_level:.2f}")

    def set_vertebral_points(self, vertebral_points_list: list[VertebralPoints]):
        """Nastav seznam vertebrálních bodů k zobrazení"""
        self.vertebral_points.clear()

        for vertebral in vertebral_points_list:
            for point in vertebral.points:
                self.vertebral_points[point.label] = point
                logger.debug(f"Canvas: loaded point {point.label} ({point.x}, {point.y})")

        self.update()

    def _get_point_abbreviation(self, label: str) -> str:
        """Extrahuj typ bodu z labelu (C2 top left -> TL)"""
        label = label.upper()
        if "TOP" in label and "LEFT" in label:
            return "TL"
        elif "TOP" in label and "RIGHT" in label:
            return "TR"
        elif "BOTTOM" in label and "LEFT" in label:
            return "BL"
        elif "BOTTOM" in label and "RIGHT" in label:
            return "BR"
        elif "CENTER" in label or "CENTROID" in label:
            return "C"
        return "C"  # Default

    def _canvas_to_image_coords(self, canvas_x: int, canvas_y: int) -> tuple[float, float]:
        """Převeď canvas souřadnice na image souřadnice (bez zoomu)"""
        image_x = (canvas_x - self.pan_offset.x()) / self.zoom_level
        image_y = (canvas_y - self.pan_offset.y()) / self.zoom_level
        return image_x, image_y

    def _image_to_canvas_coords(self, image_x: float, image_y: float) -> tuple[int, int]:
        """Převeď image souřadnice na canvas souřadnice (s zoomem a panem)"""
        canvas_x = int(image_x * self.zoom_level + self.pan_offset.x())
        canvas_y = int(image_y * self.zoom_level + self.pan_offset.y())
        return canvas_x, canvas_y

    def _get_point_at_coords(self, x: int, y: int, radius: int = POINT_CLICK_RADIUS) -> str:
        """Vrátí point_id na dané souřadnici (s hitboxem), nebo None"""
        for point_id, point in self.vertebral_points.items():
            canvas_x, canvas_y = self._image_to_canvas_coords(point.x, point.y)
            dist = ((canvas_x - x) ** 2 + (canvas_y - y) ** 2) ** 0.5
            if dist <= radius:
                return point_id
        return None

    def _clamp_pan_offset(self):
        """Když se obrázek dostane k hranám, vycentruj ho místo clamping"""
        if self.image is None:
            return

        canvas_size = self.size()
        image_size = self.image.size()

        # Vypočítej velikost zoomed obrázku
        scaled_w = int(image_size.width() * self.zoom_level)
        scaled_h = int(image_size.height() * self.zoom_level)

        logger.debug(f"Canvas: _clamp_pan_offset called: canvas={canvas_size.width()}x{canvas_size.height()}, scaled={scaled_w}x{scaled_h}")

        # Pokud je obrázek MENŠÍ než canvas, vždy ho centrej
        if scaled_w < canvas_size.width():
            center_x = (canvas_size.width() - scaled_w) // 2
            self.pan_offset.setX(center_x)
            logger.debug(f"Canvas: centering X: center_x={center_x}")

        if scaled_h < canvas_size.height():
            center_y = (canvas_size.height() - scaled_h) // 2
            self.pan_offset.setY(center_y)
            logger.debug(f"Canvas: centering Y: center_y={center_y}")

        logger.debug(f"Canvas: pan_offset after clamp = {self.pan_offset}")

    # ===== PAINT =====

    def paintEvent(self, event):
        """Nakresli obrázek + body"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Nakresli obrázek
        if self.image:
            scaled_image = self.image.scaledToWidth(
                int(self.image.width() * self.zoom_level),
                Qt.SmoothTransformation,
            )
            painter.drawPixmap(self.pan_offset, scaled_image)

        # Nakresli body
        for point_id, point in self.vertebral_points.items():
            canvas_x, canvas_y = self._image_to_canvas_coords(point.x, point.y)

            # Vyber barvu a radius
            is_selected = point_id == self.selected_point_id
            point_abbr = self._get_point_abbreviation(point_id)
            color = self.point_colors.get(point_abbr, QColor(200, 200, 200))
            radius = POINT_SELECTED_RADIUS if is_selected else POINT_RADIUS

            # Nakresli bod
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(canvas_x - radius, canvas_y - radius, radius * 2, radius * 2)

            # Pokud je vybraný, nakresli obrys
            if is_selected:
                painter.setPen(QPen(QColor(0, 0, 0), 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(
                    canvas_x - radius - 2, canvas_y - radius - 2, (radius + 2) * 2, (radius + 2) * 2
                )

            # Nakresli label (pokud je zapnuté)
            if SHOW_POINT_LABELS:
                painter.setPen(QPen(QColor(0, 0, 0), 1))
                painter.setFont(QFont("Arial", 8))
                painter.drawText(canvas_x + radius + 2, canvas_y + radius + 2, point_abbr)

        painter.end()

    # ===== MOUSE EVENTS =====

    def mousePressEvent(self, event):
        """Detect bod na kterém uživatel kliknul, nebo začni pan"""
        x, y = event.position().x(), event.position().y()

        if event.button() == Qt.LeftButton:
            # Pokud je bod pod kurzorem
            point_id = self._get_point_at_coords(x, y)

            if point_id:
                # Je bod - vyberi ho POUZE pokud NE spacebar
                if not self.space_pressed:
                    self.selected_point_id = point_id
                    self.pointSelected.emit(point_id)
                    logger.debug(f"Canvas: point selected {point_id}")
                    self.update()

            # Pokud spacebar, aktivuj pan
            if self.space_pressed:
                self.dragging = True
                self.drag_start_pos = QPoint(x, y)
                logger.debug(f"Canvas: pan started (space+left) at {self.drag_start_pos}")

        elif event.button() == Qt.MiddleButton:
            # Middle mouse button = pan start
            self.dragging = True
            self.drag_start_pos = QPoint(x, y)
            logger.debug(f"Canvas: pan started (middle) at {self.drag_start_pos}")

    def mouseMoveEvent(self, event):
        """Drag bod nebo pan canvas"""
        if self.dragging and self.drag_start_pos:
            # Pan mode: move canvas
            delta = QPoint(event.position().x(), event.position().y()) - self.drag_start_pos
            self.pan_offset += delta
            self._clamp_pan_offset()  # Aplikuj limity aby se obrázek nepánoval mimo canvas
            self.drag_start_pos = QPoint(event.position().x(), event.position().y())
            logger.debug(f"Canvas: panning, offset={self.pan_offset}")
            self.update()

    def mouseReleaseEvent(self, event):
        """Ukonči pan"""
        if event.button() == Qt.MiddleButton or event.button() == Qt.LeftButton:
            self.dragging = False
            self.drag_start_pos = None

    def wheelEvent(self, event):
        """Scroll = zoom kolem kurzoru (pivot point)"""
        if not self.image:
            return

        # Získej pozici kurzoru na canvas
        cursor_pos = event.position()
        cursor_x = int(cursor_pos.x())
        cursor_y = int(cursor_pos.y())

        # Převeď canvas coords na image coords (aby se zoom dělal kolem správného místa)
        image_x, image_y = self._canvas_to_image_coords(cursor_x, cursor_y)

        # Staré zoom
        old_zoom = self.zoom_level

        # Vypočítej nové zoom
        if event.angleDelta().y() > 0:
            # Scroll up = zoom in
            self.zoom_level *= ZOOM_STEP
        else:
            # Scroll down = zoom out
            self.zoom_level /= ZOOM_STEP

        # Clamp zoom - IMPORTANT: Nesmí se oddálit pod min_zoom_level!
        self.zoom_level = max(self.min_zoom_level, min(self.zoom_level, 5.0))

        # Vypočítej nový pan offset aby se pivot point zůstal na stejné místo
        # Nová canvas pozice pivotu = staré canvas pozice
        new_canvas_x, new_canvas_y = self._image_to_canvas_coords(image_x, image_y)
        delta_x = cursor_x - new_canvas_x
        delta_y = cursor_y - new_canvas_y
        self.pan_offset += QPoint(delta_x, delta_y)

        # Aplikuj limity aby se obrázek nepánoval mimo canvas
        self._clamp_pan_offset()

        logger.debug(f"Canvas: zoom={self.zoom_level:.2f}, pan_offset={self.pan_offset}")
        self.update()

    # ===== KEYBOARD EVENTS =====

    def keyPressEvent(self, event):
        """Klávesnice pro pan + future editing"""
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self.space_pressed = True
            logger.debug("Canvas: Space pressed - pan mode ON")
        elif event.key() == Qt.Key_Escape:
            self.selected_point_id = None
            self.update()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """Ukonči spacebar pan"""
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self.space_pressed = False
            logger.debug("Canvas: Space released - pan mode OFF")

    def resizeEvent(self, event):
        """Canvas se změnil - re-fit image"""
        super().resizeEvent(event)
        if self.image and AUTO_FIT_IMAGE:
            self._auto_fit_image()
            logger.debug(f"Canvas resized to {event.size().width()}x{event.size().height()}")

        # Vycentruj offset pokud je obrázek menší než canvas
        self._clamp_pan_offset()

    # ===== PUBLIC METHODS =====

    def select_point(self, point_id: str):
        """Highlight specific point"""
        self.selected_point_id = point_id
        self.update()

    def deselect_point(self):
        """Deselect current point"""
        self.selected_point_id = None
        self.update()

    def update_point_position(self, point_id: str, x: float, y: float):
        """Update point position (from external source like table)"""
        if point_id in self.vertebral_points:
            self.vertebral_points[point_id].x = x
            self.vertebral_points[point_id].y = y
            logger.debug(f"Canvas: point {point_id} updated to ({x}, {y})")
            self.update()

    def reset_zoom_and_pan(self):
        """Reset zoom a pan na default"""
        self.zoom_level = 1.0
        self.pan_offset = QPoint(0, 0)
        if AUTO_FIT_IMAGE:
            self._auto_fit_image()
        self.update()


class ImageCanvasPanel(QWidget):
    """Main container pro canvas s controls"""

    # Signals
    pointSelected = Signal(str)  # point_id
    pointMoved = Signal(str, float, float)  # point_id, x, y

    def __init__(self, parent=None):
        super().__init__(parent)
        logger.info("ImageCanvasPanel: initializing")

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)  # CRITICAL: Žádný spacing!

        # Canvas
        self.canvas = PointsOverlay()
        self.canvas.pointSelected.connect(self._on_point_selected)
        layout.addWidget(self.canvas, stretch=1)  # DŮLEŽITÉ: stretch=1 aby se expandoval!

        # Status bar (placeholder) - SKRYJ aby se canvas zobrazoval na plno
        self.status_label = QLabel("Canvas ready")
        self.status_label.setStyleSheet("padding: 0px; margin: 0px; background-color: #f0f0f0; border-radius: 3px;")
        self.status_label.setMaximumHeight(0)  # Skrytý ale stále dostupný pro update
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

    def set_image(self, pixmap: QPixmap):
        """Nastav obrázek na canvas"""
        self.canvas.set_image(pixmap)
        self.status_label.setText(f"Image: {pixmap.width()}x{pixmap.height()} | Zoom: 100%")

    def set_vertebral_points(self, vertebral_points_list: list[VertebralPoints]):
        """Nastav body k zobrazení"""
        self.canvas.set_vertebral_points(vertebral_points_list)
        self.status_label.setText(f"Loaded {len(self.canvas.vertebral_points)} points")

    def set_point_colors(self, colors_dict):
        """Nastav novou paletu barev pro body (per-model)"""
        self.canvas.set_point_colors(colors_dict)

    def _on_point_selected(self, point_id: str):
        """Canvas vybral bod -> emit signal"""
        self.pointSelected.emit(point_id)

    def select_point(self, point_id: str):
        """Highlight bod z external source (např. tabulka)"""
        self.canvas.select_point(point_id)

    def deselect_point(self):
        """Deselect current point"""
        self.canvas.deselect_point()

    def update_point_position(self, point_id: str, x: float, y: float):
        """Update bod z external source"""
        self.canvas.update_point_position(point_id, x, y)

    def reset_view(self):
        """Reset zoom a pan"""
        self.canvas.reset_zoom_and_pan()
