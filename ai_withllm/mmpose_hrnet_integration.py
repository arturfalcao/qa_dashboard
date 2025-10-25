#!/usr/bin/env python3
"""
MMPose integration for HRNet-W48 trained on DeepFashion2.
This provides accurate fashion landmark detection using the official MMPose framework.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json
import warnings
warnings.filterwarnings('ignore')

try:
    from mmpose.apis import init_model, inference_topdown
    from mmpose.registry import VISUALIZERS
    from mmpose.structures import PoseDataSample
    from mmengine.structures import InstanceData
    import torch
except ImportError as e:
    print(f"Error importing MMPose: {e}")
    print("Please install: pip install mmpose mmcv mmengine mmdet")
    exit(1)


class MMPoseHRNetDetector:
    """MMPose-based HRNet detector for fashion landmarks."""

    # DeepFashion2 has 294 keypoints across 13 categories
    DEEPFASHION2_CATEGORIES = {
        'short_sleeved_shirt': 0,
        'long_sleeved_shirt': 1,
        'short_sleeved_outwear': 2,
        'long_sleeved_outwear': 3,
        'vest': 4,
        'sling': 5,
        'shorts': 6,
        'trousers': 7,
        'skirt': 8,
        'short_sleeved_dress': 9,
        'long_sleeved_dress': 10,
        'vest_dress': 11,
        'sling_dress': 12
    }

    # Key landmark indices for measurements (subset of 294 points)
    MEASUREMENT_LANDMARKS = {
        'tops': {
            # Collar/Neckline points (typically indices 0-4)
            'collar_left': 0,
            'collar_center': 2,
            'collar_right': 4,

            # Shoulder points (typically indices 5, 10)
            'shoulder_left': 5,
            'shoulder_right': 10,

            # Armpit points (typically indices 6, 11)
            'armpit_left': 6,
            'armpit_right': 11,

            # Chest measurement points
            'chest_left': 20,
            'chest_right': 21,

            # Hem points (typically indices 15-19)
            'hem_left': 15,
            'hem_center': 17,
            'hem_right': 19,

            # Cuff points (for long sleeves, indices vary)
            'cuff_left_outer': 35,
            'cuff_left_inner': 37,
            'cuff_right_outer': 43,
            'cuff_right_inner': 45
        },
        'bottoms': {
            # Waistband points
            'waist_left': 168,
            'waist_center': 169,
            'waist_right': 170,

            # Hip points
            'hip_left': 171,
            'crotch': 172,
            'hip_right': 173,

            # Hem points
            'hem_left_outer': 176,
            'hem_left_inner': 177,
            'hem_right_outer': 180,
            'hem_right_inner': 181
        }
    }

    def __init__(self, model_path: str = None, device: str = 'cuda'):
        """Initialize the MMPose HRNet detector."""
        self.device = device if torch.cuda.is_available() else 'cpu'

        # Default model path
        if model_path is None:
            model_path = 'models/pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth'

        self.model_path = Path(model_path)

        # Create config file if it doesn't exist
        self.config_path = self.create_config_file()

        # Initialize model
        print(f"Loading model from {self.model_path}")
        self.model = init_model(
            str(self.config_path),
            str(self.model_path),
            device=self.device
        )

        print(f"MMPose HRNet detector initialized on {self.device}")

    def create_config_file(self) -> Path:
        """Create the MMPose config file for HRNet-W48 DeepFashion2."""
        config_path = Path('hrnet_w48_deepfashion2.py')

        config_content = """
# HRNet-W48 for DeepFashion2 Fashion Landmark Detection

_base_ = ['default_runtime.py']

# Model
model = dict(
    type='TopdownPoseEstimator',
    data_preprocessor=dict(
        type='PoseDataPreprocessor',
        mean=[123.675, 116.28, 103.53],
        std=[58.395, 57.12, 57.375],
        bgr_to_rgb=True),
    backbone=dict(
        type='HRNet',
        in_channels=3,
        extra=dict(
            stage1=dict(
                num_modules=1,
                num_branches=1,
                block='BOTTLENECK',
                num_blocks=(4,),
                num_channels=(64,)),
            stage2=dict(
                num_modules=1,
                num_branches=2,
                block='BASIC',
                num_blocks=(4, 4),
                num_channels=(48, 96)),
            stage3=dict(
                num_modules=4,
                num_branches=3,
                block='BASIC',
                num_blocks=(4, 4, 4),
                num_channels=(48, 96, 192)),
            stage4=dict(
                num_modules=3,
                num_branches=4,
                block='BASIC',
                num_blocks=(4, 4, 4, 4),
                num_channels=(48, 96, 192, 384))),
        init_cfg=dict(
            type='Pretrained',
            checkpoint='torchvision://resnet50')),
    head=dict(
        type='HeatmapHead',
        in_channels=48,
        out_channels=294,  # DeepFashion2 has 294 keypoints
        deconv_out_channels=None,
        loss=dict(type='KeypointMSELoss', use_target_weight=True),
        decoder=dict(
            type='MSRAHeatmap',
            input_size=(288, 384),
            heatmap_size=(72, 96),
            sigma=3)),
    test_cfg=dict(
        flip_test=True,
        flip_mode='heatmap',
        shift_heatmap=True))

# Dataset
dataset_type = 'DeepFashion2Dataset'
data_mode = 'topdown'
data_root = ''

# Pipeline
test_pipeline = [
    dict(type='LoadImage'),
    dict(type='GetBBoxCenterScale'),
    dict(type='TopdownAffine', input_size=(288, 384)),
    dict(
        type='PackPoseInputs',
        meta_keys=('id', 'img_id', 'img_path', 'ori_shape', 'img_shape',
                   'input_size', 'input_center', 'input_scale'))
]

# For single image inference
val_dataloader = dict(
    batch_size=1,
    num_workers=1,
    persistent_workers=False,
    drop_last=False,
    sampler=dict(type='DefaultSampler', shuffle=False, round_up=False),
    dataset=dict(
        type=dataset_type,
        data_root=data_root,
        data_mode=data_mode,
        ann_file='',
        data_prefix=dict(img=''),
        pipeline=test_pipeline))

test_dataloader = val_dataloader

# Runtime
default_scope = 'mmpose'
default_hooks = dict(
    timer=dict(type='IterTimerHook'),
    logger=dict(type='LoggerHook', interval=50),
    param_scheduler=dict(type='ParamSchedulerHook'),
    checkpoint=dict(type='CheckpointHook', interval=10),
    sampler_seed=dict(type='DistSamplerSeedHook'),
    visualization=dict(type='PoseVisualizationHook', enable=False))

env_cfg = dict(
    cudnn_benchmark=False,
    mp_cfg=dict(mp_start_method='fork', opencv_num_threads=0),
    dist_cfg=dict(backend='nccl'))

log_level = 'INFO'
load_from = None
resume = False
"""

        # Also create default_runtime.py
        runtime_config = """
default_scope = 'mmpose'
default_hooks = dict(
    timer=dict(type='IterTimerHook'),
    logger=dict(type='LoggerHook', interval=50),
    param_scheduler=dict(type='ParamSchedulerHook'),
    checkpoint=dict(type='CheckpointHook', interval=10),
    sampler_seed=dict(type='DistSamplerSeedHook'),
    visualization=dict(type='PoseVisualizationHook', enable=False),
)

env_cfg = dict(
    cudnn_benchmark=False,
    mp_cfg=dict(mp_start_method='fork', opencv_num_threads=0),
    dist_cfg=dict(backend='nccl'),
)

log_level = 'INFO'
load_from = None
resume = False
"""

        with open(config_path, 'w') as f:
            f.write(config_content)

        runtime_path = Path('default_runtime.py')
        with open(runtime_path, 'w') as f:
            f.write(runtime_config)

        return config_path

    def detect_landmarks(self, image_path: str, conf_threshold: float = 0.3) -> Dict:
        """Detect fashion landmarks in an image."""
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        h, w = image.shape[:2]

        # Create bounding box for the whole image
        # MMPose expects person/garment bounding boxes
        bboxes = np.array([[0, 0, w, h, 1.0]], dtype=np.float32)

        # Run inference
        results = inference_topdown(self.model, image_path, bboxes)

        # Process results
        landmarks = []
        confidences = []

        if results and len(results) > 0:
            result = results[0]  # Take first detection

            if hasattr(result, 'pred_instances'):
                keypoints = result.pred_instances.keypoints[0]  # Shape: (294, 2)
                keypoint_scores = result.pred_instances.keypoint_scores[0]  # Shape: (294,)

                for i in range(len(keypoints)):
                    if keypoint_scores[i] > conf_threshold:
                        x, y = keypoints[i]
                        landmarks.append((int(x), int(y)))
                        confidences.append(float(keypoint_scores[i]))
                    else:
                        landmarks.append(None)
                        confidences.append(0.0)

        # Determine garment type based on detected landmarks
        garment_type = self.infer_garment_type(landmarks, confidences)

        return {
            'landmarks': landmarks,
            'confidences': confidences,
            'garment_type': garment_type,
            'num_detected': sum(1 for l in landmarks if l is not None),
            'image_size': (w, h)
        }

    def infer_garment_type(self, landmarks: List, confidences: List) -> str:
        """Infer garment type based on detected landmarks."""
        # Simple heuristic: check which category's landmarks have highest average confidence

        # Check for top garment landmarks (shoulders, collar, sleeves)
        top_indices = list(range(0, 60))  # First 60 landmarks are typically for tops
        top_conf = [confidences[i] for i in top_indices if i < len(confidences)]
        avg_top_conf = np.mean(top_conf) if top_conf else 0

        # Check for bottom garment landmarks (waist, legs, hem)
        bottom_indices = list(range(158, 182))  # Indices for bottoms
        bottom_conf = [confidences[i] for i in bottom_indices if i < len(confidences)]
        avg_bottom_conf = np.mean(bottom_conf) if bottom_conf else 0

        if avg_top_conf > avg_bottom_conf:
            return 'top'
        elif avg_bottom_conf > avg_top_conf:
            return 'bottom'
        else:
            return 'unknown'

    def extract_key_measurements(self, detection_result: Dict) -> Dict:
        """Extract key measurement points from all detected landmarks."""
        landmarks = detection_result['landmarks']
        garment_type = detection_result['garment_type']

        measurements = {}

        if garment_type == 'top':
            # Extract top measurements
            landmark_map = self.MEASUREMENT_LANDMARKS['tops']

            # Shoulders
            if self._check_landmark(landmarks, 5) and self._check_landmark(landmarks, 10):
                measurements['shoulder_left'] = landmarks[5]
                measurements['shoulder_right'] = landmarks[10]
                measurements['shoulder_width'] = self._calculate_distance(landmarks[5], landmarks[10])

            # Armpits
            if self._check_landmark(landmarks, 6) and self._check_landmark(landmarks, 11):
                measurements['armpit_left'] = landmarks[6]
                measurements['armpit_right'] = landmarks[11]
                measurements['armpit_width'] = self._calculate_distance(landmarks[6], landmarks[11])

            # Chest (use armpit level or specific chest points if available)
            if self._check_landmark(landmarks, 20) and self._check_landmark(landmarks, 21):
                measurements['chest_left'] = landmarks[20]
                measurements['chest_right'] = landmarks[21]
                measurements['chest_width'] = self._calculate_distance(landmarks[20], landmarks[21])
            elif 'armpit_left' in measurements and 'armpit_right' in measurements:
                # Estimate chest as slightly below armpits
                left_x = measurements['armpit_left'][0]
                right_x = measurements['armpit_right'][0]
                chest_y = measurements['armpit_left'][1] + 50
                measurements['chest_left'] = (left_x, chest_y)
                measurements['chest_right'] = (right_x, chest_y)
                measurements['chest_width'] = abs(right_x - left_x)

            # Hem
            if self._check_landmark(landmarks, 15) and self._check_landmark(landmarks, 19):
                measurements['hem_left'] = landmarks[15]
                measurements['hem_right'] = landmarks[19]
                measurements['hem_width'] = self._calculate_distance(landmarks[15], landmarks[19])

            # Collar
            if self._check_landmark(landmarks, 2):
                measurements['collar_center'] = landmarks[2]

            # Cuffs (for long sleeves)
            if self._check_landmark(landmarks, 35) and self._check_landmark(landmarks, 43):
                measurements['cuff_left'] = landmarks[35]
                measurements['cuff_right'] = landmarks[43]
                measurements['sleeve_span'] = self._calculate_distance(landmarks[35], landmarks[43])

        elif garment_type == 'bottom':
            # Extract bottom measurements
            if self._check_landmark(landmarks, 168) and self._check_landmark(landmarks, 170):
                measurements['waist_left'] = landmarks[168]
                measurements['waist_right'] = landmarks[170]
                measurements['waist_width'] = self._calculate_distance(landmarks[168], landmarks[170])

            if self._check_landmark(landmarks, 176) and self._check_landmark(landmarks, 180):
                measurements['hem_left'] = landmarks[176]
                measurements['hem_right'] = landmarks[180]
                measurements['hem_width'] = self._calculate_distance(landmarks[176], landmarks[180])

        return measurements

    def _check_landmark(self, landmarks: List, idx: int) -> bool:
        """Check if a landmark exists and is valid."""
        return idx < len(landmarks) and landmarks[idx] is not None

    def _calculate_distance(self, p1: Tuple, p2: Tuple) -> float:
        """Calculate Euclidean distance between two points."""
        return np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

    def visualize_measurements(self, image_path: str, detection_result: Dict,
                              measurements: Dict) -> np.ndarray:
        """Visualize detected landmarks and measurements on the image."""
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        vis = image.copy()

        # Color scheme
        colors = {
            'shoulder': (0, 0, 255),      # Red
            'armpit': (255, 0, 255),      # Magenta
            'chest': (0, 255, 255),       # Cyan
            'collar': (255, 255, 0),      # Yellow
            'hem': (255, 100, 0),         # Orange
            'cuff': (0, 255, 0),          # Green
            'waist': (128, 0, 255)        # Purple
        }

        # Draw all detected landmarks as small dots
        landmarks = detection_result['landmarks']
        for i, landmark in enumerate(landmarks):
            if landmark is not None:
                cv2.circle(vis, landmark, 3, (200, 200, 200), -1)

        # Draw key measurement points
        for name, point in measurements.items():
            if isinstance(point, tuple) and len(point) == 2:
                # Determine color
                color = (255, 255, 255)
                for key in colors:
                    if key in name.lower():
                        color = colors[key]
                        break

                # Draw point
                cv2.circle(vis, point, 10, color, -1)
                cv2.circle(vis, point, 12, (0, 0, 0), 2)

                # Add label
                label = name.replace('_', ' ').title()
                cv2.putText(vis, label, (point[0] + 15, point[1] + 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
                cv2.putText(vis, label, (point[0] + 15, point[1] + 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)

        # Draw measurement lines
        measurement_lines = [
            ('shoulder_left', 'shoulder_right', 'Shoulder'),
            ('armpit_left', 'armpit_right', 'Armpit'),
            ('chest_left', 'chest_right', 'Chest'),
            ('hem_left', 'hem_right', 'Hem'),
            ('cuff_left', 'cuff_right', 'Sleeve Span'),
            ('waist_left', 'waist_right', 'Waist')
        ]

        for left_key, right_key, label in measurement_lines:
            if left_key in measurements and right_key in measurements:
                left_point = measurements[left_key]
                right_point = measurements[right_key]

                # Draw line
                cv2.line(vis, left_point, right_point, (0, 255, 0), 2)

                # Add measurement text
                mid_x = (left_point[0] + right_point[0]) // 2
                mid_y = (left_point[1] + right_point[1]) // 2

                width_key = f"{label.lower()}_width"
                if width_key.replace(' ', '_') in measurements:
                    value = measurements[width_key.replace(' ', '_')]
                    text = f"{label}: {value:.0f}px"
                else:
                    dist = self._calculate_distance(left_point, right_point)
                    text = f"{label}: {dist:.0f}px"

                cv2.putText(vis, text, (mid_x - 60, mid_y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
                cv2.putText(vis, text, (mid_x - 60, mid_y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 1)

        # Add summary
        garment_type = detection_result['garment_type']
        num_detected = detection_result['num_detected']
        cv2.putText(vis, f"Garment Type: {garment_type} | Landmarks: {num_detected}",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        return vis


def main():
    """Test the MMPose HRNet detector."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('image_path', help='Path to garment image')
    parser.add_argument('--model', default='models/pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth',
                       help='Path to model checkpoint')
    parser.add_argument('--output-dir', default='mmpose_results', help='Output directory')
    parser.add_argument('--conf-threshold', type=float, default=0.3, help='Confidence threshold')
    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize detector
    print("Initializing MMPose HRNet detector...")
    detector = MMPoseHRNetDetector(model_path=args.model)

    # Detect landmarks
    print(f"Processing {args.image_path}...")
    detection_result = detector.detect_landmarks(args.image_path, args.conf_threshold)

    # Extract key measurements
    measurements = detector.extract_key_measurements(detection_result)

    # Visualize results
    vis_image = detector.visualize_measurements(args.image_path, detection_result, measurements)

    # Save visualization
    image_name = Path(args.image_path).stem
    output_path = output_dir / f"{image_name}_mmpose_results.jpg"
    cv2.imwrite(str(output_path), vis_image)
    print(f"Saved visualization to {output_path}")

    # Save JSON results
    json_path = output_dir / f"{image_name}_measurements.json"
    json_data = {
        'garment_type': detection_result['garment_type'],
        'num_landmarks': detection_result['num_detected'],
        'image_size': detection_result['image_size'],
        'measurements': {k: v if not isinstance(v, tuple) else list(v)
                        for k, v in measurements.items()}
    }

    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    print(f"Saved measurements to {json_path}")

    # Print summary
    print(f"\nDetection Summary:")
    print(f"  Garment Type: {detection_result['garment_type']}")
    print(f"  Landmarks Detected: {detection_result['num_detected']}/294")
    print(f"\nKey Measurements:")
    for name, value in measurements.items():
        if not name.endswith('_width') and not name.endswith('_span'):
            print(f"  {name}: {value}")
    print(f"\nDistances:")
    for name, value in measurements.items():
        if name.endswith('_width') or name.endswith('_span'):
            print(f"  {name}: {value:.1f} pixels")


if __name__ == '__main__':
    main()