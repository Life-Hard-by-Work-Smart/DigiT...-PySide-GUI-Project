"""Atlas UNet Configuration"""
from pathlib import Path

SPATIAL_DIMS = 2
IN_CHANNELS = 1
NUM_CLASSES = 7
CHANNELS = (32, 64, 128, 256, 512)
STRIDES = (2, 2, 2, 2)
NUM_RES_UNITS = 2
SLIDING_WINDOW_SIZE = (512, 512)
SLIDING_WINDOW_OVERLAP = 0.5
CONF_THRESH_DEFAULT = 0.5
MIN_COMPONENT_SIZE = 500
_MODULE_DIR = Path(__file__).parent
MODEL_WEIGHTS_PATH = str(_MODULE_DIR / "weights" / "atlas-model-final.pth")
CLASS_COLORS_BGR = {
    0: (0, 0, 0),
    1: (255, 0, 0),
    2: (0, 255, 0),
    3: (0, 0, 255),
    4: (255, 255, 0),
    5: (255, 0, 255),
    6: (0, 255, 255),
}
