import sys
from dataclasses import dataclass, field
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFrame,
    QTabWidget,
    QListWidget,
    QListWidgetItem,
    QTabBar,
    QStackedWidget,
    QMenu,
    QMenuBar,
    QScrollArea,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QColor


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

        # Dolní tlačítka
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(5, 5, 5, 5)

        self.confirm_button = QPushButton("Potvrdit body")
        self.confirm_button.setFixedHeight(40)
        self.confirm_button.setCursor(Qt.PointingHandCursor)
        self.confirm_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 12px;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)

        button_layout.addWidget(self.confirm_button)
        layout.addLayout(button_layout)

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


class SessionScreen(QWidget):
    """Jednotlivá session obrazovka s X-ray a workflow step panelem"""

    def __init__(self, session_name):
        super().__init__()
        self.session_name = session_name
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # ===== LEFT: X-RAY DISPLAY AREA =====
        xray_frame = QFrame()
        xray_frame.setStyleSheet("background-color: white;")
        xray_layout = QVBoxLayout(xray_frame)
        xray_label = QLabel(f"X-ray Display\n({self.session_name})")
        xray_label.setAlignment(Qt.AlignCenter)
        xray_label.setStyleSheet("color: #666; font-size: 14px;")
        xray_layout.addWidget(xray_label)
        layout.addWidget(xray_frame, stretch=1)

        # ===== RIGHT: WORKFLOW STEP PANEL =====
        workflow_frame = QFrame()
        workflow_frame.setStyleSheet("background-color: #f9f9f9;")
        workflow_frame.setFixedWidth(300)
        workflow_layout = QVBoxLayout(workflow_frame)
        workflow_layout.setContentsMargins(5, 5, 5, 5)
        workflow_layout.setSpacing(5)

        # Top menu bar (Settings, Body, Results)
        menu_layout = QHBoxLayout()
        self.menu_buttons = {}
        menu_items = ["Nastavení", "Body", "Výsledky"]

        for i, menu_item in enumerate(menu_items):
            btn = QPushButton(menu_item)
            btn.setFixedHeight(28)
            btn.setCheckable(True)
            if i == 0:  # Prvni je defaultne vybran
                btn.setChecked(True)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #e0e0e0;
                    border: 1px solid #999;
                    border-radius: 3px;
                    color: #333;
                }
                QPushButton:hover {
                    background-color: #d0d0d0;
                }
                QPushButton:checked {
                    background-color: #45a049;
                    color: white;
                    font-weight: bold;
                }
            """)
            btn.clicked.connect(lambda checked, idx=i: self.show_content(idx))
            self.menu_buttons[menu_item] = btn
            menu_layout.addWidget(btn)

        workflow_layout.addLayout(menu_layout)

        # ===== STACKED WIDGET PRO OBSAH =====
        self.stacked_widget = QStackedWidget()

        # Content 1: Nastavení
        content_frame_1 = QFrame()
        content_frame_1.setStyleSheet(
            "border: 1px solid #ddd; background-color: white;"
        )
        content_layout_1 = QVBoxLayout(content_frame_1)
        content_label_1 = QLabel("Výběr modelu a parametrů")
        content_label_1.setAlignment(Qt.AlignCenter)
        content_label_1.setStyleSheet("color: #666; font-size: 12px;")
        content_layout_1.addWidget(content_label_1)

        # Inference button - uložení jako self.inference_button pro pozdější použití
        self.inference_button = QPushButton("Spustit Inferenci")
        self.inference_button.setFixedHeight(40)
        self.inference_button.setCursor(Qt.PointingHandCursor)
        self.inference_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 12px;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        # Placeholder pro budoucí funkcionalitu - lze přidat connect k metodě
        # self.inference_button.clicked.connect(self.on_inference_clicked)

        content_layout_1.addStretch()
        content_layout_1.addWidget(self.inference_button)
        self.stacked_widget.addWidget(content_frame_1)

        # Content 2: Body
        content_frame_2 = QFrame()
        content_frame_2.setStyleSheet("background-color: white;")
        content_layout_2 = QVBoxLayout(content_frame_2)
        content_layout_2.setContentsMargins(0, 0, 0, 0)
        content_layout_2.setSpacing(0)

        # Použij nový VertebralPointsPanel
        self.vertebral_panel = VertebralPointsPanel()
        content_layout_2.addWidget(self.vertebral_panel)

        self.stacked_widget.addWidget(content_frame_2)

        # Content 3: Výsledky
        content_frame_3 = QFrame()
        content_frame_3.setStyleSheet(
            "border: 1px solid #ddd; background-color: white;"
        )
        content_layout_3 = QVBoxLayout(content_frame_3)
        content_label_3 = QLabel("Výsledky analýzy")
        content_label_3.setAlignment(Qt.AlignCenter)
        content_label_3.setStyleSheet("color: #666; font-size: 12px;")
        content_layout_3.addWidget(content_label_3)
        # export metrics button - uložení jako self.export_metrics_button pro pozdější použití
        self.export_metrics_button = QPushButton("Exportovat")
        self.export_metrics_button.setFixedHeight(40)
        self.export_metrics_button.setCursor(Qt.PointingHandCursor)
        self.export_metrics_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 12px;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        # Placeholder pro budoucí funkcionalitu - lze přidat connect k metodě
        # self.export_metrics_button.clicked.connect(self.on_inference_clicked)

        content_layout_3.addStretch()
        content_layout_3.addWidget(self.export_metrics_button)

        self.stacked_widget.addWidget(content_frame_3)

        workflow_layout.addWidget(self.stacked_widget, stretch=1)
        layout.addWidget(workflow_frame)

    def show_content(self, index):
        """Zobraz obsah podle vybraného menu"""
        # Odznač všechna tlačítka
        for btn in self.menu_buttons.values():
            btn.setChecked(False)

        # Označ kliknuté tlačítko
        clicked_btn = list(self.menu_buttons.values())[index]
        clicked_btn.setChecked(True)

        # Změň stránku v stacked widgetu
        self.stacked_widget.setCurrentIndex(index)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DigiTech-Spiner")
        self.resize(1400, 800)
        self.session_counter = 0

        # ===== MENU BAR =====
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")
        new_blank_session_action = file_menu.addAction("New Blank Session")
        new_blank_session_action.triggered.connect(self.add_new_session)
        new_session_action = file_menu.addAction("New Session")
        new_session_action.triggered.connect(self.add_new_session)
        file_menu.addSeparator()
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

        # Help menu
        help_menu = menubar.addMenu("Help")
        help_menu.addAction("About")
        help_menu.addAction("Documentation")

        # ===== MAIN WIDGET =====
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ===== SESSION TABS (jako v prohlížeči) =====
        self.session_tabs = QTabWidget()
        self.session_tabs.setTabsClosable(True)
        self.session_tabs.tabCloseRequested.connect(self.close_session_tab)

        # Přidej první session
        self.add_new_session()

        main_layout.addWidget(self.session_tabs)

        ## nepoužívá se / nedává smysl
        # # ===== BOTTOM BAR =====
        # bottom_frame = QFrame()
        # bottom_frame.setStyleSheet("border-top: 1px solid #ccc; background-color: #f5f5f5;")
        # bottom_layout = QHBoxLayout(bottom_frame)
        # bottom_layout.setContentsMargins(10, 5, 10, 5)

        # bottom_layout.addStretch()

        # btn_submit = QPushButton("Aquit")
        # btn_submit.setFixedWidth(100)
        # btn_submit.setStyleSheet("""
        #     QPushButton {
        #         background-color: #4CAF50;
        #         color: white;
        #         font-weight: bold;
        #         border-radius: 4px;
        #         padding: 5px;
        #     }
        #     QPushButton:hover {
        #         background-color: #45a049;
        #     }
        # """)
        # bottom_layout.addWidget(btn_submit)

        # main_layout.addWidget(bottom_frame)

    def add_new_session(self):
        """Přidej novou session jako tab"""
        self.session_counter += 1
        session_name = f"Session {self.session_counter}"
        session_widget = SessionScreen(session_name)
        self.session_tabs.addTab(session_widget, session_name)
        self.session_tabs.setCurrentIndex(self.session_tabs.count() - 1)

    def close_session_tab(self, index):
        """Zavři session tab"""
        if self.session_tabs.count() > 1:
            self.session_tabs.removeTab(index)
        else:
            self.close()
            pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
