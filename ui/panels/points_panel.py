"""Panel pro zobrazení vertebrálních bodů"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
)

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QPushButton

from core.models import Point, VertebralPoints
from logger import logger


class VertebralPointItem(QFrame):
    """Widget pro zobrazení jednoho obratle s jeho body"""

    # Signal emitovaný když se klikne na bod
    pointSelected = Signal(str)  # point_id

    def __init__(self, vertebral: VertebralPoints):
        super().__init__()
        self.vertebral = vertebral
        self.selected_point_id = None  # Aktuálně vybraný bod
        self.point_buttons = {}  # point_id -> button widget

        # Výchozí styl
        self.default_style = "background-color: #e8e8e8; border-radius: 10px; padding: 5px;"
        self.selected_style = "background-color: #d4edda; border: 2px solid #28a745; border-radius: 10px; padding: 5px;"
        self.setStyleSheet(self.default_style)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        # Levá strana: Nadpis a souřadnice bodů
        left_layout = QVBoxLayout()
        left_layout.setSpacing(4)

        # Nadpis obratle
        title_label = QLabel(vertebral.name)
        title_label.setStyleSheet(
            "font-weight: bold; font-size: 18px; color: #333; margin-bottom: 4px;"
        )
        left_layout.addWidget(title_label)

        # Barvy pro různé typy bodů
        point_colors = {
            'TL': QColor(255, 192, 203),      # Pink - Top Left
            'TR': QColor(144, 238, 144),      # Light Green - Top Right
            'BL': QColor(173, 216, 230),      # Light Blue - Bottom Left
            'BR': QColor(255, 255, 153),      # Light Yellow - Bottom Right
            'C': QColor(255, 200, 124),       # Light Orange - Centroid
        }

        # Dynamicky zobraz všechny body pro tento obratel
        for point in vertebral.points:
            # Extrahuj zkrácení z labelu (poslední část - "C2 top left" -> "TL")
            point_abbr = self._get_point_abbreviation(point.label)
            color = point_colors.get(point_abbr, QColor(200, 200, 200))  # Default grey

            row_layout = QHBoxLayout()
            row_layout.setSpacing(6)
            row_layout.setContentsMargins(0, 0, 0, 0)

            # Barevný indikátor
            indicator = QFrame()
            indicator.setFixedSize(16, 16)
            indicator.setStyleSheet(
                f"background-color: {color.name()}; border: 1px solid #999; border-radius: 8px;"
            )
            row_layout.addWidget(indicator)

            # Text s souřadnicemi - KLIKATELNÉ TLAČÍTKO
            text = f"{point_abbr}: X: {point.x:.2f} Y: {point.y:.2f}"
            point_button = QPushButton(text)
            point_button.setFlat(True)
            point_button.setStyleSheet("""
                QPushButton {
                    color: #666;
                    font-size: 12px;
                    text-align: left;
                    padding: 2px 4px;
                    border: 1px solid transparent;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #f0f0f0;
                    border: 1px solid #ccc;
                }
            """)
            point_button.setCursor(Qt.PointingHandCursor)

            # Store button for later reference
            point_id = point.label  # Use point.label as the identifier
            self.point_buttons[point_id] = point_button

            # Connect signal
            point_button.clicked.connect(lambda checked=False, pid=point_id: self._on_point_clicked(pid))

            row_layout.addWidget(point_button)
            row_layout.addStretch()

            left_layout.addLayout(row_layout)

        layout.addLayout(left_layout, stretch=1)

    @staticmethod
    def _get_point_abbreviation(label: str) -> str:
        """Extrahuj zkrácení bodu z labelu

        Args:
            label: Plný label (např. "C2 top left", "C3 bottom right", "C4 centroid")

        Returns:
            Zkrácení (TL, TR, BL, BR, C)
        """
        label_lower = label.lower()

        if 'centroid' in label_lower:
            return 'C'
        elif 'top left' in label_lower:
            return 'TL'
        elif 'top right' in label_lower:
            return 'TR'
        elif 'bottom left' in label_lower:
            return 'BL'
        elif 'bottom right' in label_lower:
            return 'BR'
        else:
            return '?'

    def update_data(self, vertebral: VertebralPoints):
        """Aktualizuj data obratle"""
        self.vertebral = vertebral
        self.update()

    def _on_point_clicked(self, point_id: str):
        """Bod byl vybrán"""
        self.selected_point_id = point_id
        self.pointSelected.emit(point_id)
        # Vizuálně zvýrazni bod
        self._update_point_highlight()
        logger.debug(f"VertebralPointItem: point {point_id} selected")

    def select_point(self, point_id: str):
        """Zvýrazni bod (voláno z canvas nebo programově)"""
        self.selected_point_id = point_id
        self._update_point_highlight()

    def deselect_point(self):
        """Zrušit zvýraznění"""
        self.selected_point_id = None
        self._update_point_highlight()

    def _update_point_highlight(self):
        """Aktualizuj vizuální styl dle vybraného bodu"""
        for point_id, button in self.point_buttons.items():
            if point_id == self.selected_point_id:
                # Vybraný bod - tmavší barva + border
                button.setStyleSheet("""
                    QPushButton {
                        color: #333;
                        font-size: 12px;
                        font-weight: bold;
                        text-align: left;
                        padding: 2px 4px;
                        background-color: #fff3cd;
                        border: 2px solid #ffc107;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #ffe69c;
                        border: 2px solid #ff9800;
                    }
                """)
            else:
                # Normální bod
                button.setStyleSheet("""
                    QPushButton {
                        color: #666;
                        font-size: 12px;
                        text-align: left;
                        padding: 2px 4px;
                        border: 1px solid transparent;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #f0f0f0;
                        border: 1px solid #ccc;
                    }
                """)


class VertebralPointsPanel(QFrame):
    """Panel pro zobrazení všech bodů obratlů"""

    # Signal emitovaný když uživatel vybere bod v tabulce
    pointSelected = Signal(str)  # point_id

    def __init__(self):
        super().__init__()
        self.vertebrals: list[VertebralPoints] = []
        self.vertebral_items = []  # Pro přístup k jednotlivým položkám
        self.init_ui()
        # Bez sample dat - čeka na set_vertebral_data()

    def init_ui(self):
        """Inicializuj UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Scrollovatelná oblast pro body
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: white;
            }
            QScrollBar:vertical {
                background-color: transparent;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #d0d0d0;
                border-radius: 5px;
                min-height: 20px;
                margin: 2px 2px 2px 2px;
                border: none;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #999;
            }
            QScrollBar::handle:vertical:pressed {
                background-color: #666;
            }
            QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
            QScrollBar::add-line:vertical {
                border: none;
                background: none;
            }
        """)

        # Container pro položky
        self.container_widget = QWidget()
        self.container_widget.setStyleSheet("background-color: white;")
        self.container_layout = QVBoxLayout(self.container_widget)
        self.container_layout.setSpacing(12)
        self.container_layout.setContentsMargins(8, 8, 8, 8)

        scroll_area.setWidget(self.container_widget)
        layout.addWidget(scroll_area, stretch=1)

    def set_vertebral_data(self, vertebrals: list[VertebralPoints]):
        """Nastav data obratlů a aktualizuj zobrazení"""
        self.vertebrals = vertebrals
        self.refresh_display()

    def refresh_display(self):
        """Obnovit zobrazení všech obratlů"""
        # Vyčistit starý obsah
        self.vertebral_items = []
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Přidat nové položky
        for vertebral in self.vertebrals:
            item = VertebralPointItem(vertebral)
            # Propoj signal - když se klikne na bod v tabulce, vylej signal nahoru
            item.pointSelected.connect(self._on_point_selected)
            self.vertebral_items.append(item)
            self.container_layout.addWidget(item)

        self.container_layout.addStretch()

    def _on_point_selected(self, point_id: str):
        """Bod byl vybrán v tabulce"""
        self.pointSelected.emit(point_id)
        logger.debug(f"VertebralPointsPanel: point {point_id} selected")

    def select_point(self, point_id: str):
        """Zvýrazni bod programově (voleno z canvas)"""
        # Najdi bod v items a zvýrazni ho
        for item in self.vertebral_items:
            if point_id in item.point_buttons:
                item.select_point(point_id)
            else:
                item.deselect_point()

    def deselect_all(self):
        """Zrušit zvýraznění všech bodů"""
        for item in self.vertebral_items:
            item.deselect_point()