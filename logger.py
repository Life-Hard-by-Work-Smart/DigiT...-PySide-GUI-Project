"""Centrální loging pro aplikaci"""

import logging
import sys
from pathlib import Path
from config import LOGGING_ENABLED, LOG_TO_FILE, LOG_TO_CONSOLE, LOG_DEBUG_FILE, LOG_OUTPUT_FILE

# Log soubory
LOG_FILE = Path(__file__).parent / "app.log"
DEBUG_LOG_FILE = Path(__file__).parent / "debug.log"
OUTPUT_LOG_FILE = Path(__file__).parent / "app_output.log"

# Setup logger
logger = logging.getLogger("DigiTech")
logger.setLevel(logging.DEBUG)

# Pokud je logování vypnuté, nekonfiguruj handlery
if not LOGGING_ENABLED:
    logger.addHandler(logging.NullHandler())
else:
    # Console handler
    if LOG_TO_CONSOLE:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler - app.log (standardní INFO level)
    if LOG_TO_FILE:
        file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Debug file handler - debug.log (všechny DEBUG a vyšší)
    if LOG_DEBUG_FILE:
        debug_handler = logging.FileHandler(DEBUG_LOG_FILE, encoding='utf-8')
        debug_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(funcName)s() - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        debug_handler.setFormatter(formatter)
        logger.addHandler(debug_handler)

    # Output file handler - app_output.log (pro specifické output loggování)
    if LOG_OUTPUT_FILE:
        output_handler = logging.FileHandler(OUTPUT_LOG_FILE, encoding='utf-8')
        output_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '[%(asctime)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        output_handler.setFormatter(formatter)
        logger.addHandler(output_handler)

# Export
__all__ = ['logger']
