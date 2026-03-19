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
    ARROW_KEY_STEP,                  # Pixel per arrow key press
    ARROW_KEY_STEP_SHIFT,
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
        self.dragging_point = False  # True když táhneme bod (ne pan)
        self.dragging_point_id = None  # Který bod se právě táhne

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
        """Extrahuj typ bodu z labelu - vrací plný text (C2 top left -> top left)"""
        # Extrahuj část za obratle (C2 top left -> top left)
        parts = label.split()
        if len(parts) > 1:
            return ' '.join(parts[1:])
        return label

    def _get_point_abbreviation_short(self, label: str) -> str:
        """Extrahuj typ bodu z labelu - vrací zkratku (C2 top left -> TL)"""
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

    def _lighten_color(self, color: QColor) -> QColor:
        """Zjasnit barvu pro vybraný bod"""
        # Sní hodnoty na 0-1 rozsah
        h, s, v, a = color.getHsv()
        # Zvětšit brightness
        v = min(255, int(v * 1.3))
        s = max(0, int(s * 0.8))  # Snížit saturaci pro měkčí vzhled
        return QColor.fromHsv(h, s, v, a)

    def _get_point_at_coords(self, x: int, y: int, radius: int = POINT_CLICK_RADIUS) -> str:
        """Vrátí point_id na dané souřadnici (s hitboxem), nebo None"""
        for point_id, point in self.vertebral_points.items():
            canvas_x, canvas_y = self._image_to_canvas_coords(point.x, point.y)
            dist = ((canvas_x - x) ** 2 + (canvas_y - y) ** 2) ** 0.5
            if dist <= radius:
                return point_id
        return None

    def _clamp_pan_offset(self):
        """Smooth bounds clamping - žádné sudden jumps, jenom limituj k hranicím"""
        if self.image is None:
            return

        canvas_size = self.size()
        image_size = self.image.size()

        # Vypočítej velikost zoomed obrázku
        scaled_w = int(image_size.width() * self.zoom_level)
        scaled_h = int(image_size.height() * self.zoom_level)

        logger.debug(f"Canvas: _clamp_pan_offset: canvas={canvas_size.width()}x{canvas_size.height()}, scaled={scaled_w}x{scaled_h}, zoom={self.zoom_level:.2f}x")

        # SMOOTH CLAMPING: Pokud je obrázek VĚTŠÍ než canvas, limituj pan k hranicím
        if scaled_w > canvas_size.width():
            # Pan může být 0 až (obrázek_width - canvas_width)
            max_pan_x = canvas_size.width() - scaled_w
            if self.pan_offset.x() > 0:
                self.pan_offset.setX(0)
            elif self.pan_offset.x() < max_pan_x:
                self.pan_offset.setX(max_pan_x)
        else:
            # Obrázek je MENŠÍ - centrej ho aby vypadal lépe
            center_x = (canvas_size.width() - scaled_w) // 2
            self.pan_offset.setX(center_x)

        if scaled_h > canvas_size.height():
            # Pan může být 0 až (obrázek_height - canvas_height)
            max_pan_y = canvas_size.height() - scaled_h
            if self.pan_offset.y() > 0:
                self.pan_offset.setY(0)
            elif self.pan_offset.y() < max_pan_y:
                self.pan_offset.setY(max_pan_y)
        else:
            # Obrázek je MENŠÍ - centrej ho
            center_y = (canvas_size.height() - scaled_h) // 2
            self.pan_offset.setY(center_y)

        logger.debug(f"Canvas: pan_offset after smooth clamp = {self.pan_offset}")

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
            point_label = self._get_point_abbreviation(point_id)  # Plný text pro display
            point_abbr = self._get_point_abbreviation_short(point_id)  # Zkratka pro barvu
            color = self.point_colors.get(point_abbr, QColor(200, 200, 200))

            # Pokud je vybraný, nastav jasnější barvu
            if is_selected:
                color = self._lighten_color(color)

            radius = POINT_SELECTED_RADIUS if is_selected else POINT_RADIUS

            # Nakresli bod
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(canvas_x - radius, canvas_y - radius, radius * 2, radius * 2)

            # Pokud je vybraný, nakresli obrys (silnější)
            if is_selected:
                painter.setPen(QPen(QColor(255, 165, 0), 3))  # Oranžový border
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(
                    canvas_x - radius - 3, canvas_y - radius - 3, (radius + 3) * 2, (radius + 3) * 2
                )
            else:
                # Normální bod - jemný border
                painter.setPen(QPen(QColor(100, 100, 100), 1))
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(
                    canvas_x - radius - 1, canvas_y - radius - 1, (radius + 1) * 2, (radius + 1) * 2
                )

            # Nakresli label (pokud je zapnuté)
            if SHOW_POINT_LABELS:
                painter.setPen(QPen(QColor(0, 255, 0), 1))  # Radioaktivní zelená ☢️
                painter.setFont(QFont("Arial", 8))
                painter.drawText(canvas_x + radius + 2, canvas_y + radius + 2, point_label)

        # === ZOOM INDICATOR - v pravém horním rohu ===
        zoom_text = f"Zoom: {self.zoom_level:.2f}x"
        painter.setFont(QFont("Arial", 9, weight=QFont.Bold))

        # Vypočítej text velikost
        font_metrics = painter.fontMetrics()
        text_width = font_metrics.horizontalAdvance(zoom_text)
        text_height = font_metrics.height()

        # Pozice v pravém horním rohu
        margin = 3
        padding = 6
        box_width = text_width + padding * 2
        box_height = text_height + padding * 2

        x = self.width() - box_width - margin
        y = margin

        # Nakresli zakulacený bílý box
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255))  # Bílé pozadí
        painter.drawRoundedRect(int(x), int(y), int(box_width), int(box_height), 6, 6)

        # Nakresli černý text
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.drawText(int(x + padding), int(y + padding + font_metrics.ascent()), zoom_text)

        painter.end()

    # ===== MOUSE EVENTS =====

    def mousePressEvent(self, event):
        """Detect bod na kterém uživatel kliknul, nebo začni pan"""
        x, y = event.position().x(), event.position().y()

        if event.button() == Qt.LeftButton:
            # Pokud je bod pod kurzorem
            point_id = self._get_point_at_coords(x, y)
            logger.debug(f"Canvas: left click at ({x}, {y}), point_id={point_id}")

            if point_id:
                # Je bod - vyberi ho POUZE pokud NE spacebar
                if not self.space_pressed:
                    self.selected_point_id = point_id
                    self.pointSelected.emit(point_id)
                    logger.debug(f"Canvas: point selected {point_id}")
                    # Phase 3: Start point dragging
                    self.dragging_point = True
                    self.dragging_point_id = point_id
                    self.drag_start_pos = QPoint(x, y)
                    logger.debug(f"Canvas: START DRAGGING point {point_id}")
                    self.update()
                    return

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
        x, y = event.position().x(), event.position().y()

        # Phase 3: Pokud táhneme bod
        if self.dragging_point and self.dragging_point_id:
            logger.debug(f"Canvas: dragging point {self.dragging_point_id}")
            # Převeď canvas coords na image coords
            image_x, image_y = self._canvas_to_image_coords(x, y)

            # Bounds check - bod musí zůstat v image
            if self.image:
                image_x = max(0, min(image_x, self.image.width() - 1))
                image_y = max(0, min(image_y, self.image.height() - 1))

            # Update bod v data model
            point = self.vertebral_points.get(self.dragging_point_id)
            if point:
                point.x = image_x
                point.y = image_y
                # Emit signal - tabulka se updatuje
                self.pointMoved.emit(self.dragging_point_id, image_x, image_y)
                logger.debug(f"Canvas: point {self.dragging_point_id} moved to ({image_x:.1f}, {image_y:.1f})")
            else:
                logger.warning(f"Canvas: point {self.dragging_point_id} NOT FOUND in vertebral_points!")

            self.update()
            return

        # Pan mode (původní logika)
        if self.dragging and self.drag_start_pos:
            # Pan mode: move canvas
            delta = QPoint(event.position().x(), event.position().y()) - self.drag_start_pos
            self.pan_offset += delta
            self._clamp_pan_offset()  # Aplikuj limity aby se obrázek nepánoval mimo canvas
            self.drag_start_pos = QPoint(event.position().x(), event.position().y())
            logger.debug(f"Canvas: panning, offset={self.pan_offset}")
            self.update()

    def mouseReleaseEvent(self, event):
        """Ukonči pan nebo tahání bodu"""
        if event.button() == Qt.MiddleButton or event.button() == Qt.LeftButton:
            # Phase 3: Stop point dragging
            if self.dragging_point:
                self.dragging_point = False
                self.dragging_point_id = None
                logger.debug("Canvas: point drag finished")

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
        """Klávesnice pro pan + point editing"""
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self.space_pressed = True
            logger.debug("Canvas: Space pressed - pan mode ON")
        elif event.key() == Qt.Key_Escape:
            self.selected_point_id = None
            self.update()
        # Phase 3.2: Arrow keys pro posun bodu
        elif self.selected_point_id and not event.isAutoRepeat():
            point = self.vertebral_points.get(self.selected_point_id)
            if point:
                # Zjisti step (1 nebo 5)
                step = ARROW_KEY_STEP_SHIFT if event.modifiers() & Qt.ShiftModifier else ARROW_KEY_STEP # Pixel per arrow key press


                # Zjisti směr
                delta_x, delta_y = 0, 0
                if event.key() == Qt.Key_Left:
                    delta_x = -step
                elif event.key() == Qt.Key_Right:
                    delta_x = step
                elif event.key() == Qt.Key_Up:
                    delta_y = -step
                elif event.key() == Qt.Key_Down:
                    delta_y = step

                # Pokud se pohybujeme
                if delta_x != 0 or delta_y != 0:
                    # Update bod
                    new_x = point.x + delta_x
                    new_y = point.y + delta_y

                    # Bounds check
                    if self.image:
                        new_x = max(0, min(new_x, self.image.width() - 1))
                        new_y = max(0, min(new_y, self.image.height() - 1))

                    point.x = new_x
                    point.y = new_y

                    # Emit signal
                    self.pointMoved.emit(self.selected_point_id, new_x, new_y)
                    logger.debug(f"Canvas: point {self.selected_point_id} moved by arrow to ({new_x:.1f}, {new_y:.1f})")

                    self.update()
                    return

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

    def focus_on_point(self, point_id: str):
        """Auto-focus na bod: zoomuj a panuj aby byl bod uprostřed canvasu

        Použití: když se bod vybere v tabulce, chceme vidět ho v centru
        """
        if point_id not in self.vertebral_points:
            logger.warning(f"Canvas: focus_on_point - bod {point_id} nenalezen")
            return

        point = self.vertebral_points[point_id]

        # Nastavit zoom na 2.5x pro pohodlné editování
        self.zoom_level = 2.5
        logger.debug(f"Canvas: focus_on_point {point_id} - zoom set to 2.5x")

        canvas_size = self.size()
        image_size = self.image.size() if self.image else None
        if not image_size:
            return

        scaled_w = int(image_size.width() * self.zoom_level)
        scaled_h = int(image_size.height() * self.zoom_level)

        # Převeď bod z image coords na canvas coords aby byl uprostřed
        # Bod v image je (point.x, point.y)
        # Chceme aby byl na (canvas_width/2, canvas_height/2)

        # Pan offset se kalkuluje takto:
        # canvas_x = image_x * zoom_level + pan_offset.x()
        # Chceme: canvas_width/2 = point.x * zoom_level + pan_offset.x()
        # Takže: pan_offset.x() = canvas_width/2 - point.x * zoom_level

        target_pan_x = canvas_size.width() // 2 - int(point.x * self.zoom_level)
        target_pan_y = canvas_size.height() // 2 - int(point.y * self.zoom_level)

        self.pan_offset.setX(target_pan_x)
        self.pan_offset.setY(target_pan_y)

        # Aplikuj smooth bounds clamping
        self._clamp_pan_offset()

        logger.debug(f"Canvas: focus_on_point {point_id} ({point.x:.1f}, {point.y:.1f}) - pan set to {self.pan_offset}")
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
        self.canvas.pointMoved.connect(self._on_point_moved)  # Phase 3.4: Relay pointMoved signal
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
        """Canvas vybral bod -> emit signal + auto-focus"""
        self.pointSelected.emit(point_id)
        # Auto-focus: zoomuj a centruj na bod
        self.canvas.focus_on_point(point_id)

    def _on_point_moved(self, point_id: str, x: float, y: float):
        """Phase 3.4: Canvas pohyboval bodem -> relay signal"""
        self.pointMoved.emit(point_id, x, y)

    def select_point(self, point_id: str):
        """Highlight bod z external source (např. tabulka)"""
        self.canvas.select_point(point_id)
        # Auto-focus: zoomuj a centruj na bod
        self.canvas.focus_on_point(point_id)

    def deselect_point(self):
        """Deselect current point"""
        self.canvas.deselect_point()

    def update_point_position(self, point_id: str, x: float, y: float):
        """Update bod z external source"""
        self.canvas.update_point_position(point_id, x, y)

    def reset_view(self):
        """Reset zoom a pan"""
        self.canvas.reset_zoom_and_pan()
