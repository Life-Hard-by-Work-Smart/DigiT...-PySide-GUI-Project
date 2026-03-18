"""Hlavní okno aplikace"""

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QTabWidget,
)

from ui.session_screen import SessionScreen
from config import WINDOW_WIDTH, WINDOW_HEIGHT
from logger import logger


class MainWindow(QMainWindow):
    """Hlavní okno s tab managementem pro sessions"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DigiTech-Spiner")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.session_counter = 0

        logger.info("MainWindow inicializován")

        self._setup_menu()
        self._setup_tabs()

    def _setup_menu(self):
        """Nastav menu bar"""
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

    def _setup_tabs(self):
        """Nastav tab widget pro session management"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Session tabs (jako v prohlížeči)
        self.session_tabs = QTabWidget()
        self.session_tabs.setTabsClosable(True)
        self.session_tabs.tabCloseRequested.connect(self.close_session_tab)

        # Přidej první session
        self.add_new_session()

        main_layout.addWidget(self.session_tabs)

    def add_new_session(self):
        """Přidej novou session jako tab"""
        self.session_counter += 1
        session_name = f"Session {self.session_counter}"
        session_widget = SessionScreen(session_name)
        self.session_tabs.addTab(session_widget, session_name)
        self.session_tabs.setCurrentIndex(self.session_tabs.count() - 1)
        logger.info(f"Nová session vytvořena: {session_name}")

    def close_session_tab(self, index):
        """Zavři session tab"""
        if self.session_tabs.count() > 1:
            self.session_tabs.removeTab(index)
            logger.info("Session zavřena")
        else:
            self.close()
