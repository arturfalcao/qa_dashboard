#!/usr/bin/env python3
"""
Segmentation module for isolating garments from background.
Provides OpenCV baseline with production-ready SAM integration.
"""

import cv2
import numpy as np
from typing import Optional, Dict, Any, Tuple, List
import logging
import torch

logger = logging.getLogger(__name__)


class GarmentSegmenter:
    """
    Segments garments from black bench background.
    Uses robust OpenCV pipeline by default, with SAM refinement when enabled.
    """

    def __init__(self, use_sam: bool = False, sam_checkpoint: Optional[str] = None,
                 device: Optional[str] = None):
        """
        Initialize segmenter.

        Args:
            use_sam: Whether to use Segment Anything Model
            sam_checkpoint: Path to SAM model checkpoint
            device: Device for SAM ('cuda', 'cpu', or None for auto-detect)
        """
        self.use_sam = use_sam
        self.sam = None
        self.sam_predictor = None

        # Auto-detect device if not specified
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device

        if use_sam:
            self._init_sam(sam_checkpoint)

        # Parameters for OpenCV segmentation
        self.min_area_ratio = 0.15  # Minimum area as ratio of image size (15%)
        self.max_area_ratio = 0.85  # Maximum area as ratio of image size (85%)
        self.margin_px = 15          # Minimum margin from image edges in pixels

    def _init_sam(self, checkpoint_path: Optional[str]):
        """Initialize SAM model with proper error handling."""
        if not checkpoint_path:
            logger.warning("SAM checkpoint not provided, disabling SAM")
            self.use_sam = False
            return

        try:
            from segment_anything import sam_model_registry, SamPredictor

            # Detect model type from checkpoint name
            if 'vit_h' in checkpoint_path.lower():
                model_type = 'vit_h'
            elif 'vit_l' in checkpoint_path.lower():
                model_type = 'vit_l'
            else:
                model_type = 'vit_b'  # Default to base model

            logger.info(f"Loading SAM model type: {model_type} from {checkpoint_path}")

            # Load SAM model
            sam = sam_model_registry[model_type](checkpoint=checkpoint_path)
            sam.to(device=self.device)
            sam.eval()

            # Create predictor
            self.sam_predictor = SamPredictor(sam)
            self.sam = sam

            logger.info(f"SAM model loaded successfully on {self.device}")

        except ImportError as e:
            logger.error(f"SAM not installed: {e}")
            logger.info("Install with: pip install segment-anything")
            self.use_sam = False
        except FileNotFoundError:
            logger.error(f"SAM checkpoint not found: {checkpoint_path}")
            self.use_sam = False
        except Exception as e:
            logger.error(f"Failed to initialize SAM: {e}")
            self.use_sam = False

    def segment_opencv(self, image: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Segment garment using robust OpenCV pipeline.

        Pipeline:
        1. Adaptive thresholding (handles uneven lighting)
        2. Otsu's method for global threshold
        3. Morphological operations to clean up
        4. Hole filling
        5. Largest component selection

        Args:
            image: Input BGR image

        Returns:
            mask: Binary mask (255 for garment, 0 for background)
            info: Segmentation information including QC status
        """
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        h, w = gray.shape
        total_pixels = h * w

        # Step 1: Adaptive threshold (handles local lighting variations)
        adaptive = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            blockSize=51,  # Larger block for garment-scale features
            C=10
        )

        # Step 2: Global Otsu threshold
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Step 3: Combine adaptive and Otsu
        combined = cv2.bitwise_or(adaptive, otsu)

        # Step 4: Morphological cleaning
        kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        cleaned = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel_small)

        kernel_large = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        closed = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel_large)

        # Step 5: Fill holes and select largest component
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        mask = np.zeros_like(closed)
        if contours:
            # Sort by area and get largest
            contours = sorted(contours, key=cv2.contourArea, reverse=True)
            cv2.drawContours(mask, [contours[0]], -1, 255, -1)

        # Compute segmentation info with QC
        info = self._compute_mask_info(mask, image.shape[:2])
        info['method'] = 'opencv'

        return mask, info

    def segment_sam_refine(self, image: np.ndarray, initial_mask: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Refine segmentation using SAM with extreme points prompting.

        Args:
            image: Input BGR image
            initial_mask: Initial mask from OpenCV or other source

        Returns:
            mask: Refined binary mask
            info: Segmentation information
        """
        if not self.use_sam or self.sam_predictor is None:
            logger.warning("SAM not available, returning initial mask")
            info = self._compute_mask_info(initial_mask, image.shape[:2])
            info['method'] = 'opencv_fallback'
            return initial_mask, info

        try:
            # Convert BGR to RGB for SAM
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Set image in predictor
            self.sam_predictor.set_image(image_rgb)

            # Extract extreme points from initial mask for positive prompts
            ys, xs = np.where(initial_mask > 0)

            if len(xs) == 0 or len(ys) == 0:
                # No initial mask, use center points
                h, w = image.shape[:2]
                pos_points = np.array([
                    [w // 2, h // 2],
                    [w // 3, h // 2],
                    [2 * w // 3, h // 2],
                ], dtype=np.float32)
            else:
                x_min, x_max = xs.min(), xs.max()
                y_min, y_max = ys.min(), ys.max()

                # Use extreme points as positive prompts
                pos_points = np.array([
                    [x_min, (y_min + y_max) // 2],  # Left center
                    [x_max, (y_min + y_max) // 2],  # Right center
                    [(x_min + x_max) // 2, y_min],  # Top center
                    [(x_min + x_max) // 2, y_max],  # Bottom center
                    [(x_min + x_max) // 2, (y_min + y_max) // 2],  # Center
                ], dtype=np.float32)

            # Add negative points at corners (likely ArUco marker locations)
            h, w = image.shape[:2]
            neg_points = np.array([
                [10, 10],           # Top-left corner
                [w - 10, 10],       # Top-right corner
                [10, h - 10],       # Bottom-left corner
                [w - 10, h - 10],   # Bottom-right corner
            ], dtype=np.float32)

            # Combine points and labels
            all_points = np.vstack([pos_points, neg_points])
            point_labels = np.array([1] * len(pos_points) + [0] * len(neg_points))

            # Predict masks
            masks, scores, logits = self.sam_predictor.predict(
                point_coords=all_points,
                point_labels=point_labels,
                multimask_output=True,
                return_logits=True
            )

            # Select best mask (highest score)
            best_idx = np.argmax(scores)
            mask = masks[best_idx].astype(np.uint8) * 255

            # Compute info
            info = self._compute_mask_info(mask, image.shape[:2])
            info['method'] = 'sam'
            info['sam_score'] = float(scores[best_idx])
            info['num_masks_generated'] = len(masks)

            logger.info(f"SAM refinement complete, score: {scores[best_idx]:.3f}")

            return mask, info

        except Exception as e:
            logger.error(f"SAM segmentation failed: {e}, falling back to initial mask")
            info = self._compute_mask_info(initial_mask, image.shape[:2])
            info['method'] = 'opencv_fallback'
            info['sam_error'] = str(e)
            return initial_mask, info

    def segment(self, image: np.ndarray, force_sam: bool = False) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Main segmentation method with automatic refinement decision.

        Args:
            image: Input BGR image
            force_sam: Force SAM refinement regardless of QC

        Returns:
            mask: Binary mask (255 for garment, 0 for background)
            info: Segmentation information with QC status
        """
        # Always start with OpenCV baseline
        mask, info = self.segment_opencv(image)

        # Check if refinement needed
        qc_failed = not info.get('quality_checks', {}).get('ok', False)

        # Use SAM if: force_sam=True OR (SAM enabled AND QC failed)
        if force_sam or (self.use_sam and qc_failed):
            logger.info(f"Applying SAM refinement (force={force_sam}, qc_failed={qc_failed})")
            mask, info = self.segment_sam_refine(image, mask)

        return mask, info

    def _compute_mask_info(self, mask: np.ndarray, image_shape: Tuple[int, int]) -> Dict[str, Any]:
        """
        Compute information about the segmentation mask with comprehensive QC.

        Args:
            mask: Binary mask
            image_shape: (height, width) of original image

        Returns:
            Dictionary with mask statistics and QC results
        """
        h, w = image_shape
        total_pixels = h * w

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        info = {
            'mask_area': int(np.sum(mask > 0)),
            'area_ratio': float(np.sum(mask > 0) / total_pixels),
            'num_components': len(contours)
        }

        if contours:
            # Get largest contour
            largest = max(contours, key=cv2.contourArea)
            x, y, w_box, h_box = cv2.boundingRect(largest)

            info.update({
                'bbox': [int(x), int(y), int(w_box), int(h_box)],
                'bbox_center': [int(x + w_box // 2), int(y + h_box // 2)],
                'aspect_ratio': float(w_box / h_box) if h_box > 0 else 1.0,
                'solidity': float(cv2.contourArea(largest) / (w_box * h_box)) if w_box * h_box > 0 else 0,
                'margin_distances': {
                    'top': int(y),
                    'bottom': int(h - (y + h_box)),
                    'left': int(x),
                    'right': int(w - (x + w_box))
                }
            })

            # Quality checks with updated thresholds
            min_margin = self.margin_px

            area_ok = self.min_area_ratio <= info['area_ratio'] <= self.max_area_ratio
            margins_ok = all(d >= min_margin for d in info['margin_distances'].values())
            single_component = len(contours) == 1
            solidity_ok = info['solidity'] > 0.7  # Garments should be fairly solid

            info['quality_checks'] = {
                'area_ok': area_ok,
                'margins_ok': margins_ok,
                'single_component': single_component,
                'solidity_ok': solidity_ok,
                'ok': area_ok and margins_ok and single_component and solidity_ok
            }
        else:
            info.update({
                'bbox': None,
                'quality_checks': {
                    'area_ok': False,
                    'margins_ok': False,
                    'single_component': False,
                    'solidity_ok': False,
                    'ok': False
                }
            })

        return info

    def refine_mask(self, mask: np.ndarray, image: np.ndarray) -> np.ndarray:
        """
        Refine mask edges using GrabCut or similar techniques.

        Args:
            mask: Initial binary mask
            image: Original BGR image

        Returns:
            Refined mask
        """
        if np.sum(mask) == 0:
            return mask

        try:
            # Initialize GrabCut with the mask
            gc_mask = np.zeros(mask.shape, dtype=np.uint8)
            gc_mask[mask > 0] = cv2.GC_PR_FGD  # Probable foreground
            gc_mask[mask == 0] = cv2.GC_BGD    # Definite background

            # Add definite foreground in center of mask
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                # Get center region
                M = cv2.moments(contours[0])
                if M['m00'] > 0:
                    cx = int(M['m10'] / M['m00'])
                    cy = int(M['m01'] / M['m00'])
                    radius = 30
                    cv2.circle(gc_mask, (cx, cy), radius, cv2.GC_FGD, -1)

            # Apply GrabCut
            bgd_model = np.zeros((1, 65), np.float64)
            fgd_model = np.zeros((1, 65), np.float64)

            cv2.grabCut(image, gc_mask, None, bgd_model, fgd_model, 3, cv2.GC_INIT_WITH_MASK)

            # Extract refined mask
            refined = np.where((gc_mask == cv2.GC_FGD) | (gc_mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)

            # Ensure we didn't lose too much
            if np.sum(refined) < 0.5 * np.sum(mask):
                logger.warning("GrabCut removed too much, keeping original mask")
                return mask

            return refined

        except Exception as e:
            logger.warning(f"Mask refinement failed: {e}")
            return mask


def visualize_segmentation(image: np.ndarray, mask: np.ndarray, info: Dict[str, Any]) -> np.ndarray:
    """
    Visualize segmentation result with overlay and info.

    Args:
        image: Original image
        mask: Segmentation mask
        info: Segmentation info dictionary

    Returns:
        Visualization image
    """
    vis = image.copy()

    # Create colored overlay
    overlay = np.zeros_like(vis)
    overlay[mask > 0] = [0, 255, 0]  # Green for garment

    # Blend with original
    vis = cv2.addWeighted(vis, 0.7, overlay, 0.3, 0)

    # Draw bounding box if available
    if info.get('bbox'):
        x, y, w, h = info['bbox']
        cv2.rectangle(vis, (x, y), (x + w, y + h), (255, 0, 0), 2)

    # Add text info
    text_y = 30

    # Show method used
    method = info.get('method', 'unknown')
    cv2.putText(vis, f"Method: {method}", (10, text_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    text_y += 25

    # Show QC results
    qc = info.get('quality_checks', {})
    overall_ok = qc.get('ok', False)
    color = (0, 255, 0) if overall_ok else (0, 0, 255)
    cv2.putText(vis, f"QC: {'PASS' if overall_ok else 'FAIL'}",
                (10, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    text_y += 25

    # Individual checks
    for key, value in qc.items():
        if key != 'ok':
            color = (0, 255, 0) if value else (0, 0, 255)
            cv2.putText(vis, f"  {key}: {'OK' if value else 'FAIL'}",
                       (10, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            text_y += 20

    # Add area ratio
    if 'area_ratio' in info:
        cv2.putText(vis, f"Area: {info['area_ratio']*100:.1f}%",
                   (10, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        text_y += 20

    # Add SAM score if available
    if 'sam_score' in info:
        cv2.putText(vis, f"SAM Score: {info['sam_score']:.3f}",
                   (10, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    return vis


def main():
    """Test segmentation on an image."""
    import argparse

    parser = argparse.ArgumentParser(description='Test garment segmentation')
    parser.add_argument('--image', required=True, help='Input image')
    parser.add_argument('--sam', action='store_true', help='Use SAM if available')
    parser.add_argument('--sam-checkpoint', help='Path to SAM checkpoint')
    parser.add_argument('--output', help='Output mask path')
    parser.add_argument('--visualize', action='store_true', help='Show visualization')
    parser.add_argument('--force-sam', action='store_true', help='Force SAM refinement')
    args = parser.parse_args()

    # Load image
    image = cv2.imread(args.image)
    if image is None:
        print(f"Error: Could not load {args.image}")
        return

    # Initialize segmenter
    segmenter = GarmentSegmenter(use_sam=args.sam, sam_checkpoint=args.sam_checkpoint)

    # Segment
    print(f"Segmenting with SAM={'enabled' if segmenter.use_sam else 'disabled'}...")
    mask, info = segmenter.segment(image, force_sam=args.force_sam)

    # Print info
    print(f"Segmentation results:")
    print(f"  - Method: {info.get('method', 'unknown')}")
    print(f"  - Area ratio: {info.get('area_ratio', 0)*100:.1f}%")
    print(f"  - Components: {info.get('num_components', 0)}")
    if info.get('bbox'):
        print(f"  - Bounding box: {info['bbox']}")
    if info.get('quality_checks'):
        qc = info['quality_checks']
        print(f"  - Quality: {'PASS' if qc.get('ok') else 'FAIL'}")
        for k, v in qc.items():
            if k != 'ok':
                print(f"    • {k}: {'OK' if v else 'FAIL'}")
    if 'sam_score' in info:
        print(f"  - SAM confidence: {info['sam_score']:.3f}")

    # Save mask
    if args.output:
        cv2.imwrite(args.output, mask)
        print(f"Saved mask to {args.output}")

    # Visualize
    if args.visualize:
        vis = visualize_segmentation(image, mask, info)
        cv2.imshow('Segmentation', vis)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()