from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFrame,
    QStackedWidget,
    QFileDialog,
    QScrollArea,
    QComboBox
)

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap, QDragEnterEvent, QDropEvent, QColor


from ui.panels.drag_drop_frame import DragDropFrame
from ui.panels.points_panel import VertebralPointsPanel
from ui.panels.image_canvas_panel import ImageCanvasPanel
from core.models import MLInferenceSimulator
from core.io import InferenceOutputHandler
from config import POINT_COLORS, POINT_COLORS_MODEL_2
from logger import logger


class SessionScreen(QWidget):
    """Jednotlivá session obrazovka s X-ray a workflow step panelem"""
    def __init__(self, session_name):
        super().__init__()
        self.session_name = session_name

        # State variables
        self.image_loaded = False
        self.image_confirmed = False  # Nový stav - potvrzení snímku
        self.inference_completed = False
        self.points_confirmed = False

        # Inference setup
        self.current_image_path = None
        self.ml_inference = None  # ML model simulator
        self.io_handler = InferenceOutputHandler()  # Handler pro zpracování výstupu

        # IMPORTANT: Uložiště výsledků inference per-model
        # Format: {"model 1": vertebral_results_list, "model 2": vertebral_results_list, ...}
        self.inference_results_by_model = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # Žádné margins - canvas na plno!
        layout.setSpacing(0)  # Žádná mezera

        # LEFT: Drag-drop frame s canvas
        self.xray_frame = DragDropFrame()
        self.xray_frame.image_loaded.connect(self.on_image_loaded)
        self.xray_frame.setStyleSheet("border: 2px solid #999; background-color: white; margin: 0px; padding: 0px;")
        self.xray_frame.setAcceptDrops(True)  # Drag-drop aktivní
        xray_layout = QVBoxLayout(self.xray_frame)
        xray_layout.setContentsMargins(0, 0, 0, 0)
        xray_layout.setSpacing(0)

        # Canvas - bude hlavní plocha pro zobrazení obrázku a bodů
        self.canvas_panel = ImageCanvasPanel()
        self.canvas_panel.pointSelected.connect(self._on_canvas_point_selected)

        # Widget pro text a tlačítko (overlay) - zobrazuje se na začátku
        overlay_widget = QWidget()
        overlay_layout = QVBoxLayout(overlay_widget)
        overlay_layout.setContentsMargins(10, 10, 10, 10)
        overlay_layout.addStretch()

        # Top bar - text a tlačítko pro výběr souboru (vycentrovaný)
        top_bar = QHBoxLayout()
        top_bar.addStretch()

        self.xray_label = QLabel("Drag a drop snímek sem")
        self.xray_label.setStyleSheet("color: #666; font-size: 12px; font-weight: bold;")
        top_bar.addWidget(self.xray_label)

        # Malé tlačítko vedle textu
        self.open_file_btn = QPushButton("📁")
        self.open_file_btn.setFixedSize(32, 32)
        self.open_file_btn.setCursor(Qt.PointingHandCursor)
        self.open_file_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        self.open_file_btn.clicked.connect(self.on_open_file_dialog)
        top_bar.addWidget(self.open_file_btn)
        top_bar.addStretch()

        overlay_layout.addLayout(top_bar)
        overlay_layout.addStretch()

        # Stacked widget - zobrazuj buď overlay (na začátku) nebo canvas (po inference)
        self.xray_stack = QStackedWidget()
        self.xray_stack.setContentsMargins(0, 0, 0, 0)  # CRITICAL: Žádné margins
        self.xray_stack.setStyleSheet("margin: 0px; padding: 0px; border: 0px;")  # CRITICAL: Žádné padding
        self.xray_stack.addWidget(overlay_widget)  # Index 0 - overlay
        self.xray_stack.addWidget(self.canvas_panel)  # Index 1 - canvas
        self.xray_stack.setCurrentIndex(0)  # Zobraz overlay na začátku
        xray_layout.addWidget(self.xray_stack, stretch=1)

        layout.addWidget(self.xray_frame, stretch=2)  # Canvas = 2/3 plochy

        # Uložit pixmap pro později (po inference)
        self.current_pixmap = None

        # ===== RIGHT: WORKFLOW STEP PANEL =====
        self.workflow_frame = QFrame()
        self.workflow_frame.setStyleSheet(
            "border: 1px solid #ccc; background-color: #f9f9f9;"
        )
        # Nastavit width - preferuj malý, ale expanduj pokud je prostor
        self.workflow_frame.setMinimumWidth(280)
        # NO MAXIMUM WIDTH - nechť se dá expandovat
        workflow_layout = QVBoxLayout(self.workflow_frame)
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
            elif i == 1:  # Body - zakázány do inference
                btn.setEnabled(False)
            elif i == 2:  # Výsledky - zakázány do potvrzení bodů
                btn.setEnabled(False)

            btn.setStyleSheet("""
                QPushButton {
                    background-color: #e0e0e0;
                    border: 1px solid #999;
                    border-radius: 3px;
                }
                QPushButton:hover:enabled {
                    background-color: #d0d0d0;
                }
                QPushButton:checked {
                    background-color: #4CAF50;
                    color: white;
                    font-weight: bold;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                    color: #888888;
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
            "border: 1px solid #ddd;" \
            " background-color: white;"
        )
        content_layout_1 = QVBoxLayout(content_frame_1)

        content_label_1 = QLabel("Výběr snímku")
        content_label_1.setAlignment(Qt.AlignCenter)
        content_label_1.setStyleSheet("color: #666; font-size: 12px; font-weight: bold;")
        content_layout_1.addWidget(content_label_1)

        # 2 tlačítka - Smazat snímek a Potvrdit snímek
        buttons_layout = QHBoxLayout()

        self.delete_image_btn = QPushButton("�️ Smazat")
        self.delete_image_btn.setFixedHeight(28)
        self.delete_image_btn.setCursor(Qt.PointingHandCursor)
        self.delete_image_btn.setEnabled(False)  # Disabled dokud není snímek
        self.delete_image_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                font-weight: bold;
                font-size: 10px;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton:hover:enabled {
                background-color: #DA190B;
            }
            QPushButton:pressed:enabled {
                background-color: #BA000D;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #888888;
            }
        """)
        self.delete_image_btn.clicked.connect(self.on_delete_image_clicked)
        buttons_layout.addWidget(self.delete_image_btn)

        self.confirm_image_btn = QPushButton("✓ Potvrdit")
        self.confirm_image_btn.setFixedHeight(28)
        self.confirm_image_btn.setCursor(Qt.PointingHandCursor)
        self.confirm_image_btn.setEnabled(False)  # Disabled dokud není snímek
        self.confirm_image_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 10px;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton:hover:enabled {
                background-color: #45a049;
            }
            QPushButton:pressed:enabled {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #888888;
            }
        """)
        self.confirm_image_btn.clicked.connect(self.on_confirm_image_clicked)
        buttons_layout.addWidget(self.confirm_image_btn)

        content_layout_1.addLayout(buttons_layout)

        # Spacer
        content_layout_1.addSpacing(10)

        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        content_layout_1.addWidget(separator)

        # Spacer
        content_layout_1.addSpacing(10)

        # Dropdown pro výběr modelu (disabled dokud se nepotvrdí snímek)
        model_label = QLabel("Model:")
        model_label.setStyleSheet("color: #333; font-size: 11px; font-weight: bold;")
        content_layout_1.addWidget(model_label)

        self.model_combo = QComboBox()
        self.model_combo.addItems(["model 1", "model 2"])
        self.model_combo.setCurrentIndex(0)  # Default na model 1
        self.model_combo.setFixedHeight(32)
        self.model_combo.setFixedWidth(150)
        self.model_combo.setEnabled(False)  # Disabled dokud se nepotvrdí snímek
        self.model_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 4px;
                background-color: white;
                color: #333;
                font-size: 12px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                color: #333;
                selection-background-color: #4CAF50;
            }
            QComboBox:disabled {
                background-color: #f5f5f5;
                color: #999;
            }
        """)
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        content_layout_1.addWidget(self.model_combo)

        # Spacer
        content_layout_1.addSpacing(10)

        # Parameters box - viditelný jen pro model 2
        self.params_label = QLabel("Nastavení parametrů:")
        self.params_label.setStyleSheet("color: #333; font-size: 11px; font-weight: bold;")
        self.params_label.setVisible(False)
        content_layout_1.addWidget(self.params_label)

        self.params_box = QFrame()
        self.params_box.setStyleSheet("border: 1px solid #ccc; background-color: #f9f9f9; border-radius: 4px;")
        self.params_box.setMinimumHeight(80)
        params_box_layout = QVBoxLayout(self.params_box)
        params_box_layout.setContentsMargins(8, 8, 8, 8)
        params_placeholder = QLabel("Zde budou parametry pro model 2")
        params_placeholder.setAlignment(Qt.AlignCenter)
        params_placeholder.setStyleSheet("color: #999; font-size: 10px;")
        params_box_layout.addWidget(params_placeholder)
        self.params_box.setVisible(False)
        content_layout_1.addWidget(self.params_box)

        # Spacer
        content_layout_1.addStretch()


        # Inference button - uložení jako self.inference_button pro pozdější použití
        self.inference_button = QPushButton("Spustit Inferenci")
        self.inference_button.setFixedHeight(40)
        self.inference_button.setCursor(Qt.PointingHandCursor)
        self.inference_button.setEnabled(False)  # Zakázáno na začátku
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
            QPushButton:hover:enabled {
                background-color: #45a049;
            }
            QPushButton:pressed:enabled {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #888888;
            }
        """)
        # Propoj s metodou pro spuštění inference
        self.inference_button.clicked.connect(self.on_inference_clicked)



        content_layout_1.addStretch()
        content_layout_1.addWidget(self.inference_button)
        self.stacked_widget.addWidget(content_frame_1)


        # Content 2: Body - pouze tabulka s body (canvas je v main xray_frame)
        content_frame_2 = QFrame()
        content_frame_2.setStyleSheet(
            "border: 1px solid #ddd;" \
            " background-color: white;"
        )
        content_layout_2_main = QVBoxLayout(content_frame_2)
        content_layout_2_main.setContentsMargins(5, 5, 5, 5)
        content_layout_2_main.setSpacing(5)

        # Nadpis
        content_label_2 = QLabel("Vertebrální body")
        content_label_2.setStyleSheet("color: #333; font-size: 12px; font-weight: bold;")
        content_layout_2_main.addWidget(content_label_2)

        # Points table
        self.vertebral_panel = VertebralPointsPanel()
        content_layout_2_main.addWidget(self.vertebral_panel, stretch=1)

        # confirm points button - bottom
        self.confirm_points_button = QPushButton("Potvrdit body")
        self.confirm_points_button.setFixedHeight(40)
        self.confirm_points_button.setCursor(Qt.PointingHandCursor)
        self.confirm_points_button.setStyleSheet("""
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
        self.confirm_points_button.clicked.connect(self.on_confirm_points_clicked)
        content_layout_2_main.addWidget(self.confirm_points_button)

        self.stacked_widget.addWidget(content_frame_2)


        # Content 3: Výsledky =
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
        layout.addWidget(self.workflow_frame, stretch=1)  # Menu = 1/3 plochy

    def show_content(self, index):
        """Zobraz obsah podle vybraného menu - ale jen pokud jsou splněny podmínky"""
        menu_names = ["Nastavení", "Body", "Výsledky"]

        # Pokud chceš jít na Body, musí být inference hotova
        if index == 1 and not self.inference_completed:
            # Odznač a zůstaň na Nastavení
            for btn in self.menu_buttons.values():
                btn.setChecked(False)
            self.menu_buttons["Nastavení"].setChecked(True)
            self.stacked_widget.setCurrentIndex(0)
            return

        # Pokud chceš jít na Výsledky, musí být body potvrzeny
        if index == 2 and not self.points_confirmed:
            # Odznač a zůstaň na Body
            for btn in self.menu_buttons.values():
                btn.setChecked(False)
            self.menu_buttons["Body"].setChecked(True)
            self.stacked_widget.setCurrentIndex(1)
            return

        # Odznač všechna tlačítka
        for btn in self.menu_buttons.values():
            btn.setChecked(False)

        # Označ kliknuté tlačítko
        clicked_btn = list(self.menu_buttons.values())[index]
        clicked_btn.setChecked(True)

        # Změň stránku v stacked widgetu
        self.stacked_widget.setCurrentIndex(index)

        # Řídí viditelnost UI prvků podle tabu
        self.update_ui_visibility(index)

    def update_ui_visibility(self, current_tab_index):
        """Aktualizuj viditelnost prvků podle aktivního tabu"""
        # Jen v Nastavení je vidět button na výběr souboru a drag-drop
        is_settings = (current_tab_index == 0)
        # Tlačítko zmizí po nahrání obrázku
        self.open_file_btn.setVisible(is_settings and not self.image_loaded)
        self.xray_frame.setAcceptDrops(is_settings)

    def on_open_file_dialog(self):
        """Otevři file dialog pro výběr obrázku"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Otevřít snímek",
            "",
            "Obrázky (*.png *.jpg *.jpeg *.bmp *.gif);;Všechny soubory (*.*)"
        )
        if file_path:
            self.load_image(file_path)

    def load_image(self, file_path):
        """Načti snímek a zobraz ho + aktivuj potvrzovací tlačítka"""
        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            # Uložit cestu a pixmap pro pozdější použití v inference
            self.current_image_path = file_path
            self.current_pixmap = pixmap

            # Zobraz canvas s obrázkem (bez bodů - jen obrázek)
            self.canvas_panel.set_image(pixmap)
            self.xray_stack.setCurrentIndex(1)  # Zobraz canvas (místo overlay)

            # Markuj, že je snímek načten a aktivuj tlačítka na potvrzení
            self.image_loaded = True
            self.delete_image_btn.setEnabled(True)
            self.confirm_image_btn.setEnabled(True)

            logger.info(f"[Session {self.session_name}] Obrázek načten: {file_path} ({pixmap.width()}x{pixmap.height()})")

            logger.info(f"[Session {self.session_name}] Obrázek načten: {file_path} ({pixmap.width()}x{pixmap.height()})")

    def on_image_loaded(self, file_path):
        """Callback při drag-drop obrázku"""
        self.load_image(file_path)

    def on_delete_image_clicked(self):
        """Smaž aktuální snímek a resetuj stav"""
        self.current_pixmap = None
        self.current_image_path = None
        self.image_loaded = False
        self.image_confirmed = False

        # Reset tlačítek
        self.delete_image_btn.setEnabled(False)
        self.confirm_image_btn.setEnabled(False)

        # Reset dropdown a ostatního
        self.model_combo.setCurrentIndex(0)
        self.model_combo.setEnabled(False)
        self.params_label.setVisible(False)
        self.params_box.setVisible(False)

        # Reset workflow
        self.inference_button.setText("Spustit Inferenci")
        self.inference_button.setEnabled(False)
        self.inference_completed = False
        self.menu_buttons["Body"].setEnabled(False)
        self.menu_buttons["Výsledky"].setEnabled(False)
        self.points_confirmed = False

        # Zobraz overlay namísto canvas
        self.xray_stack.setCurrentIndex(0)

    def on_confirm_image_clicked(self):
        """Potvrď snímek - poté se už nepůjde měnit, ale zpřístupní se workflow"""
        self.image_confirmed = True

        # Zakáž tlačítka na správu snímku
        self.delete_image_btn.setEnabled(False)
        self.confirm_image_btn.setEnabled(False)

        # Zpřístupni výběr modelu
        self.model_combo.setEnabled(True)
        self.inference_button.setEnabled(True)

    def on_inference_clicked(self):
        """Spusť ML inference a zobraz výsledky v points panelu + canvas"""
        if not self.image_confirmed or not self.current_image_path:
            logger.warning(f"[Session {self.session_name}] Chyba: snímek není potvrzen nebo cesta chybí")
            return

        try:
            # Inicializuj ML model pokud neexistuje
            if self.ml_inference is None:
                self.ml_inference = MLInferenceSimulator()

            # Spusť inference - z uživatelské perspektivy to jen pracuje s obrázkem
            logger.info(f"[Session {self.session_name}] Inference spuštěna pro: {self.current_image_path}")
            inference_json = self.ml_inference.predict(self.current_image_path)

            if not inference_json:
                logger.error(f"[Session {self.session_name}] Inference vrátila None")
                return

            # Zpracuj JSON výstup na VertebralPoints pro UI
            vertebral_results = self.io_handler.parse_inference_output(inference_json)

            if vertebral_results:
                logger.info(f"[Session {self.session_name}] Inference úspěšná - {len(vertebral_results)} obratlů")

                # IMPORTANT: Ulož výsledky pro aktuální model
                current_model = self.model_combo.currentText()
                self.inference_results_by_model[current_model] = vertebral_results
                logger.info(f"[Session {self.session_name}] Výsledky uloženy pro model: {current_model}")

                # Předej výsledky canvas panelu (vlevo)
                if self.current_pixmap:
                    self.canvas_panel.set_image(self.current_pixmap)
                    self.canvas_panel.set_vertebral_points(vertebral_results)

                    # IMPORTANT: Nastav barvy podle modelu
                    if current_model == "model 2":
                        self.canvas_panel.set_point_colors(POINT_COLORS_MODEL_2)
                    else:
                        self.canvas_panel.set_point_colors(POINT_COLORS)

                    logger.info(f"[Session {self.session_name}] Canvas updated with image and {len(vertebral_results)} points")

                # Předej výsledky points panelu (vpravo - tabulka)
                self.vertebral_panel.set_vertebral_data(vertebral_results)

                self.inference_completed = True
            else:
                logger.warning(f"[Session {self.session_name}] Parsing vrátil prázdný seznam")
                return

            # Aktivuj Body po dokončení inference
            self.menu_buttons["Body"].setEnabled(True)
            self.inference_button.setText("✓ Inference hotova")
            self.inference_button.setEnabled(False)

            # Přepni na canvas (z overlay) - index 1
            self.xray_stack.setCurrentIndex(1)
            logger.debug(f"[Session {self.session_name}] Canvas switched from overlay")

            # Automaticky přepni do Body tabu
            self.menu_buttons["Body"].click()

        except Exception as e:
            logger.error(f"[Session {self.session_name}] Chyba při inference: {e}")
            import traceback
            traceback.print_exc()

    def on_confirm_points_clicked(self):
        """Obsluha kliknutí na 'Potvrdit body' - lze volat opakovaně"""
        logger.info(f"[Session {self.session_name}] Body potvrzeny")
        self.points_confirmed = True
        # Aktivuj Výsledky po potvrzení bodů
        self.menu_buttons["Výsledky"].setEnabled(True)

        # Automaticky přepni do Výsledky tabu
        self.menu_buttons["Výsledky"].click()

    def _on_canvas_point_selected(self, point_id: str):
        """Canvas vybral bod - zvýrazni ho v tabulce"""
        logger.debug(f"[Session {self.session_name}] Canvas selected point: {point_id}")
        # TODO: Phase 2 - highlight bod v VertebralPointsPanel

    def on_model_changed(self, model_name):
        """Změna modelu - aktualizuj UI a zpřístupni inference tlačítko"""
        logger.debug(f"[Session {self.session_name}] Model změněn na: {model_name}")

        # Zobraz/skryj parametry box podle modelu
        is_model_2 = (model_name == "model 2")
        self.params_label.setVisible(is_model_2)
        self.params_box.setVisible(is_model_2)

        # IMPORTANT: Pokud máme uložené výsledky pro tento model, zobraz je!
        if model_name in self.inference_results_by_model:
            logger.info(f"[Session {self.session_name}] Načítám uložené výsledky pro: {model_name}")
            vertebral_results = self.inference_results_by_model[model_name]

            # Zobraz výsledky v canvas
            if self.current_pixmap:
                self.canvas_panel.set_image(self.current_pixmap)
                self.canvas_panel.set_vertebral_points(vertebral_results)

                # IMPORTANT: Nastav barvy podle modelu
                if model_name == "model 2":
                    self.canvas_panel.set_point_colors(POINT_COLORS_MODEL_2)
                else:
                    self.canvas_panel.set_point_colors(POINT_COLORS)

            # Zobraz výsledky v tabulce
            self.vertebral_panel.set_vertebral_data(vertebral_results)

            # Aktivuj Body a Výsledky protože máme data
            self.menu_buttons["Body"].setEnabled(True)
            self.inference_completed = True
            self.inference_button.setText("✓ Inference hotova")
            self.inference_button.setEnabled(False)
            logger.info(f"[Session {self.session_name}] Výsledky načteny: {len(vertebral_results)} bodů")
        else:
            # Žádné uložené výsledky - resetuj UI a vymaz body z canvasu
            logger.info(f"[Session {self.session_name}] Žádné uložené výsledky pro: {model_name}")

            # VYMAZAT body z canvasu a tabulky
            self.canvas_panel.set_vertebral_points([])  # Vyčisti body na canvasu
            self.vertebral_panel.set_vertebral_data([])  # Vyčisti tabulku

            # Inference button je dostupný jen pokud je snímek potvrzen
            if self.image_confirmed:
                self.inference_button.setEnabled(True)
                self.inference_button.setText("Spustit Inferenci")
                self.inference_completed = False  # Reset inference status
                # Zákáž Body a Výsledky znovu
                self.menu_buttons["Body"].setEnabled(False)
                self.menu_buttons["Výsledky"].setEnabled(False)
                self.points_confirmed = False