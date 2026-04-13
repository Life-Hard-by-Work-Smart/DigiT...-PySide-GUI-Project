
"""Hlavní vstupní bod aplikace DigiTech-Spiner"""

import sys
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from core.models.initialize_models import initialize_models
from logger import logger


def main():
    """Spusť aplikaci"""
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QToolTip {
            color: #1a1a1a;
            background-color: #f5f5f5;
            border: 1px solid #aaaaaa;
            padding: 4px 6px;
        }
    """)

    # Initialize ML models - jedenkrát na startu
    logger.info("Initializing ML models...")
    initialize_models()

    window = MainWindow()
    window.show()
    logger.info("Aplikace spuštěna")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


