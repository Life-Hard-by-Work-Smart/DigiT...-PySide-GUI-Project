"""
Keypoint Extraction - Extract 4 corners + centroid from vertebral segmentation

Takes colored segmentation mask and extracts LabelMe-format keypoints.
Handles robust contour approximation, quad fitting, and subpixel refinement.

Original code from toBeIntegrated/Src/Atlas/keypoint_extraction.py
Adapted for use as library module in GUI application.
"""

import json
from pathlib import Path

import cv2
import numpy as np

from core.models.UNet import config
from logger import logger


# ==========================
# Utility Functions
# ==========================

def unique_colors_bgr(img_bgr: np.ndarray) -> list[tuple[int, int, int]]:
    """Return unique BGR colors excluding black background (0,0,0)."""
    flat = img_bgr.reshape(-1, 3)
    colors = np.unique(flat, axis=0)
    colors = [tuple(map(int, c)) for c in colors]
    colors = [c for c in colors if c != (0, 0, 0)]
    return colors


def mask_from_color(img_bgr: np.ndarray, color_bgr: tuple[int, int, int], tol: int = 0) -> np.ndarray:
    """Binary mask of pixels matching a BGR color, optionally with tolerance."""
    b, g, r = color_bgr
    if tol <= 0:
        m = (img_bgr[:, :, 0] == b) & (img_bgr[:, :, 1] == g) & (img_bgr[:, :, 2] == r)
        return m.astype(np.uint8) * 255
    lower = np.array([max(0, b - tol), max(0, g - tol), max(0, r - tol)], dtype=np.uint8)
    upper = np.array([min(255, b + tol), min(255, g + tol), min(255, r + tol)], dtype=np.uint8)
    return cv2.inRange(img_bgr, lower, upper)


def clean_binary(mask_u8: np.ndarray, k: int = 5) -> np.ndarray:
    """Binary morphological cleaning: opening + closing"""
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    m = cv2.morphologyEx(mask_u8, cv2.MORPH_OPEN, kernel, iterations=1)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, kernel, iterations=2)
    return m


def main_contour(mask_u8: np.ndarray):
    """Extract largest contour from binary mask"""
    cnts, _ = cv2.findContours(mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cnts:
        return None
    return max(cnts, key=cv2.contourArea)


def approx_poly_n(contour: np.ndarray, n_vertices: int) -> np.ndarray | None:
    """
    Approximate contour to exactly n_vertices.
    Returns Nx2 array or None.
    """
    try:
        approx = cv2.approxPolyN(contour, n_vertices, True)
        if approx is not None and len(approx) == n_vertices:
            return approx.reshape(-1, 2)
    except Exception:
        pass

    peri = cv2.arcLength(contour, True)
    for eps in np.linspace(0.005, 0.20, 40):
        approx = cv2.approxPolyDP(contour, eps * peri, True)
        if len(approx) == n_vertices:
            return approx.reshape(-1, 2)

    return None


def pairwise_min_distance(pts: np.ndarray) -> float:
    """Return minimum pairwise Euclidean distance between points."""
    pts = pts.astype(np.float32)
    min_dist = np.inf
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            d = float(np.linalg.norm(pts[i] - pts[j]))
            min_dist = min(min_dist, d)
    return 0.0 if not np.isfinite(min_dist) else min_dist


def polygon_min_edge_length(pts: np.ndarray) -> float:
    """Return minimum edge length of a closed polygon."""
    pts = pts.astype(np.float32)
    min_edge = np.inf
    for i in range(len(pts)):
        p1 = pts[i]
        p2 = pts[(i + 1) % len(pts)]
        d = float(np.linalg.norm(p1 - p2))
        min_edge = min(min_edge, d)
    return 0.0 if not np.isfinite(min_edge) else min_edge


def polygon_area_abs(pts: np.ndarray) -> float:
    """Return absolute polygon area."""
    pts = pts.astype(np.float32).reshape(-1, 1, 2)
    return float(abs(cv2.contourArea(pts)))


def merge_close_points(pts: np.ndarray, merge_dist: float = 6.0) -> np.ndarray:
    """Merge points closer than merge_dist by replacing with their mean."""
    if pts is None or len(pts) == 0:
        return np.empty((0, 2), dtype=np.float32)

    pts_list = [p.astype(np.float32) for p in pts]
    merged = []

    while pts_list:
        ref = pts_list.pop(0)
        group = [ref]
        rest = []

        for p in pts_list:
            if np.linalg.norm(p - ref) < merge_dist:
                group.append(p)
            else:
                rest.append(p)

        merged.append(np.mean(group, axis=0))
        pts_list = rest

    return np.array(merged, dtype=np.float32)


def quad_is_valid(
    pts: np.ndarray,
    min_pair_dist: float = 8.0,
    min_area: float = 50.0,
    min_edge: float = 6.0,
) -> bool:
    """Validate 4-point polygon to reject degenerate quads."""
    if pts is None or len(pts) != 4:
        return False

    pts = pts.astype(np.float32)

    if pairwise_min_distance(pts) < min_pair_dist:
        return False

    if polygon_area_abs(pts) < min_area:
        return False

    if polygon_min_edge_length(pts) < min_edge:
        return False

    return True


def approx_quad(contour: np.ndarray) -> np.ndarray | None:
    """
    Robust 4-corner extraction.
    1) try polygon approximation
    2) merge almost duplicated points if needed
    3) fallback to minAreaRect on convex hull
    """
    quad = approx_poly_n(contour, 4)
    if quad is not None:
        quad = quad.astype(np.float32)
        if quad_is_valid(quad):
            return quad

        merged = merge_close_points(quad, merge_dist=6.0)
        if len(merged) == 4 and quad_is_valid(merged):
            return merged.astype(np.float32)

    hull = cv2.convexHull(contour)
    rect = cv2.minAreaRect(hull)
    box = cv2.boxPoints(rect).astype(np.float32)

    if quad_is_valid(box, min_pair_dist=5.0, min_area=30.0, min_edge=5.0):
        return box

    return None


def order_quad_clockwise(pts_xy: np.ndarray) -> np.ndarray:
    """Order quad corners as: TL, TR, BR, BL"""
    pts = pts_xy.astype(np.float32)

    y_order = np.argsort(pts[:, 1])
    top = pts[y_order[:2]]
    bottom = pts[y_order[2:]]

    top = top[np.argsort(top[:, 0])]
    bottom = bottom[np.argsort(bottom[:, 0])]

    tl, tr = top
    bl, br = bottom

    return np.array([tl, tr, br, bl], dtype=np.float32)


def order_quad_from_previous_bottom(
    pts_xy: np.ndarray,
    prev_bl: np.ndarray | None,
    prev_br: np.ndarray | None,
) -> np.ndarray:
    """
    Order current vertebra corners using previous vertebra bottom points.
    Uses previous BL/BR as reference for current TL/TR.
    """
    pts = pts_xy.astype(np.float32)

    if prev_bl is None or prev_br is None or len(pts) != 4:
        return order_quad_clockwise(pts)

    best_score = np.inf
    best_top_idx = None
    best_assignment = None

    for i in range(4):
        for j in range(i + 1, 4):
            pair = pts[[i, j]]

            s1 = np.linalg.norm(pair[0] - prev_bl) + np.linalg.norm(pair[1] - prev_br)
            s2 = np.linalg.norm(pair[0] - prev_br) + np.linalg.norm(pair[1] - prev_bl)

            if s1 <= s2:
                score = s1
                assignment = (0, 1)
            else:
                score = s2
                assignment = (1, 0)

            if score < best_score:
                best_score = score
                best_top_idx = (i, j)
                best_assignment = assignment

    if best_top_idx is None:
        return order_quad_clockwise(pts)

    top_idx = list(best_top_idx)
    bottom_idx = [k for k in range(4) if k not in top_idx]

    top_pair = pts[top_idx]
    bottom_pair = pts[bottom_idx]

    tl = top_pair[best_assignment[0]]
    tr = top_pair[best_assignment[1]]

    bottom_pair = bottom_pair[np.argsort(bottom_pair[:, 0])]
    bl, br = bottom_pair[0], bottom_pair[1]

    return np.array([tl, tr, br, bl], dtype=np.float32)


def order_triangle_bl_br_apex(pts_xy: np.ndarray) -> np.ndarray:
    """Order 3 points to (bottom-left, bottom-right, apex)."""
    pts = pts_xy.astype(np.float32)

    apex_idx = np.argmin(pts[:, 1])
    apex = pts[apex_idx]

    base = np.delete(pts, apex_idx, axis=0)
    if base[0, 0] <= base[1, 0]:
        bl, br = base[0], base[1]
    else:
        bl, br = base[1], base[0]

    return np.stack([bl, br, apex], axis=0)


def refine_subpix(mask_u8: np.ndarray, corners_xy: np.ndarray, win: int = 7) -> np.ndarray:
    """Subpixel refinement using cornerSubPix on blurred mask."""
    gray = cv2.GaussianBlur(mask_u8, (5, 5), 0)
    c = corners_xy.astype(np.float32).reshape(-1, 1, 2)
    term = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 1e-4)
    refined = cv2.cornerSubPix(gray, c, (win, win), (-1, -1), term)
    return refined.reshape(-1, 2)


def centroid_of_mask(mask_u8: np.ndarray) -> tuple[float, float] | None:
    """Calculate centroid of binary mask."""
    m = cv2.moments(mask_u8, binaryImage=True)
    if m["m00"] == 0:
        return None
    cx = m["m10"] / m["m00"]
    cy = m["m01"] / m["m00"]
    return float(cx), float(cy)


def bottom_edge_endpoints_from_contour(contour: np.ndarray, band_frac: float = 0.12, min_band_px: int = 8):
    """Extract bottom edge endpoints."""
    pts = contour.reshape(-1, 2).astype(np.float32)

    y = pts[:, 1]
    min_y = float(np.min(y))
    max_y = float(np.max(y))
    height = max_y - min_y

    band = max(min_band_px, int(round(band_frac * height)))
    thresh = max_y - band

    bottom_pts = pts[y >= thresh]
    if len(bottom_pts) < 2:
        idx = np.argsort(y)[-2:]
        bottom_pts = pts[idx]

    bl = bottom_pts[np.argmin(bottom_pts[:, 0])]
    br = bottom_pts[np.argmax(bottom_pts[:, 0])]

    if bl[0] > br[0]:
        bl, br = br, bl

    return bl, br


def apex_top_point_from_contour(contour: np.ndarray, y_tol: int = 2) -> np.ndarray:
    """Return apex (topmost point) using y-band for stability."""
    pts = contour.reshape(-1, 2).astype(np.float32)
    min_y = float(np.min(pts[:, 1]))
    band = pts[pts[:, 1] <= (min_y + y_tol)]
    if len(band) == 0:
        band = pts[np.argmin(pts[:, 1]): np.argmin(pts[:, 1]) + 1]
    apex = np.mean(band, axis=0)
    return apex


# ==========================
# LabelMe Output
# ==========================

def labelme_point(label: str, x: float, y: float) -> dict:
    """Create LabelMe format point"""
    return {
        "label": label,
        "points": [[float(x), float(y)]],
        "group_id": None,
        "description": "",
        "shape_type": "point",
        "flags": {},
    }


def build_labelme_json(image_path: str, w: int, h: int, shapes: list[dict], version: str = "5.2.1") -> dict:
    """Build complete LabelMe JSON structure"""
    return {
        "version": version,
        "flags": {},
        "shapes": shapes,
        "imagePath": Path(image_path).name,
        "imageData": "",
        "imageHeight": int(h),
        "imageWidth": int(w),
    }


# ==========================
# Main Extraction
# ==========================

def extract_keypoints_from_mask(
    mask_bgr: np.ndarray,
    image_name: str,
    image_width: int,
    image_height: int,
    labels: list[str] = None,
    tol: int = 0,
    min_area: int = 300,
) -> dict:
    """
    Extract keypoints from colored segmentation mask.

    Returns LabelMe-format JSON dict with keypoints.
    """
    colors = unique_colors_bgr(mask_bgr)
    if not colors:
        logger.warning(f"[Keypoints] No non-black colors found in mask")
        return build_labelme_json(image_name, image_width, image_height, [])

    vertebra_items = []
    for c in colors:
        m = mask_from_color(mask_bgr, c, tol=tol)
        m = clean_binary(m, k=5)

        if cv2.countNonZero(m) < min_area:
            continue

        ctr = centroid_of_mask(m)
        if ctr is None:
            continue

        vertebra_items.append({"color": c, "mask": m, "centroid": ctr})

    if not vertebra_items:
        logger.warning(f"[Keypoints] No usable regions after filtering")
        return build_labelme_json(image_name, image_width, image_height, [])

    vertebra_items.sort(key=lambda it: it["centroid"][1])
    n = len(vertebra_items)

    if labels is None:
        default = config.VERTEBRAE_CLASSES  # ["C2", "C3", ...]
        if n == len(default):
            names = default
        else:
            names = [f"V{i+1}" for i in range(n)]
    else:
        if len(labels) == n:
            names = labels
        elif len(labels) < n:
            start = n - len(labels)
            vertebra_items = vertebra_items[start:]
            names = labels
            n = len(vertebra_items)
        else:
            names = labels[:n]

    shapes: list[dict] = []
    prev_bl = None
    prev_br = None

    for it, name in zip(vertebra_items, names):
        m = it["mask"]
        cnt = main_contour(m)
        if cnt is None or cv2.contourArea(cnt) < min_area:
            continue

        # Special handling for C2 (triangle)
        if name == "C2":
            tri = approx_poly_n(cnt, 3)

            if tri is not None:
                tri = order_triangle_bl_br_apex(tri)
                tri = refine_subpix(m, tri, win=7)
                tri = order_triangle_bl_br_apex(tri)

                bl, br, apex_ref = tri
            else:
                bl, br = bottom_edge_endpoints_from_contour(cnt, band_frac=0.5, min_band_px=8)
                apex = apex_top_point_from_contour(cnt, y_tol=3)
                pts3 = np.stack([bl, br, apex], axis=0)
                pts3 = refine_subpix(m, pts3, win=7)
                bl, br, apex_ref = pts3[0], pts3[1], pts3[2]

            shapes.append(labelme_point(f"{name} bottom left", bl[0], bl[1]))
            shapes.append(labelme_point(f"{name} bottom right", br[0], br[1]))
            shapes.append(labelme_point(f"{name} centroid", apex_ref[0], apex_ref[1]))

            prev_bl = bl.astype(np.float32)
            prev_br = br.astype(np.float32)
            continue

        # Standard quad for C3-C7
        quad = approx_quad(cnt)
        if quad is None:
            continue

        quad = refine_subpix(m, quad, win=7)

        if not quad_is_valid(quad, min_pair_dist=5.0, min_area=30.0, min_edge=4.0):
            rect = cv2.minAreaRect(cv2.convexHull(cnt))
            quad = cv2.boxPoints(rect).astype(np.float32)

        quad = order_quad_from_previous_bottom(quad, prev_bl, prev_br)
        tl, tr, br, bl = quad

        shapes.append(labelme_point(f"{name} top left", tl[0], tl[1]))
        shapes.append(labelme_point(f"{name} top right", tr[0], tr[1]))
        shapes.append(labelme_point(f"{name} bottom right", br[0], br[1]))
        shapes.append(labelme_point(f"{name} bottom left", bl[0], bl[1]))

        prev_bl = bl.astype(np.float32)
        prev_br = br.astype(np.float32)

    data = build_labelme_json(image_name, image_width, image_height, shapes, version="5.2.1")

    logger.info(f"[Keypoints] Extracted {len(shapes)} keypoints from mask")

    return data
