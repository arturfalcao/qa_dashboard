#!/usr/bin/env python3
"""
AI-based Ruler Detection System
Uses vision models to accurately detect and measure rulers in images
"""

import cv2
import numpy as np
from typing import Dict, Optional, Tuple, List
import torch
from transformers import pipeline, AutoProcessor, AutoModelForZeroShotObjectDetection
from PIL import Image
import supervision as sv

class AIRulerDetector:
    """AI-powered ruler detection using zero-shot object detection"""

    def __init__(self, known_length_cm: float = 31.0, model_type: str = "grounding-dino"):
        """
        Initialize AI ruler detector

        Args:
            known_length_cm: Known ruler length in cm
            model_type: Model to use ("grounding-dino" or "owlvit")
        """
        self.known_length_cm = known_length_cm
        self.model_type = model_type

        print(f"🤖 Initializing AI Ruler Detector...")

        if model_type == "grounding-dino":
            # Use Grounding DINO for zero-shot detection
            try:
                from groundingdino.util.inference import load_model, load_image, predict
                import groundingdino.datasets.transforms as T

                self.model = load_model(
                    "groundingdino/config/GroundingDINO_SwinT_OGC.py",
                    "weights/groundingdino_swint_ogc.pth"
                )
                self.use_grounding_dino = True
                print("✅ Grounding DINO model loaded")
            except:
                print("⚠️ Grounding DINO not available, falling back to OWL-ViT")
                self.use_grounding_dino = False
                self._load_owlvit()
        else:
            self.use_grounding_dino = False
            self._load_owlvit()

    def _load_owlvit(self):
        """Load OWL-ViT model as fallback"""
        model_name = "google/owlvit-base-patch32"
        self.processor = AutoProcessor.from_pretrained(model_name)
        self.model = AutoModelForZeroShotObjectDetection.from_pretrained(model_name)
        self.model.eval()
        print("✅ OWL-ViT model loaded")

    def detect_ruler(self, image: np.ndarray) -> Dict:
        """
        Detect ruler using AI model

        Args:
            image: Input image (BGR)

        Returns:
            Dict with ruler info including pixels_per_cm and bounding box
        """
        h, w = image.shape[:2]

        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)

        print("🔍 Detecting ruler with AI model...")

        # Text prompts for ruler detection
        ruler_prompts = [
            "yellow ruler",
            "measuring ruler",
            "ruler with measurements",
            "yellow measuring tape",
            "ruler with numbers",
            "31cm ruler",
            "centimeter ruler"
        ]

        best_detection = None
        best_score = 0

        if self.use_grounding_dino:
            best_detection = self._detect_with_grounding_dino(image_rgb, ruler_prompts)
        else:
            best_detection = self._detect_with_owlvit(pil_image, ruler_prompts)

        if best_detection is None:
            # Fallback to simpler detection
            print("⚠️ AI detection failed, using color-based fallback")
            return self._fallback_detection(image)

        # Calculate pixels per cm from detection
        x, y, w, h = best_detection['bbox']

        # Determine if ruler is horizontal or vertical
        if w > h:
            # Horizontal ruler
            ruler_length_px = w
            orientation = 'horizontal'
        else:
            # Vertical ruler
            ruler_length_px = h
            orientation = 'vertical'

        pixels_per_cm = ruler_length_px / self.known_length_cm

        print(f"✅ Ruler detected: {orientation}")
        print(f"   Bounding box: {x}, {y}, {w}, {h}")
        print(f"   Length in pixels: {ruler_length_px:.0f}")
        print(f"   Pixels per cm: {pixels_per_cm:.2f}")
        print(f"   Confidence: {best_detection['score']:.1%}")

        return {
            'pixels_per_cm': pixels_per_cm,
            'bbox': (x, y, w, h),
            'confidence': best_detection['score'],
            'orientation': orientation,
            'method': 'ai_detection'
        }

    def _detect_with_owlvit(self, image: Image.Image, prompts: List[str]) -> Optional[Dict]:
        """Detect ruler using OWL-ViT model"""

        best_detection = None
        best_score = 0

        for prompt in prompts:
            try:
                # Prepare inputs
                inputs = self.processor(text=[prompt], images=image, return_tensors="pt")

                # Run inference
                with torch.no_grad():
                    outputs = self.model(**inputs)

                # Process results
                target_sizes = torch.tensor([image.size[::-1]])
                results = self.processor.post_process_object_detection(
                    outputs=outputs,
                    target_sizes=target_sizes,
                    threshold=0.1
                )

                # Get boxes and scores
                boxes = results[0]["boxes"].cpu().numpy()
                scores = results[0]["scores"].cpu().numpy()

                if len(boxes) > 0:
                    # Find best detection
                    best_idx = scores.argmax()
                    if scores[best_idx] > best_score:
                        box = boxes[best_idx]
                        best_score = scores[best_idx]
                        best_detection = {
                            'bbox': (int(box[0]), int(box[1]),
                                   int(box[2] - box[0]), int(box[3] - box[1])),
                            'score': float(best_score),
                            'prompt': prompt
                        }
            except Exception as e:
                print(f"   Failed with prompt '{prompt}': {e}")
                continue

        return best_detection

    def _detect_with_grounding_dino(self, image: np.ndarray, prompts: List[str]) -> Optional[Dict]:
        """Detect ruler using Grounding DINO model"""
        # This would require Grounding DINO installation
        # Placeholder for now
        return None

    def _fallback_detection(self, image: np.ndarray) -> Dict:
        """Fallback to color-based detection when AI fails"""

        # Convert to HSV for color detection
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Yellow color range for typical rulers
        lower_yellow = np.array([15, 50, 50])
        upper_yellow = np.array([35, 255, 255])

        # Create mask
        mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

        # Apply morphology to clean up
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            raise ValueError("No ruler detected")

        # Find the most elongated contour (likely the ruler)
        best_contour = None
        best_ratio = 0

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 1000:  # Skip small contours
                continue

            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = max(w, h) / min(w, h)

            if aspect_ratio > best_ratio and aspect_ratio > 5:  # Ruler should be elongated
                best_ratio = aspect_ratio
                best_contour = contour

        if best_contour is None:
            raise ValueError("No elongated ruler-like object found")

        x, y, w, h = cv2.boundingRect(best_contour)
        ruler_length_px = max(w, h)
        pixels_per_cm = ruler_length_px / self.known_length_cm

        return {
            'pixels_per_cm': pixels_per_cm,
            'bbox': (x, y, w, h),
            'confidence': 0.5,  # Lower confidence for fallback
            'orientation': 'horizontal' if w > h else 'vertical',
            'method': 'color_fallback'
        }


class VisionLanguageRulerDetector:
    """Alternative approach using vision-language models like CLIP or BLIP"""

    def __init__(self, known_length_cm: float = 31.0):
        """Initialize vision-language ruler detector"""
        self.known_length_cm = known_length_cm

        print("🤖 Initializing Vision-Language Ruler Detector...")

        # Load BLIP for visual question answering
        try:
            from transformers import BlipProcessor, BlipForQuestionAnswering
            model_name = "Salesforce/blip-vqa-base"
            self.processor = BlipProcessor.from_pretrained(model_name)
            self.model = BlipForQuestionAnswering.from_pretrained(model_name)
            self.model.eval()
            print("✅ BLIP VQA model loaded")
            self.use_blip = True
        except:
            print("⚠️ BLIP not available")
            self.use_blip = False

    def detect_ruler(self, image: np.ndarray) -> Dict:
        """
        Detect ruler using vision-language model

        Args:
            image: Input image (BGR)

        Returns:
            Dict with ruler info
        """
        # Convert to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)

        if self.use_blip:
            return self._detect_with_blip(pil_image, image)
        else:
            return self._detect_with_sliding_window(image)

    def _detect_with_blip(self, pil_image: Image.Image, cv_image: np.ndarray) -> Dict:
        """Use BLIP to find ruler in image"""

        questions = [
            "Where is the yellow ruler in this image?",
            "Is there a measuring ruler in this image?",
            "What color is the ruler?",
            "Is the ruler horizontal or vertical?"
        ]

        answers = []
        for question in questions:
            inputs = self.processor(pil_image, question, return_tensors="pt")
            with torch.no_grad():
                out = self.model.generate(**inputs)
            answer = self.processor.decode(out[0], skip_special_tokens=True)
            answers.append(answer)
            print(f"   Q: {question}")
            print(f"   A: {answer}")

        # Use answers to guide detection
        # This is simplified - in practice you'd parse the answers more carefully
        return self._detect_with_sliding_window(cv_image)

    def _detect_with_sliding_window(self, image: np.ndarray) -> Dict:
        """Sliding window approach to find ruler-like objects"""

        h, w = image.shape[:2]

        # Expected ruler dimensions (approximate)
        expected_lengths = [
            (int(self.known_length_cm * 40), 100),  # Horizontal ruler
            (100, int(self.known_length_cm * 40))   # Vertical ruler
        ]

        best_match = None
        best_score = 0

        for exp_w, exp_h in expected_lengths:
            # Slide window across image
            for y in range(0, h - exp_h, 50):
                for x in range(0, w - exp_w, 50):
                    window = image[y:y+exp_h, x:x+exp_w]

                    # Check if window contains ruler-like features
                    score = self._score_ruler_likelihood(window)

                    if score > best_score:
                        best_score = score
                        best_match = (x, y, exp_w, exp_h)

        if best_match is None:
            raise ValueError("No ruler detected")

        x, y, w, h = best_match
        ruler_length_px = max(w, h)
        pixels_per_cm = ruler_length_px / self.known_length_cm

        return {
            'pixels_per_cm': pixels_per_cm,
            'bbox': best_match,
            'confidence': best_score,
            'orientation': 'horizontal' if w > h else 'vertical',
            'method': 'vision_language'
        }

    def _score_ruler_likelihood(self, window: np.ndarray) -> float:
        """Score how likely a window contains a ruler"""

        # Check for yellow color
        hsv = cv2.cvtColor(window, cv2.COLOR_BGR2HSV)
        lower_yellow = np.array([15, 50, 50])
        upper_yellow = np.array([35, 255, 255])
        mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
        yellow_ratio = np.sum(mask > 0) / mask.size

        # Check for straight edges
        edges = cv2.Canny(window, 50, 150)
        edge_ratio = np.sum(edges > 0) / edges.size

        # Combined score
        score = (yellow_ratio * 0.5) + (edge_ratio * 0.5)

        return score


def test_ai_ruler_detection(image_path: str):
    """Test AI ruler detection"""

    print(f"\n{'='*60}")
    print(f"Testing AI Ruler Detection")
    print(f"Image: {image_path}")
    print('='*60)

    # Load image
    image = cv2.imread(image_path)
    if image is None:
        print(f"Error: Could not load {image_path}")
        return

    # Try AI detection
    try:
        detector = AIRulerDetector(known_length_cm=31.0, model_type="owlvit")
        result = detector.detect_ruler(image)

        print(f"\n✅ AI Detection successful!")
        print(f"   Pixels per cm: {result['pixels_per_cm']:.2f}")
        print(f"   Method: {result['method']}")

        # Draw result
        x, y, w, h = result['bbox']
        vis = image.copy()
        cv2.rectangle(vis, (x, y), (x+w, y+h), (0, 255, 0), 3)
        cv2.putText(vis, f"AI: {result['pixels_per_cm']:.1f} px/cm",
                   (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        output_path = f"ai_ruler_detection_{Path(image_path).stem}.png"
        cv2.imwrite(output_path, vis)
        print(f"   Visualization saved: {output_path}")

    except Exception as e:
        print(f"❌ AI Detection failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    from pathlib import Path
    test_ai_ruler_detection("../test_images_mesurements/ant.jpg")