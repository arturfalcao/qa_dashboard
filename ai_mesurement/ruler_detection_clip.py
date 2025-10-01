#!/usr/bin/env python3
"""
CLIP-based Ruler Detection System
Uses CLIP to identify ruler regions in images with high accuracy
"""

import cv2
import numpy as np
from typing import Dict, Optional, Tuple, List
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel
import torch.nn.functional as F

class CLIPRulerDetector:
    """Use CLIP to detect rulers in images through region proposals"""

    def __init__(self, known_length_cm: float = 31.0, device: str = "cpu"):
        """
        Initialize CLIP-based ruler detector

        Args:
            known_length_cm: Known ruler length in cm
            device: Device to run model on
        """
        self.known_length_cm = known_length_cm
        self.device = device

        print("🤖 Loading CLIP for ruler detection...")
        model_name = "openai/clip-vit-base-patch32"
        self.model = CLIPModel.from_pretrained(model_name)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model.to(device)
        self.model.eval()
        print("✅ CLIP model loaded for ruler detection")

        # Text descriptions for rulers
        self.ruler_prompts = [
            "a yellow measuring ruler",
            "a ruler with centimeter markings",
            "a 31 centimeter ruler",
            "a yellow ruler with numbers",
            "a measuring tape",
            "a construction ruler",
            "a metric ruler"
        ]

        # Negative prompts (what it's NOT)
        self.negative_prompts = [
            "clothing",
            "fabric",
            "garment",
            "background",
            "floor",
            "wall"
        ]

    def detect_ruler(self, image: np.ndarray) -> Dict:
        """
        Detect ruler in image using CLIP

        Args:
            image: Input image (BGR)

        Returns:
            Dict with ruler info including pixels_per_cm and bounding box
        """
        h, w = image.shape[:2]
        print(f"🔍 Detecting ruler with CLIP (image: {w}x{h})...")

        # Convert to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Generate region proposals
        proposals = self._generate_region_proposals(image_rgb)

        # Score each proposal with CLIP
        best_proposal = None
        best_score = -float('inf')

        print(f"   Evaluating {len(proposals)} region proposals...")

        for i, (x, y, prop_w, prop_h) in enumerate(proposals):
            # Extract region
            region = image_rgb[y:y+prop_h, x:x+prop_w]

            if region.size == 0:
                continue

            # Score with CLIP
            score = self._score_region_as_ruler(region)

            if score > best_score:
                best_score = score
                best_proposal = (x, y, prop_w, prop_h)

        if best_proposal is None:
            print("⚠️ No ruler detected with CLIP, trying color-based detection...")
            return self._color_based_detection(image)

        x, y, w, h = best_proposal

        # Refine the bounding box
        x, y, w, h = self._refine_bbox(image, x, y, w, h)

        # Determine orientation and calculate scale
        if w > h:
            ruler_length_px = w
            orientation = 'horizontal'
        else:
            ruler_length_px = h
            orientation = 'vertical'

        pixels_per_cm = ruler_length_px / self.known_length_cm

        # Convert score to confidence (0-1 range)
        confidence = min(1.0, max(0.0, (best_score + 10) / 20))

        print(f"✅ Ruler detected with CLIP!")
        print(f"   Location: ({x}, {y})")
        print(f"   Size: {w}x{h} pixels")
        print(f"   Orientation: {orientation}")
        print(f"   Length: {ruler_length_px:.0f} pixels")
        print(f"   Scale: {pixels_per_cm:.2f} pixels/cm")
        print(f"   Confidence: {confidence:.1%}")

        return {
            'pixels_per_cm': pixels_per_cm,
            'bbox': (x, y, w, h),
            'confidence': confidence,
            'orientation': orientation,
            'method': 'clip_detection'
        }

    def _generate_region_proposals(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Generate potential ruler regions using selective search and geometric constraints"""

        h, w = image.shape[:2]
        proposals = []

        # Expected ruler aspect ratios
        ruler_aspects = [10, 12, 15, 20, 25, 30]  # Ruler is very elongated

        # Expected ruler sizes (based on typical 31cm ruler at different distances)
        min_ruler_length = int(min(w, h) * 0.15)  # At least 15% of image dimension
        max_ruler_length = int(min(w, h) * 0.8)   # At most 80% of image dimension

        # Generate proposals based on expected ruler dimensions
        for aspect in ruler_aspects:
            # Horizontal rulers
            for ruler_w in range(min_ruler_length, max_ruler_length, 50):
                ruler_h = ruler_w // aspect
                if ruler_h < 20:  # Too thin
                    continue

                # Try different positions
                for y in range(0, h - ruler_h, h // 10):
                    for x in range(0, w - ruler_w, w // 10):
                        proposals.append((x, y, ruler_w, ruler_h))

            # Vertical rulers
            for ruler_h in range(min_ruler_length, max_ruler_length, 50):
                ruler_w = ruler_h // aspect
                if ruler_w < 20:  # Too thin
                    continue

                # Try different positions
                for y in range(0, h - ruler_h, h // 10):
                    for x in range(0, w - ruler_w, w // 10):
                        proposals.append((x, y, ruler_w, ruler_h))

        # Add edge-based proposals
        edge_proposals = self._get_edge_based_proposals(image)
        proposals.extend(edge_proposals)

        # Limit number of proposals
        if len(proposals) > 100:
            # Sample to keep computation manageable
            step = len(proposals) // 100
            proposals = proposals[::step]

        return proposals

    def _get_edge_based_proposals(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Generate proposals based on edge detection"""

        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        proposals = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 500:  # Skip small contours
                continue

            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = max(w, h) / min(w, h)

            # Look for elongated objects
            if aspect_ratio > 8:  # Ruler-like aspect ratio
                proposals.append((x, y, w, h))

        return proposals

    def _score_region_as_ruler(self, region: np.ndarray) -> float:
        """Score how likely a region contains a ruler using CLIP"""

        # Resize region for CLIP
        pil_region = Image.fromarray(region)

        # Encode image and texts
        with torch.no_grad():
            # Process positive prompts
            inputs = self.processor(
                text=self.ruler_prompts,
                images=pil_region,
                return_tensors="pt",
                padding=True
            )

            outputs = self.model(**inputs)
            logits_per_image = outputs.logits_per_image
            probs = logits_per_image.softmax(dim=1)

            # Get best ruler score
            ruler_score = probs.max().item()

            # Process negative prompts for contrast
            neg_inputs = self.processor(
                text=self.negative_prompts,
                images=pil_region,
                return_tensors="pt",
                padding=True
            )

            neg_outputs = self.model(**neg_inputs)
            neg_logits = neg_outputs.logits_per_image
            neg_probs = neg_logits.softmax(dim=1)

            # Get best negative score
            neg_score = neg_probs.max().item()

            # Final score: ruler score minus negative score
            final_score = ruler_score - neg_score

        return final_score

    def _refine_bbox(self, image: np.ndarray, x: int, y: int, w: int, h: int) -> Tuple[int, int, int, int]:
        """Refine bounding box using color and edge information"""

        # Extract region with padding
        pad = 20
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(image.shape[1], x + w + pad)
        y2 = min(image.shape[0], y + h + pad)

        region = image[y1:y2, x1:x2]

        # Convert to HSV for yellow detection
        hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)

        # Yellow range
        lower_yellow = np.array([15, 50, 50])
        upper_yellow = np.array([35, 255, 255])
        mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

        # Find contours in mask
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            # Find largest contour
            largest = max(contours, key=cv2.contourArea)
            rx, ry, rw, rh = cv2.boundingRect(largest)

            # Adjust coordinates back to original image
            return (x1 + rx, y1 + ry, rw, rh)

        return (x, y, w, h)

    def _color_based_detection(self, image: np.ndarray) -> Dict:
        """Fallback to color-based detection"""

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Yellow color range
        lower_yellow = np.array([15, 40, 40])
        upper_yellow = np.array([40, 255, 255])
        mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

        # Morphology to clean up
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            raise ValueError("No ruler detected")

        # Find most ruler-like contour
        best_contour = None
        best_score = 0

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 1000:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = max(w, h) / min(w, h)

            # Score based on aspect ratio and area
            if aspect_ratio > 8:  # Elongated
                score = aspect_ratio * np.sqrt(area)
                if score > best_score:
                    best_score = score
                    best_contour = contour

        if best_contour is None:
            raise ValueError("No ruler-like object found")

        x, y, w, h = cv2.boundingRect(best_contour)
        ruler_length_px = max(w, h)
        pixels_per_cm = ruler_length_px / self.known_length_cm

        return {
            'pixels_per_cm': pixels_per_cm,
            'bbox': (x, y, w, h),
            'confidence': 0.5,
            'orientation': 'horizontal' if w > h else 'vertical',
            'method': 'color_fallback'
        }

def test_clip_ruler_detection(image_path: str):
    """Test CLIP-based ruler detection"""

    print(f"\n{'='*60}")
    print(f"Testing CLIP Ruler Detection")
    print(f"Image: {image_path}")
    print('='*60)

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not load {image_path}")
        return

    try:
        # Initialize detector
        detector = CLIPRulerDetector(known_length_cm=31.0)

        # Detect ruler
        result = detector.detect_ruler(image)

        print(f"\n✅ Detection successful!")

        # Visualize result
        x, y, w, h = result['bbox']
        vis = image.copy()
        cv2.rectangle(vis, (x, y), (x+w, y+h), (0, 255, 0), 3)
        cv2.putText(vis, f"CLIP: {result['pixels_per_cm']:.1f} px/cm",
                   (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(vis, f"Confidence: {result['confidence']:.1%}",
                   (x, y+h+30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Draw ruler length line
        if result['orientation'] == 'horizontal':
            cv2.line(vis, (x, y+h//2), (x+w, y+h//2), (255, 0, 0), 2)
        else:
            cv2.line(vis, (x+w//2, y), (x+w//2, y+h), (255, 0, 0), 2)

        from pathlib import Path
        output_path = f"clip_ruler_detection_{Path(image_path).stem}.png"
        cv2.imwrite(output_path, vis)
        print(f"💾 Visualization saved: {output_path}")

        # Calculate what this means for measurements
        print(f"\n📏 MEASUREMENT IMPLICATIONS:")
        test_widths = [1000, 2000, 3000, 4000]
        for width_px in test_widths:
            width_cm = width_px / result['pixels_per_cm']
            print(f"   {width_px} pixels = {width_cm:.1f} cm")

    except Exception as e:
        print(f"❌ Detection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_clip_ruler_detection("../test_images_mesurements/ant.jpg")