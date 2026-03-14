import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QTabWidget, QListWidget, QListWidgetItem,
    QTabBar, QStackedWidget, QMenu, QMenuBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

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
        xray_frame.setStyleSheet("border: 2px solid #999; background-color: white;")
        xray_layout = QVBoxLayout(xray_frame)
        xray_label = QLabel(f"X-ray Display\n({self.session_name})")
        xray_label.setAlignment(Qt.AlignCenter)
        xray_label.setStyleSheet("color: #666; font-size: 14px;")
        xray_layout.addWidget(xray_label)
        layout.addWidget(xray_frame, stretch=1)
        
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
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #e0e0e0;
                    border: 1px solid #999;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #d0d0d0;
                }
                QPushButton:checked {
                    background-color: #4CAF50;
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
        content_frame_1.setStyleSheet("border: 1px solid #ddd; background-color: white;")
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
        # Placeholder pro budoucí funkcionalitu - lze přidat connect k metodě
        # self.confirm_points_button.clicked.connect(self.on_inference_clicked)
        
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
