from dataclasses import dataclass, field
from points_panel import *
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
)

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap, QDragEnterEvent, QDropEvent, QColor


@dataclass
class Point:
    """Souřadnice bodu"""

    x: float = 0.0
    y: float = 0.0


@dataclass
class VertebralPoints:
    """Body rohů obratlů (LT, RT, LB, RB - Left/Right Top/Bottom)"""

    name: str  # C2, C3, C4, ...
    lt: Point = field(default_factory=Point)  # Left Top
    rt: Point = field(default_factory=Point)  # Right Top
    lb: Point = field(default_factory=Point)  # Left Bottom
    rb: Point = field(default_factory=Point)  # Right Bottom


class VertebralPointItem(QFrame):
    """Widget pro zobrazení jednoho obratlů s jeho body"""

    def __init__(self, vertebral: VertebralPoints):
        super().__init__()
        self.vertebral = vertebral
        self.setStyleSheet(
            "background-color: #e8e8e8; border-radius: 10px; padding: 5px;"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        # Levá strana: Souřadnice bodů
        left_layout = QVBoxLayout()
        left_layout.setSpacing(4)

        # Nadpis obratlů
        title_label = QLabel(vertebral.name)
        title_label.setStyleSheet(
            "font-weight: bold; font-size: 18px; color: #333; margin-bottom: 4px;"
        )
        left_layout.addWidget(title_label)

        # Body s barvnými indikátory
        points_data = [
            ("LT", vertebral.lt, QColor(255, 192, 203)),  # Pink
            ("RT", vertebral.rt, QColor(144, 238, 144)),  # Light Green
            ("LB", vertebral.lb, QColor(173, 216, 230)),  # Light Blue
            ("RB", vertebral.rb, QColor(255, 255, 153)),  # Light Yellow
        ]

        for point_name, point, color in points_data:
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

            # Text s souřadnicemi
            text = f"{point_name}: X: {point.x:.2f} Y: {point.y:.2f}"
            label = QLabel(text)
            label.setStyleSheet("color: #666; font-size: 12px;")
            row_layout.addWidget(label)
            row_layout.addStretch()

            left_layout.addLayout(row_layout)

        layout.addLayout(left_layout, stretch=1)

    def update_data(self, vertebral: VertebralPoints):
        """Aktualizuj data obratlů"""
        self.vertebral = vertebral
        self.update()


class VertebralPointsPanel(QFrame):
    """Panel pro zobrazení všech bodů obratlů"""

    def __init__(self):
        super().__init__()
        self.vertebrals: list[VertebralPoints] = []
        self.init_ui()
        # Inicializuj s ukázkovými daty
        self.set_sample_data()

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

    def set_sample_data(self):
        """Nastav ukázková data pro testování"""
        sample_vertebrals = [
            VertebralPoints(
                name="C2",
                lt=Point(125.50, 180.75),
                rt=Point(225.30, 182.10),
                lb=Point(128.80, 265.40),
                rb=Point(222.60, 267.85),
            ),
            VertebralPoints(
                name="C3",
                lt=Point(130.20, 275.60),
                rt=Point(220.90, 278.30),
                lb=Point(132.50, 360.15),
                rb=Point(218.75, 362.95),
            ),
            VertebralPoints(
                name="C4",
                lt=Point(128.95, 370.10),
                rt=Point(222.15, 372.80),
                lb=Point(131.60, 455.25),
                rb=Point(219.40, 458.05),
            ),
            VertebralPoints(
                name="C5",
                lt=Point(129.75, 465.50),
                rt=Point(221.25, 468.20),
                lb=Point(132.35, 550.30),
                rb=Point(218.85, 553.10),
            ),
            VertebralPoints(
                name="C6",
                lt=Point(129.75, 465.50),
                rt=Point(221.25, 468.20),
                lb=Point(132.35, 550.30),
                rb=Point(218.85, 553.10),
            ),
            VertebralPoints(
                name="C7",
                lt=Point(129.75, 465.50),
                rt=Point(221.25, 468.20),
                lb=Point(132.35, 550.30),
                rb=Point(218.85, 553.10),
            ),
        ]
        self.set_vertebral_data(sample_vertebrals)

    def set_vertebral_data(self, vertebrals: list[VertebralPoints]):
        """Nastav data obratlů a aktualizuj zobrazení"""
        self.vertebrals = vertebrals
        self.refresh_display()

    def refresh_display(self):
        """Obnovit zobrazení všech obratlů"""
        # Vyčistit starý obsah
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Přidat nové položky
        for vertebral in self.vertebrals:
            item = VertebralPointItem(vertebral)
            self.container_layout.addWidget(item)

        self.container_layout.addStretch()