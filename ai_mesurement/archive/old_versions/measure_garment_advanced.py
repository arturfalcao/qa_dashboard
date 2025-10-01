#!/usr/bin/env python3
"""
Advanced Garment Measurement System V3
Enhanced architecture with comprehensive measurements and reporting
"""

import cv2
import numpy as np
import json
import argparse
from pathlib import Path
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

from ruler_detection_smart import SmartRulerDetector
from garment_segmentation_v2 import ImprovedGarmentSegmenter
from garment_measurement import GarmentMeasurer


class GarmentSize(Enum):
    """Standard garment size classifications"""
    XS = "Extra Small"
    S = "Small"
    M = "Medium"
    L = "Large"
    XL = "Extra Large"
    XXL = "2X Large"
    XXXL = "3X Large"
    UNKNOWN = "Unknown"


@dataclass
class MeasurementResult:
    """Structured measurement result"""
    height_cm: float
    width_cm: float
    chest_circumference_estimate_cm: float
    area_cm2: float
    diagonal_cm: float
    aspect_ratio: float
    pixels_per_cm: float
    confidence_score: float
    estimated_size: str
    size_category: str
    measurement_points: Dict
    quality_metrics: Dict


class AdvancedMeasurementEngine:
    """Enhanced measurement engine with improved accuracy and features"""

    # Standard t-shirt size chart (chest circumference in cm)
    SIZE_CHART = {
        GarmentSize.XS: {'min': 76, 'max': 86, 'height': (40, 50)},
        GarmentSize.S: {'min': 86, 'max': 96, 'height': (45, 55)},
        GarmentSize.M: {'min': 96, 'max': 106, 'height': (50, 60)},
        GarmentSize.L: {'min': 106, 'max': 116, 'height': (55, 65)},
        GarmentSize.XL: {'min': 116, 'max': 126, 'height': (60, 70)},
        GarmentSize.XXL: {'min': 126, 'max': 136, 'height': (65, 75)},
        GarmentSize.XXXL: {'min': 136, 'max': 146, 'height': (70, 80)},
    }

    def __init__(self, ruler_length_cm: float = 31.0, debug: bool = False):
        self.ruler_length_cm = ruler_length_cm
        self.debug = debug
        self.ruler_detector = SmartRulerDetector(known_length_cm=ruler_length_cm, debug=debug)
        self.segmenter = ImprovedGarmentSegmenter(debug=debug)

    def measure(self, image_path: str) -> MeasurementResult:
        """
        Comprehensive measurement pipeline with enhanced features
        """
        print(f"\n{'='*70}")
        print(f"🔬 ADVANCED GARMENT MEASUREMENT SYSTEM V3")
        print(f"{'='*70}\n")

        # Load and validate image
        image = self._load_and_validate_image(image_path)

        # Phase 1: Ruler calibration
        ruler_info = self._calibrate_with_ruler(image)
        pixels_per_cm = ruler_info['pixels_per_cm']

        # Phase 2: Garment segmentation
        mask, garment_info = self._segment_garment(image, ruler_info['bbox'])

        # Phase 3: Advanced measurements
        measurements = self._perform_advanced_measurements(
            image, mask, garment_info, pixels_per_cm
        )

        # Phase 4: Size estimation
        size_info = self._estimate_size(measurements)

        # Phase 5: Quality assessment
        quality = self._assess_measurement_quality(ruler_info, garment_info, measurements)

        # Compile results
        result = MeasurementResult(
            height_cm=measurements['height_cm'],
            width_cm=measurements['width_cm'],
            chest_circumference_estimate_cm=measurements['chest_estimate_cm'],
            area_cm2=measurements['area_cm2'],
            diagonal_cm=measurements['diagonal_cm'],
            aspect_ratio=measurements['aspect_ratio'],
            pixels_per_cm=pixels_per_cm,
            confidence_score=quality['overall_confidence'],
            estimated_size=size_info['size'],
            size_category=size_info['category'],
            measurement_points=measurements['points'],
            quality_metrics=quality
        )

        # Generate report
        self._generate_report(result, image_path)

        # Save visualizations if debug
        if self.debug:
            self._save_advanced_visualization(image, mask, measurements, result)

        return result

    def _load_and_validate_image(self, image_path: str) -> np.ndarray:
        """Load and validate input image"""
        if not Path(image_path).exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Failed to load image: {image_path}")

        print(f"📸 Image loaded: {image.shape[1]}x{image.shape[0]} pixels")

        # Check image quality
        if image.shape[0] < 1000 or image.shape[1] < 1000:
            print("⚠️  Warning: Low resolution image may affect accuracy")

        return image

    def _calibrate_with_ruler(self, image: np.ndarray) -> Dict:
        """Calibrate measurement scale using ruler"""
        print(f"\n{'='*70}")
        print("📏 PHASE 1: RULER CALIBRATION")
        print(f"{'='*70}")

        ruler_info = self.ruler_detector.detect_ruler(image)

        print(f"✅ Ruler detected successfully")
        print(f"   • Method: {ruler_info['method']}")
        print(f"   • Scale: {ruler_info['pixels_per_cm']:.2f} pixels/cm")
        print(f"   • Confidence: {ruler_info.get('confidence', 0):.2%}")

        return ruler_info

    def _segment_garment(self, image: np.ndarray, ruler_bbox: Tuple) -> Tuple[np.ndarray, Dict]:
        """Segment garment from image"""
        print(f"\n{'='*70}")
        print("👕 PHASE 2: GARMENT SEGMENTATION")
        print(f"{'='*70}")

        mask, info = self.segmenter.segment_garment(image, ruler_bbox=ruler_bbox)

        print(f"✅ Garment segmented successfully")
        print(f"   • Area: {info['area']:,} pixels²")
        print(f"   • Coverage: {info['area']/(image.shape[0]*image.shape[1])*100:.1f}% of image")

        return mask, info

    def _perform_advanced_measurements(self, image: np.ndarray, mask: np.ndarray,
                                      garment_info: Dict, pixels_per_cm: float) -> Dict:
        """Perform comprehensive measurements"""
        print(f"\n{'='*70}")
        print("📐 PHASE 3: ADVANCED MEASUREMENTS")
        print(f"{'='*70}")

        # Basic measurements
        measurer = GarmentMeasurer(pixels_per_cm=pixels_per_cm)
        basic = measurer.measure_garment(image, mask, garment_info)

        # Calculate additional metrics
        diagonal_px = np.linalg.norm(
            np.array(basic['extreme_points']['top']) -
            np.array(basic['extreme_points']['bottom'])
        )
        diagonal_cm = diagonal_px / pixels_per_cm

        # Estimate chest circumference (approximation)
        chest_estimate_cm = basic['width_cm'] * 2  # Simple estimation

        # Aspect ratio
        aspect_ratio = basic['width_cm'] / basic['height_cm']

        # Compile measurements
        measurements = {
            'height_cm': basic['height_cm'],
            'width_cm': basic['width_cm'],
            'area_cm2': basic['area_cm2'],
            'diagonal_cm': diagonal_cm,
            'chest_estimate_cm': chest_estimate_cm,
            'aspect_ratio': aspect_ratio,
            'points': basic['extreme_points'],
            'pixels_per_cm': pixels_per_cm
        }

        print(f"✅ Measurements completed")
        print(f"   • Height: {measurements['height_cm']:.1f} cm")
        print(f"   • Width: {measurements['width_cm']:.1f} cm")
        print(f"   • Chest (est.): {chest_estimate_cm:.1f} cm")
        print(f"   • Aspect ratio: {aspect_ratio:.2f}")

        return measurements

    def _estimate_size(self, measurements: Dict) -> Dict:
        """Estimate garment size based on measurements"""
        print(f"\n{'='*70}")
        print("🏷️ PHASE 4: SIZE ESTIMATION")
        print(f"{'='*70}")

        chest_cm = measurements['chest_estimate_cm']
        height_cm = measurements['height_cm']

        estimated_size = GarmentSize.UNKNOWN
        for size, specs in self.SIZE_CHART.items():
            if specs['min'] <= chest_cm <= specs['max']:
                if specs['height'][0] <= height_cm <= specs['height'][1]:
                    estimated_size = size
                    break

        # Determine if adult or child
        if height_cm < 40:
            category = "Children's"
        elif height_cm < 60:
            category = "Youth/Adult Small"
        else:
            category = "Adult"

        size_info = {
            'size': estimated_size.name,
            'description': estimated_size.value,
            'category': category,
            'chest_range': self.SIZE_CHART.get(estimated_size, {}).get('min', 0)
        }

        print(f"✅ Size estimated: {size_info['size']} ({size_info['description']})")
        print(f"   • Category: {size_info['category']}")

        return size_info

    def _assess_measurement_quality(self, ruler_info: Dict, garment_info: Dict,
                                   measurements: Dict) -> Dict:
        """Assess measurement quality and confidence"""
        print(f"\n{'='*70}")
        print("✨ PHASE 5: QUALITY ASSESSMENT")
        print(f"{'='*70}")

        # Calculate quality metrics
        ruler_confidence = ruler_info.get('confidence', 0.5)

        # Check if measurements are reasonable
        height_valid = 20 <= measurements['height_cm'] <= 100
        width_valid = 20 <= measurements['width_cm'] <= 100
        ratio_valid = 0.5 <= measurements['aspect_ratio'] <= 2.0

        # Overall confidence
        overall_confidence = (
            ruler_confidence * 0.4 +
            (1.0 if height_valid else 0.5) * 0.2 +
            (1.0 if width_valid else 0.5) * 0.2 +
            (1.0 if ratio_valid else 0.5) * 0.2
        )

        quality = {
            'ruler_confidence': ruler_confidence,
            'measurement_validity': all([height_valid, width_valid, ratio_valid]),
            'overall_confidence': overall_confidence,
            'warnings': []
        }

        if overall_confidence < 0.7:
            quality['warnings'].append("Low confidence - verify measurements manually")
        if not height_valid:
            quality['warnings'].append("Height measurement may be incorrect")
        if not width_valid:
            quality['warnings'].append("Width measurement may be incorrect")

        print(f"✅ Quality assessment complete")
        print(f"   • Confidence: {overall_confidence:.1%}")
        print(f"   • Valid measurements: {'Yes' if quality['measurement_validity'] else 'No'}")

        return quality

    def _generate_report(self, result: MeasurementResult, image_path: str):
        """Generate detailed measurement report"""
        print(f"\n{'='*70}")
        print("📊 MEASUREMENT REPORT")
        print(f"{'='*70}")

        print(f"\n📏 DIMENSIONS:")
        print(f"   • Height: {result.height_cm:.2f} cm ({result.height_cm/2.54:.1f} inches)")
        print(f"   • Width: {result.width_cm:.2f} cm ({result.width_cm/2.54:.1f} inches)")
        print(f"   • Chest (estimated): {result.chest_circumference_estimate_cm:.1f} cm")
        print(f"   • Area: {result.area_cm2:.0f} cm²")
        print(f"   • Aspect Ratio: {result.aspect_ratio:.2f}")

        print(f"\n🏷️ SIZE ESTIMATION:")
        print(f"   • Size: {result.estimated_size}")
        print(f"   • Category: {result.size_category}")

        print(f"\n✨ QUALITY METRICS:")
        print(f"   • Confidence Score: {result.confidence_score:.1%}")
        print(f"   • Scale: {result.pixels_per_cm:.2f} pixels/cm")

        if result.quality_metrics.get('warnings'):
            print(f"\n⚠️  WARNINGS:")
            for warning in result.quality_metrics['warnings']:
                print(f"   • {warning}")

        # Save JSON report
        report_path = Path(image_path).parent / f"measurement_report_{Path(image_path).stem}.json"
        report_data = asdict(result)
        report_data['image_path'] = str(image_path)

        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)

        print(f"\n💾 Report saved to: {report_path}")

    def _save_advanced_visualization(self, image: np.ndarray, mask: np.ndarray,
                                    measurements: Dict, result: MeasurementResult):
        """Save comprehensive visualization with annotations"""
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches

        fig = plt.figure(figsize=(20, 12))

        # Create grid
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

        # 1. Original image with measurements overlay
        ax1 = fig.add_subplot(gs[0:2, 0:2])
        overlay = image.copy()

        # Draw measurement lines
        pts = measurements['points']

        # Height line
        cv2.line(overlay, pts['top'], pts['bottom'], (0, 255, 0), 4)
        cv2.circle(overlay, pts['top'], 12, (0, 255, 0), -1)
        cv2.circle(overlay, pts['bottom'], 12, (0, 255, 0), -1)

        # Width line
        cv2.line(overlay, pts['left'], pts['right'], (255, 0, 0), 4)
        cv2.circle(overlay, pts['left'], 12, (255, 0, 0), -1)
        cv2.circle(overlay, pts['right'], 12, (255, 0, 0), -1)

        # Add measurement annotations
        cv2.putText(overlay, f"H: {result.height_cm:.1f}cm",
                   (pts['top'][0] + 30, (pts['top'][1] + pts['bottom'][1])//2),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)

        cv2.putText(overlay, f"W: {result.width_cm:.1f}cm",
                   ((pts['left'][0] + pts['right'][0])//2, pts['left'][1] - 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 0, 0), 3)

        ax1.imshow(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB))
        ax1.set_title('Garment Measurements', fontsize=14, fontweight='bold')
        ax1.axis('off')

        # 2. Segmentation mask
        ax2 = fig.add_subplot(gs[0, 2])
        ax2.imshow(mask, cmap='gray')
        ax2.set_title('Segmentation Mask', fontsize=12)
        ax2.axis('off')

        # 3. Isolated garment
        ax3 = fig.add_subplot(gs[1, 2])
        masked = cv2.bitwise_and(image, image, mask=mask)
        ax3.imshow(cv2.cvtColor(masked, cv2.COLOR_BGR2RGB))
        ax3.set_title('Isolated Garment', fontsize=12)
        ax3.axis('off')

        # 4. Measurement info panel
        ax4 = fig.add_subplot(gs[2, :])
        ax4.axis('off')

        # Create text summary
        info_text = f"""
MEASUREMENT SUMMARY
{'='*50}
Dimensions:
  • Height: {result.height_cm:.2f} cm ({result.height_cm/2.54:.1f} in)
  • Width: {result.width_cm:.2f} cm ({result.width_cm/2.54:.1f} in)
  • Chest (est.): {result.chest_circumference_estimate_cm:.1f} cm
  • Area: {result.area_cm2:.0f} cm²

Size Estimation:
  • Size: {result.estimated_size} ({result.size_category})
  • Confidence: {result.confidence_score:.1%}

Scale: {result.pixels_per_cm:.2f} pixels/cm
"""
        ax4.text(0.1, 0.5, info_text, fontsize=11, family='monospace',
                transform=ax4.transAxes, verticalalignment='center')

        # Main title
        fig.suptitle('Advanced Garment Measurement Analysis',
                    fontsize=16, fontweight='bold')

        # Save
        output_path = 'advanced_measurement_visualization.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()

        print(f"\n📈 Visualization saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Advanced Garment Measurement System V3',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--image', '-i', required=True,
                       help='Path to garment image')
    parser.add_argument('--ruler-length', '-r', type=float, default=31.0,
                       help='Known ruler length in cm (default: 31.0)')
    parser.add_argument('--debug', '-d', action='store_true',
                       help='Enable debug visualizations')

    args = parser.parse_args()

    try:
        # Initialize system
        system = AdvancedMeasurementEngine(
            ruler_length_cm=args.ruler_length,
            debug=args.debug
        )

        # Perform measurement
        result = system.measure(args.image)

        print(f"\n✅ Measurement completed successfully!")
        print(f"{'='*70}\n")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())