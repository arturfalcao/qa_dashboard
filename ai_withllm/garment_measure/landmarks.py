#!/usr/bin/env python3
"""
Landmark detection module with HRNet ONNX integration for garment keypoints.
"""

import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class LandmarkDetector:
    """
    Detects measurement keypoints on garments.
    Uses heuristics by default with HRNet ONNX inference when available.
    """

    # Landmark definitions per garment type
    LANDMARKS = {
        'tshirt': [
            'left_shoulder', 'right_shoulder',
            'left_armpit', 'right_armpit',
            'left_sleeve_end', 'right_sleeve_end',
            'bottom_hem_center',
            'neck_center'
        ],
        'hoodie': [
            'left_shoulder', 'right_shoulder',
            'left_armpit', 'right_armpit',
            'left_sleeve_end', 'right_sleeve_end',
            'bottom_hem_center',
            'neck_center',
            'hood_top'
        ],
        'pants': [
            'waist_left', 'waist_right',
            'hip_left', 'hip_right',
            'crotch',
            'left_hem', 'right_hem',
            'left_thigh', 'right_thigh',
            'left_outseam_top', 'right_outseam_top'
        ],
        'shorts': [
            'waist_left', 'waist_right',
            'hip_left', 'hip_right',
            'crotch',
            'left_hem', 'right_hem',
            'left_outseam_top', 'right_outseam_top'
        ],
        'skirt': [
            'waist_left', 'waist_right',
            'hip_left', 'hip_right',
            'hem_left', 'hem_center', 'hem_right'
        ],
        'dress': [
            'bust_left', 'bust_right',
            'waist_left', 'waist_right',
            'hip_left', 'hip_right',
            'hem_left', 'hem_center', 'hem_right',
            'shoulder_left', 'shoulder_right'
        ]
    }

    def __init__(self, model_path: Optional[str] = None,
                 ppm: float = 2.0,
                 device: Optional[str] = None,
                 conf_threshold: float = 0.45):
        """
        Initialize landmark detector.

        Args:
            model_path: Path to ONNX HRNet model
            ppm: Pixels per mm for distance thresholds
            device: Device for inference ('cuda', 'cpu', or None for auto)
            conf_threshold: Minimum confidence for model predictions
        """
        self.model = None
        self.model_path = model_path
        self.ppm = ppm
        self.conf_threshold = conf_threshold
        self.device = device

        # Model input/output specs
        self.input_name = None
        self.input_shape = None
        self.output_names = None

        if model_path:
            self._load_onnx_model()

    def _load_onnx_model(self):
        """Load HRNet ONNX model for keypoint detection."""
        try:
            import onnxruntime as ort

            # Determine providers based on device
            # Check if CUDA is available using onnxruntime's method
            cuda_available = 'CUDAExecutionProvider' in ort.get_available_providers()

            if self.device == 'cuda' or (self.device is None and cuda_available):
                providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
                logger.info("Using CUDA for ONNX inference")
            else:
                providers = ['CPUExecutionProvider']
                logger.info("Using CPU for ONNX inference")

            # Create inference session
            session_options = ort.SessionOptions()
            session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            self.model = ort.InferenceSession(
                self.model_path,
                providers=providers,
                sess_options=session_options
            )

            # Get input/output info
            self.input_name = self.model.get_inputs()[0].name
            self.input_shape = self.model.get_inputs()[0].shape  # [batch, channels, height, width]
            self.output_names = [out.name for out in self.model.get_outputs()]

            logger.info(f"Loaded HRNet ONNX model from {self.model_path}")
            logger.info(f"Input shape: {self.input_shape}, Output names: {self.output_names}")

        except ImportError:
            logger.error("ONNX Runtime not installed. Install with: pip install onnxruntime-gpu")
            self.model = None
        except Exception as e:
            logger.error(f"Failed to load HRNet model: {e}")
            self.model = None

    def detect_heuristic(self, image: np.ndarray, mask: np.ndarray,
                        garment_type: str) -> Dict[str, Tuple[float, float, float]]:
        """
        Detect landmarks using heuristic methods (existing implementation).
        """
        # [Previous heuristic implementation remains unchanged]
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return {}

        # Get largest contour
        contour = max(contours, key=cv2.contourArea)

        # Get bounding box and moments
        x, y, w, h = cv2.boundingRect(contour)
        M = cv2.moments(contour)
        cx = int(M['m10'] / M['m00']) if M['m00'] > 0 else x + w // 2
        cy = int(M['m01'] / M['m00']) if M['m00'] > 0 else y + h // 2

        landmarks = {}

        if garment_type in ['tshirt', 'hoodie']:
            landmarks = self._detect_top_landmarks(mask, contour, x, y, w, h, cx, cy)
        elif garment_type in ['pants', 'shorts']:
            landmarks = self._detect_bottom_landmarks(mask, contour, x, y, w, h, cx, cy)
        elif garment_type == 'skirt':
            landmarks = self._detect_skirt_landmarks(mask, contour, x, y, w, h, cx, cy)
        elif garment_type == 'dress':
            landmarks = self._detect_dress_landmarks(mask, contour, x, y, w, h, cx, cy)

        return landmarks

    def _infer_on_roi(self, image: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Run ONNX inference on a region of interest.

        Args:
            image: Full image (BGR)
            bbox: ROI bounding box (x, y, w, h)

        Returns:
            Heatmaps for keypoints
        """
        if self.model is None:
            return None

        try:
            x, y, w, h = bbox

            # Extract and pad ROI
            pad = 20
            x1 = max(0, x - pad)
            y1 = max(0, y - pad)
            x2 = min(image.shape[1], x + w + pad)
            y2 = min(image.shape[0], y + h + pad)

            roi = image[y1:y2, x1:x2]

            # Resize to model input size
            target_h = self.input_shape[2] if len(self.input_shape) > 2 else 256
            target_w = self.input_shape[3] if len(self.input_shape) > 3 else 256
            resized = cv2.resize(roi, (target_w, target_h))

            # Normalize (ImageNet stats)
            normalized = resized.astype(np.float32) / 255.0
            mean = np.array([0.485, 0.456, 0.406]).reshape(1, 1, 3)
            std = np.array([0.229, 0.224, 0.225]).reshape(1, 1, 3)
            normalized = (normalized - mean) / std

            # Prepare input tensor (NCHW format)
            input_tensor = normalized.transpose(2, 0, 1)  # HWC to CHW
            input_tensor = np.expand_dims(input_tensor, 0).astype(np.float32)

            # Run inference
            outputs = self.model.run(self.output_names, {self.input_name: input_tensor})
            heatmaps = outputs[0][0]  # Remove batch dimension

            # Scale back to original ROI size
            num_keypoints = heatmaps.shape[0]
            scaled_heatmaps = np.zeros((num_keypoints, y2-y1, x2-x1))
            for i in range(num_keypoints):
                scaled_heatmaps[i] = cv2.resize(heatmaps[i], (x2-x1, y2-y1))

            return scaled_heatmaps, (x1, y1)

        except Exception as e:
            logger.error(f"ROI inference failed: {e}")
            return None, (0, 0)

    def _soft_argmax_2d(self, heatmaps: np.ndarray) -> np.ndarray:
        """
        Extract keypoint locations using differentiable soft-argmax.

        Args:
            heatmaps: (K, H, W) heatmaps

        Returns:
            (K, 3) array of (x, y, confidence)
        """
        K, H, W = heatmaps.shape
        heatmaps_reshaped = heatmaps.reshape(K, -1)

        # Apply softmax
        heatmaps_exp = np.exp(heatmaps_reshaped - heatmaps_reshaped.max(axis=1, keepdims=True))
        heatmaps_norm = heatmaps_exp / (heatmaps_exp.sum(axis=1, keepdims=True) + 1e-8)

        # Create coordinate grids
        xx, yy = np.meshgrid(np.arange(W), np.arange(H))
        xx_flat = xx.flatten()
        yy_flat = yy.flatten()

        # Compute weighted coordinates
        x_coords = (heatmaps_norm * xx_flat).sum(axis=1)
        y_coords = (heatmaps_norm * yy_flat).sum(axis=1)
        confidences = heatmaps_norm.max(axis=1)

        return np.stack([x_coords, y_coords, confidences], axis=1)

    def detect_with_model(self, image: np.ndarray, mask: np.ndarray,
                         garment_type: str,
                         seed_landmarks: Dict[str, Tuple[float, float, float]]) -> Dict[str, Tuple[float, float, float]]:
        """
        Detect landmarks using HRNet model with seed guidance.

        Args:
            image: Original image (BGR)
            mask: Segmentation mask
            garment_type: Type of garment
            seed_landmarks: Initial landmarks from heuristics

        Returns:
            Refined landmarks
        """
        if self.model is None:
            return seed_landmarks

        # Get garment bounding box from mask
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return seed_landmarks

        x, y, w, h = cv2.boundingRect(max(contours, key=cv2.contourArea))

        # Run inference on garment ROI
        heatmaps, offset = self._infer_on_roi(image, (x, y, w, h))
        if heatmaps is None:
            return seed_landmarks

        # Extract keypoints from heatmaps
        keypoints = self._soft_argmax_2d(heatmaps)

        # Map model keypoints to landmark names
        landmark_names = self.LANDMARKS.get(garment_type, [])
        refined_landmarks = {}

        for i, name in enumerate(landmark_names):
            if i >= len(keypoints):
                # Use seed if model doesn't have this keypoint
                if name in seed_landmarks:
                    refined_landmarks[name] = seed_landmarks[name]
                continue

            # Get model prediction
            model_x = keypoints[i, 0] + offset[0]
            model_y = keypoints[i, 1] + offset[1]
            model_conf = keypoints[i, 2]

            # Check if we should use model or seed
            if name in seed_landmarks:
                seed_x, seed_y, seed_conf = seed_landmarks[name]

                # Compute distance between model and seed
                distance_px = np.sqrt((model_x - seed_x)**2 + (model_y - seed_y)**2)
                distance_mm = distance_px / self.ppm

                # Use model if: high confidence AND close to seed
                if model_conf > self.conf_threshold and distance_mm < 30:
                    refined_landmarks[name] = (float(model_x), float(model_y), float(model_conf))
                else:
                    # Keep seed landmark
                    refined_landmarks[name] = seed_landmarks[name]
            else:
                # No seed, use model if confident
                if model_conf > self.conf_threshold:
                    refined_landmarks[name] = (float(model_x), float(model_y), float(model_conf))

        return refined_landmarks

    def detect(self, image: np.ndarray, mask: np.ndarray,
              garment_type: str) -> Dict[str, Tuple[float, float, float]]:
        """
        Main landmark detection method with model/heuristic fusion.

        Args:
            image: Original image (BGR)
            mask: Binary segmentation mask
            garment_type: Type of garment

        Returns:
            Dictionary mapping landmark name to (x, y, confidence) tuples
        """
        # Always start with heuristic detection
        heuristic_landmarks = self.detect_heuristic(image, mask, garment_type)

        # Refine with model if available
        if self.model is not None:
            landmarks = self.detect_with_model(image, mask, garment_type, heuristic_landmarks)
            logger.info(f"Used HRNet model to refine {len(landmarks)} landmarks")
        else:
            landmarks = heuristic_landmarks

        # Apply final refinement
        landmarks = self.refine_landmarks(landmarks, image, mask)

        return landmarks

    def refine_landmarks(self, landmarks: Dict[str, Tuple[float, float, float]],
                        image: np.ndarray, mask: np.ndarray) -> Dict[str, Tuple[float, float, float]]:
        """Edge-based refinement (existing implementation)."""
        refined = {}

        # Detect edges for refinement
        edges = cv2.Canny(mask, 50, 150)

        for name, (x, y, conf) in landmarks.items():
            # Search in local window for strongest edge
            window_size = 10
            x_min = max(0, int(x - window_size))
            x_max = min(image.shape[1], int(x + window_size))
            y_min = max(0, int(y - window_size))
            y_max = min(image.shape[0], int(y + window_size))

            window = edges[y_min:y_max, x_min:x_max]

            if window.size > 0 and np.sum(window) > 0:
                # Find center of mass of edges in window
                y_coords, x_coords = np.where(window > 0)
                if len(x_coords) > 0:
                    refined_x = x_min + np.mean(x_coords)
                    refined_y = y_min + np.mean(y_coords)
                    refined[name] = (float(refined_x), float(refined_y), conf)
                else:
                    refined[name] = (x, y, conf)
            else:
                refined[name] = (x, y, conf)

        return refined

    # [Previous helper methods remain unchanged]
    def _detect_top_landmarks(self, mask, contour, x, y, w, h, cx, cy):
        """Previous implementation"""
        landmarks = {}
        # ... (keep existing heuristic implementation)
        return landmarks

    def _detect_bottom_landmarks(self, mask, contour, x, y, w, h, cx, cy):
        """Previous implementation"""
        landmarks = {}
        # ... (keep existing heuristic implementation)
        return landmarks

    def _detect_skirt_landmarks(self, mask, contour, x, y, w, h, cx, cy):
        """Previous implementation"""
        landmarks = {}
        # ... (keep existing heuristic implementation)
        return landmarks

    def _detect_dress_landmarks(self, mask, contour, x, y, w, h, cx, cy):
        """Previous implementation"""
        landmarks = {}
        # ... (keep existing heuristic implementation)
        return landmarks


def main():
    """Test landmark detection with ONNX model."""
    import argparse

    parser = argparse.ArgumentParser(description='Test landmark detection')
    parser.add_argument('--image', required=True, help='Input image')
    parser.add_argument('--mask', required=True, help='Segmentation mask')
    parser.add_argument('--type', default='tshirt', help='Garment type')
    parser.add_argument('--model', help='Path to ONNX HRNet model')
    parser.add_argument('--output', help='Output visualization')
    parser.add_argument('--threshold', type=float, default=0.45,
                        help='Confidence threshold for model predictions')
    args = parser.parse_args()

    # Load images
    image = cv2.imread(args.image)
    mask = cv2.imread(args.mask, cv2.IMREAD_GRAYSCALE)

    if image is None or mask is None:
        print("Error: Could not load images")
        return

    # Initialize detector
    detector = LandmarkDetector(
        model_path=args.model,
        conf_threshold=args.threshold
    )

    # Detect landmarks
    print(f"Detecting landmarks for {args.type}...")
    print(f"Using {'HRNet model' if detector.model else 'heuristics only'}")
    landmarks = detector.detect(image, mask, args.type)

    print(f"Found {len(landmarks)} landmarks:")
    for name, (x, y, conf) in landmarks.items():
        print(f"  {name}: ({x:.1f}, {y:.1f}) conf={conf:.2f}")

    # Visualize if requested
    if args.output:
        from landmarks import visualize_landmarks
        vis = visualize_landmarks(image, landmarks)
        cv2.imwrite(args.output, vis)
        print(f"Saved visualization to {args.output}")


if __name__ == '__main__':
    main()
