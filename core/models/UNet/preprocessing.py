"""
Atlas UNet Model Inference - Preprocessing & Model Loading

Handles:
- Model building and loading from checkpoint
- Image preprocessing (histogram equalization, scaling, padding)
- Postprocessing (morphological operations, cleaning)
- Inference with sliding window approach

Original code from toBeIntegrated/Src/Atlas/single_inference.py
Adapted for use as library module in GUI application.
"""

import os
import numpy as np
from PIL import Image
import cv2

import torch
from monai.networks.nets import UNet
from monai.inferers import sliding_window_inference
from monai.transforms import Compose, ScaleIntensityd, SpatialPadd, ToTensord

from scipy.ndimage import binary_opening, binary_closing, binary_fill_holes
from skimage.measure import label, regionprops

from core.models.UNet import config
from core.models.utils.image_utils import HistogramEqualizationd

from logger import logger


# ==========================
# 1) Model Building & Loading
# ==========================

def build_model(num_classes: int = None, in_channels: int = None) -> torch.nn.Module:
    """Build UNet model architecture"""
    if num_classes is None:
        num_classes = config.NUM_CLASSES
    if in_channels is None:
        in_channels = config.IN_CHANNELS

    return UNet(
        spatial_dims=config.SPATIAL_DIMS,
        in_channels=in_channels,
        out_channels=num_classes,
        channels=config.CHANNELS,
        strides=config.STRIDES,
        num_res_units=config.NUM_RES_UNITS,
    )


def load_trained_model(model_path: str, device: torch.device) -> torch.nn.Module:
    """Load trained model from checkpoint"""
    logger.info(f"[Atlas] Loading model from: {model_path}")

    model = build_model().to(device)
    checkpoint = torch.load(model_path, map_location=device)

    if isinstance(checkpoint, dict):
        if "model_state_dict" in checkpoint:
            state_dict = checkpoint["model_state_dict"]
        elif "state_dict" in checkpoint:
            state_dict = checkpoint["state_dict"]
        else:
            state_dict = checkpoint
    else:
        raise ValueError("Unknown checkpoint format (expected dict)")

    logger.debug(f"[Atlas] Checkpoint keys sample: {list(state_dict.keys())[:5]}")
    logger.debug(f"[Atlas] Total state_dict keys: {len(state_dict)}")

    model.load_state_dict(state_dict, strict=True)
    model.eval()

    logger.info(f"[Atlas] Model loaded successfully on device: {device}")
    return model


def get_inference_transform(roi_size=None):
    """Get MONAI transform pipeline for inference"""
    if roi_size is None:
        roi_size = config.SLIDING_WINDOW_SIZE

    return Compose([
        HistogramEqualizationd(keys=["image"]),
        ScaleIntensityd(keys=["image"]),
        SpatialPadd(keys=["image", "image_raw"], spatial_size=roi_size),
        ToTensord(keys=["image", "image_raw"]),
    ])


# ==========================
# 2) Postprocessing
# ==========================

def clean_class(mask_cls: np.ndarray, min_size: int = 500) -> np.ndarray:
    """Clean binary mask: remove small components, fill holes"""
    if not mask_cls.any():
        return mask_cls

    labeled = label(mask_cls)
    regions = regionprops(labeled)

    for r in regions:
        if r.area < min_size:
            labeled[labeled == r.label] = 0

    labeled = label(labeled > 0)
    regions = regionprops(labeled)
    if len(regions) == 0:
        return np.zeros_like(mask_cls, dtype=bool)

    areas = [r.area for r in regions]
    largest_label = regions[int(np.argmax(areas))].label
    mask_main = (labeled == largest_label)

    struct = np.ones((3, 3), dtype=bool)
    mask_main = binary_opening(mask_main, structure=struct)
    mask_main = binary_closing(mask_main, structure=struct)
    mask_main = binary_fill_holes(mask_main)

    return mask_main


def postprocess_mask(pred_mask: np.ndarray, num_classes: int = None, min_size: int = 500) -> np.ndarray:
    """Postprocess prediction mask: clean each class separately"""
    if num_classes is None:
        num_classes = config.NUM_CLASSES

    h, w = pred_mask.shape
    cleaned = np.zeros((h, w), dtype=np.uint8)

    for cls in range(1, num_classes):
        cls_mask = (pred_mask == cls)
        cls_clean = clean_class(cls_mask, min_size=min_size)
        cleaned[cls_clean] = cls

    return cleaned


def relabel_by_vertical_position(mask: np.ndarray, class_ids=(1, 2, 3, 4, 5, 6)) -> np.ndarray:
    """
    Relabel classes by vertical position (top to bottom).
    Ensures anatomically correct ordering.
    """
    centroids = []

    for cls in class_ids:
        m = (mask == cls)
        if not m.any():
            continue
        lab = label(m)
        regs = regionprops(lab)
        if not regs:
            continue

        areas = [r.area for r in regs]
        r_main = regs[int(np.argmax(areas))]
        y, _x = r_main.centroid
        centroids.append((cls, y))

    centroids_sorted = sorted(centroids, key=lambda t: t[1])

    new_mask = np.zeros_like(mask, dtype=np.uint8)
    for new_label, (old_label, _) in enumerate(centroids_sorted, start=1):
        new_mask[mask == old_label] = new_label

    return new_mask


# ==========================
# 3) Inference
# ==========================

@torch.no_grad()
def run_inference_on_image(
    model: torch.nn.Module,
    img_path: str,
    device: torch.device,
    transform,
    roi_size=None,
    sw_batch_size: int = 4,
    overlap: float = 0.25,
    conf_thresh: float = None,
    apply_relabel: bool = True,
    min_size: int = 500,
) -> tuple[np.ndarray, Image.Image]:
    """
    Run inference on single image with sliding window approach.

    Returns:
        (cleaned_mask, overlay_base_image)
    """
    if roi_size is None:
        roi_size = config.SLIDING_WINDOW_SIZE
    if conf_thresh is None:
        conf_thresh = config.CONF_THRESH_DEFAULT

    logger.debug(f"[Atlas] Loading image: {img_path}")

    img_pil = Image.open(img_path).convert("RGB")
    img_np_hw3 = np.array(img_pil, dtype=np.float32)
    orig_h, orig_w = img_np_hw3.shape[:2]

    img_np = np.transpose(img_np_hw3, (2, 0, 1))

    data = {"image": img_np, "image_raw": img_np.copy()}
    data = transform(data)

    img_tensor = data["image"].unsqueeze(0).to(device)
    raw_tensor = data["image_raw"]

    logger.debug(f"[Atlas] Running sliding window inference (roi_size={roi_size}, overlap={overlap})")

    logits = sliding_window_inference(
        inputs=img_tensor,
        roi_size=roi_size,
        sw_batch_size=sw_batch_size,
        predictor=model,
        overlap=overlap,
        mode="gaussian",
        device=device,
        sw_device=device,
    )

    probs = torch.softmax(logits, dim=1)
    max_prob, pred = probs.max(dim=1)

    pred_mask = pred.squeeze(0).cpu().numpy()
    max_prob_np = max_prob.squeeze(0).cpu().numpy()

    pred_mask[max_prob_np < conf_thresh] = 0

    logger.debug(f"[Atlas] Postprocessing mask")
    cleaned_mask = postprocess_mask(pred_mask, num_classes=config.NUM_CLASSES, min_size=min_size)
    if apply_relabel:
        cleaned_mask = relabel_by_vertical_position(cleaned_mask)

    cleaned_mask = cleaned_mask[:orig_h, :orig_w].astype(np.uint8)

    raw_img_np = raw_tensor.permute(1, 2, 0).cpu().numpy()
    raw_img_np = np.clip(raw_img_np, 0, 255).astype(np.uint8)
    raw_img_np = raw_img_np[:orig_h, :orig_w, :]
    overlay_base = Image.fromarray(raw_img_np, mode="RGB")

    logger.info(f"[Atlas] Inference complete: {img_path}")

    return cleaned_mask, overlay_base


# ==========================
# 4) Color visualization
# ==========================

def mask_to_color_bgr(mask: np.ndarray, colors_bgr: dict = None) -> np.ndarray:
    """Convert class mask to colored BGR image"""
    if colors_bgr is None:
        colors_bgr = config.CLASS_COLORS_BGR

    h, w = mask.shape
    colored = np.zeros((h, w, 3), dtype=np.uint8)

    for cls_id, bgr_color in colors_bgr.items():
        colored[mask == cls_id] = bgr_color

    return colored


def blend_mask_with_image(image_bgr: np.ndarray, mask: np.ndarray, alpha: float = 0.5) -> tuple:
    """
    Blend segmentation mask with original image.

    Returns:
        (original_image, colored_mask, blended_image)
    """
    colored_mask = mask_to_color_bgr(mask)
    overlay = image_bgr.copy()
    overlay[mask > 0] = colored_mask[mask > 0]
    blended = cv2.addWeighted(overlay, alpha, image_bgr, 1 - alpha, 0)
    return image_bgr, colored_mask, blended
