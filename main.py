import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QTabWidget, QListWidget, QListWidgetItem,
    QTabBar, QStackedWidget, QMenu, QMenuBar, QFileDialog, QScrollArea,
    QComboBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QPixmap, QDragEnterEvent, QDropEvent

class DragDropFrame(QFrame):
    """Frame s drag-and-drop podporou pro snímky"""
    image_loaded = Signal(str)  # Signal - emituje cestu ke snímku
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.image_path = None
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Když uživatel táhne soubor nad frame"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """Když uživatel pustí soubor na frame"""
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        if files:
            file_path = files[0]
            # Zkontroluj, jestli je to snímek
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                self.load_image(file_path)

    def load_image(self, file_path):
        """Ulož cestu ke snímku a emituj signál"""
        self.image_path = file_path
        self.image_loaded.emit(file_path)

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
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Drag-drop frame
        self.xray_frame = DragDropFrame()
        self.xray_frame.image_loaded.connect(self.on_image_loaded)
        self.xray_frame.setStyleSheet("border: 2px solid #999; background-color: white;")
        self.xray_frame.setAcceptDrops(True)  # Drag-drop aktivní
        xray_layout = QVBoxLayout(self.xray_frame)
        xray_layout.setContentsMargins(0, 0, 0, 0)
        xray_layout.setSpacing(0)
        
        # Scroll area pro snímek
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.image_display = QLabel()
        self.image_display.setAlignment(Qt.AlignCenter)
        self.image_display.setStyleSheet("background-color: #f5f5f5;")
        scroll_area.setWidget(self.image_display)
        
        # Widget pro text a tlačítko (overlay)
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
        
        # Stacked widget - zobrazuj buď scroll_area nebo overlay
        self.xray_stack = QStackedWidget()
        self.xray_stack.addWidget(scroll_area)  # Index 0
        self.xray_stack.addWidget(overlay_widget)  # Index 1
        self.xray_stack.setCurrentIndex(1)  # Zobraz overlay na začátku
        
        xray_layout.addWidget(self.xray_stack, stretch=1)
        
        layout.addWidget(self.xray_frame, stretch=1)
        
        # ===== RIGHT: WORKFLOW STEP PANEL =====
        workflow_frame = QFrame()
        workflow_frame.setStyleSheet("border: 1px solid #ccc; background-color: #f9f9f9;")
        workflow_frame.setFixedWidth(250)
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
        content_frame_1.setStyleSheet("border: 1px solid #ddd; background-color: white;")
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

        
        
        # Content 2: Body
        content_frame_2 = QFrame()
        content_frame_2.setStyleSheet("border: 1px solid #ddd; background-color: white;")
        content_layout_2 = QVBoxLayout(content_frame_2)
        content_label_2 = QLabel("Bodíky")
        content_label_2.setAlignment(Qt.AlignCenter)
        content_label_2.setStyleSheet("color: #666; font-size: 12px;")
        content_layout_2.addWidget(content_label_2)
        # confirm points button - uložení jako self.confirm_points_button pro pozdější použití
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
        # Propoj s metodou pro potvrzení bodů
        self.confirm_points_button.clicked.connect(self.on_confirm_points_clicked)
        
        content_layout_2.addStretch()
        content_layout_2.addWidget(self.confirm_points_button)
        self.stacked_widget.addWidget(content_frame_2)
        
        # Content 3: Výsledky
        content_frame_3 = QFrame()
        content_frame_3.setStyleSheet("border: 1px solid #ddd; background-color: white;")
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
            # Přizpůsobi velikost obrázku do dostupného místa
            max_size = 800  # max rozměr
            scaled_pixmap = pixmap.scaledToWidth(max_size, Qt.SmoothTransformation)
            self.image_display.setPixmap(scaled_pixmap)
            
            # Markuj, že je snímek načten a aktivuj tlačítka na potvrzení
            self.image_loaded = True
            self.delete_image_btn.setEnabled(True)
            self.confirm_image_btn.setEnabled(True)
            
            # Zobraz snímek namísto overlay (index 0 = scroll_area)
            self.xray_stack.setCurrentIndex(0)
    
    def on_image_loaded(self, file_path):
        """Callback při drag-drop obrázku"""
        self.load_image(file_path)
    
    def on_delete_image_clicked(self):
        """Smaž aktuální snímek a resetuj stav"""
        self.image_display.clear()
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
        
        # Zobraz overlay namíst obrázku
        self.xray_stack.setCurrentIndex(1)
    
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
        """Obsluha kliknutí na 'Spustit Inferenci'"""
        if self.image_loaded:
            # TODO: Sem přijde skutečná inference logika
            print(f"[Session {self.session_name}] Inference spuštěna")
            self.inference_completed = True
            # Aktivuj Body po dokončení inference
            self.menu_buttons["Body"].setEnabled(True)
            self.inference_button.setText("✓ Inference hotova")
            self.inference_button.setEnabled(False)
    
    def on_confirm_points_clicked(self):
        """Obsluha kliknutí na 'Potvrdit body' - lze volat opakovaně"""
        # TODO: Sem přijde logika potvrzení bodů
        print(f"[Session {self.session_name}] Body potvrzeny")
        self.points_confirmed = True
        # Aktivuj Výsledky po potvrzení bodů
        self.menu_buttons["Výsledky"].setEnabled(True)
    
    def on_model_changed(self, model_name):
        """Změna modelu - aktualizuj UI a zpřístupni inference tlačítko"""
        print(f"[Session {self.session_name}] Model změněn na: {model_name}")
        
        # Zobraz/skryj parametry box podle modelu
        is_model_2 = (model_name == "model 2")
        self.params_label.setVisible(is_model_2)
        self.params_box.setVisible(is_model_2)
        
        # Inference button je dostupný jen pokud je snímek potvrzen
        if self.image_confirmed:
            self.inference_button.setEnabled(True)
            self.inference_button.setText("Spustit Inferenci")
            self.inference_completed = False  # Reset inference status
            # Zákáž Body a Výsledky znovu
            self.menu_buttons["Body"].setEnabled(False)
            self.menu_buttons["Výsledky"].setEnabled(False)
            self.points_confirmed = False

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
