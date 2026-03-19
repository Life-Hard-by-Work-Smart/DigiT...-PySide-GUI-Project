"""Centrální konfigurace aplikace"""

from pathlib import Path
from PySide6.QtGui import QColor

# Cesty
PROJECT_ROOT = Path(__file__).parent
TESTING_DATA_DIR = PROJECT_ROOT / "testing_data"

# Testovací data pro ML inference
TEST_IMAGE_PATH = TESTING_DATA_DIR / "0001035_image.png"
TEST_RESULTS_PATH = TESTING_DATA_DIR / "0001035_maskhat.json"

# Dostupné modely (ML tým bude přidávat)
AVAILABLE_MODELS = [
    {"name": "model 1", "description": "Default model"},
    {"name": "model 2", "description": "Advanced model with parameters"},
]

# UI - Main Window
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 800
MAX_IMAGE_SIZE = 800

# Canvas - Points Visualization
POINT_COLORS = {
    'TL': QColor(255, 192, 203),      # Pink - Top Left
    'TR': QColor(144, 238, 144),      # Light Green - Top Right
    'BL': QColor(173, 216, 230),      # Light Blue - Bottom Left
    'BR': QColor(255, 255, 153),      # Light Yellow - Bottom Right
    'C': QColor(255, 200, 124),       # Light Orange - Centroid
}

# Alternativní barvy pro model 2 (přeházené pro lepší rozlišení)
POINT_COLORS_MODEL_2 = {
    'TL': QColor(144, 238, 144),      # Light Green - Top Left (bylo TR)
    'TR': QColor(173, 216, 230),      # Light Blue - Top Right (bylo BL)
    'BL': QColor(255, 255, 153),      # Light Yellow - Bottom Left (bylo BR)
    'BR': QColor(255, 200, 124),      # Light Orange - Bottom Right (bylo C)
    'C': QColor(255, 192, 203),       # Pink - Centroid (bylo TL)
}

POINT_RADIUS = 2                      # Radius in pixels (diameter = 4px)
POINT_SELECTED_RADIUS = 4             # Selected: radius in pixels (diameter = 8px)
POINT_CLICK_RADIUS = 5                # Hitbox radius in pixels (10px diameter)
SHOW_POINT_LABELS = False             # Show TL/TR/BL/BR/C labels on canvas

# Canvas - Pan/Zoom Controls
ZOOM_STEP = 1.1                       # Scroll zoom increment
AUTO_FIT_IMAGE = True                 # Auto-center image in canvas on load
ALLOW_POINTS_OUTSIDE_IMAGE = False    # Keep points within image bounds

# Canvas - Point Editing
RESTRICT_SELECTION_TO_TABLE = True    # Only table allows point selection (no direct canvas click)
ARROW_KEY_STEP = 1                    # Pixel per arrow key press
ARROW_KEY_STEP_SHIFT = 0.33              # Pixel per Shift+arrow key press

# Inference
INFERENCE_TIMEOUT = 30  # sekund
