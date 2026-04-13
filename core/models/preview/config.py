"""Preview model configuration

Configuration for Preview ML inference simulator.
Used for testing and demonstration without requiring actual GPU/CUDA.
"""

from pathlib import Path

# Base paths
MODEL_DIR = Path(__file__).parent
PROJECT_ROOT = MODEL_DIR.parent.parent.parent

# Test data paths
TESTING_DATA_DIR = PROJECT_ROOT / "testing_data"
TEST_IMAGE_PATH = TESTING_DATA_DIR / "0001035_image.png"
TEST_RESULTS_PATH = TESTING_DATA_DIR / "0001035_maskhat.json"

# Model info
MODEL_NAME = "preview"
DESCRIPTION = "Preview simulator - uses pre-computed results for testing"

# Output format
OUTPUT_FORMAT = "labelme_5.2.1"  # LabelMe format

# Logging
LOG_LEVEL = "INFO"
