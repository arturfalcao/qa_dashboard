#!/usr/bin/env python3
"""
Garment Hole Detection Module
Detects and analyzes holes, tears, and defects in garments
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import math

# Try to import AI detector for enhanced detection
try:
    from zero_shot_defect_detector import ZeroShotDefectDetector, ZeroShotDefect
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("⚠️ Zero-shot detector not available, using traditional CV only")


@dataclass
class HoleInfo:
    """Information about a detected hole"""
    contour: np.ndarray
    area_pixels: float
    area_cm2: float
    center: Tuple[int, int]
    bbox: Tuple[int, int, int, int]  # x, y, width, height
    perimeter_pixels: float
    perimeter_cm: float
    circularity: float  # 1.0 = perfect circle, lower = more irregular
    severity: str  # 'small', 'medium', 'large', 'critical'
    type: str  # 'hole', 'tear', 'worn_area'


class GarmentHoleDetector:
    """
    Detects holes, tears, and worn areas in garments
    """

    def __init__(self, pixels_per_cm: float = 10.0, debug: bool = False, min_size: str = 'medium', use_ai: bool = True):
        """
        Initialize hole detector

        Args:
            pixels_per_cm: Scale factor for real measurements
            debug: Enable debug output
            min_size: Minimum defect size to detect ('tiny', 'small', 'medium', 'large')
            use_ai: Use AI for enhanced defect detection
        """
        self.pixels_per_cm = pixels_per_cm
        self.debug = debug
        self.min_size = min_size
        self.use_ai = use_ai and AI_AVAILABLE

        # Initialize zero-shot detector if requested and available
        if self.use_ai:
            try:
                # Using 85% for better balance between precision and recall
                self.ai_detector = ZeroShotDefectDetector(confidence_threshold=0.85, debug=debug)
                print("✅ Zero-shot defect detection enabled (85% confidence)")
            except Exception as e:
                print(f"⚠️ Could not initialize zero-shot detector: {e}")
                self.use_ai = False

        # Size-based minimum thresholds in cm²
        min_area_cm2 = {
            'tiny': 0.05,
            'small': 0.1,
            'medium': 0.5,  # Only detect medium and above
            'large': 2.0
        }

        # Set minimum area based on selected threshold
        min_area = min_area_cm2.get(min_size, 0.5)
        self.MIN_HOLE_AREA_PX = int(min_area * (pixels_per_cm ** 2))
        self.MAX_HOLE_AREA_PX = 10000  # Maximum area (to filter out false positives)

        # Size categories (in cm²)
        self.SIZE_THRESHOLDS = {
            'tiny': 0.1,     # < 0.1 cm² (pinhole)
            'small': 0.5,    # 0.1 - 0.5 cm²
            'medium': 2.0,   # 0.5 - 2.0 cm²
            'large': 5.0,    # 2.0 - 5.0 cm²
            'critical': float('inf')  # > 5.0 cm²
        }

    def detect_holes(self, image: np.ndarray, mask: np.ndarray) -> List[HoleInfo]:
        """
        Detect holes in garment

        Args:
            image: Original garment image
            mask: Segmentation mask of the garment

        Returns:
            List of detected holes with information
        """
        if self.debug:
            print("\n🔍 HOLE DETECTION")
            print("-" * 40)

        # Step 1: Find all contours (external and internal)
        holes = []

        # Method 1: Find internal contours (holes within the garment)
        internal_holes = self._find_internal_contours(mask)

        # Method 2: Detect worn/thin areas using intensity analysis
        worn_areas = self._detect_worn_areas(image, mask)

        # Method 3: Detect tears using edge detection
        tears = self._detect_tears(image, mask)

        # Combine all detections
        all_defects = internal_holes + worn_areas + tears

        # Filter and classify each defect
        for contour, defect_type in all_defects:
            hole_info = self._analyze_hole(contour, defect_type)
            if hole_info:
                holes.append(hole_info)

        # Apply AI enhancement if available
        if self.use_ai and len(holes) > 0:
            holes = self._enhance_with_ai(image, mask, holes)

        if self.debug:
            print(f"✅ Detected {len(holes)} defects")
            for i, hole in enumerate(holes):
                print(f"   {i+1}. {hole.type}: {hole.area_cm2:.2f} cm² ({hole.severity})")

        return holes

    def _find_internal_contours(self, mask: np.ndarray) -> List[Tuple[np.ndarray, str]]:
        """Find holes as internal contours within the mask"""

        # Ensure mask is binary
        _, binary_mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)

        # Find contours with hierarchy
        contours, hierarchy = cv2.findContours(
            binary_mask,
            cv2.RETR_TREE,  # Retrieve all contours with hierarchy
            cv2.CHAIN_APPROX_SIMPLE
        )

        if hierarchy is None:
            return []

        internal_contours = []
        hierarchy = hierarchy[0]

        # Find contours that are holes (have a parent contour)
        for i, contour in enumerate(contours):
            # Check if this contour has a parent (is inside another contour)
            parent = hierarchy[i][3]
            if parent != -1:  # Has a parent, so it's an internal contour
                area = cv2.contourArea(contour)
                if self.MIN_HOLE_AREA_PX <= area <= self.MAX_HOLE_AREA_PX:
                    internal_contours.append((contour, 'hole'))

        return internal_contours

    def _detect_worn_areas(self, image: np.ndarray, mask: np.ndarray) -> List[Tuple[np.ndarray, str]]:
        """Detect worn or thin areas using intensity analysis"""

        worn_areas = []

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Apply mask to focus only on garment
        masked_gray = cv2.bitwise_and(gray, gray, mask=mask)

        # Calculate mean and std of garment pixels
        garment_pixels = gray[mask > 0]
        if len(garment_pixels) == 0:
            return worn_areas

        mean_intensity = np.mean(garment_pixels)
        std_intensity = np.std(garment_pixels)

        # Find abnormally bright areas (potential worn/thin spots)
        # These might appear brighter if backlit or if fabric is thin
        threshold = mean_intensity + 2 * std_intensity
        _, bright_areas = cv2.threshold(masked_gray, min(threshold, 250), 255, cv2.THRESH_BINARY)

        # Remove noise
        kernel = np.ones((3, 3), np.uint8)
        bright_areas = cv2.morphologyEx(bright_areas, cv2.MORPH_OPEN, kernel)
        bright_areas = cv2.morphologyEx(bright_areas, cv2.MORPH_CLOSE, kernel)

        # Find contours of bright areas
        contours, _ = cv2.findContours(bright_areas, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            area = cv2.contourArea(contour)
            if self.MIN_HOLE_AREA_PX <= area <= self.MAX_HOLE_AREA_PX:
                worn_areas.append((contour, 'worn_area'))

        return worn_areas

    def _detect_tears(self, image: np.ndarray, mask: np.ndarray) -> List[Tuple[np.ndarray, str]]:
        """Detect tears using edge detection and line analysis"""

        tears = []

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Apply mask
        masked = cv2.bitwise_and(gray, gray, mask=mask)

        # Detect edges
        edges = cv2.Canny(masked, 50, 150)

        # Remove edges at garment boundary
        kernel = np.ones((5, 5), np.uint8)
        eroded_mask = cv2.erode(mask, kernel, iterations=2)
        internal_edges = cv2.bitwise_and(edges, edges, mask=eroded_mask)

        # Detect lines (potential tears)
        lines = cv2.HoughLinesP(
            internal_edges,
            1,
            np.pi / 180,
            threshold=30,
            minLineLength=20,
            maxLineGap=10
        )

        if lines is not None:
            # Group nearby lines into tear regions
            tear_mask = np.zeros_like(mask)
            for line in lines:
                x1, y1, x2, y2 = line[0]
                cv2.line(tear_mask, (x1, y1), (x2, y2), 255, 3)

            # Dilate to connect nearby lines
            tear_mask = cv2.dilate(tear_mask, kernel, iterations=1)

            # Find contours of tear regions
            contours, _ = cv2.findContours(tear_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                area = cv2.contourArea(contour)
                if area >= self.MIN_HOLE_AREA_PX:
                    # Check if it's elongated (tear-like)
                    rect = cv2.minAreaRect(contour)
                    width = min(rect[1])
                    height = max(rect[1])
                    if height > 0 and width > 0:
                        aspect_ratio = height / width
                        if aspect_ratio > 2:  # Elongated shape
                            tears.append((contour, 'tear'))

        return tears

    def _analyze_hole(self, contour: np.ndarray, defect_type: str) -> Optional[HoleInfo]:
        """Analyze a potential hole/defect"""

        area_px = cv2.contourArea(contour)

        # Filter out too small or too large areas
        if area_px < self.MIN_HOLE_AREA_PX or area_px > self.MAX_HOLE_AREA_PX:
            return None

        # Calculate properties
        perimeter_px = cv2.arcLength(contour, True)
        M = cv2.moments(contour)

        if M["m00"] == 0:
            return None

        center_x = int(M["m10"] / M["m00"])
        center_y = int(M["m01"] / M["m00"])

        # Bounding box
        x, y, w, h = cv2.boundingRect(contour)

        # Circularity (1 = perfect circle)
        if perimeter_px > 0:
            circularity = 4 * np.pi * area_px / (perimeter_px ** 2)
        else:
            circularity = 0

        # Convert to real measurements
        area_cm2 = area_px / (self.pixels_per_cm ** 2)
        perimeter_cm = perimeter_px / self.pixels_per_cm

        # Classify severity
        severity = self._classify_severity(area_cm2)

        return HoleInfo(
            contour=contour,
            area_pixels=area_px,
            area_cm2=area_cm2,
            center=(center_x, center_y),
            bbox=(x, y, w, h),
            perimeter_pixels=perimeter_px,
            perimeter_cm=perimeter_cm,
            circularity=circularity,
            severity=severity,
            type=defect_type
        )

    def _classify_severity(self, area_cm2: float) -> str:
        """Classify hole severity based on size"""

        if area_cm2 < self.SIZE_THRESHOLDS['tiny']:
            return 'tiny'
        elif area_cm2 < self.SIZE_THRESHOLDS['small']:
            return 'small'
        elif area_cm2 < self.SIZE_THRESHOLDS['medium']:
            return 'medium'
        elif area_cm2 < self.SIZE_THRESHOLDS['large']:
            return 'large'
        else:
            return 'critical'

    def _enhance_with_ai(self, image: np.ndarray, mask: np.ndarray,
                        traditional_holes: List[HoleInfo]) -> List[HoleInfo]:
        """
        Use zero-shot AI to filter false positives from traditional detection

        Args:
            image: Original image
            mask: Garment mask
            traditional_holes: Holes detected by traditional methods

        Returns:
            Filtered list of AI-validated holes with 90% confidence
        """
        if self.debug:
            print(f"\n🤖 ZERO-SHOT AI VALIDATION")
            print(f"   Validating {len(traditional_holes)} candidates...")

        # Convert to format for zero-shot detector
        candidates = [(hole.contour, hole.type) for hole in traditional_holes]

        # Use zero-shot detector to validate with 90% confidence
        ai_results = self.ai_detector.detect(image, candidates)

        # Convert back to HoleInfo format
        ai_validated_holes = []

        for ai_defect in ai_results:
            # Find matching traditional hole
            best_match = None
            min_distance = float('inf')

            for hole in traditional_holes:
                dx = hole.center[0] - ai_defect.center[0]
                dy = hole.center[1] - ai_defect.center[1]
                distance = math.sqrt(dx*dx + dy*dy)

                if distance < min_distance:
                    min_distance = distance
                    best_match = hole

            # If we found a match, keep it with updated type
            if best_match and min_distance < 50:
                best_match.type = ai_defect.type
                ai_validated_holes.append(best_match)

        if self.debug:
            print(f"   ✅ {len(ai_validated_holes)} defects validated with ≥90% confidence")
            print(f"   ❌ {len(traditional_holes) - len(ai_validated_holes)} rejected as false positives")

        # Return validated holes or empty if none pass 90% threshold
        return ai_validated_holes

    def visualize_holes(self, image: np.ndarray, holes: List[HoleInfo],
                        save_path: str = 'hole_detection.png') -> np.ndarray:
        """
        Visualize detected holes on the image

        Args:
            image: Original image
            holes: List of detected holes
            save_path: Path to save visualization

        Returns:
            Annotated image
        """
        annotated = image.copy()

        # Color scheme by severity
        colors = {
            'tiny': (0, 255, 0),      # Green
            'small': (0, 255, 255),    # Yellow
            'medium': (0, 165, 255),   # Orange
            'large': (0, 0, 255),      # Red
            'critical': (255, 0, 255)  # Magenta
        }

        for i, hole in enumerate(holes):
            color = colors.get(hole.severity, (255, 255, 255))

            # Draw contour
            cv2.drawContours(annotated, [hole.contour], -1, color, 2)

            # Draw bounding box
            x, y, w, h = hole.bbox
            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 1)

            # Add label
            label = f"{hole.type[0].upper()}{i+1}: {hole.area_cm2:.2f}cm²"
            cv2.putText(annotated, label,
                       (x, y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX,
                       0.4, color, 1)

            # Mark center
            cv2.circle(annotated, hole.center, 3, color, -1)

        # Add summary
        summary_y = 30
        cv2.putText(annotated, f"Detected {len(holes)} defects:",
                   (10, summary_y),
                   cv2.FONT_HERSHEY_SIMPLEX,
                   0.7, (255, 255, 255), 2)

        # Count by type
        type_counts = {}
        for hole in holes:
            type_counts[hole.type] = type_counts.get(hole.type, 0) + 1

        for j, (dtype, count) in enumerate(type_counts.items()):
            cv2.putText(annotated, f"  {dtype}: {count}",
                       (10, summary_y + 25 * (j + 1)),
                       cv2.FONT_HERSHEY_SIMPLEX,
                       0.6, (255, 255, 255), 1)

        cv2.imwrite(save_path, annotated)
        return annotated

    def generate_report(self, holes: List[HoleInfo]) -> Dict:
        """
        Generate a detailed report of detected holes

        Args:
            holes: List of detected holes

        Returns:
            Dictionary with analysis report
        """
        report = {
            'total_defects': len(holes),
            'total_damage_area_cm2': sum(h.area_cm2 for h in holes),
            'defects_by_type': {},
            'defects_by_severity': {},
            'critical_defects': [],
            'defect_details': []
        }

        # Count by type and severity
        for hole in holes:
            # By type
            if hole.type not in report['defects_by_type']:
                report['defects_by_type'][hole.type] = 0
            report['defects_by_type'][hole.type] += 1

            # By severity
            if hole.severity not in report['defects_by_severity']:
                report['defects_by_severity'][hole.severity] = 0
            report['defects_by_severity'][hole.severity] += 1

            # Track critical defects
            if hole.severity in ['large', 'critical']:
                report['critical_defects'].append({
                    'type': hole.type,
                    'area_cm2': hole.area_cm2,
                    'location': hole.center
                })

            # Add to details
            report['defect_details'].append({
                'type': hole.type,
                'severity': hole.severity,
                'area_cm2': round(hole.area_cm2, 2),
                'perimeter_cm': round(hole.perimeter_cm, 2),
                'circularity': round(hole.circularity, 2),
                'center': hole.center,
                'bbox': hole.bbox
            })

        # Calculate quality score (100 = perfect, 0 = severely damaged)
        damage_factor = min(report['total_damage_area_cm2'] / 10, 1)  # Cap at 10 cm²
        critical_factor = len(report['critical_defects']) * 0.2
        quality_score = max(0, 100 - (damage_factor * 50) - (critical_factor * 50))
        report['quality_score'] = round(quality_score, 1)

        # Add recommendation
        if quality_score >= 90:
            report['recommendation'] = 'Excellent condition - no repair needed'
        elif quality_score >= 70:
            report['recommendation'] = 'Good condition - minor repairs recommended'
        elif quality_score >= 50:
            report['recommendation'] = 'Fair condition - repairs needed'
        elif quality_score >= 30:
            report['recommendation'] = 'Poor condition - significant repairs required'
        else:
            report['recommendation'] = 'Critical condition - may not be repairable'

        return report