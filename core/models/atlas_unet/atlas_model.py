"""
Atlas UNet Model Wrapper - Implementace BaseMLInference

Wraps preprocessing, inference, keypoint extraction do unified interface.
"""

from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import numpy as np
from PIL import Image

from core.models.base_inference import BaseMLInference
from core.models.data_structures import VertebralPoints, Point
from core.models.atlas_unet.config import (
    MODEL_WEIGHTS_PATH,
    NUM_CLASSES,
    SLIDING_WINDOW_SIZE,
    CLASS_COLORS_BGR
)
from core.models.atlas_unet.preprocessing import (
    load_trained_model,
    run_inference_on_image,
    get_inference_transform,
    postprocess_mask,
    relabel_by_vertical_position
)
from core.models.atlas_unet.keypoint_extraction import extract_keypoints_from_mask
from logger import logger


class AtlasUNetModel(BaseMLInference):
    """
    Atlas UNet Model - 7-class vertebral segmentation (C2-C7)

    Features:
    - UNet architecture with 512×512 sliding window inference
    - 7-class output (C2, C3, C4, C5, C6, C7, background)
    - Histogram equalization preprocessing
    - Morphological postprocessing
    - Keypoint extraction (4 corners + centroid per vertebra)
    - LabelMe JSON 5.2.1 output format

    Threading:
    - Can be called from QThread workers (inference is CPU/GPU-bound)
    - NOT thread-safe internally - use per-session instances
    """

    def __init__(self, device: str = "cuda", **kwargs):
        """
        Initialize Atlas UNet model

        Args:
            device: "cuda" (GPU) or "cpu"
            **kwargs: Additional config overrides
        """
        super().__init__(model_name="atlas_unet", device=device)

        self.device = device
        self.model = None
        self.transform = None
        self._initialized = False

        logger.info(f"✓ AtlasUNetModel initialized (device={device})")

    def predict(self, image_path: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        BaseMLInference interface - predict from file path

        Args:
            image_path: Path to image file
            **kwargs: Additional parameters

        Returns:
            LabelMe JSON format dict or None on error
        """
        try:
            from PIL import Image as PILImage

            # Load image from path
            image = PILImage.open(image_path).convert('L')  # Grayscale
            image_np = np.array(image)

            # Run inference - pass both image_np and image_path for processing
            result = self.infer({
                'image': image_np,
                'image_path': image_path,
                'return_mask': False,
                'return_keypoints': True,
                'return_visualization': False
            })

            if result.get('status') != 'success':
                logger.error(f"Inference failed: {result.get('error')}")
                return None

            # Extract LabelMe JSON fields from result
            # infer() already returns 'shapes', 'version', 'flags', etc.
            labelme_json = {
                'version': result.get('version', '5.2.1'),
                'flags': result.get('flags', {}),
                'shapes': result.get('shapes', []),
                'imagePath': result.get('imagePath', ''),
                'imageData': result.get('imageData', ''),
                'imageHeight': result.get('imageHeight', 0),
                'imageWidth': result.get('imageWidth', 0),
            }

            return labelme_json

        except Exception as e:
            logger.error(f"Predict failed: {e}")
            return None

    def get_model_name(self) -> str:
        """Return model name for BaseMLInference compatibility"""
        return "Atlas UNet (C2-C7 Segmentation)"

    def infer(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run inference na obrázku

        Args:
            input_data: {
                'image': PIL.Image or np.ndarray,
                'return_mask': bool (default True),
                'return_keypoints': bool (default True),
                'return_visualization': bool (default False)
            }

        Returns:
            {
                'status': 'success' or 'error',
                'mask': np.ndarray (7-class segmentation) - if return_mask=True,
                'keypoints': Dict[int, VertebralPoints] (per-vertebra keypoints) - if return_keypoints=True,
                'visualization': np.ndarray (original + mask overlay) - if return_visualization=True,
                'error': str - if status='error'
            }
        """
        try:
            # Lazy load model if needed
            if not self._initialized:
                self._initialize_model()

            # Parsuj input
            image = input_data.get('image')
            image_path = input_data.get('image_path')  # Get image path if provided
            return_mask = input_data.get('return_mask', True)
            return_keypoints = input_data.get('return_keypoints', True)
            return_visualization = input_data.get('return_visualization', False)

            if image is None:
                raise ValueError("'image' required in input_data")

            # Convert to numpy if PIL
            if isinstance(image, Image.Image):
                image_np = np.array(image)
            else:
                image_np = image

            # Ensure uint8 grayscale
            if len(image_np.shape) == 3:
                # RGB -> Grayscale
                image_np = np.mean(image_np[:, :, :3], axis=2).astype(np.uint8)

            logger.debug(f"Running inference on image shape: {image_np.shape}")

            # Run inference - use provided image_path for loading
            if image_path:
                mask_7class, overlay_img = run_inference_on_image(
                    model=self.model,
                    img_path=image_path,
                    device=self.device,
                    transform=self.transform
                )
            else:
                raise ValueError("image_path required for inference")

            # Postprocessing
            mask_cleaned = postprocess_mask(mask_7class)
            mask_relabeled = relabel_by_vertical_position(mask_cleaned)  # No need to pass image_np

            # Build result
            result = {'status': 'success'}

            if return_mask:
                result['mask'] = mask_relabeled

            if return_keypoints:
                # Convert 2D labeled mask to 3D BGR color mask for keypoint extraction
                from core.models.atlas_unet import config

                image_height, image_width = image_np.shape[:2]
                image_name = Path(image_path).stem if image_path else "image"

                mask_bgr = np.zeros((image_height, image_width, 3), dtype=np.uint8)
                for class_id, color in config.CLASS_COLORS_BGR.items():
                    mask_bgr[mask_relabeled == class_id] = color

                keypoints_labelme = extract_keypoints_from_mask(
                    mask_bgr,
                    image_name,
                    image_width,
                    image_height
                )

                # Return LabelMe JSON format (same as preview model)
                # Copy just the shapes, version, and other LabelMe fields
                for key in ['version', 'flags', 'shapes', 'imagePath', 'imageData', 'imageHeight', 'imageWidth']:
                    if key in keypoints_labelme:
                        result[key] = keypoints_labelme[key]

            if return_visualization:
                result['visualization'] = self._visualize_result(
                    image_np,
                    mask_relabeled
                )

            logger.info("✓ Inference completed successfully")
            return result

        except Exception as e:
            logger.error(f"✗ Inference failed: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def _initialize_model(self) -> None:
        """Lazy-load model checkpoint"""
        try:
            logger.info("Loading Atlas UNet model...")

            # Build model architecture
            import torch
            from core.models.atlas_unet.preprocessing import build_model
            self.model = build_model()

            # Load checkpoint
            model_path = Path(MODEL_WEIGHTS_PATH)
            if not model_path.exists():
                raise FileNotFoundError(f"Model weights not found: {model_path}")

            self.model = load_trained_model(str(model_path), self.device)
            self.model.eval()

            # Get transform pipeline
            self.transform = get_inference_transform()

            self._initialized = True
            logger.info("✓ Model loaded successfully")

        except Exception as e:
            logger.error(f"✗ Failed to load model: {e}")
            raise

    def _convert_labelme_to_vertebral_points(
        self,
        labelme_json: Dict,
        image_shape: Tuple[int, int]
    ) -> Dict[int, VertebralPoints]:
        """
        Convert LabelMe JSON format to VertebralPoints

        LabelMe format from extract_keypoints_from_mask returns individual point shapes:
            {
                'shapes': [
                    {'label': 'C2 top left', 'points': [[x1,y1]], ...},
                    {'label': 'C2 top right', 'points': [[x2,y2]], ...},
                    {'label': 'C2 bottom left', 'points': [[x3,y3]], ...},
                    {'label': 'C2 bottom right', 'points': [[x4,y4]], ...},
                    {'label': 'C2 centroid', 'points': [[x5,y5]], ...},
                    ...
                ]
            }

        Returns:
            {
                2: VertebralPoints(top_left=Point(...), top_right=..., bottom_right=..., bottom_left=..., centroid=...),
                3: VertebralPoints(...),
                ...
            }
        """
        result = {}

        # Map vertebra label to number
        label_to_num = {
            'C2': 2, 'C3': 3, 'C4': 4, 'C5': 5, 'C6': 6, 'C7': 7
        }

        # Collect points by vertebra
        vertebra_points_map = {}  # {2: {'top_left': Point(...), ...}}

        for shape in labelme_json.get('shapes', []):
            label = shape.get('label', '').strip()
            points = shape.get('points', [])

            if not points or not label:
                continue

            # Parse label like "C2 top left" -> vertebra_name="C2", point_name="top left"
            parts = label.rsplit(' ', 2)  # Split from right to handle multi-word point names
            if len(parts) < 2:
                continue

            vertebra_name = parts[0]
            point_name = ' '.join(parts[1:])

            if vertebra_name not in label_to_num:
                continue

            vertebra_num = label_to_num[vertebra_name]
            point_coord = points[0]  # First (and only) point in this shape

            if vertebra_num not in vertebra_points_map:
                vertebra_points_map[vertebra_num] = {}

            vertebra_points_map[vertebra_num][point_name] = Point(x=point_coord[0], y=point_coord[1])

        # Build VertebralPoints for each vertebra that has all 5 required points
        required_points = {'top left', 'top right', 'bottom left', 'bottom right', 'centroid'}

        for vertebra_num, points_dict in vertebra_points_map.items():
            # For C2, we need 3 points: bottom left, bottom right, centroid
            if vertebra_num == 2:
                c2_required = {'bottom left', 'bottom right', 'centroid'}
                if not c2_required.issubset(set(points_dict.keys())):
                    continue
                vertebral_points = VertebralPoints(
                    top_left=points_dict.get('bottom left'),  # Use bottom_left as top_left for C2
                    top_right=points_dict.get('bottom right'),  # Use bottom_right as top_right for C2
                    bottom_right=points_dict.get('centroid'),  # Use centroid as bottom_right for C2
                    bottom_left=points_dict.get('bottom left'),  # Use bottom_left as is
                    centroid=points_dict.get('centroid')
                )
            else:
                # For C3-C7, we need all 5 points
                if not required_points.issubset(set(points_dict.keys())):
                    continue
                vertebral_points = VertebralPoints(
                    top_left=points_dict['top left'],
                    top_right=points_dict['top right'],
                    bottom_right=points_dict['bottom right'],
                    bottom_left=points_dict['bottom left'],
                    centroid=points_dict['centroid']
                )

            result[vertebra_num] = vertebral_points

        return result

    def _visualize_result(
        self,
        image_np: np.ndarray,
        mask_7class: np.ndarray
    ) -> np.ndarray:
        """
        Create visualization of mask overlaid on original image

        Returns:
            RGB image with color-coded mask overlay
        """
        try:
            import cv2

            # Convert grayscale to RGB if needed
            if len(image_np.shape) == 2:
                image_rgb = cv2.cvtColor(image_np, cv2.COLOR_GRAY2BGR)
            else:
                image_rgb = image_np[:, :, :3]

            # Blend mask onto image
            alpha = 0.4
            visualization = image_rgb.copy().astype(float)

            # Apply class colors
            for class_idx in range(1, 8):  # Skip background (0)
                class_mask = (mask_7class == class_idx).astype(float)

                # Get color from config
                color_bgr = CLASS_COLORS_BGR.get(
                    class_idx,
                    (128, 128, 128)
                )

                for channel in range(3):
                    visualization[:, :, channel] += (
                        class_mask * color_bgr[channel] * alpha
                    )

            visualization = np.clip(visualization, 0, 255).astype(np.uint8)
            return visualization

        except Exception as e:
            logger.warning(f"Visualization failed: {e}")
            return image_np

    def cleanup(self) -> None:
        """
        Clean up resources (remove model from GPU/CPU)

        Called when model is unloaded from manager
        """
        try:
            if self.model is not None:
                del self.model
                self.model = None

            self._initialized = False
            logger.info("✓ AtlasUNetModel cleaned up")

        except Exception as e:
            logger.error(f"⚠ Cleanup error: {e}")
