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

            # Convert to LabelMe JSON format for compatibility
            keypoints = result.get('keypoints', {})

            labelme_json = {
                'version': '5.2.1',
                'flags': {},
                'shapes': []
            }

            # Convert keypoints to LabelMe shapes
            for vertebra_num, vpoints in keypoints.items():
                vertebra_label = f'C{vertebra_num}'

                points_list = [
                    [vpoints.top_left.x, vpoints.top_left.y],
                    [vpoints.top_right.x, vpoints.top_right.y],
                    [vpoints.bottom_right.x, vpoints.bottom_right.y],
                    [vpoints.bottom_left.x, vpoints.bottom_left.y],
                    [vpoints.centroid.x, vpoints.centroid.y],
                ]

                labelme_json['shapes'].append({
                    'label': vertebra_label,
                    'points': points_list,
                    'group_id': None,
                    'description': '',
                    'shape_type': 'polygon',
                    'flags': {}
                })

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
                # Extract keypoints from colored mask
                keypoints_labelme = extract_keypoints_from_mask(
                    mask_relabeled,
                    image_np
                )

                # Convert to VertebralPoints format
                result['keypoints'] = self._convert_labelme_to_vertebral_points(
                    keypoints_labelme,
                    image_np.shape
                )

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

        LabelMe format:
            {
                'shapes': [
                    {
                        'label': 'C2',
                        'points': [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
                        ...
                    },
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

        # Map label to vertebra number
        label_to_num = {
            'C2': 2, 'C3': 3, 'C4': 4, 'C5': 5, 'C6': 6, 'C7': 7
        }

        for shape in labelme_json.get('shapes', []):
            label = shape.get('label', '')
            points = shape.get('points', [])

            if label not in label_to_num or len(points) < 5:
                continue

            vertebra_num = label_to_num[label]

            # Points: [top_left, top_right, bottom_right, bottom_left, centroid]
            vertebral_points = VertebralPoints(
                top_left=Point(x=points[0][0], y=points[0][1]),
                top_right=Point(x=points[1][0], y=points[1][1]),
                bottom_right=Point(x=points[2][0], y=points[2][1]),
                bottom_left=Point(x=points[3][0], y=points[3][1]),
                centroid=Point(x=points[4][0], y=points[4][1])
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
