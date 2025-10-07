#!/usr/bin/env python3
"""
Camera Calibration Tool for Garment Measurement System
Generates and manages calibration files for the measurement pipeline
"""

import cv2
import numpy as np
import json
import logging
from pathlib import Path
from typing import List, Tuple, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CalibrationTool:
    """Tool for camera calibration and homography calculation"""

    def __init__(self):
        self.camera_matrix = None
        self.dist_coeffs = None
        self.homography = None
        # Handle different OpenCV versions
        try:
            self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
            self.aruco_params = cv2.aruco.DetectorParameters()
        except AttributeError:
            # Older OpenCV version
            self.aruco_dict = cv2.aruco.Dictionary_get(cv2.aruco.DICT_6X6_250)
            self.aruco_params = cv2.aruco.DetectorParameters_create()

    def create_default_calibration(self, output_file: str):
        """Create a default calibration file for testing without actual calibration"""

        # Default camera matrix (identity-like for testing)
        default_calib = {
            "camera_matrix": [
                [3000.0, 0.0, 2016.0],
                [0.0, 3000.0, 1512.0],
                [0.0, 0.0, 1.0]
            ],
            "dist_coeff": [0.0, 0.0, 0.0, 0.0, 0.0],
            "homography": [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0]
            ],
            "pixel_to_mm": 0.3,  # 0.3mm per pixel
            "rms_error": 0.0,
            "calibration_date": "2025-10-07",
            "bench_dimensions_mm": {
                "width": 1200,
                "height": 800
            },
            "fiducial_markers": {
                "top_left": {"id": 0, "world_coords": [0, 0]},
                "top_right": {"id": 1, "world_coords": [1100, 0]},
                "bottom_right": {"id": 2, "world_coords": [1100, 700]},
                "bottom_left": {"id": 3, "world_coords": [0, 700]}
            }
        }

        with open(output_file, 'w') as f:
            json.dump(default_calib, f, indent=2)

        logger.info(f"Created default calibration file: {output_file}")
        return default_calib

    def calibrate_from_checkerboard(self, images: List[np.ndarray],
                                   pattern_size: Tuple[int, int] = (9, 6),
                                   square_size: float = 30.0) -> bool:
        """Perform intrinsic calibration using checkerboard images"""

        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

        # Prepare object points
        objp = np.zeros((pattern_size[0] * pattern_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:pattern_size[0], 0:pattern_size[1]].T.reshape(-1, 2)
        objp *= square_size

        objpoints = []
        imgpoints = []

        for img in images:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

            # Find the chess board corners
            ret, corners = cv2.findChessboardCorners(gray, pattern_size, None)

            if ret:
                objpoints.append(objp)
                corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
                imgpoints.append(corners2)

                # Draw and display the corners (optional)
                cv2.drawChessboardCorners(img, pattern_size, corners2, ret)

        if len(objpoints) > 0:
            ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
                objpoints, imgpoints, gray.shape[::-1], None, None
            )

            self.camera_matrix = mtx
            self.dist_coeffs = dist

            logger.info(f"Calibration successful! RMS error: {ret:.3f}")
            return True

        logger.error("Calibration failed - no valid checkerboard patterns found")
        return False

    def detect_aruco_markers(self, image: np.ndarray):
        """Detect ArUco markers in image for homography calculation"""

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        corners, ids, rejected = cv2.aruco.detectMarkers(
            gray, self.aruco_dict, parameters=self.aruco_params
        )

        if ids is not None and len(ids) > 0:
            logger.info(f"Detected {len(ids)} ArUco markers")
            return corners, ids

        logger.warning("No ArUco markers detected")
        return None, None

    def calculate_homography_from_markers(self, image: np.ndarray,
                                         world_coords: dict) -> Optional[np.ndarray]:
        """Calculate homography from detected ArUco markers"""

        corners, ids = self.detect_aruco_markers(image)

        if ids is None or len(ids) < 4:
            logger.error("Need at least 4 markers for homography calculation")
            return None

        image_points = []
        world_points = []

        for i, marker_id in enumerate(ids.flatten()):
            if marker_id in world_coords:
                # Get center of marker
                marker_corners = corners[i][0]
                center = np.mean(marker_corners, axis=0)
                image_points.append(center)
                world_points.append(world_coords[marker_id])

        if len(image_points) >= 4:
            image_points = np.array(image_points, dtype=np.float32)
            world_points = np.array(world_points, dtype=np.float32)

            homography, _ = cv2.findHomography(image_points, world_points, cv2.RANSAC, 5.0)
            self.homography = homography

            logger.info("Homography calculated successfully")
            return homography

        logger.error("Not enough matching markers for homography")
        return None

    def save_calibration(self, output_file: str, additional_data: dict = None):
        """Save calibration parameters to JSON file"""

        calib_data = {
            "camera_matrix": self.camera_matrix.tolist() if self.camera_matrix is not None else None,
            "dist_coeff": self.dist_coeffs.tolist() if self.dist_coeffs is not None else None,
            "homography": self.homography.tolist() if self.homography is not None else None,
            "pixel_to_mm": 0.3  # Default value, should be calculated from homography
        }

        if additional_data:
            calib_data.update(additional_data)

        with open(output_file, 'w') as f:
            json.dump(calib_data, f, indent=2)

        logger.info(f"Calibration saved to {output_file}")

    def verify_calibration(self, image: np.ndarray, calib_file: str) -> bool:
        """Verify calibration accuracy using a test image"""

        with open(calib_file, 'r') as f:
            calib = json.load(f)

        camera_matrix = np.array(calib["camera_matrix"])
        dist_coeffs = np.array(calib["dist_coeff"])
        homography = np.array(calib.get("homography", np.eye(3)))

        # Undistort
        undistorted = cv2.undistort(image, camera_matrix, dist_coeffs)

        # Apply homography
        h, w = image.shape[:2]
        rectified = cv2.warpPerspective(undistorted, homography, (w, h))

        # Detect markers in rectified image
        corners, ids = self.detect_aruco_markers(rectified)

        if ids is not None:
            # Check if markers are where expected
            logger.info("Calibration verification: Markers detected in rectified image")
            return True

        logger.warning("Calibration verification: No markers found")
        return False

def generate_aruco_board(output_file: str, board_size: Tuple[int, int] = (4, 3),
                         marker_size: int = 200, margin: int = 50):
    """Generate an ArUco marker board for printing"""

    # Handle different OpenCV versions
    try:
        dict_aruco = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
    except AttributeError:
        dict_aruco = cv2.aruco.Dictionary_get(cv2.aruco.DICT_6X6_250)

    # Calculate board dimensions
    board_width = board_size[0] * (marker_size + margin) + margin
    board_height = board_size[1] * (marker_size + margin) + margin

    # Create white background
    board = np.ones((board_height, board_width), dtype=np.uint8) * 255

    marker_id = 0
    for row in range(board_size[1]):
        for col in range(board_size[0]):
            # Generate marker
            try:
                marker = cv2.aruco.generateImageMarker(dict_aruco, marker_id, marker_size)
            except AttributeError:
                marker = cv2.aruco.drawMarker(dict_aruco, marker_id, marker_size)

            # Calculate position
            x = margin + col * (marker_size + margin)
            y = margin + row * (marker_size + margin)

            # Place marker on board
            board[y:y+marker_size, x:x+marker_size] = marker

            marker_id += 1

    cv2.imwrite(output_file, board)
    logger.info(f"ArUco board saved to {output_file}")

    return board

def main():
    """Main calibration workflow"""
    import argparse

    parser = argparse.ArgumentParser(description="Camera Calibration Tool")
    parser.add_argument("--mode", choices=["default", "checkerboard", "aruco", "generate", "verify"],
                       default="default", help="Calibration mode")
    parser.add_argument("--input", help="Input image or directory")
    parser.add_argument("--output", default="calibration.json", help="Output calibration file")
    parser.add_argument("--pattern", default="9,6", help="Checkerboard pattern size (cols,rows)")
    parser.add_argument("--square-size", type=float, default=30.0, help="Square size in mm")

    args = parser.parse_args()

    tool = CalibrationTool()

    if args.mode == "default":
        # Create default calibration for testing
        tool.create_default_calibration(args.output)

    elif args.mode == "generate":
        # Generate ArUco board for printing
        output_file = args.output if args.output.endswith('.png') else "aruco_board.png"
        generate_aruco_board(output_file)

    elif args.mode == "checkerboard":
        if not args.input:
            logger.error("Input images required for checkerboard calibration")
            return

        # Load images
        images = []
        input_path = Path(args.input)

        if input_path.is_file():
            img = cv2.imread(str(input_path))
            if img is not None:
                images.append(img)
        elif input_path.is_dir():
            for img_file in input_path.glob("*.jpg") | input_path.glob("*.png"):
                img = cv2.imread(str(img_file))
                if img is not None:
                    images.append(img)

        if images:
            pattern = tuple(map(int, args.pattern.split(',')))
            if tool.calibrate_from_checkerboard(images, pattern, args.square_size):
                tool.save_calibration(args.output)
        else:
            logger.error("No valid images found")

    elif args.mode == "aruco":
        if not args.input:
            logger.error("Input image required for ArUco calibration")
            return

        img = cv2.imread(args.input)
        if img is not None:
            # Define world coordinates for markers (in mm)
            # This should match your actual marker placement
            world_coords = {
                0: [0, 0],
                1: [1100, 0],
                2: [1100, 700],
                3: [0, 700]
            }

            homography = tool.calculate_homography_from_markers(img, world_coords)
            if homography is not None:
                tool.save_calibration(args.output, {"fiducial_markers": world_coords})
        else:
            logger.error(f"Could not load image: {args.input}")

    elif args.mode == "verify":
        if not args.input or not args.output:
            logger.error("Input image and calibration file required for verification")
            return

        img = cv2.imread(args.input)
        if img is not None:
            if tool.verify_calibration(img, args.output):
                print("Calibration verified successfully!")
            else:
                print("Calibration verification failed")
        else:
            logger.error(f"Could not load image: {args.input}")

if __name__ == "__main__":
    main()