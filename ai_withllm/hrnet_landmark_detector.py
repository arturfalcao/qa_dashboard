#!/usr/bin/env python3
"""
HRNet-based Fashion Landmark Detection Module

This module implements fashion landmark detection using HRNet (High-Resolution Network)
trained on DeepFashion2 dataset. It detects key points on garment images for accurate
measurement and analysis.

Based on: https://github.com/svip-lab/HRNet-for-Fashion-Landmark-Estimation.PyTorch
"""

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BasicBlock(nn.Module):
    """Basic residual block for HRNet"""
    expansion = 1

    def __init__(self, inplanes, planes, stride=1):
        super(BasicBlock, self).__init__()
        self.conv1 = nn.Conv2d(inplanes, planes, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes, momentum=0.1)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(planes, momentum=0.1)

        self.downsample = None
        if stride != 1 or inplanes != planes * self.expansion:
            self.downsample = nn.Sequential(
                nn.Conv2d(inplanes, planes * self.expansion, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(planes * self.expansion, momentum=0.1)
            )
        self.stride = stride

    def forward(self, x):
        residual = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.conv2(out)
        out = self.bn2(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual
        out = self.relu(out)

        return out


class Bottleneck(nn.Module):
    """Bottleneck block for HRNet"""
    expansion = 4

    def __init__(self, inplanes, planes, stride=1):
        super(Bottleneck, self).__init__()
        self.conv1 = nn.Conv2d(inplanes, planes, kernel_size=1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes, momentum=0.1)
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(planes, momentum=0.1)
        self.conv3 = nn.Conv2d(planes, planes * self.expansion, kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm2d(planes * self.expansion, momentum=0.1)
        self.relu = nn.ReLU(inplace=True)

        self.downsample = None
        if stride != 1 or inplanes != planes * self.expansion:
            self.downsample = nn.Sequential(
                nn.Conv2d(inplanes, planes * self.expansion, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(planes * self.expansion, momentum=0.1),
            )
        self.stride = stride

    def forward(self, x):
        residual = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)
        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)
        out = self.conv3(out)
        out = self.bn3(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual
        out = self.relu(out)

        return out


class PoseHighResolutionNet(nn.Module):
    """HRNet model for pose estimation"""

    def __init__(self, num_joints=294, **kwargs):
        super(PoseHighResolutionNet, self).__init__()

        # Stem
        self.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=2, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(64, momentum=0.1)
        self.conv2 = nn.Conv2d(64, 64, kernel_size=3, stride=2, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(64, momentum=0.1)
        self.relu = nn.ReLU(inplace=True)

        # Stage 1
        self.layer1 = self._make_layer(Bottleneck, 64, 64, 4)

        # Configuration for HRNet-W48
        self.stage2_cfg = {'num_modules': 1, 'num_branches': 2, 'num_blocks': [4, 4], 'num_channels': [48, 96]}
        self.transition1 = self._make_transition_layer([256], self.stage2_cfg['num_channels'])
        self.stage2, pre_stage_channels = self._make_stage(self.stage2_cfg)

        self.stage3_cfg = {'num_modules': 4, 'num_branches': 3, 'num_blocks': [4, 4, 4], 'num_channels': [48, 96, 192]}
        self.transition2 = self._make_transition_layer(pre_stage_channels, self.stage3_cfg['num_channels'])
        self.stage3, pre_stage_channels = self._make_stage(self.stage3_cfg)

        self.stage4_cfg = {'num_modules': 3, 'num_branches': 4, 'num_blocks': [4, 4, 4, 4], 'num_channels': [48, 96, 192, 384]}
        self.transition3 = self._make_transition_layer(pre_stage_channels, self.stage4_cfg['num_channels'])
        self.stage4, pre_stage_channels = self._make_stage(self.stage4_cfg)

        # Final layer
        self.final_layer = nn.Conv2d(pre_stage_channels[0], num_joints, kernel_size=1, stride=1, padding=0)

    def _make_layer(self, block, inplanes, planes, blocks, stride=1):
        layers = []
        layers.append(block(inplanes, planes, stride))
        inplanes = planes * block.expansion
        for i in range(1, blocks):
            layers.append(block(inplanes, planes))
        return nn.Sequential(*layers)

    def _make_transition_layer(self, num_channels_pre_layer, num_channels_cur_layer):
        num_branches_cur = len(num_channels_cur_layer)
        num_branches_pre = len(num_channels_pre_layer)

        transition_layers = []
        for i in range(num_branches_cur):
            if i < num_branches_pre:
                if num_channels_cur_layer[i] != num_channels_pre_layer[i]:
                    transition_layers.append(nn.Sequential(
                        nn.Conv2d(num_channels_pre_layer[i], num_channels_cur_layer[i], 3, 1, 1, bias=False),
                        nn.BatchNorm2d(num_channels_cur_layer[i]),
                        nn.ReLU(inplace=True)))
                else:
                    transition_layers.append(None)
            else:
                conv3x3s = []
                for j in range(i+1-num_branches_pre):
                    inchannels = num_channels_pre_layer[-1]
                    outchannels = num_channels_cur_layer[i] if j == i-num_branches_pre else inchannels
                    conv3x3s.append(nn.Sequential(
                        nn.Conv2d(inchannels, outchannels, 3, 2, 1, bias=False),
                        nn.BatchNorm2d(outchannels),
                        nn.ReLU(inplace=True)))
                transition_layers.append(nn.Sequential(*conv3x3s))

        return nn.ModuleList(transition_layers)

    def _make_stage(self, layer_config):
        num_modules = layer_config['num_modules']
        num_branches = layer_config['num_branches']
        num_blocks = layer_config['num_blocks']
        num_channels = layer_config['num_channels']

        modules = []
        for i in range(num_modules):
            # Multi-scale fusion
            if i == 0:
                modules.append(HighResolutionModule(num_branches, BasicBlock, num_blocks, num_channels))
            else:
                modules.append(HighResolutionModule(num_branches, BasicBlock, num_blocks, num_channels))

        return nn.Sequential(*modules), num_channels

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.conv2(x)
        x = self.bn2(x)
        x = self.relu(x)

        x = self.layer1(x)

        x_list = []
        for i in range(self.stage2_cfg['num_branches']):
            if self.transition1[i] is not None:
                x_list.append(self.transition1[i](x))
            else:
                x_list.append(x)
        y_list = self.stage2(x_list)

        x_list = []
        for i in range(self.stage3_cfg['num_branches']):
            if self.transition2[i] is not None:
                x_list.append(self.transition2[i](y_list[-1] if i >= len(y_list) else y_list[i]))
            else:
                x_list.append(y_list[i])
        y_list = self.stage3(x_list)

        x_list = []
        for i in range(self.stage4_cfg['num_branches']):
            if self.transition3[i] is not None:
                x_list.append(self.transition3[i](y_list[-1] if i >= len(y_list) else y_list[i]))
            else:
                x_list.append(y_list[i])
        y_list = self.stage4(x_list)

        x = self.final_layer(y_list[0])

        return x


class HighResolutionModule(nn.Module):
    """High Resolution Module for HRNet"""

    def __init__(self, num_branches, block, num_blocks, num_channels):
        super(HighResolutionModule, self).__init__()

        self.num_branches = num_branches
        self.num_channels = num_channels
        self.branches = self._make_branches(num_branches, block, num_blocks, num_channels)
        self.fuse_layers = self._make_fuse_layers()
        self.relu = nn.ReLU(inplace=True)

    def _make_branches(self, num_branches, block, num_blocks, num_channels):
        branches = []
        for i in range(num_branches):
            branches.append(self._make_one_branch(i, block, num_blocks, num_channels))
        return nn.ModuleList(branches)

    def _make_one_branch(self, branch_index, block, num_blocks, num_channels):
        layers = []
        layers.append(block(num_channels[branch_index], num_channels[branch_index]))
        for i in range(1, num_blocks[branch_index]):
            layers.append(block(num_channels[branch_index], num_channels[branch_index]))
        return nn.Sequential(*layers)

    def _make_fuse_layers(self):
        if self.num_branches == 1:
            return None

        num_branches = self.num_branches
        fuse_layers = []
        for i in range(num_branches):
            fuse_layer = []
            for j in range(num_branches):
                if j > i:
                    fuse_layer.append(nn.Sequential(
                        nn.Conv2d(self.num_channels[j], self.num_channels[i], 1, 1, 0, bias=False),
                        nn.BatchNorm2d(self.num_channels[i]),
                        nn.Upsample(scale_factor=2**(j-i), mode='nearest')))
                elif j == i:
                    fuse_layer.append(None)
                else:
                    conv3x3s = []
                    for k in range(i-j):
                        if k == i - j - 1:
                            conv3x3s.append(nn.Sequential(
                                nn.Conv2d(self.num_channels[j], self.num_channels[i], 3, 2, 1, bias=False),
                                nn.BatchNorm2d(self.num_channels[i])))
                        else:
                            conv3x3s.append(nn.Sequential(
                                nn.Conv2d(self.num_channels[j], self.num_channels[j], 3, 2, 1, bias=False),
                                nn.BatchNorm2d(self.num_channels[j]),
                                nn.ReLU(inplace=True)))
                    fuse_layer.append(nn.Sequential(*conv3x3s))
            fuse_layers.append(nn.ModuleList(fuse_layer))

        return nn.ModuleList(fuse_layers)

    def forward(self, x):
        for i in range(self.num_branches):
            x[i] = self.branches[i](x[i])

        if self.fuse_layers is not None:
            x_fuse = []
            for i in range(len(self.fuse_layers)):
                y = x[0] if i == 0 else self.fuse_layers[i][0](x[0])
                for j in range(1, self.num_branches):
                    if i == j:
                        y = y + x[j]
                    else:
                        y = y + self.fuse_layers[i][j](x[j])
                x_fuse.append(self.relu(y))
            return x_fuse
        else:
            return x


class FashionLandmarkDetector:
    """
    High-level interface for fashion landmark detection using HRNet
    """

    # DeepFashion2 landmark definitions (294 points total)
    LANDMARK_CATEGORIES = {
        'short_sleeved_shirt': list(range(0, 25)),
        'long_sleeved_shirt': list(range(25, 58)),
        'short_sleeved_outwear': list(range(58, 89)),
        'long_sleeved_outwear': list(range(89, 128)),
        'vest': list(range(128, 143)),
        'sling': list(range(143, 158)),
        'shorts': list(range(158, 168)),
        'trousers': list(range(168, 182)),
        'skirt': list(range(182, 190)),
        'short_sleeved_dress': list(range(190, 219)),
        'long_sleeved_dress': list(range(219, 256)),
        'vest_dress': list(range(256, 275)),
        'sling_dress': list(range(275, 294))
    }

    # Detailed landmark labels for measurement purposes
    LANDMARK_LABELS = {
        'short_sleeved_shirt': {
            0: 'left_collar_tip', 1: 'left_collar_center', 2: 'center_collar',
            3: 'right_collar_center', 4: 'right_collar_tip',
            5: 'left_shoulder', 6: 'left_armpit',
            7: 'left_sleeve_top_edge', 8: 'left_sleeve_cuff_outer', 9: 'left_sleeve_cuff_inner',
            10: 'right_shoulder', 11: 'right_armpit',
            12: 'right_sleeve_top_edge', 13: 'right_sleeve_cuff_outer', 14: 'right_sleeve_cuff_inner',
            15: 'left_hem_corner', 16: 'left_hem_side', 17: 'center_hem',
            18: 'right_hem_side', 19: 'right_hem_corner',
            20: 'left_chest', 21: 'right_chest', 22: 'center_chest',
            23: 'waist_left', 24: 'waist_right'
        },
        'long_sleeved_shirt': {
            25: 'left_collar_tip', 26: 'left_collar_center', 27: 'center_collar',
            28: 'right_collar_center', 29: 'right_collar_tip',
            30: 'left_shoulder', 31: 'left_armpit',
            32: 'left_sleeve_shoulder_seam', 33: 'left_elbow_outer', 34: 'left_elbow_inner',
            35: 'left_sleeve_cuff_outer', 36: 'left_sleeve_cuff_center', 37: 'left_sleeve_cuff_inner',
            38: 'right_shoulder', 39: 'right_armpit',
            40: 'right_sleeve_shoulder_seam', 41: 'right_elbow_outer', 42: 'right_elbow_inner',
            43: 'right_sleeve_cuff_outer', 44: 'right_sleeve_cuff_center', 45: 'right_sleeve_cuff_inner',
            46: 'left_hem_corner', 47: 'left_hem_quarter', 48: 'center_hem',
            49: 'right_hem_quarter', 50: 'right_hem_corner',
            51: 'left_chest', 52: 'center_chest', 53: 'right_chest',
            54: 'waist_left', 55: 'waist_center', 56: 'waist_right',
            57: 'placket_top'
        },
        'vest': {
            128: 'left_collar_tip', 129: 'left_neckline', 130: 'center_neckline',
            131: 'right_neckline', 132: 'right_collar_tip',
            133: 'left_shoulder', 134: 'left_armhole_top', 135: 'left_armhole_bottom',
            136: 'right_shoulder', 137: 'right_armhole_top', 138: 'right_armhole_bottom',
            139: 'left_hem', 140: 'center_hem', 141: 'right_hem',
            142: 'center_chest'
        },
        'trousers': {
            168: 'waistband_left', 169: 'waistband_center', 170: 'waistband_right',
            171: 'left_hip', 172: 'crotch', 173: 'right_hip',
            174: 'left_thigh', 175: 'left_knee', 176: 'left_hem_outer', 177: 'left_hem_inner',
            178: 'right_thigh', 179: 'right_knee', 180: 'right_hem_outer', 181: 'right_hem_inner'
        },
        'shorts': {
            158: 'waistband_left', 159: 'waistband_center', 160: 'waistband_right',
            161: 'left_hip', 162: 'crotch', 163: 'right_hip',
            164: 'left_hem_outer', 165: 'left_hem_inner',
            166: 'right_hem_outer', 167: 'right_hem_inner'
        },
        'skirt': {
            182: 'waistband_left', 183: 'waistband_center', 184: 'waistband_right',
            185: 'left_hip', 186: 'right_hip',
            187: 'hem_left', 188: 'hem_center', 189: 'hem_right'
        }
    }

    # Define measurement connections (what landmarks to connect for measurements)
    MEASUREMENTS = {
        'collar_width': ['left_collar_tip', 'right_collar_tip'],
        'shoulder_width': ['left_shoulder', 'right_shoulder'],
        'chest_width': ['left_chest', 'right_chest'],
        'waist_width': ['waist_left', 'waist_right'],
        'sleeve_length': ['left_shoulder', 'left_sleeve_cuff_center'],
        'shirt_length': ['center_collar', 'center_hem'],
        'armpit_to_armpit': ['left_armpit', 'right_armpit'],
        'hem_width': ['left_hem_corner', 'right_hem_corner'],
        'inseam': ['crotch', 'left_hem_inner'],
        'outseam': ['waistband_left', 'left_hem_outer']
    }

    def __init__(self, model_path: str, device: str = 'cuda' if torch.cuda.is_available() else 'cpu'):
        """
        Initialize the landmark detector

        Args:
            model_path: Path to the pretrained HRNet model
            device: Device to run the model on ('cuda' or 'cpu')
        """
        self.device = torch.device(device)
        self.model = self._load_model(model_path)
        self.model.eval()

        # Standard input size for HRNet
        self.input_width = 384
        self.input_height = 288

        # Image normalization parameters
        self.mean = [0.485, 0.456, 0.406]
        self.std = [0.229, 0.224, 0.225]

        logger.info(f"Landmark detector initialized on {device}")

    def _load_model(self, model_path: str) -> nn.Module:
        """Load the pretrained HRNet model"""
        model = PoseHighResolutionNet(num_joints=294)

        if Path(model_path).exists():
            checkpoint = torch.load(model_path, map_location=self.device)

            # Handle different checkpoint formats
            if 'state_dict' in checkpoint:
                state_dict = checkpoint['state_dict']
            else:
                state_dict = checkpoint

            # Remove 'module.' prefix if present (from DataParallel)
            new_state_dict = {}
            for k, v in state_dict.items():
                if k.startswith('module.'):
                    new_state_dict[k[7:]] = v
                else:
                    new_state_dict[k] = v

            model.load_state_dict(new_state_dict, strict=False)
            logger.info(f"Model loaded from {model_path}")
        else:
            logger.warning(f"Model file not found at {model_path}. Using random initialization.")

        model.to(self.device)
        return model

    def preprocess_image(self, image: np.ndarray) -> Tuple[torch.Tensor, Tuple[int, int], Tuple[float, float]]:
        """
        Preprocess image for HRNet

        Args:
            image: Input image (H, W, 3) in BGR format

        Returns:
            Preprocessed tensor, original size, and scale factors
        """
        orig_height, orig_width = image.shape[:2]

        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Resize to model input size
        resized = cv2.resize(image_rgb, (self.input_width, self.input_height))

        # Normalize
        normalized = resized.astype(np.float32) / 255.0
        for i in range(3):
            normalized[:, :, i] = (normalized[:, :, i] - self.mean[i]) / self.std[i]

        # Convert to tensor (C, H, W)
        tensor = torch.from_numpy(normalized.transpose(2, 0, 1)).float()
        tensor = tensor.unsqueeze(0).to(self.device)

        # Calculate scale factors for coordinate transformation
        scale_x = orig_width / self.input_width
        scale_y = orig_height / self.input_height

        return tensor, (orig_width, orig_height), (scale_x, scale_y)

    def detect_landmarks(self, image: np.ndarray, confidence_threshold: float = 0.3) -> Dict:
        """
        Detect fashion landmarks in an image

        Args:
            image: Input image (H, W, 3) in BGR format
            confidence_threshold: Minimum confidence for landmark detection

        Returns:
            Dictionary containing detected landmarks and their confidences
        """
        # Preprocess image
        tensor, orig_size, scale_factors = self.preprocess_image(image)

        # Run inference
        with torch.no_grad():
            heatmaps = self.model(tensor)

        # Process heatmaps
        heatmaps = heatmaps.squeeze(0).cpu().numpy()
        num_joints = heatmaps.shape[0]

        landmarks = []
        confidences = []

        for i in range(num_joints):
            heatmap = heatmaps[i]

            # Find peak in heatmap
            max_val = np.max(heatmap)
            if max_val > confidence_threshold:
                # Get coordinates of maximum
                max_loc = np.unravel_index(np.argmax(heatmap), heatmap.shape)
                y, x = max_loc

                # Convert to original image coordinates
                x_orig = x * 4 * scale_factors[0]  # 4x because heatmap is 1/4 of input size
                y_orig = y * 4 * scale_factors[1]

                landmarks.append((int(x_orig), int(y_orig)))
                confidences.append(float(max_val))
            else:
                landmarks.append(None)
                confidences.append(0.0)

        # Determine garment category based on visible landmarks
        detected_category = self._infer_garment_category(confidences)

        return {
            'landmarks': landmarks,
            'confidences': confidences,
            'category': detected_category,
            'num_detected': sum(1 for l in landmarks if l is not None)
        }

    def _infer_garment_category(self, confidences: List[float]) -> str:
        """Infer garment category based on detected landmarks"""
        best_category = None
        best_score = 0

        for category, indices in self.LANDMARK_CATEGORIES.items():
            # Calculate average confidence for this category's landmarks
            category_confidences = [confidences[i] for i in indices if i < len(confidences)]
            if category_confidences:
                avg_confidence = np.mean([c for c in category_confidences if c > 0])
                if avg_confidence > best_score:
                    best_score = avg_confidence
                    best_category = category

        return best_category

    def get_landmark_labels(self, detection_result: Dict) -> Dict[str, Tuple[int, int]]:
        """
        Get landmark labels for detected category

        Returns:
            Dictionary mapping label names to (x, y) coordinates
        """
        category = detection_result['category']
        landmarks = detection_result['landmarks']
        labeled_landmarks = {}

        if category and category in self.LANDMARK_LABELS:
            labels = self.LANDMARK_LABELS[category]
            for idx, label in labels.items():
                if idx < len(landmarks) and landmarks[idx] is not None:
                    labeled_landmarks[label] = landmarks[idx]

        return labeled_landmarks

    def calculate_measurements(self, detection_result: Dict, pixels_per_cm: float = None) -> Dict[str, float]:
        """
        Calculate garment measurements from landmarks

        Args:
            detection_result: Result from detect_landmarks()
            pixels_per_cm: Calibration factor (if None, returns pixel measurements)

        Returns:
            Dictionary of measurements in cm (if calibrated) or pixels
        """
        labeled_landmarks = self.get_landmark_labels(detection_result)
        measurements = {}

        for measurement_name, landmark_names in self.MEASUREMENTS.items():
            if len(landmark_names) == 2:
                if landmark_names[0] in labeled_landmarks and landmark_names[1] in labeled_landmarks:
                    p1 = labeled_landmarks[landmark_names[0]]
                    p2 = labeled_landmarks[landmark_names[1]]
                    distance = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

                    if pixels_per_cm:
                        measurements[measurement_name] = distance / pixels_per_cm
                    else:
                        measurements[measurement_name] = distance

        return measurements

    def draw_landmarks_with_labels(self, image: np.ndarray, detection_result: Dict,
                                  show_measurements: bool = True,
                                  point_size: int = 8,
                                  font_scale: float = 0.5) -> np.ndarray:
        """
        Draw landmarks with meaningful labels for measurement

        Args:
            image: Input image
            detection_result: Result from detect_landmarks()
            show_measurements: Whether to draw measurement lines
            point_size: Size of landmark points
            font_scale: Scale of label text

        Returns:
            Image with labeled landmarks
        """
        result_image = image.copy()
        labeled_landmarks = self.get_landmark_labels(detection_result)

        # Define colors for different landmark types
        colors = {
            'collar': (255, 0, 0),      # Blue for collar
            'shoulder': (0, 255, 0),    # Green for shoulders
            'chest': (255, 255, 0),     # Cyan for chest
            'waist': (255, 0, 255),     # Magenta for waist
            'hem': (0, 255, 255),       # Yellow for hem
            'sleeve': (128, 255, 128),  # Light green for sleeves
            'armpit': (255, 128, 0),    # Orange for armpits
            'armhole': (255, 128, 128), # Light red for armholes
            'default': (128, 128, 255)  # Light blue default
        }

        # Draw measurement lines if requested
        if show_measurements:
            measurements = self.calculate_measurements(detection_result)
            for measurement_name, landmark_names in self.MEASUREMENTS.items():
                if measurement_name in measurements and len(landmark_names) == 2:
                    if landmark_names[0] in labeled_landmarks and landmark_names[1] in labeled_landmarks:
                        p1 = labeled_landmarks[landmark_names[0]]
                        p2 = labeled_landmarks[landmark_names[1]]

                        # Draw measurement line
                        cv2.line(result_image, p1, p2, (0, 200, 0), 2, cv2.LINE_AA)

                        # Add measurement label at midpoint
                        mid_x = (p1[0] + p2[0]) // 2
                        mid_y = (p1[1] + p2[1]) // 2
                        value = measurements[measurement_name]
                        label = f"{measurement_name}: {value:.1f}px"

                        # Add background for text
                        (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale * 0.8, 1)
                        cv2.rectangle(result_image, (mid_x - 5, mid_y - h - 5),
                                    (mid_x + w + 5, mid_y + 5), (255, 255, 255), -1)
                        cv2.putText(result_image, label, (mid_x, mid_y),
                                  cv2.FONT_HERSHEY_SIMPLEX, font_scale * 0.8, (0, 150, 0), 1, cv2.LINE_AA)

        # Draw landmarks with labels
        for label, coord in labeled_landmarks.items():
            # Determine color based on landmark type
            color = colors['default']
            for key in colors:
                if key in label.lower():
                    color = colors[key]
                    break

            # Draw landmark point
            cv2.circle(result_image, coord, point_size, color, -1)
            cv2.circle(result_image, coord, point_size + 2, (0, 0, 0), 2)

            # Add label text
            text_x = coord[0] + point_size + 5
            text_y = coord[1] + 3

            # Add background for text
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
            cv2.rectangle(result_image, (text_x - 2, text_y - h - 2),
                        (text_x + w + 2, text_y + 4), (255, 255, 255), -1)
            cv2.putText(result_image, label, (text_x, text_y),
                      cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), 1, cv2.LINE_AA)

        # Add summary text
        category = detection_result['category']
        num_detected = len(labeled_landmarks)
        cv2.putText(result_image, f"Garment: {category} | Landmarks: {num_detected}",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

        return result_image

    def draw_landmarks(self, image: np.ndarray, detection_result: Dict,
                      point_size: int = 5, line_thickness: int = 2) -> np.ndarray:
        """
        Draw detected landmarks on the image

        Args:
            image: Input image
            detection_result: Result from detect_landmarks()
            point_size: Size of landmark points
            line_thickness: Thickness of connecting lines

        Returns:
            Image with drawn landmarks
        """
        result_image = image.copy()
        landmarks = detection_result['landmarks']
        confidences = detection_result['confidences']
        category = detection_result['category']

        if category and category in self.LANDMARK_CATEGORIES:
            indices = self.LANDMARK_CATEGORIES[category]

            # Define connections based on garment type
            connections = self._get_garment_connections(category)

            # Draw connections
            for connection in connections:
                idx1, idx2 = connection
                if idx1 in indices and idx2 in indices:
                    actual_idx1 = indices[indices.index(idx1)] if idx1 in indices else idx1
                    actual_idx2 = indices[indices.index(idx2)] if idx2 in indices else idx2

                    if (actual_idx1 < len(landmarks) and actual_idx2 < len(landmarks) and
                        landmarks[actual_idx1] is not None and landmarks[actual_idx2] is not None):
                        cv2.line(result_image, landmarks[actual_idx1], landmarks[actual_idx2],
                                (0, 255, 0), line_thickness)

            # Draw points
            for i, landmark in enumerate(landmarks):
                if landmark is not None:
                    # Color based on confidence
                    confidence = confidences[i]
                    color = (0, int(255 * confidence), int(255 * (1 - confidence)))
                    cv2.circle(result_image, landmark, point_size, color, -1)

                    # Add index label for debugging
                    cv2.putText(result_image, str(i),
                               (landmark[0] + 5, landmark[1] - 5),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255), 1)

        # Add category text
        cv2.putText(result_image, f"Category: {category}",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(result_image, f"Detected: {detection_result['num_detected']} landmarks",
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        return result_image

    def _get_garment_connections(self, category: str) -> List[Tuple[int, int]]:
        """Get landmark connections for visualization based on garment type"""
        # Define basic connection patterns for different garment types
        # These are simplified examples - you may need to adjust based on actual landmark definitions

        connections = []

        if 'shirt' in category or 'outwear' in category:
            # Collar/neckline
            connections.extend([(0, 1), (1, 2), (2, 3), (3, 0)])
            # Shoulders to sleeves
            connections.extend([(0, 4), (3, 8)])
            # Sleeve outlines
            connections.extend([(4, 5), (5, 6), (6, 7)])
            connections.extend([(8, 9), (9, 10), (10, 11)])
            # Bottom hem
            connections.extend([(12, 13), (13, 14), (14, 15), (15, 12)])

        elif 'dress' in category:
            # Similar to shirt but extended
            connections.extend([(0, 1), (1, 2), (2, 3), (3, 0)])
            connections.extend([(0, 4), (3, 8)])
            connections.extend([(4, 5), (5, 6), (6, 7)])
            connections.extend([(8, 9), (9, 10), (10, 11)])
            # Waist and bottom
            connections.extend([(12, 13), (13, 14), (14, 15), (15, 12)])
            connections.extend([(16, 17), (17, 18), (18, 19), (19, 16)])

        elif 'trousers' in category or 'shorts' in category:
            # Waistband
            connections.extend([(0, 1), (1, 2), (2, 3), (3, 0)])
            # Legs
            connections.extend([(0, 4), (4, 5), (5, 6)])
            connections.extend([(3, 7), (7, 8), (8, 9)])
            # Bottom hems
            connections.extend([(6, 10), (9, 11)])

        elif 'skirt' in category:
            # Waistband
            connections.extend([(0, 1), (1, 2), (2, 3), (3, 0)])
            # Bottom hem
            connections.extend([(4, 5), (5, 6), (6, 7), (7, 4)])

        return connections


def main():
    """Example usage of the landmark detector"""
    import argparse

    parser = argparse.ArgumentParser(description="HRNet Fashion Landmark Detection")
    parser.add_argument("--model", default="models/pose_hrnet-w48_384x288-deepfashion2_mAP_0.7017.pth",
                       help="Path to pretrained model")
    parser.add_argument("--image", required=True, help="Input image path")
    parser.add_argument("--output", help="Output image path")
    parser.add_argument("--confidence", type=float, default=0.3,
                       help="Confidence threshold for landmark detection")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu",
                       help="Device to use (cuda/cpu)")

    args = parser.parse_args()

    # Initialize detector
    detector = FashionLandmarkDetector(args.model, args.device)

    # Load image
    image = cv2.imread(args.image)
    if image is None:
        print(f"Error: Could not load image from {args.image}")
        return

    # Detect landmarks
    print("Detecting landmarks...")
    result = detector.detect_landmarks(image, args.confidence)

    print(f"Detected category: {result['category']}")
    print(f"Number of landmarks detected: {result['num_detected']}")

    # Draw landmarks
    result_image = detector.draw_landmarks(image, result)

    # Save or display result
    if args.output:
        cv2.imwrite(args.output, result_image)
        print(f"Result saved to {args.output}")
    else:
        cv2.imshow("Landmarks", result_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()