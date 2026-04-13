"""Atlas UNet model configuration

Configuration for Atlas UNet 7-class vertebrae segmentation model.
All paths are relative to this file or project root.
"""

from pathlib import Path

# Base paths
MODEL_DIR = Path(__file__).parent
WEIGHTS_DIR = MODEL_DIR / "weights"

# Model weights
MODEL_WEIGHTS_PATH = WEIGHTS_DIR / "atlas-model-final.pth"

# Model architecture
MODEL_NAME = "atlas_unet"
NUM_CLASSES = 7  # 6 vertebrae (C2-C7) + background
IN_CHANNELS = 3
SPATIAL_DIMS = 2

# Model structure
CHANNELS = (16, 32, 64, 128, 256)
STRIDES = (2, 2, 2, 2)
NUM_RES_UNITS = 2

# Preprocessing
HISTOGRAM_EQUALIZATION = True
EXPECTED_INPUT_SIZE = (512, 512)
SCALE_INTENSITY = True  # Normalize to [0, 1]

# Inference
SLIDING_WINDOW_SIZE = (512, 512)
SLIDING_WINDOW_OVERLAP = 0.25  # 25% overlap for better edge handling
ROI_SIZE = (512, 512)
CONF_THRESH_DEFAULT = 0.5

# Postprocessing
MORPHOLOGICAL_OPENING_KERNEL = 5
MORPHOLOGICAL_CLOSING_KERNEL = 5
MORPHOLOGICAL_OPENING_ITERATIONS = 1
MORPHOLOGICAL_CLOSING_ITERATIONS = 2

# Output format
OUTPUT_FORMAT = "labelme_5.2.1"  # LabelMe format

# Class labels and colors (BGR format)
VERTEBRAE_CLASSES = ["C2", "C3", "C4", "C5", "C6", "C7"]

CLASS_COLORS_BGR = {
    0: (0, 0, 0),          # Background - black
    1: (255, 0, 255),      # C2 - Magenta
    2: (0, 255, 255),      # C3 - Cyan
    3: (255, 165, 0),      # C4 - Orange
    4: (80, 140, 255),     # C5 - Light Blue
    5: (255, 80, 80),      # C6 - Red
    6: (0, 220, 100),      # C7 - Green
}

# Keypoint extraction
KEYPOINT_LABELS_PER_VERTEBRA = ["top left", "top right", "bottom left", "bottom right", "centroid"]

# Device (cuda/cpu) - will be auto-detected at runtime
DEVICE = "auto"  # "cuda", "cpu", or "auto"

# Logging
LOG_LEVEL = "INFO"
