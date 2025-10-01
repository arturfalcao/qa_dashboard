"""
Improved Garment Segmentation
Better preprocessing + smarter mask selection
"""

import cv2
import numpy as np
from typing import Tuple, Dict


class ImprovedGarmentSegmenter:
    """
    Enhanced garment segmentation with better preprocessing
    """

    def __init__(self, debug: bool = False):
        self.debug = debug

    def segment_garment(
        self,
        image: np.ndarray,
        ruler_bbox: Tuple[int, int, int, int] = None
    ) -> Tuple[np.ndarray, Dict]:
        """
        Segment garment from image with improved methods

        Args:
            image: Input BGR image
            ruler_bbox: Optional ruler bounding box to exclude (x, y, w, h)

        Returns:
            garment_mask: Binary mask of garment
            garment_info: Dictionary with contour and measurements
        """

        print(f"🎯 Segmenting garment with improved methods...")

        # Downscale for faster processing
        h, w = image.shape[:2]
        max_dim = 1500
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            image_small = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

            # Scale ruler bbox if provided
            if ruler_bbox:
                rx, ry, rw, rh = ruler_bbox
                ruler_bbox_small = (
                    int(rx * scale), int(ry * scale),
                    int(rw * scale), int(rh * scale)
                )
            else:
                ruler_bbox_small = None
        else:
            image_small = image
            scale = 1.0
            ruler_bbox_small = ruler_bbox

        # Step 1: Enhanced preprocessing
        preprocessed = self._preprocess_image(image_small)

        # Step 2: Multi-method segmentation
        masks = []

        # Method 1: GrabCut (iterative segmentation)
        grabcut_mask = self._segment_grabcut(preprocessed, image_small)
        if grabcut_mask is not None:
            masks.append(('grabcut', grabcut_mask))

        # Method 2: Improved color segmentation
        color_mask = self._segment_by_color_enhanced(preprocessed, image_small)
        if color_mask is not None:
            masks.append(('color', color_mask))

        # Method 3: Watershed segmentation
        watershed_mask = self._segment_watershed(preprocessed, image_small)
        if watershed_mask is not None:
            masks.append(('watershed', watershed_mask))

        if not masks:
            raise ValueError("All segmentation methods failed")

        # Step 3: Select best mask
        best_mask = self._select_best_mask(masks, image_small, ruler_bbox_small)

        # Step 4: Isolate garment (exclude ruler and other objects)
        garment_mask_small, garment_info_small = self._isolate_garment(
            image_small,
            best_mask,
            ruler_bbox_small
        )

        # Step 5: Upscale mask back to original size
        if scale != 1.0:
            garment_mask = cv2.resize(
                garment_mask_small,
                (image.shape[1], image.shape[0]),
                interpolation=cv2.INTER_NEAREST
            )

            # Recalculate contour on full-size mask
            contours, _ = cv2.findContours(garment_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                garment_contour = max(contours, key=cv2.contourArea)
            else:
                garment_contour = garment_info_small['contour']

            # Scale bbox and area
            bx, by, bw, bh = garment_info_small['bbox']
            garment_info = {
                'contour': garment_contour,
                'bbox': (
                    int(bx / scale), int(by / scale),
                    int(bw / scale), int(bh / scale)
                ),
                'area': cv2.contourArea(garment_contour) if garment_contour is not None else int(garment_info_small['area'] / (scale ** 2))
            }
        else:
            garment_mask = garment_mask_small
            garment_info = garment_info_small

        if self.debug:
            self._visualize_segmentation(image, garment_mask, garment_info)

        return garment_mask, garment_info

    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Enhanced preprocessing for better segmentation"""

        # 1. Simple Gaussian blur (faster than bilateral)
        denoised = cv2.GaussianBlur(image, (5, 5), 0)

        # 2. Enhance contrast (CLAHE)
        lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)

        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

        # 3. Slight sharpening
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]]) / 9
        sharpened = cv2.filter2D(enhanced, -1, kernel)

        return sharpened

    def _segment_grabcut(self, preprocessed: np.ndarray, original: np.ndarray) -> np.ndarray:
        """
        GrabCut segmentation - iterative foreground/background separation
        Very effective for garments on uniform backgrounds
        """

        try:
            # Initialize mask
            mask = np.zeros(original.shape[:2], np.uint8)

            # Define rectangle for initial foreground (exclude borders)
            h, w = original.shape[:2]
            margin = int(min(h, w) * 0.05)  # 5% margin
            rect = (margin, margin, w - 2*margin, h - 2*margin)

            # GrabCut temporary arrays
            bgd_model = np.zeros((1, 65), np.float64)
            fgd_model = np.zeros((1, 65), np.float64)

            # Run GrabCut
            cv2.grabCut(
                original,
                mask,
                rect,
                bgd_model,
                fgd_model,
                5,  # iterations
                cv2.GC_INIT_WITH_RECT
            )

            # Create binary mask (probable FG + definite FG)
            mask2 = np.where((mask == 2) | (mask == 0), 0, 1).astype('uint8')

            # Clean up
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask2 = cv2.morphologyEx(mask2, cv2.MORPH_OPEN, kernel, iterations=1)
            mask2 = cv2.morphologyEx(mask2, cv2.MORPH_CLOSE, kernel, iterations=2)

            return mask2 * 255

        except Exception as e:
            print(f"   ⚠️  GrabCut failed: {e}")
            return None

    def _segment_by_color_enhanced(self, preprocessed: np.ndarray, original: np.ndarray) -> np.ndarray:
        """Enhanced color-based segmentation"""

        # Detect background color from corners
        hsv = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2HSV)

        h, w = hsv.shape[:2]
        corner_size = 50

        corners = [
            hsv[0:corner_size, 0:corner_size],
            hsv[0:corner_size, w-corner_size:w],
            hsv[h-corner_size:h, 0:corner_size],
            hsv[h-corner_size:h, w-corner_size:w]
        ]

        corner_pixels = np.vstack([c.reshape(-1, 3) for c in corners])
        median_bg = np.median(corner_pixels, axis=0).astype(np.uint8)

        # Create mask for background
        h_range, s_range, v_range = 20, 70, 70

        lower = np.array([
            max(0, int(median_bg[0]) - h_range),
            max(0, int(median_bg[1]) - s_range),
            max(0, int(median_bg[2]) - v_range)
        ], dtype=np.uint8)

        upper = np.array([
            min(179, int(median_bg[0]) + h_range),
            min(255, int(median_bg[1]) + s_range),
            min(255, int(median_bg[2]) + v_range)
        ], dtype=np.uint8)

        bg_mask = cv2.inRange(hsv, lower, upper)

        # Invert to get foreground
        fg_mask = cv2.bitwise_not(bg_mask)

        # Morphological cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel, iterations=1)

        return fg_mask

    def _segment_watershed(self, preprocessed: np.ndarray, original: np.ndarray) -> np.ndarray:
        """Watershed segmentation - good for separating touching objects"""

        try:
            gray = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2GRAY)

            # Threshold
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            # Morphological operations
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)

            # Sure background
            sure_bg = cv2.dilate(opening, kernel, iterations=3)

            # Sure foreground (distance transform)
            dist_transform = cv2.distanceTransform(opening, cv2.DIST_L2, 5)
            _, sure_fg = cv2.threshold(dist_transform, 0.3 * dist_transform.max(), 255, 0)
            sure_fg = np.uint8(sure_fg)

            # Unknown region
            unknown = cv2.subtract(sure_bg, sure_fg)

            # Marker labelling
            _, markers = cv2.connectedComponents(sure_fg)
            markers = markers + 1
            markers[unknown == 255] = 0

            # Watershed
            markers = cv2.watershed(original, markers)

            # Create mask (exclude boundaries)
            mask = np.zeros_like(gray)
            mask[markers > 1] = 255

            return mask

        except Exception as e:
            print(f"   ⚠️  Watershed failed: {e}")
            return None

    def _select_best_mask(
        self,
        masks: list,
        image: np.ndarray,
        ruler_bbox: Tuple = None
    ) -> np.ndarray:
        """Select best segmentation mask"""

        if len(masks) == 1:
            method, mask = masks[0]
            print(f"   ✅ Using {method} segmentation")
            return mask

        # Score each mask
        scored = []

        for method, mask in masks:
            # Count foreground pixels
            fg_pixels = np.sum(mask > 0)
            total_pixels = mask.shape[0] * mask.shape[1]
            fg_ratio = fg_pixels / total_pixels

            # Good masks have 10-70% foreground
            if 0.1 < fg_ratio < 0.7:
                # Find largest contour
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    largest = max(contours, key=cv2.contourArea)
                    area = cv2.contourArea(largest)

                    # Score based on area and method
                    score = area
                    if method == 'grabcut':
                        score *= 1.2  # Prefer GrabCut

                    scored.append((score, method, mask))

        if not scored:
            # Fallback to first mask
            return masks[0][1]

        scored.sort(key=lambda x: x[0], reverse=True)
        _, best_method, best_mask = scored[0]

        print(f"   ✅ Using {best_method} segmentation (best score)")

        return best_mask

    def _isolate_garment(
        self,
        image: np.ndarray,
        mask: np.ndarray,
        ruler_bbox: Tuple = None
    ) -> Tuple[np.ndarray, Dict]:
        """Isolate garment from mask, excluding ruler"""

        # Find all contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            raise ValueError("No contours found in mask")

        # Exclude ruler region if provided
        valid_contours = []
        image_area = image.shape[0] * image.shape[1]

        for contour in contours:
            area = cv2.contourArea(contour)

            # Filter by size
            if area < image_area * 0.05:  # Too small
                continue

            # Check if overlaps with ruler
            if ruler_bbox:
                rx, ry, rw, rh = ruler_bbox
                x, y, w, h = cv2.boundingRect(contour)

                # Check IoU with ruler bbox
                overlap_x = max(0, min(x+w, rx+rw) - max(x, rx))
                overlap_y = max(0, min(y+h, ry+rh) - max(y, ry))
                overlap_area = overlap_x * overlap_y

                contour_area = w * h
                overlap_ratio = overlap_area / contour_area

                if overlap_ratio > 0.5:  # More than 50% overlap with ruler
                    continue

            # Check aspect ratio (garments are not too elongated)
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = max(w, h) / max(min(w, h), 1)

            if aspect_ratio < 5:  # Not too elongated (would be ruler)
                valid_contours.append((contour, area))

        if not valid_contours:
            raise ValueError("No valid garment contours found after filtering")

        # Get largest valid contour (should be garment)
        valid_contours.sort(key=lambda x: x[1], reverse=True)
        garment_contour = valid_contours[0][0]

        # Create clean mask
        garment_mask = np.zeros_like(mask)
        cv2.drawContours(garment_mask, [garment_contour], -1, 255, -1)

        # Get bbox
        x, y, w, h = cv2.boundingRect(garment_contour)

        garment_info = {
            'contour': garment_contour,
            'bbox': (x, y, w, h),
            'area': cv2.contourArea(garment_contour)
        }

        print(f"   ✅ Garment isolated: {garment_info['area']:.0f} pixels²")

        return garment_mask, garment_info

    def _visualize_segmentation(self, image: np.ndarray, mask: np.ndarray, info: Dict):
        """Save debug visualization"""
        import matplotlib.pyplot as plt

        fig, axes = plt.subplots(1, 3, figsize=(15, 5))

        # Original
        axes[0].imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        axes[0].set_title('Original Image')
        axes[0].axis('off')

        # Mask
        axes[1].imshow(mask, cmap='gray')
        axes[1].set_title('Garment Mask')
        axes[1].axis('off')

        # Overlay
        overlay = image.copy()
        mask_colored = np.zeros_like(image)
        mask_colored[mask > 0] = [0, 255, 0]
        overlay = cv2.addWeighted(overlay, 0.7, mask_colored, 0.3, 0)

        x, y, w, h = info['bbox']
        cv2.rectangle(overlay, (x, y), (x+w, y+h), (255, 0, 0), 3)

        axes[2].imshow(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB))
        axes[2].set_title('Segmentation Result')
        axes[2].axis('off')

        plt.tight_layout()
        plt.savefig('debug_improved_segmentation.png', dpi=150, bbox_inches='tight')
        plt.close()

        print(f"✅ Debug visualization saved: debug_improved_segmentation.png")
