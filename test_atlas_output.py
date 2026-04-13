"""Test co vrací atlas_unet model"""
import json
from pathlib import Path
from core.models.initialize_models import initialize_models
from core.models.model_manager import ModelManager

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
print("RESULT TYPE:", type(result))
print("=" * 80)
print("RESULT KEYS:", result.keys() if isinstance(result, dict) else "NOT A DICT")
print("=" * 80)

if isinstance(result, dict):
    for key in result.keys():
        val = result[key]
        if key == 'shapes':
            print(f"\n{key}: list of {len(val)} shapes")
            if val:
                print(f"  First shape: {val[0]}")
        elif key == 'mask':
            print(f"\n{key}: {type(val)} shape {val.shape if hasattr(val, 'shape') else 'N/A'}")
        else:
            print(f"\n{key}: {val}")

print("\n" + "=" * 80)
print("FULL RESULT JSON:")
print("=" * 80)

# Serialize - skip mask because it's numpy
result_to_print = {k: v for k, v in result.items() if k != 'mask'}
print(json.dumps(result_to_print, indent=2, default=str))
