#!/usr/bin/env python3
"""
Pre-trained Models for Fabric Defect Detection
Using state-of-the-art models without need for training
"""

import cv2
import numpy as np
import torch
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')


@dataclass
class DefectDetection:
    """Defect detection result"""
    type: str
    confidence: float
    bbox: Tuple[int, int, int, int]
    mask: Optional[np.ndarray]
    area_pixels: int
    description: str


class PretrainedDefectDetector:
    """
    Uses pre-trained models for fabric defect detection
    Available models:
    1. YOLOv8 with COCO (can detect some damage)
    2. SAM (Segment Anything Model) for precise segmentation
    3. Anomaly detection models
    """

    def __init__(self, model_type: str = 'yolov8', device: str = 'cpu'):
        """
        Initialize with pre-trained model

        Args:
            model_type: 'yolov8', 'sam', 'anomaly'
            device: 'cuda' or 'cpu'
        """
        self.model_type = model_type
        self.device = device

        print(f"🤖 Initializing {model_type.upper()} defect detector...")

        if model_type == 'yolov8':
            self._init_yolo()
        elif model_type == 'sam':
            self._init_sam()
        elif model_type == 'anomaly':
            self._init_anomaly()
        else:
            print("⚠️ Unknown model type, using YOLOv8")
            self._init_yolo()

    def _init_yolo(self):
        """Initialize YOLOv8"""
        try:
            from ultralytics import YOLO

            # Try to use a pre-trained model
            # YOLOv8 can detect some defects in objects
            self.model = YOLO('yolov8n.pt')  # Nano version for speed
            print("✅ YOLOv8 loaded")

            # Classes that might indicate damage/defects
            self.defect_classes = ['hole', 'tear', 'damage', 'crack']

        except ImportError:
            print("❌ YOLOv8 not available. Install with: pip install ultralytics")
            self.model = None

    def _init_sam(self):
        """Initialize SAM (Segment Anything Model)"""
        try:
            # SAM is excellent for segmenting anything, including defects
            print("🔍 Loading SAM model...")

            # Note: SAM requires manual download of checkpoint
            # from https://github.com/facebookresearch/segment-anything

            from segment_anything import sam_model_registry, SamAutomaticMaskGenerator

            # Use the smallest model for speed
            sam_checkpoint = "sam_vit_b_01ec64.pth"  # Need to download this
            model_type = "vit_b"

            sam = sam_model_registry[model_type](checkpoint=sam_checkpoint)
            sam.to(device=self.device)

            self.mask_generator = SamAutomaticMaskGenerator(
                model=sam,
                points_per_side=16,  # Fewer points for speed
                pred_iou_thresh=0.8,
                stability_score_thresh=0.85,
                min_mask_region_area=100
            )

            print("✅ SAM loaded successfully")

        except Exception as e:
            print(f"❌ SAM not available: {e}")
            print("   Download checkpoint from: https://github.com/facebookresearch/segment-anything")
            self.mask_generator = None

    def _init_anomaly(self):
        """Initialize anomaly detection model"""
        try:
            # Using anomalib for industrial anomaly detection
            from anomalib.models import Padim
            from anomalib.data.utils import read_image

            # PaDiM is good for fabric defects
            self.model = Padim(
                backbone="resnet18",
                layers=["layer1", "layer2", "layer3"]
            )

            print("✅ Anomaly detection model loaded")

        except ImportError:
            print("❌ Anomalib not available. Install with: pip install anomalib")
            self.model = None

    def detect_defects_yolo(self, image: np.ndarray) -> List[DefectDetection]:
        """Detect defects using YOLOv8"""
        if self.model is None:
            return []

        detections = []

        # Run detection
        results = self.model(image, conf=0.25)

        # Process results
        for r in results:
            boxes = r.boxes
            if boxes is not None:
                for box in boxes:
                    # Get box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = box.conf[0].item()
                    cls = int(box.cls[0].item())

                    # Check if it could be a defect
                    # YOLOv8 doesn't have specific defect classes,
                    # but we can look for unusual detections

                    detections.append(DefectDetection(
                        type='potential_defect',
                        confidence=conf,
                        bbox=(int(x1), int(y1), int(x2-x1), int(y2-y1)),
                        mask=None,
                        area_pixels=int((x2-x1) * (y2-y1)),
                        description=f"YOLOv8 detection (conf: {conf:.2f})"
                    ))

        return detections

    def detect_defects_sam(self, image: np.ndarray, point_coords: List[Tuple[int, int]] = None) -> List[DefectDetection]:
        """
        Detect defects using SAM

        Args:
            image: Input image
            point_coords: Optional list of points to check for defects

        Returns:
            List of detected defects
        """
        if self.mask_generator is None:
            return []

        detections = []

        if point_coords:
            # Use provided points as prompts
            # SAM can segment around specific points
            for point in point_coords:
                # Here you would use SamPredictor for point prompts
                # This is more complex and requires proper setup
                pass
        else:
            # Generate masks automatically
            masks = self.mask_generator.generate(image)

            # Analyze each mask to determine if it's a defect
            for mask_data in masks:
                mask = mask_data['segmentation']
                area = mask_data['area']

                # Analyze mask characteristics
                if self._is_defect_mask(mask, image):
                    bbox = mask_data['bbox']

                    detections.append(DefectDetection(
                        type='hole_or_defect',
                        confidence=mask_data['predicted_iou'],
                        bbox=tuple(bbox),
                        mask=mask,
                        area_pixels=area,
                        description="SAM detected anomaly"
                    ))

        return detections

    def _is_defect_mask(self, mask: np.ndarray, image: np.ndarray) -> bool:
        """
        Analyze if a mask represents a defect

        Defects typically have:
        - Different intensity than surrounding
        - Small to medium size
        - Often circular or irregular shape
        """
        # Get masked region
        masked_pixels = image[mask > 0]
        if len(masked_pixels) == 0:
            return False

        # Get surrounding pixels
        kernel = np.ones((5, 5), np.uint8)
        dilated = cv2.dilate(mask.astype(np.uint8), kernel, iterations=2)
        surrounding_mask = dilated - mask.astype(np.uint8)
        surrounding_pixels = image[surrounding_mask > 0]

        if len(surrounding_pixels) == 0:
            return False

        # Compare intensities
        masked_mean = np.mean(masked_pixels)
        surrounding_mean = np.mean(surrounding_pixels)

        # Defects are usually darker
        if masked_mean < surrounding_mean * 0.7:
            return True

        # Or much brighter (holes with light showing through)
        if masked_mean > surrounding_mean * 1.3:
            return True

        return False

    def detect(self, image: np.ndarray) -> List[DefectDetection]:
        """
        Main detection method

        Args:
            image: Input image (BGR)

        Returns:
            List of detected defects
        """
        if self.model_type == 'yolov8':
            return self.detect_defects_yolo(image)
        elif self.model_type == 'sam':
            return self.detect_defects_sam(image)
        elif self.model_type == 'anomaly':
            # Anomaly detection would go here
            return []
        else:
            return []


# Alternative: Use existing fabric defect detection models
class FabricDefectModels:
    """
    Information about available pre-trained models for fabric defects
    """

    @staticmethod
    def available_models():
        """List available pre-trained models"""

        models = {
            "YOLOv8-Fabric": {
                "description": "YOLOv8 fine-tuned on fabric defects",
                "url": "https://github.com/ultralytics/ultralytics",
                "classes": ["hole", "stain", "tear", "missing_yarn"],
                "available": False  # Needs training
            },

            "SAM": {
                "description": "Segment Anything Model - can segment any defect",
                "url": "https://github.com/facebookresearch/segment-anything",
                "classes": ["any"],
                "available": True  # Pre-trained available
            },

            "Anomalib": {
                "description": "Industrial anomaly detection library",
                "url": "https://github.com/openvinotoolkit/anomalib",
                "models": ["PaDiM", "PatchCore", "STFPM"],
                "available": True  # Pre-trained available
            },

            "MVTec AD": {
                "description": "Models trained on MVTec Anomaly Detection dataset",
                "url": "https://www.mvtec.com/company/research/datasets/mvtec-ad",
                "categories": ["carpet", "grid", "leather", "tile", "wood"],
                "available": True  # Some have fabric-like textures
            },

            "AITEX": {
                "description": "Models trained on AITEX fabric defect dataset",
                "url": "https://www.aitex.es/",
                "defects": ["hole", "stain", "color", "broken"],
                "available": False  # Needs specific training
            },

            "Deep-Fabric": {
                "description": "Deep learning models for fabric defect detection",
                "url": "Research paper models",
                "architectures": ["ResNet", "EfficientNet", "Vision Transformer"],
                "available": False  # Academic models, need implementation
            }
        }

        return models

    @staticmethod
    def recommend_model(task: str = "hole_detection"):
        """Recommend best model for specific task"""

        if task == "hole_detection":
            return """
            RECOMMENDED APPROACH for hole detection:

            1. **SAM (Segment Anything Model)** - BEST OPTION
               - Already pre-trained
               - Excellent at segmenting small objects
               - Can use point prompts for specific areas
               - No fabric-specific training needed

            2. **Anomalib with PaDiM**
               - Good for detecting anomalies in textures
               - Works well on fabric-like materials
               - Can be fine-tuned with few examples

            3. **Custom YOLOv8**
               - Needs training data (500+ annotated holes)
               - Very fast once trained
               - High accuracy possible

            4. **Traditional CV + ML**
               - Use color/texture features
               - Train a simple classifier (SVM, Random Forest)
               - Works with small datasets (50-100 examples)
            """

        return "No specific recommendation for this task"


def main():
    """Example usage"""

    print("="*70)
    print("PRE-TRAINED MODELS FOR FABRIC DEFECT DETECTION")
    print("="*70)

    # Show available models
    models_info = FabricDefectModels()
    available = models_info.available_models()

    print("\n📚 Available Pre-trained Models:")
    for name, info in available.items():
        status = "✅" if info.get('available', False) else "❌"
        print(f"\n{status} {name}:")
        print(f"   {info['description']}")
        if 'url' in info:
            print(f"   URL: {info['url']}")

    # Get recommendation
    print("\n" + "="*70)
    print(models_info.recommend_model("hole_detection"))
    print("="*70)


if __name__ == "__main__":
    main()