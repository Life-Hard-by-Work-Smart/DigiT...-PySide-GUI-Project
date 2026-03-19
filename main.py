
"""Hlavní vstupní bod aplikace DigiTech-Spiner"""

import sys
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from logger import logger


def main():
    """Spusť aplikaci"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    logger.info("Aplikace spuštěna")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


