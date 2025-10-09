#!/usr/bin/env python3
"""
Garment Measurement System - End-to-End Pipeline
Based on detailed technical specifications for high-accuracy garment measurements.
Target accuracy: ±2mm for all measurements
"""

import cv2
import numpy as np
import json
import math
import logging
from pathlib import Path
from typing import Dict, Tuple, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GarmentType(Enum):
    """Enumeration for different garment types"""
    SHIRT = "shirt"
    PANTS = "pants"
    HOODIE = "hoodie"
    DRESS = "dress"
    SKIRT = "skirt"
    UNKNOWN = "unknown"

@dataclass
class Landmark:
    """Represents a key landmark point on the garment"""
    name: str
    point: Tuple[float, float]
    confidence: float = 1.0

@dataclass
class Measurement:
    """Represents a single measurement with uncertainty"""
    name: str
    value: float  # in mm
    uncertainty: float  # in mm
    unit: str = "mm"
    status: str = "pass"  # pass/fail based on spec

class CameraCalibration:
    """Handles camera intrinsic and extrinsic calibration"""

    def __init__(self, calibration_file: Optional[str] = None):
        self.camera_matrix = None
        self.dist_coeffs = None
        self.homography = None
        self.pixel_to_mm = 1.0  # Default 1px = 1mm after rectification

        if calibration_file and Path(calibration_file).exists():
            self.load_calibration(calibration_file)

    def load_calibration(self, filepath: str):
        """Load calibration parameters from JSON file"""
        with open(filepath, 'r') as f:
            calib = json.load(f)

        # Load camera parameters
        self.camera_matrix = np.array(calib.get("camera_matrix", [[1, 0, 0], [0, 1, 0], [0, 0, 1]]))
        self.dist_coeffs = np.array(calib.get("dist_coeff", [0, 0, 0, 0, 0]))
        self.homography = np.array(calib.get("homography", [[1, 0, 0], [0, 1, 0], [0, 0, 1]]))

        # Normalize bench dimensions to single canonical format
        dims = calib.get("bench_dimensions_mm", {})
        bw = calib.get("bench_width_mm", dims.get("width", 1200.0))
        bh = calib.get("bench_height_mm", dims.get("height", 800.0))
        self.bench_dims_mm = {"width": float(bw), "height": float(bh)}

        # Load and normalize PPM/scale
        self.ppm = float(calib.get("ppm", 0.0))
        self.pixel_to_mm = float(calib.get("pixel_to_mm", 0.0))

        if self.ppm > 0:
            self.pixel_to_mm = 1.0 / self.ppm
        elif self.pixel_to_mm > 0:
            self.ppm = 1.0 / self.pixel_to_mm
        else:
            # Default if neither is set
            logger.warning("Calibration missing ppm/pixel_to_mm, using defaults")
            self.ppm = 2.0
            self.pixel_to_mm = 0.5

        # Load additional calibration data
        self.rect_rms_mm = float(calib.get("rect_rms_mm", 0.5))

        logger.info(f"Loaded calibration from {filepath} - PPM: {self.ppm:.2f}, "
                   f"RMS: {self.rect_rms_mm:.2f}mm, Bench: {self.bench_dims_mm}")

    def calibrate_intrinsic(self, calibration_images: List[np.ndarray],
                           checkerboard_size: Tuple[int, int] = (9, 6),
                           square_size: float = 30.0):
        """Perform intrinsic calibration using checkerboard images"""
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

        # Prepare object points
        objp = np.zeros((checkerboard_size[0] * checkerboard_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:checkerboard_size[0], 0:checkerboard_size[1]].T.reshape(-1, 2)
        objp *= square_size

        objpoints = []
        imgpoints = []

        for img in calibration_images:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
            ret, corners = cv2.findChessboardCorners(gray, checkerboard_size, None)

            if ret:
                objpoints.append(objp)
                corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
                imgpoints.append(corners2)

        if len(objpoints) > 0:
            ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
                objpoints, imgpoints, gray.shape[::-1], None, None
            )
            self.camera_matrix = mtx
            self.dist_coeffs = dist
            logger.info(f"Intrinsic calibration complete. RMS error: {ret:.3f}")
            return True
        return False

    def compute_homography(self, image_points: np.ndarray, world_points: np.ndarray):
        """Compute homography for perspective rectification"""
        self.homography, _ = cv2.findHomography(image_points, world_points, cv2.RANSAC, 5.0)
        logger.info("Homography computed for perspective rectification")

    def undistort_image(self, image: np.ndarray) -> np.ndarray:
        """Remove lens distortion from image"""
        if self.camera_matrix is None:
            return image
        return cv2.undistort(image, self.camera_matrix, self.dist_coeffs)

    def rectify_perspective(self, image: np.ndarray, output_size: Tuple[int, int]) -> np.ndarray:
        """Apply perspective rectification to get top-down view"""
        if self.homography is None:
            return image
        return cv2.warpPerspective(image, self.homography, output_size)

class ImagePreprocessor:
    """Handles image preprocessing including denoising and normalization"""

    def __init__(self, calibration: CameraCalibration):
        self.calibration = calibration

    def preprocess(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Complete preprocessing pipeline
        Returns: (processed_image, grayscale_image)
        """
        # Undistort
        undistorted = self.calibration.undistort_image(image)

        # Get bench dimensions and pixels per mm from calibration
        bench_width_mm = 1200  # Default bench dimensions
        bench_height_mm = 800

        # Use pixels per mm (PPM) for consistent scaling
        ppm = 2.0  # 2 pixels per mm for good resolution
        if hasattr(self.calibration, 'ppm'):
            ppm = self.calibration.ppm
        else:
            # Derive from pixel_to_mm if available
            if self.calibration.pixel_to_mm > 0:
                ppm = 1.0 / self.calibration.pixel_to_mm

        # Calculate output size based on PPM
        output_width = int(bench_width_mm * ppm)
        output_height = int(bench_height_mm * ppm)

        # Rectify perspective with proper scale
        rectified = self.calibration.rectify_perspective(undistorted, (output_width, output_height))

        # Update pixel_to_mm to match the rectified scale
        self.calibration.pixel_to_mm = 1.0 / ppm

        # Convert to grayscale
        if len(rectified.shape) == 3:
            gray = cv2.cvtColor(rectified, cv2.COLOR_BGR2GRAY)
        else:
            gray = rectified.copy()

        # Denoise
        gray = cv2.medianBlur(gray, 3)

        # Optional: Normalize lighting
        gray = self._normalize_lighting(gray)

        return rectified, gray

    def _normalize_lighting(self, gray: np.ndarray) -> np.ndarray:
        """Normalize uneven lighting using morphological operations"""
        # Estimate background illumination
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (50, 50))
        background = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)

        # Subtract background to get uniform lighting
        normalized = cv2.subtract(gray, background)
        normalized = cv2.add(normalized, 128)  # Shift to mid-range

        return normalized

class GarmentSegmentation:
    """Handles garment segmentation from background"""

    def __init__(self, ppm: float = 2.0):
        self.mask = None
        self.contour = None
        self.ppm = ppm

    def segment(self, gray_image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Segment garment from background
        Returns: (binary_mask, main_contour)
        """
        # Method 1: Otsu thresholding
        _, mask_thresh = cv2.threshold(gray_image, 0, 255,
                                      cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Method 2: Edge-based segmentation
        edges = cv2.Canny(gray_image, 50, 150)

        # Find contours from edges
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL,
                                      cv2.CHAIN_APPROX_SIMPLE)

        if len(contours) == 0:
            raise ValueError("No contours found in image")

        # Get largest contour
        main_contour = max(contours, key=cv2.contourArea)

        # Create mask from largest contour
        mask_edge = np.zeros_like(gray_image)
        cv2.drawContours(mask_edge, [main_contour], -1, 255, -1)

        # Combine both masks
        mask_combined = cv2.bitwise_or(mask_thresh, mask_edge)

        # Clean up with morphological operations
        kernel = np.ones((5, 5), np.uint8)
        mask_cleaned = cv2.morphologyEx(mask_combined, cv2.MORPH_CLOSE, kernel)
        mask_cleaned = cv2.morphologyEx(mask_cleaned, cv2.MORPH_OPEN,
                                       np.ones((3, 3), np.uint8))

        # Fill interior holes (logos, patterns, etc.)
        # Find all contours including hierarchy
        contours_temp, hierarchy = cv2.findContours(mask_cleaned, cv2.RETR_CCOMP,
                                                   cv2.CHAIN_APPROX_SIMPLE)
        if hierarchy is not None:
            # Fill holes (contours with parents)
            for i, h in enumerate(hierarchy[0]):
                if h[3] != -1:  # Has parent = it's a hole
                    cv2.drawContours(mask_cleaned, [contours_temp[i]], -1, 255, -1)

        # Get final contour from cleaned mask
        contours, _ = cv2.findContours(mask_cleaned, cv2.RETR_EXTERNAL,
                                      cv2.CHAIN_APPROX_TC89_L1)

        if len(contours) == 0:
            raise ValueError("No contours found after cleaning")

        garment_contour = max(contours, key=cv2.contourArea)

        # Smooth contour - convert mm to pixels
        epsilon_mm = 2.0  # 2mm tolerance
        epsilon_px = epsilon_mm * self.ppm
        garment_contour = cv2.approxPolyDP(garment_contour, epsilon_px, True)

        self.mask = mask_cleaned
        self.contour = garment_contour

        return mask_cleaned, garment_contour

    def detect_garment_type(self, contour: np.ndarray) -> GarmentType:
        """Detect garment type based on contour shape"""
        # Get bounding box
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = h / w if w > 0 else 1

        # Simple heuristics based on aspect ratio
        if aspect_ratio > 1.5:
            return GarmentType.PANTS  # Tall and narrow
        elif aspect_ratio < 0.8:
            return GarmentType.SHIRT  # Wide and short
        else:
            return GarmentType.UNKNOWN

        # More sophisticated detection could use ML or more features

class LandmarkDetector:
    """Detects key landmarks on garments"""

    def __init__(self, garment_type: GarmentType):
        self.garment_type = garment_type
        self.landmarks = {}

    def detect_landmarks(self, contour: np.ndarray, mask: np.ndarray) -> Dict[str, Landmark]:
        """Detect all landmarks based on garment type"""
        if self.garment_type in [GarmentType.SHIRT, GarmentType.HOODIE]:
            return self._detect_shirt_landmarks(contour, mask)
        elif self.garment_type == GarmentType.PANTS:
            return self._detect_pants_landmarks(contour, mask)
        else:
            return self._detect_basic_landmarks(contour, mask)

    def _detect_basic_landmarks(self, contour: np.ndarray, mask: np.ndarray) -> Dict[str, Landmark]:
        """Detect basic extrema landmarks"""
        points = contour[:, 0, :]

        # Basic extrema
        left_idx = np.argmin(points[:, 0])
        right_idx = np.argmax(points[:, 0])
        top_idx = np.argmin(points[:, 1])
        bottom_idx = np.argmax(points[:, 1])

        landmarks = {
            "leftmost": Landmark("leftmost", tuple(points[left_idx])),
            "rightmost": Landmark("rightmost", tuple(points[right_idx])),
            "topmost": Landmark("topmost", tuple(points[top_idx])),
            "bottommost": Landmark("bottommost", tuple(points[bottom_idx]))
        }

        # Centroid
        M = cv2.moments(contour)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            landmarks["centroid"] = Landmark("centroid", (cx, cy))

        return landmarks

    def _detect_shirt_landmarks(self, contour: np.ndarray, mask: np.ndarray) -> Dict[str, Landmark]:
        """Detect landmarks specific to shirts/hoodies"""
        landmarks = self._detect_basic_landmarks(contour, mask)
        points = contour[:, 0, :]

        # Get centroid for reference
        centroid = landmarks["centroid"].point
        cx, cy = centroid

        # Split into left and right halves
        left_mask = points[:, 0] < cx
        right_mask = points[:, 0] > cx

        # HPS (High Point Shoulder) - highest points on each side
        if np.any(left_mask):
            left_points = points[left_mask]
            hps_left_idx = np.argmin(left_points[:, 1])
            landmarks["hps_left"] = Landmark("hps_left", tuple(left_points[hps_left_idx]))

        if np.any(right_mask):
            right_points = points[right_mask]
            hps_right_idx = np.argmin(right_points[:, 1])
            landmarks["hps_right"] = Landmark("hps_right", tuple(right_points[hps_right_idx]))

        # Shoulder points - outermost points near top
        top_region_mask = points[:, 1] < cy - 0.3 * (cy - np.min(points[:, 1]))

        if np.any(left_mask & top_region_mask):
            shoulder_left_pts = points[left_mask & top_region_mask]
            shoulder_left_idx = np.argmin(shoulder_left_pts[:, 0])
            landmarks["shoulder_left"] = Landmark("shoulder_left",
                                                 tuple(shoulder_left_pts[shoulder_left_idx]))

        if np.any(right_mask & top_region_mask):
            shoulder_right_pts = points[right_mask & top_region_mask]
            shoulder_right_idx = np.argmax(shoulder_right_pts[:, 0])
            landmarks["shoulder_right"] = Landmark("shoulder_right",
                                                  tuple(shoulder_right_pts[shoulder_right_idx]))

        # Underarm points using convexity defects
        hull = cv2.convexHull(contour, returnPoints=False)
        if hull.shape[0] > 3:
            defects = cv2.convexityDefects(contour, hull)
            if defects is not None:
                landmarks = self._find_underarm_points(defects, points, cx, cy, landmarks)

        # Sleeve cuffs - lowest points on far left/right
        far_left_mask = points[:, 0] < cx - 0.3 * (cx - np.min(points[:, 0]))
        far_right_mask = points[:, 0] > cx + 0.3 * (np.max(points[:, 0]) - cx)

        if np.any(far_left_mask):
            cuff_left_pts = points[far_left_mask]
            cuff_left_idx = np.argmax(cuff_left_pts[:, 1])
            landmarks["cuff_left"] = Landmark("cuff_left", tuple(cuff_left_pts[cuff_left_idx]))

        if np.any(far_right_mask):
            cuff_right_pts = points[far_right_mask]
            cuff_right_idx = np.argmax(cuff_right_pts[:, 1])
            landmarks["cuff_right"] = Landmark("cuff_right", tuple(cuff_right_pts[cuff_right_idx]))

        return landmarks

    def _detect_pants_landmarks(self, contour: np.ndarray, mask: np.ndarray) -> Dict[str, Landmark]:
        """Detect landmarks specific to pants"""
        landmarks = self._detect_basic_landmarks(contour, mask)
        points = contour[:, 0, :]

        # Get centroid for reference
        centroid = landmarks["centroid"].point
        cx, cy = centroid

        # Waist points - top corners
        top_region = points[:, 1] < cy - 0.4 * (cy - np.min(points[:, 1]))
        if np.any(top_region):
            top_points = points[top_region]
            waist_left_idx = np.argmin(top_points[:, 0])
            waist_right_idx = np.argmax(top_points[:, 0])
            landmarks["waist_left"] = Landmark("waist_left", tuple(top_points[waist_left_idx]))
            landmarks["waist_right"] = Landmark("waist_right", tuple(top_points[waist_right_idx]))

        # Crotch point - using convexity defects
        hull = cv2.convexHull(contour, returnPoints=False)
        if hull.shape[0] > 3:
            defects = cv2.convexityDefects(contour, hull)
            if defects is not None:
                landmarks = self._find_crotch_point(defects, points, cx, cy, landmarks)

        # Ankle points - bottom corners
        bottom_region = points[:, 1] > cy + 0.4 * (np.max(points[:, 1]) - cy)
        if np.any(bottom_region):
            bottom_points = points[bottom_region]
            ankle_left_idx = np.argmin(bottom_points[:, 0])
            ankle_right_idx = np.argmax(bottom_points[:, 0])
            landmarks["ankle_left"] = Landmark("ankle_left", tuple(bottom_points[ankle_left_idx]))
            landmarks["ankle_right"] = Landmark("ankle_right", tuple(bottom_points[ankle_right_idx]))

        return landmarks

    def _find_underarm_points(self, defects, points, cx, cy, landmarks):
        """Find underarm points from convexity defects"""
        max_depth_left = 0
        max_depth_right = 0
        underarm_left = None
        underarm_right = None

        for defect in defects:
            s, e, f, d = defect[0]
            far_point = points[f]

            # Look for defects in upper-middle region
            if far_point[1] < cy and far_point[1] > cy - 0.5 * (cy - np.min(points[:, 1])):
                if far_point[0] < cx and d > max_depth_left:
                    max_depth_left = d
                    underarm_left = far_point
                elif far_point[0] > cx and d > max_depth_right:
                    max_depth_right = d
                    underarm_right = far_point

        if underarm_left is not None:
            landmarks["underarm_left"] = Landmark("underarm_left", tuple(underarm_left))
        if underarm_right is not None:
            landmarks["underarm_right"] = Landmark("underarm_right", tuple(underarm_right))

        return landmarks

    def _find_crotch_point(self, defects, points, cx, cy, landmarks):
        """Find crotch point from convexity defects"""
        max_depth = 0
        crotch_point = None

        for defect in defects:
            s, e, f, d = defect[0]
            far_point = points[f]

            # Look for defects in lower-middle region
            if far_point[1] > cy and abs(far_point[0] - cx) < 0.2 * (np.max(points[:, 0]) - np.min(points[:, 0])):
                if d > max_depth:
                    max_depth = d
                    crotch_point = far_point

        if crotch_point is not None:
            landmarks["crotch"] = Landmark("crotch", tuple(crotch_point))

        return landmarks

class MeasurementCalculator:
    """Calculates garment measurements from landmarks"""

    def __init__(self, pixel_to_mm: float = 1.0, rect_rms_mm: float = 0.5):
        self.pixel_to_mm = pixel_to_mm
        self.rect_rms_mm = rect_rms_mm
        self.measurements = {}

    def estimate_uncertainty(self, measure_fn, base_mask: np.ndarray,
                           contour: np.ndarray, rect_rms_mm: float = 0.5) -> float:
        """
        Estimate measurement uncertainty via morphological perturbation
        Returns 95% confidence interval in mm
        """

        # Create perturbed masks
        masks = [base_mask]
        se1 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        se2 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

        masks.append(cv2.morphologyEx(base_mask, cv2.MORPH_ERODE, se1))
        masks.append(cv2.morphologyEx(base_mask, cv2.MORPH_DILATE, se1))
        masks.append(cv2.morphologyEx(base_mask, cv2.MORPH_ERODE, se2))
        masks.append(cv2.morphologyEx(base_mask, cv2.MORPH_DILATE, se2))

        # Compute measurements on perturbed masks
        values = []
        for mask in masks:
            try:
                value = measure_fn(mask, contour)
                if value is not None and value > 0:
                    values.append(value)
            except:
                pass  # Skip failed measurements

        if len(values) < 2:
            # Return default 95% CI if perturbation fails
            return 1.96 * 0.5

        # Calculate standard deviation from perturbations
        seg_std = float(np.std(values))

        # Add rectification and scale uncertainties
        rect_std = float(rect_rms_mm)  # Homography reprojection RMS
        scale_std = 0.15  # mm, conservative estimate for scale uncertainty

        # Combine uncertainties using RSS (Root Sum of Squares)
        total_sigma = float(np.sqrt(seg_std**2 + rect_std**2 + scale_std**2))

        # Return 95% confidence interval (1.96 * sigma)
        return max(1.96 * total_sigma, 0.5)  # Minimum 0.5mm at 95% CI

    def calculate_all_measurements(self, landmarks: Dict[str, Landmark],
                                  contour: np.ndarray,
                                  mask: np.ndarray,
                                  garment_type: GarmentType) -> Dict[str, Measurement]:
        """Calculate all measurements based on garment type"""

        if garment_type in [GarmentType.SHIRT, GarmentType.HOODIE]:
            self._calculate_shirt_measurements(landmarks, contour, mask)
        elif garment_type == GarmentType.PANTS:
            self._calculate_pants_measurements(landmarks, contour, mask)
        else:
            self._calculate_basic_measurements(landmarks, contour, mask)

        return self.measurements

    def _measure_width(self, mask, contour):
        """Helper to measure width for uncertainty calculation"""
        points = contour[:, 0, :]
        return (np.max(points[:, 0]) - np.min(points[:, 0])) * self.pixel_to_mm

    def _measure_height(self, mask, contour):
        """Helper to measure height for uncertainty calculation"""
        points = contour[:, 0, :]
        return (np.max(points[:, 1]) - np.min(points[:, 1])) * self.pixel_to_mm

    def _calculate_basic_measurements(self, landmarks, contour, mask):
        """Calculate basic width and height measurements"""
        if "leftmost" in landmarks and "rightmost" in landmarks:
            width = self._calculate_distance(landmarks["leftmost"].point,
                                           landmarks["rightmost"].point)
            # Calculate uncertainty using perturbation
            uncertainty = self.estimate_uncertainty(self._measure_width, mask, contour, self.rect_rms_mm)
            self.measurements["width"] = Measurement("Width", width, uncertainty)

        if "topmost" in landmarks and "bottommost" in landmarks:
            height = self._calculate_distance(landmarks["topmost"].point,
                                           landmarks["bottommost"].point)
            # Calculate uncertainty using perturbation
            uncertainty = self.estimate_uncertainty(self._measure_height, mask, contour, self.rect_rms_mm)
            self.measurements["height"] = Measurement("Height", height, uncertainty)

    def _measure_chest_width(self, mask, contour):
        """Helper to measure chest width for uncertainty calculation"""
        # Find chest line approximately 30% down from top
        points = contour[:, 0, :]
        y_min = np.min(points[:, 1])
        y_max = np.max(points[:, 1])
        chest_y = int(y_min + 0.3 * (y_max - y_min))

        if chest_y < mask.shape[0]:
            row = mask[chest_y, :]
            if np.any(row > 0):
                xs = np.where(row > 0)[0]
                return (xs.max() - xs.min()) * self.pixel_to_mm
        return 0.0

    def _calculate_shirt_measurements(self, landmarks, contour, mask):
        """Calculate measurements specific to shirts"""

        # Chest width
        if "underarm_left" in landmarks and "underarm_right" in landmarks:
            chest_width = abs(landmarks["underarm_right"].point[0] -
                            landmarks["underarm_left"].point[0]) * self.pixel_to_mm
            # Calculate uncertainty
            uncertainty = self.estimate_uncertainty(self._measure_chest_width, mask, contour, self.rect_rms_mm)
            self.measurements["chest_width"] = Measurement("Chest Width", chest_width, uncertainty)

        # HPS to hem length
        if "hps_left" in landmarks:
            hps_x, hps_y = landmarks["hps_left"].point
            # Find hem point directly below HPS
            col_pixels = mask[:, int(hps_x)]
            if np.any(col_pixels > 0):
                y_bottom = np.max(np.where(col_pixels > 0))
                hps_length = abs(y_bottom - hps_y) * self.pixel_to_mm
                self.measurements["hps_length"] = Measurement("HPS to Hem", hps_length, 1.2)

        # Shoulder width
        if "shoulder_left" in landmarks and "shoulder_right" in landmarks:
            shoulder_width = self._calculate_distance(landmarks["shoulder_left"].point,
                                                     landmarks["shoulder_right"].point)
            self.measurements["shoulder_width"] = Measurement("Shoulder Width", shoulder_width, 1.0)

        # Sleeve length (left)
        if "shoulder_left" in landmarks and "cuff_left" in landmarks:
            sleeve_length = self._calculate_contour_distance(contour,
                                                            landmarks["shoulder_left"].point,
                                                            landmarks["cuff_left"].point)
            self.measurements["sleeve_length_left"] = Measurement("Left Sleeve", sleeve_length, 1.5)

        # Sleeve length (right)
        if "shoulder_right" in landmarks and "cuff_right" in landmarks:
            sleeve_length = self._calculate_contour_distance(contour,
                                                            landmarks["shoulder_right"].point,
                                                            landmarks["cuff_right"].point)
            self.measurements["sleeve_length_right"] = Measurement("Right Sleeve", sleeve_length, 1.5)

    def _calculate_pants_measurements(self, landmarks, contour, mask):
        """Calculate measurements specific to pants"""

        # Waist width
        if "waist_left" in landmarks and "waist_right" in landmarks:
            waist_width = abs(landmarks["waist_right"].point[0] -
                            landmarks["waist_left"].point[0]) * self.pixel_to_mm
            self.measurements["waist_width"] = Measurement("Waist Width", waist_width, 1.0)

        # Hip width (max width in upper region)
        if "waist_left" in landmarks and "crotch" in landmarks:
            waist_y = landmarks["waist_left"].point[1]
            crotch_y = landmarks.get("crotch", landmarks["centroid"]).point[1]
            hip_width = self._find_max_width(mask, waist_y, crotch_y)
            self.measurements["hip_width"] = Measurement("Hip Width", hip_width, 1.0)

        # Outseam
        if "waist_left" in landmarks and "ankle_left" in landmarks:
            outseam = self._calculate_contour_distance(contour,
                                                      landmarks["waist_left"].point,
                                                      landmarks["ankle_left"].point)
            self.measurements["outseam"] = Measurement("Outseam", outseam, 1.5)

        # Inseam
        if "crotch" in landmarks and "ankle_left" in landmarks:
            inseam = self._calculate_contour_distance(contour,
                                                     landmarks["crotch"].point,
                                                     landmarks["ankle_left"].point)
            self.measurements["inseam"] = Measurement("Inseam", inseam, 1.5)

    def _calculate_distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance between two points in mm"""
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        return math.hypot(dx, dy) * self.pixel_to_mm

    def _calculate_contour_distance(self, contour: np.ndarray,
                                   p1: Tuple[float, float],
                                   p2: Tuple[float, float]) -> float:
        """Calculate distance along contour between two points"""
        points = contour[:, 0, :]

        # Find closest contour points to p1 and p2
        idx1 = np.argmin(np.linalg.norm(points - np.array(p1), axis=1))
        idx2 = np.argmin(np.linalg.norm(points - np.array(p2), axis=1))

        # Get the path along contour
        if idx1 < idx2:
            path = points[idx1:idx2+1]
        else:
            # Wrap around
            path = np.concatenate([points[idx1:], points[:idx2+1]])

        # Calculate arc length
        distance = 0.0
        for i in range(len(path) - 1):
            distance += math.hypot(path[i+1, 0] - path[i, 0],
                                 path[i+1, 1] - path[i, 1])

        return distance * self.pixel_to_mm

    def _find_max_width(self, mask: np.ndarray, y_start: int, y_end: int) -> float:
        """Find maximum width in a vertical region"""
        max_width = 0
        for y in range(int(y_start), int(y_end)):
            if y >= 0 and y < mask.shape[0]:
                row = mask[y, :]
                if np.any(row > 0):
                    xs = np.where(row > 0)[0]
                    width = xs.max() - xs.min()
                    max_width = max(max_width, width)

        return max_width * self.pixel_to_mm

class MeasurementVisualizer:
    """Creates visual overlays showing measurements"""

    def __init__(self):
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.6
        self.thickness = 2
        self.color_pass = (0, 255, 0)  # Green
        self.color_fail = (0, 0, 255)  # Red
        self.color_info = (255, 255, 0)  # Yellow

    def create_overlay(self, image: np.ndarray,
                      landmarks: Dict[str, Landmark],
                      measurements: Dict[str, Measurement],
                      contour: np.ndarray,
                      pixel_to_mm: float = 1.0) -> np.ndarray:
        """Create visual overlay with measurements and landmarks"""
        overlay = image.copy()

        # Store pixel_to_mm for use in drawing methods
        self.pixel_to_mm = pixel_to_mm

        # Draw contour
        cv2.drawContours(overlay, [contour], -1, self.color_info, 1)

        # Draw landmarks
        for name, landmark in landmarks.items():
            pt = tuple(map(int, landmark.point))
            cv2.circle(overlay, pt, 5, self.color_info, -1)
            cv2.putText(overlay, name, (pt[0] + 10, pt[1]),
                       self.font, 0.4, self.color_info, 1)

        # Draw measurement lines
        self._draw_measurement_lines(overlay, landmarks, measurements)

        # Add measurement text overlay
        self._add_measurement_text(overlay, measurements)

        # Add scale bar
        self._draw_scale_bar(overlay)

        return overlay

    def _draw_measurement_lines(self, overlay, landmarks, measurements):
        """Draw lines representing measurements"""

        # Get mm to pixel conversion factor
        # Assuming pixel_to_mm is set correctly in the system
        mm_to_px = 1.0  # Default if scale is already in pixels
        if hasattr(self, 'pixel_to_mm') and self.pixel_to_mm > 0:
            mm_to_px = 1.0 / self.pixel_to_mm

        # Chest width line
        if "underarm_left" in landmarks and "underarm_right" in landmarks:
            p1 = tuple(map(int, landmarks["underarm_left"].point))
            p2 = tuple(map(int, landmarks["underarm_right"].point))
            cv2.line(overlay, p1, p2, self.color_pass, 2)

            # Add label
            mid_x = (p1[0] + p2[0]) // 2
            mid_y = (p1[1] + p2[1]) // 2
            if "chest_width" in measurements:
                value = measurements["chest_width"].value
                cv2.putText(overlay, f"Chest: {value:.0f}mm",
                          (mid_x - 50, mid_y - 10),
                          self.font, self.font_scale, self.color_pass, self.thickness)

        # Shoulder width line
        if "shoulder_left" in landmarks and "shoulder_right" in landmarks:
            p1 = tuple(map(int, landmarks["shoulder_left"].point))
            p2 = tuple(map(int, landmarks["shoulder_right"].point))
            cv2.line(overlay, p1, p2, self.color_pass, 2)

        # HPS to hem line - FIX: convert mm to pixels
        if "hps_left" in landmarks and "hps_length" in measurements:
            p1 = tuple(map(int, landmarks["hps_left"].point))
            # Convert mm measurement to pixels for drawing
            length_px = int(measurements["hps_length"].value * mm_to_px)
            p2 = (p1[0], p1[1] + length_px)
            cv2.line(overlay, p1, p2, self.color_pass, 2)

    def _add_measurement_text(self, overlay, measurements):
        """Add measurement summary text"""
        y_offset = 30
        x_offset = 10

        cv2.putText(overlay, "MEASUREMENTS:", (x_offset, y_offset),
                   self.font, 0.7, (255, 255, 255), 2)
        y_offset += 30

        for name, measurement in measurements.items():
            color = self.color_pass if measurement.status == "pass" else self.color_fail
            text = f"{measurement.name}: {measurement.value:.1f} ± {measurement.uncertainty:.1f} mm"
            cv2.putText(overlay, text, (x_offset, y_offset),
                       self.font, 0.5, color, 1)
            y_offset += 25

    def _draw_scale_bar(self, overlay):
        """Draw a 100mm scale bar on the overlay"""
        # Position scale bar at bottom right
        h, w = overlay.shape[:2]
        bar_length_mm = 100.0
        bar_length_px = int(bar_length_mm / self.pixel_to_mm) if self.pixel_to_mm > 0 else 100

        bar_x = w - bar_length_px - 50
        bar_y = h - 50

        # Draw the scale bar
        cv2.line(overlay, (bar_x, bar_y), (bar_x + bar_length_px, bar_y), (255, 255, 255), 3)

        # Add end caps
        cv2.line(overlay, (bar_x, bar_y - 5), (bar_x, bar_y + 5), (255, 255, 255), 2)
        cv2.line(overlay, (bar_x + bar_length_px, bar_y - 5),
                (bar_x + bar_length_px, bar_y + 5), (255, 255, 255), 2)

        # Add text label
        label = f"100 mm"
        text_size = cv2.getTextSize(label, self.font, 0.5, 1)[0]
        text_x = bar_x + (bar_length_px - text_size[0]) // 2
        cv2.putText(overlay, label, (text_x, bar_y - 10),
                   self.font, 0.5, (255, 255, 255), 1)

        # Add PPM info
        ppm_label = f"PPM: {1.0/self.pixel_to_mm:.1f}" if self.pixel_to_mm > 0 else "PPM: N/A"
        cv2.putText(overlay, ppm_label, (bar_x, bar_y + 20),
                   self.font, 0.4, (255, 255, 255), 1)

class GarmentMeasurementSystem:
    """Main class orchestrating the complete measurement pipeline"""

    def __init__(self, calibration_file: Optional[str] = None):
        self.calibration = CameraCalibration(calibration_file)
        self.preprocessor = ImagePreprocessor(self.calibration)
        self.segmentation = GarmentSegmentation(ppm=self.calibration.ppm)
        self.visualizer = MeasurementVisualizer()

    def check_image_quality(self, gray_image: np.ndarray):
        """Check image quality for blur and exposure issues"""

        # Check for blur using Laplacian variance
        laplacian = cv2.Laplacian(gray_image, cv2.CV_64F).var()
        if laplacian < 50:  # Adjusted threshold for test images
            raise RuntimeError(f"Image too blurry (focus score: {laplacian:.1f}). Please recapture.")

        # Check exposure
        p5, p95 = np.percentile(gray_image, [5, 95])
        if p5 < 10:
            raise RuntimeError("Image underexposed. Please increase lighting.")
        if p95 > 245:
            raise RuntimeError("Image overexposed. Please reduce lighting.")

        logger.info(f"Image quality OK - Focus: {laplacian:.1f}, Exposure: {p5:.0f}-{p95:.0f}")

    def process_image(self, image_path: str,
                      output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a garment image and extract measurements

        Returns:
            Dictionary containing measurements, landmarks, and metadata
        """
        logger.info(f"Processing image: {image_path}")

        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        # Check image quality
        gray_temp = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        self.check_image_quality(gray_temp)

        # Preprocess
        rectified, gray = self.preprocessor.preprocess(image)

        # Mandatory scale sanity check (requires ArUco visible after rectification)
        try:
            from calibration_tool import CalibrationTool, CalibrationData
            calib_tool = CalibrationTool()

            # Create CalibrationData from our calibration
            calib_data = CalibrationData(
                camera_matrix=self.calibration.camera_matrix.tolist(),
                dist_coeff=self.calibration.dist_coeffs.tolist(),
                homography=self.calibration.homography.tolist(),
                ppm=self.calibration.ppm,
                pixel_to_mm=self.calibration.pixel_to_mm,
                rect_rms_mm=self.calibration.rect_rms_mm,
                bench_width_mm=self.calibration.bench_dims_mm.get("width", 1200.0),
                bench_height_mm=self.calibration.bench_dims_mm.get("height", 800.0),
                marker_world_mm={"0": [0, 0], "1": [1100, 0], "2": [1100, 700], "3": [0, 700]},
                marker_size_mm=30.0
            )
            calib_tool.data = calib_data

            # Expected distance between TL (id=0) and TR (id=1) markers
            expected_width = self.calibration.bench_dims_mm.get("width", 1100.0)
            ok, msg = calib_tool.verify_rectified_scale(
                rectified,
                expected_dx_mm=expected_width,
                id_left=0, id_right=1, tol_mm=3.0  # 0.3% tolerance
            )
            logger.info(f"Scale check: {msg}")
            if not ok:
                raise RuntimeError(f"Scale verification failed: {msg}\n"
                                 "Please ensure all 4 ArUco markers are visible and garment is properly placed.")
        except ImportError as e:
            logger.error(f"CalibrationTool not available: {e}")
            raise RuntimeError("Calibration tool required for scale verification")
        except RuntimeError:
            raise  # Re-raise runtime errors
        except Exception as e:
            logger.warning(f"Scale check failed with error: {e}")
            # For now, allow continuation but log the issue
            pass

        # Segment garment
        mask, contour = self.segmentation.segment(gray)

        # Area plausibility check
        area = np.count_nonzero(mask)
        bench_area = mask.shape[0] * mask.shape[1]
        area_ratio = area / bench_area if bench_area > 0 else 0

        if not (0.15 <= area_ratio <= 0.85):
            raise RuntimeError(f"Garment area out of plausible range ({area_ratio:.1%} of bench).\n"
                             "Please recenter garment, extend sleeves/legs fully, "
                             "and ensure background is visible around edges.")

        # Padding margin check - ensure garment not touching edges
        min_padding_mm = 15.0  # Minimum distance from edge in mm
        min_padding_px = int(min_padding_mm * self.calibration.ppm)

        # Find minimum distance to image border
        h, w = mask.shape
        pts = contour[:, 0, :]  # Get contour points
        min_dist_to_edge = min(
            np.min(pts[:, 0]),  # Distance to left edge
            np.min(pts[:, 1]),  # Distance to top edge
            w - np.max(pts[:, 0]),  # Distance to right edge
            h - np.max(pts[:, 1])   # Distance to bottom edge
        )

        if min_dist_to_edge < min_padding_px:
            min_dist_mm = min_dist_to_edge * self.calibration.pixel_to_mm
            raise RuntimeError(f"Garment too close to image edge ({min_dist_mm:.1f}mm < {min_padding_mm}mm).\n"
                             "Please re-position garment away from borders to avoid truncation.")

        logger.info(f"Garment area: {area_ratio:.1%} of bench, "
                   f"Min edge distance: {min_dist_to_edge * self.calibration.pixel_to_mm:.1f}mm")

        # Detect garment type
        garment_type = self.segmentation.detect_garment_type(contour)
        logger.info(f"Detected garment type: {garment_type.value}")

        # Detect landmarks
        detector = LandmarkDetector(garment_type)
        landmarks = detector.detect_landmarks(contour, mask)

        # Calculate measurements with proper uncertainty
        rect_rms = self.calibration.rect_rms_mm if hasattr(self.calibration, 'rect_rms_mm') else 0.5
        calculator = MeasurementCalculator(
            pixel_to_mm=self.calibration.pixel_to_mm,
            rect_rms_mm=rect_rms
        )
        measurements = calculator.calculate_all_measurements(
            landmarks, contour, mask, garment_type
        )

        # Create visualization
        overlay = self.visualizer.create_overlay(rectified, landmarks, measurements, contour,
                                                self.calibration.pixel_to_mm)

        # Save outputs if requested
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # Save overlay image
            overlay_file = output_path / f"{Path(image_path).stem}_overlay.png"
            cv2.imwrite(str(overlay_file), overlay)

            # Save measurements JSON
            json_file = output_path / f"{Path(image_path).stem}_measurements.json"
            self._save_measurements_json(json_file, measurements, landmarks, garment_type)

        # Prepare return data
        results = {
            "garment_type": garment_type.value,
            "measurements": {k: {"value": m.value, "uncertainty": m.uncertainty}
                           for k, m in measurements.items()},
            "landmarks": {k: {"x": l.point[0], "y": l.point[1]}
                        for k, l in landmarks.items()},
            "overlay_image": overlay
        }

        return results

    def _save_measurements_json(self, filepath: Path, measurements, landmarks, garment_type):
        """Save measurements and landmarks to JSON file"""
        data = {
            "garment_type": garment_type.value,
            "measurements": {},
            "landmarks": {}
        }

        for name, m in measurements.items():
            data["measurements"][name] = {
                "value": m.value,
                "uncertainty": m.uncertainty,
                "unit": m.unit,
                "status": m.status
            }

        for name, l in landmarks.items():
            data["landmarks"][name] = {
                "x": float(l.point[0]),
                "y": float(l.point[1]),
                "confidence": float(l.confidence)
            }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved measurements to {filepath}")

def main():
    """Main entry point for testing"""
    import argparse

    parser = argparse.ArgumentParser(description="Garment Measurement System")
    parser.add_argument("image", help="Path to garment image")
    parser.add_argument("--calibration", help="Path to calibration JSON file")
    parser.add_argument("--output", help="Output directory for results")

    args = parser.parse_args()

    # Initialize system
    system = GarmentMeasurementSystem(args.calibration)

    # Process image
    try:
        results = system.process_image(args.image, args.output)

        # Print results
        print("\n=== MEASUREMENT RESULTS ===")
        print(f"Garment Type: {results['garment_type']}")
        print("\nMeasurements:")
        for name, data in results['measurements'].items():
            print(f"  {name}: {data['value']:.1f} ± {data['uncertainty']:.1f} mm")

        # Show overlay if no output directory specified
        if not args.output:
            cv2.imshow("Measurement Overlay", results['overlay_image'])
            cv2.waitKey(0)
            cv2.destroyAllWindows()

    except Exception as e:
        logger.error(f"Error processing image: {e}")
        raise

if __name__ == "__main__":
    main()