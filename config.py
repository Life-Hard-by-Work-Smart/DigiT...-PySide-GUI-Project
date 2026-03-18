"""Centrální konfigurace aplikace"""

from pathlib import Path

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

# UI
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 800
MAX_IMAGE_SIZE = 800

# Inference
INFERENCE_TIMEOUT = 30  # sekund
