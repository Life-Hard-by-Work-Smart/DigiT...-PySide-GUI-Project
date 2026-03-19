"""Hlavní okno aplikace"""

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QTabBar,
    QPushButton,
    QInputDialog,
    QFileDialog,
    QMenu,
    QMessageBox,
)
from PySide6.QtCore import Qt

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
        new_blank_session_action = file_menu.addAction("New Session")
        new_blank_session_action.triggered.connect(self.add_new_session)
        new_session_action = file_menu.addAction("New Session with file")
        new_session_action.triggered.connect(self.add_new_session_with_file)
        file_menu.addSeparator()
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

        # Help menu
        help_menu = menubar.addMenu("Help")
        about_action = help_menu.addAction("About")
        about_action.triggered.connect(self.show_about)

        docs_action = help_menu.addAction("Documentation")
        docs_action.triggered.connect(self.show_documentation)

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
        self.session_tabs.tabBarClicked.connect(self._on_tab_bar_clicked)

        # Right-click context menu na tab bary
        self.session_tabs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.session_tabs.customContextMenuRequested.connect(self._on_tab_context_menu)

        # Dummy tab pro '+' button
        self.plus_tab = QWidget()
        self.plus_tab.setStyleSheet("background-color: transparent;")

        # Přidej první session jako výchozí
        self.add_new_session()

        # Přidej + tab jako poslední tab (jako v prohlížeči)
        self.session_tabs.addTab(self.plus_tab, "+")
        # Smaž close button u + tabu
        self.session_tabs.tabBar().setTabButton(self.session_tabs.count() - 1, QTabBar.RightSide, None)

        main_layout.addWidget(self.session_tabs)

    def _on_tab_bar_clicked(self, index):
        """Vyhodnocení kliknutí na tab - pokud je to '+', přidej novou session"""
        if self.session_tabs.widget(index) == self.plus_tab:
            self.add_new_session()

    def add_new_session(self):
        """Přidej novou session jako tab"""
        self.session_counter += 1
        session_name = f"Session {self.session_counter}"
        session_widget = SessionScreen(session_name)

        # Zjistíme, jestli už máme plus_tab a vložíme před něj
        plus_index = self.session_tabs.indexOf(getattr(self, 'plus_tab', None))

        if plus_index >= 0:
            # Vložíme před plus symbol
            self.session_tabs.insertTab(plus_index, session_widget, session_name)
            self.session_tabs.setCurrentIndex(plus_index)
        else:
            self.session_tabs.addTab(session_widget, session_name)
            self.session_tabs.setCurrentIndex(self.session_tabs.count() - 1)

        logger.info(f"Nová session vytvořena: {session_name}")

    def close_session_tab(self, index):
        """Zavři session tab"""
        if self.session_tabs.widget(index) != self.plus_tab:
            self.session_tabs.removeTab(index)
            logger.info("Session zavřena")

            # Pokud zbyl jen '+' tab, vynuluj counter
            if self.session_tabs.count() == 1:
                self.session_counter = 0
                logger.info("Všechny sessions zavřeny, resetuji session_counter na 0")

    def _on_tab_context_menu(self, pos):
        """Right-click context menu na tab baru"""
        tab_bar = self.session_tabs.tabBar()
        clicked_index = tab_bar.tabAt(pos)

        if clicked_index < 0:
            return  # Kliknutí mimo tab

        # Nedovolit context menu na '+' tabu
        if self.session_tabs.widget(clicked_index) == self.plus_tab:
            return

        # Vytvoř context menu
        context_menu = QMenu(self)

        # Rename action
        rename_action = context_menu.addAction("Přejmenovat session")
        rename_action.triggered.connect(lambda: self._rename_session(clicked_index))

        # Ukaž menu
        context_menu.exec(tab_bar.mapToGlobal(pos))

    def _rename_session(self, index):
        """Přejmenuj session"""
        current_name = self.session_tabs.tabText(index)

        # Dialog pro zadání nového jména
        new_name, ok = QInputDialog.getText(
            self,
            "Přejmenovat session",
            "Nové jméno:",
            text=current_name
        )

        if ok and new_name.strip():
            self.session_tabs.setTabText(index, new_name.strip())
            logger.info(f"Session přejmenována: '{current_name}' → '{new_name.strip()}'")

    def add_new_session_with_file(self):
        """Vyber soubor rovnou v exploreru a přeskoč potvzení snímku"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Vybrat snímek",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.session_counter += 1
            session_name = f"Session {self.session_counter}"
            session_widget = SessionScreen(session_name)

            # Simulated load & auto-confirm
            session_widget.on_image_loaded(file_path)
            session_widget.on_confirm_image_clicked()

            plus_index = self.session_tabs.indexOf(getattr(self, 'plus_tab', None))
            if plus_index >= 0:
                self.session_tabs.insertTab(plus_index, session_widget, session_name)
                self.session_tabs.setCurrentIndex(plus_index)
            else:
                self.session_tabs.addTab(session_widget, session_name)
                self.session_tabs.setCurrentIndex(self.session_tabs.count() - 1)

            logger.info(f"Nová session rovnou ze souboru: {session_name}")

    def show_about(self):
        """Zobraz okno About s informacemi o aplikaci"""
        QMessageBox.about(
            self,
            "About DigiTech-Spiner",
            "<h3>DigiTech-Spiner</h3>"
            "<p>Moderní nástroj pro vizualizaci, detekci a editaci vertebrálních (páteřových) bodů na rentgenových snímcích.</p>"
            "<br>"
            "<p><b>Verze:</b> 0.0.1-prealpha</p>"
            "<p><b>Framework:</b> PySide6</p>"
            "<p><b>Vyvinuto od:</b> Life-Hard-by-Work-Smart</p>"
            "<hr>"
            "<p>Tento software momentálně slouží pro výzkumné účely jako PoC a základ pro budoucí vývoj.</p>"
        )

    def show_documentation(self):
        """Zobraz obsah README.md / dokumentace v MessageBoxu, nebo zkus otevřít README"""
        try:
            with open("README.md", "r", encoding="utf-8") as f:
                content = f.read()

            # Message box s omezeným zobrazením README
            msg = QMessageBox(self)
            msg.setFixedWidth(600)
            msg.setFixedHeight(400)
            msg.setWindowTitle("Dokumentace")
            msg.setText("<b>Dokumentace projektu (README.md)</b>")
            msg.setInformativeText("Přečtěte si kompletní README v kořeni projektu pro instalaci a rychlý návod.")
            msg.setDetailedText(content[:1500] + "...\n\n(Pro zbytek dokumentace si otevřete soubor README.md v textovém editoru.)")
            msg.exec()
        except Exception as e:
            QMessageBox.warning(self, "Chyba", f"Nepodařilo se načíst dokumentaci (README.md).\nChyba: {e}")

