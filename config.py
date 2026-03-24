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
    "TL": QColor(255, 192, 203),  # Pink - Top Left
    "TR": QColor(144, 238, 144),  # Light Green - Top Right
    "BL": QColor(173, 216, 230),  # Light Blue - Bottom Left
    "BR": QColor(255, 255, 153),  # Light Yellow - Bottom Right
    "C": QColor(255, 200, 124),  # Light Orange - Centroid
}

# Alternativní barvy pro model 2 (přeházené pro lepší rozlišení)
POINT_COLORS_MODEL_2 = {
    "TL": QColor(144, 238, 144),  # Light Green - Top Left (bylo TR)
    "TR": QColor(173, 216, 230),  # Light Blue - Top Right (bylo BL)
    "BL": QColor(255, 255, 153),  # Light Yellow - Bottom Left (bylo BR)
    "BR": QColor(255, 200, 124),  # Light Orange - Bottom Right (bylo C)
    "C": QColor(255, 192, 203),  # Pink - Centroid (bylo TL)
}


POINT_RADIUS = 4  # Radius in pixels (diameter = 8px)
POINT_SELECTED_RADIUS = 6  # Selected: radius in pixels (diameter = 12px)
POINT_CLICK_RADIUS = 7  # Hitbox radius in pixels (14px diameter)
SHOW_POINT_LABELS = True  # Show TL/TR/BL/BR/C labels on canvas

# Segmentation Mask Overlay (separate module - core/graphics/segmentation_mask.py)
ENABLE_SEGMENTATION_MASK = (
    False  # Set False to fully disable the feature (no button, no drawing)
)
SEGMENTATION_MASK_ALPHA = 80  # Fill transparency 0-255 (~31% opacity)
SEGMENTATION_MASK_COLORS = [
    QColor(255, 0, 255),  # Magenta  – C2
    QColor(0, 255, 255),  # Cyan     – C3
    QColor(255, 165, 0),  # Orange   – C4
    QColor(80, 140, 255),  # Blue     – C5
    QColor(255, 80, 80),  # Red      – C6
    QColor(0, 220, 100),  # Green    – C7
    QColor(220, 220, 0),  # Yellow   – T1
    QColor(180, 80, 255),  # Purple   – T2
]

POINT_RADIUS = 3                      # Radius in pixels (diameter = 8px)
POINT_SELECTED_RADIUS = 4             # Selected: radius in pixels (diameter = 12px)
POINT_CLICK_RADIUS = 5                # Hitbox radius in pixels (14px diameter)
SHOW_POINT_LABELS = True              # Show TL/TR/BL/BR/C labels on canvas
PICTURE_FONT_SIZE = 10

# Points Panel - Label Display
USE_ABBREVIATED_LABELS = (
    False  # False = plné labely (top left, bottom right), True = zkratky (TL, BR)
)



# Canvas - Pan/Zoom Controls
ZOOM_STEP = 1.1  # Scroll zoom increment
AUTO_FIT_IMAGE = True  # Auto-center image in canvas on load
ALLOW_POINTS_OUTSIDE_IMAGE = False  # Keep points within image bounds

# Canvas - Point Editing
RESTRICT_SELECTION_TO_TABLE = (
    True  # Only table allows point selection (no direct canvas click)
)
ARROW_KEY_STEP = 1  # Pixel per arrow key press
ARROW_KEY_STEP_SHIFT = 0.33  # Pixel per Shift+arrow key press


# Logging Configuration
LOGGING_ENABLED = True               # Zapnout/vypnout logování obecně
LOG_TO_FILE = False                       # Zapisovat logs do souboru (app.log)
LOG_TO_CONSOLE = True                 # Vypisovat logs do konzole
LOG_DEBUG_FILE = False                # Zapnout detailní debug.log (True = výstup debug-level detailů)
LOG_OUTPUT_FILE = False               # Zapnout app_output.log (True = zvláštní soubor pro output)

# Inference
INFERENCE_TIMEOUT = 30  # sekund

# Prezentační mód — zobrazí demo popup segmentace při spuštění inference pro model 2
PRESENTATION_MODE = True
