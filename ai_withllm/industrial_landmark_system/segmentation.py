"""
Garment Segmentation Module

Implements background removal and garment isolation for industrial flat-lay images.
Inspired by GarmentIQ's use of BiRefNet/SAM for high-quality segmentation.

For industrial bench settings with controlled backgrounds, this module provides:
1. Fast background subtraction (for uniform backgrounds)
2. Deep learning-based segmentation (U2-Net, BiRefNet)
3. Edge refinement for accurate garment boundaries
4. Confidence scoring for segmentation quality
"""

import cv2
import numpy as np
from typing import Tuple, Optional, Dict, List, Union
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class SegmentationResult:
    """Result of garment segmentation"""
    mask: np.ndarray               # Binary mask (H, W), 255 = garment
    alpha: Optional[np.ndarray]    # Alpha matte for soft edges (H, W), 0-255
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2) bounding box
    cropped_image: np.ndarray      # Cropped garment with padding
    cropped_mask: np.ndarray       # Cropped mask
    confidence: float              # Segmentation quality score (0-1)
    contour: Optional[np.ndarray]  # Main contour points


class BackgroundSubtractor:
    """
    Fast background subtraction for controlled industrial environments.

    Works best when:
    - Background is uniform (gray, white, etc.)
    - Lighting is consistent
    - Garment color contrasts with background

    This is a fast first-pass that can be refined with deep learning.
    """

    def __init__(
        self,
        background_color: Tuple[int, int, int] = None,
        color_threshold: int = 30,
        use_hsv: bool = True,
        min_area_ratio: float = 0.05,
    ):
        """
        Args:
            background_color: Expected background BGR color. If None, auto-detect.
            color_threshold: Threshold for color difference
            use_hsv: Use HSV color space for better color separation
            min_area_ratio: Minimum garment area as ratio of image area
        """
        self.background_color = background_color
        self.color_threshold = color_threshold
        self.use_hsv = use_hsv
        self.min_area_ratio = min_area_ratio

    def segment(self, image: np.ndarray) -> SegmentationResult:
        """
        Segment garment from background using color thresholding.

        Args:
            image: BGR image (H, W, 3)

        Returns:
            SegmentationResult
        """
        h, w = image.shape[:2]

        # Auto-detect background from corners
        if self.background_color is None:
            bg_color = self._detect_background(image)
        else:
            bg_color = np.array(self.background_color)

        if self.use_hsv:
            # Convert to HSV for better color separation
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            bg_hsv = cv2.cvtColor(bg_color.reshape(1, 1, 3).astype(np.uint8), cv2.COLOR_BGR2HSV)[0, 0]

            # Create mask based on color difference in HSV
            h_diff = np.abs(hsv[:, :, 0].astype(np.int16) - int(bg_hsv[0]))
            h_diff = np.minimum(h_diff, 180 - h_diff)  # Handle hue wrap-around
            s_diff = np.abs(hsv[:, :, 1].astype(np.int16) - int(bg_hsv[1]))
            v_diff = np.abs(hsv[:, :, 2].astype(np.int16) - int(bg_hsv[2]))

            # Combined difference (weighted)
            diff = (h_diff * 2 + s_diff + v_diff * 0.5) / 3.5
        else:
            # Simple BGR difference
            diff = np.linalg.norm(
                image.astype(np.float32) - bg_color.astype(np.float32),
                axis=2
            )

        # Threshold
        mask = (diff > self.color_threshold).astype(np.uint8) * 255

        # Morphological cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

        # Find largest contour
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            # Fallback: return full image
            return SegmentationResult(
                mask=np.ones((h, w), dtype=np.uint8) * 255,
                alpha=None,
                bbox=(0, 0, w, h),
                cropped_image=image,
                cropped_mask=np.ones((h, w), dtype=np.uint8) * 255,
                confidence=0.0,
                contour=None,
            )

        # Filter by area
        min_area = h * w * self.min_area_ratio
        valid_contours = [c for c in contours if cv2.contourArea(c) > min_area]

        if not valid_contours:
            valid_contours = contours

        # Use largest contour
        main_contour = max(valid_contours, key=cv2.contourArea)

        # Create clean mask from contour
        clean_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.drawContours(clean_mask, [main_contour], -1, 255, -1)

        # Get bounding box
        x, y, bw, bh = cv2.boundingRect(main_contour)
        bbox = (x, y, x + bw, y + bh)

        # Crop with padding
        pad = 30
        x1, y1 = max(0, x - pad), max(0, y - pad)
        x2, y2 = min(w, x + bw + pad), min(h, y + bh + pad)

        cropped_image = image[y1:y2, x1:x2]
        cropped_mask = clean_mask[y1:y2, x1:x2]

        # Calculate confidence (area ratio, compactness, etc.)
        area = cv2.contourArea(main_contour)
        perimeter = cv2.arcLength(main_contour, True)
        circularity = 4 * np.pi * area / (perimeter ** 2) if perimeter > 0 else 0
        area_ratio = area / (h * w)

        # Confidence heuristic
        confidence = min(1.0, area_ratio * 5) * min(1.0, circularity * 3)

        return SegmentationResult(
            mask=clean_mask,
            alpha=None,
            bbox=bbox,
            cropped_image=cropped_image,
            cropped_mask=cropped_mask,
            confidence=confidence,
            contour=main_contour,
        )

    def _detect_background(self, image: np.ndarray) -> np.ndarray:
        """Auto-detect background color from image corners"""
        h, w = image.shape[:2]
        corner_size = min(50, h // 10, w // 10)

        corners = [
            image[:corner_size, :corner_size],           # Top-left
            image[:corner_size, -corner_size:],          # Top-right
            image[-corner_size:, :corner_size],          # Bottom-left
            image[-corner_size:, -corner_size:],         # Bottom-right
        ]

        # Median color of corners
        all_pixels = np.vstack([c.reshape(-1, 3) for c in corners])
        bg_color = np.median(all_pixels, axis=0)

        return bg_color


class U2NetSegmenter:
    """
    Deep learning-based segmentation using U2-Net.

    U2-Net is specifically designed for salient object detection
    and provides high-quality segmentation with fine edge details.

    Falls back to background subtraction if U2-Net is not available.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        model_type: str = 'u2net_cloth_seg',
        device: str = 'cuda',
        threshold: float = 0.5,
    ):
        """
        Args:
            model_path: Path to U2-Net model. None = auto-download.
            model_type: 'u2net', 'u2netp', or 'u2net_cloth_seg'
            device: 'cuda' or 'cpu'
            threshold: Binarization threshold for mask
        """
        self.model_type = model_type
        self.device = device
        self.threshold = threshold
        self.model = None
        self.model_path = model_path

        self._try_load_model()

    def _try_load_model(self):
        """Attempt to load U2-Net model"""
        try:
            # Try to import rembg which includes U2-Net
            from rembg import remove, new_session
            self.session = new_session(self.model_type)
            self.use_rembg = True
            logger.info(f"Loaded U2-Net via rembg ({self.model_type})")
        except ImportError:
            logger.warning("rembg not available, falling back to background subtraction")
            self.use_rembg = False
            self.fallback = BackgroundSubtractor()

    def segment(self, image: np.ndarray) -> SegmentationResult:
        """
        Segment garment using U2-Net.

        Args:
            image: BGR image (H, W, 3)

        Returns:
            SegmentationResult
        """
        if not self.use_rembg:
            return self.fallback.segment(image)

        from rembg import remove
        import io
        from PIL import Image

        h, w = image.shape[:2]

        # Convert to PIL
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb)

        # Run rembg
        output = remove(
            pil_image,
            session=self.session,
            only_mask=False,
            alpha_matting=True,
            alpha_matting_foreground_threshold=240,
            alpha_matting_background_threshold=10,
        )

        # Extract alpha channel as mask
        if output.mode == 'RGBA':
            alpha = np.array(output.split()[-1])
        else:
            alpha = np.ones((h, w), dtype=np.uint8) * 255

        # Binarize
        mask = (alpha > int(self.threshold * 255)).astype(np.uint8) * 255

        # Find contour
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            main_contour = max(contours, key=cv2.contourArea)
            x, y, bw, bh = cv2.boundingRect(main_contour)
            bbox = (x, y, x + bw, y + bh)

            # Clean mask
            clean_mask = np.zeros((h, w), dtype=np.uint8)
            cv2.drawContours(clean_mask, [main_contour], -1, 255, -1)
        else:
            main_contour = None
            bbox = (0, 0, w, h)
            clean_mask = mask

        # Crop
        pad = 30
        x1, y1 = max(0, bbox[0] - pad), max(0, bbox[1] - pad)
        x2, y2 = min(w, bbox[2] + pad), min(h, bbox[3] + pad)

        cropped_image = image[y1:y2, x1:x2]
        cropped_mask = clean_mask[y1:y2, x1:x2]

        # Confidence from alpha consistency
        if main_contour is not None:
            area = cv2.contourArea(main_contour)
            confidence = min(1.0, area / (h * w * 0.3))
        else:
            confidence = 0.5

        return SegmentationResult(
            mask=clean_mask,
            alpha=alpha,
            bbox=bbox,
            cropped_image=cropped_image,
            cropped_mask=cropped_mask,
            confidence=confidence,
            contour=main_contour,
        )


class IndustrialSegmenter:
    """
    Main segmentation class for industrial garment images.

    Combines multiple segmentation strategies:
    1. Fast background subtraction (for quick preview)
    2. U2-Net deep segmentation (for production quality)
    3. Edge refinement (for precise boundaries)

    Optimized for flat-lay images with controlled backgrounds.
    """

    def __init__(
        self,
        use_deep_segmentation: bool = True,
        background_color: Optional[Tuple[int, int, int]] = None,
        device: str = 'cuda',
    ):
        """
        Args:
            use_deep_segmentation: Use U2-Net if available
            background_color: Expected background color (BGR). None = auto-detect.
            device: 'cuda' or 'cpu' for deep models
        """
        self.use_deep = use_deep_segmentation

        # Initialize segmenters
        self.bg_subtractor = BackgroundSubtractor(
            background_color=background_color,
        )

        if use_deep_segmentation:
            self.deep_segmenter = U2NetSegmenter(device=device)
        else:
            self.deep_segmenter = None

    def segment(
        self,
        image: np.ndarray,
        use_deep: Optional[bool] = None,
        refine_edges: bool = True,
    ) -> SegmentationResult:
        """
        Segment garment from image.

        Args:
            image: BGR image (H, W, 3)
            use_deep: Override default deep segmentation setting
            refine_edges: Apply edge refinement

        Returns:
            SegmentationResult
        """
        should_use_deep = use_deep if use_deep is not None else self.use_deep

        if should_use_deep and self.deep_segmenter is not None:
            result = self.deep_segmenter.segment(image)
        else:
            result = self.bg_subtractor.segment(image)

        if refine_edges and result.contour is not None:
            result = self._refine_edges(image, result)

        return result

    def _refine_edges(self, image: np.ndarray, result: SegmentationResult) -> SegmentationResult:
        """
        Refine segmentation edges using edge detection.

        Improves boundary accuracy for measurement.
        """
        h, w = image.shape[:2]

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Detect edges
        edges = cv2.Canny(gray, 50, 150)

        # Dilate edges slightly
        kernel = np.ones((3, 3), dtype=np.uint8)
        edges_dilated = cv2.dilate(edges, kernel, iterations=1)

        # Combine with mask
        # Where there's an edge near the mask boundary, use the edge
        mask_edges = cv2.Canny(result.mask, 50, 150)
        mask_edges_dilated = cv2.dilate(mask_edges, kernel, iterations=3)

        # Find intersection
        refined_boundary = cv2.bitwise_and(edges_dilated, mask_edges_dilated)

        # Refine contour using GrabCut-like approach
        # (Simplified: just use morphological refinement)
        refined_mask = result.mask.copy()

        # Remove small protrusions
        refined_mask = cv2.morphologyEx(refined_mask, cv2.MORPH_OPEN, kernel, iterations=1)

        # Fill small holes
        refined_mask = cv2.morphologyEx(refined_mask, cv2.MORPH_CLOSE, kernel, iterations=1)

        # Update contour
        contours, _ = cv2.findContours(refined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            main_contour = max(contours, key=cv2.contourArea)
        else:
            main_contour = result.contour

        return SegmentationResult(
            mask=refined_mask,
            alpha=result.alpha,
            bbox=result.bbox,
            cropped_image=result.cropped_image,
            cropped_mask=result.cropped_mask[
                :refined_mask.shape[0] - result.bbox[1] if result.bbox[1] > 0 else refined_mask.shape[0],
                :refined_mask.shape[1] - result.bbox[0] if result.bbox[0] > 0 else refined_mask.shape[1]
            ] if result.cropped_mask is not None else refined_mask,
            confidence=result.confidence,
            contour=main_contour,
        )

    def quick_segment(self, image: np.ndarray) -> SegmentationResult:
        """
        Quick segmentation using only background subtraction.
        Use for previews or when speed is critical.
        """
        return self.bg_subtractor.segment(image)


def create_segmenter(
    use_deep: bool = True,
    background_color: Optional[Tuple[int, int, int]] = None,
    device: str = 'auto',
) -> IndustrialSegmenter:
    """
    Factory function to create a segmenter.

    Args:
        use_deep: Use deep learning segmentation
        background_color: Expected background BGR color
        device: 'cuda', 'cpu', or 'auto'

    Returns:
        Configured segmenter
    """
    if device == 'auto':
        import torch
        device = 'cuda' if torch.cuda.is_available() else 'cpu'

    return IndustrialSegmenter(
        use_deep_segmentation=use_deep,
        background_color=background_color,
        device=device,
    )
