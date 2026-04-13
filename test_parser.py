"""Test parser"""
import json
from pathlib import Path
from core.models.initialize_models import initialize_models
from core.models.model_manager import ModelManager
from core.io.ML_output_handler import InferenceOutputHandler

# Inicializuj modely nejdřív
initialize_models()

# Načti model
model_manager = ModelManager()
model = model_manager.get_model('atlas_unet', session_id='test')

# Spusť inference
image_path = "testing_data/0001035_image.png"
from PIL import Image
import numpy as np

img = Image.open(image_path)
img_np = np.array(img)

result = model.infer({
    'image': img_np,
    'image_path': image_path,
    'return_mask': True,
    'return_keypoints': True,
    'return_visualization': False
})

print("=" * 80)
print("RESULT STRUCTURE:")
print("=" * 80)
print(f"Result keys: {result.keys()}")
print(f"Result['shapes']: {len(result.get('shapes', []))} items")

# Teď parsuj to
print("\n" + "=" * 80)
print("PARSING RESULT:")
print("=" * 80)

vertebral_results = InferenceOutputHandler.parse_inference_output(result)
print(f"Parsed vertebral_results: {vertebral_results}")
print(f"Length: {len(vertebral_results)}")

if vertebral_results:
    for vp in vertebral_results:
        print(f"\n  {vp.name}: {len(vp.points)} points")
        for p in vp.points:
            print(f"    - {p.label}: ({p.x:.1f}, {p.y:.1f})")
