#!/usr/bin/env python3
"""
Train a simple hole detector with minimal data
Using few-shot learning approach
"""

import cv2
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
import pickle
from pathlib import Path
from typing import List, Tuple, Dict


class SimpleHoleDetector:
    """
    Train a simple detector with just a few examples
    No need for thousands of images!
    """

    def __init__(self):
        """Initialize detector"""
        self.classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        self.is_trained = False

    def extract_features(self, image_patch: np.ndarray) -> np.ndarray:
        """
        Extract simple but effective features from image patch

        Features:
        - Mean intensity
        - Standard deviation
        - Min/max intensity
        - Gradient magnitude
        - Local Binary Pattern features
        - Color histogram features
        """
        features = []

        # Convert to grayscale if needed
        if len(image_patch.shape) == 3:
            gray = cv2.cvtColor(image_patch, cv2.COLOR_BGR2GRAY)
        else:
            gray = image_patch

        # Resize to standard size
        gray = cv2.resize(gray, (32, 32))

        # 1. Statistical features
        features.append(np.mean(gray))
        features.append(np.std(gray))
        features.append(np.min(gray))
        features.append(np.max(gray))
        features.append(np.median(gray))

        # 2. Gradient features (edges)
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_mag = np.sqrt(sobelx**2 + sobely**2)
        features.append(np.mean(gradient_mag))
        features.append(np.std(gradient_mag))

        # 3. Texture features (Local Binary Pattern simplified)
        center = gray[1:-1, 1:-1]
        top = gray[:-2, 1:-1] > center
        bottom = gray[2:, 1:-1] > center
        left = gray[1:-1, :-2] > center
        right = gray[1:-1, 2:] > center

        lbp_features = [
            np.mean(top),
            np.mean(bottom),
            np.mean(left),
            np.mean(right)
        ]
        features.extend(lbp_features)

        # 4. Histogram features
        hist = cv2.calcHist([gray], [0], None, [16], [0, 256])
        hist = hist.flatten() / hist.sum()  # Normalize
        features.extend(hist.tolist())

        return np.array(features)

    def create_training_data_from_image(self, image_path: str, hole_coords: List[Tuple[int, int]]):
        """
        Create training data from a single image with marked hole locations

        Args:
            image_path: Path to image
            hole_coords: List of (x, y) coordinates of hole centers
        """
        image = cv2.imread(image_path)
        if image is None:
            print(f"Cannot load {image_path}")
            return None, None

        X_train = []
        y_train = []

        # Extract positive samples (holes)
        for x, y in hole_coords:
            # Extract patch around hole
            patch_size = 50
            x1 = max(0, x - patch_size//2)
            y1 = max(0, y - patch_size//2)
            x2 = min(image.shape[1], x + patch_size//2)
            y2 = min(image.shape[0], y + patch_size//2)

            patch = image[y1:y2, x1:x2]
            if patch.size > 0:
                features = self.extract_features(patch)
                X_train.append(features)
                y_train.append(1)  # 1 = hole

        # Extract negative samples (non-holes)
        # Random patches from the image
        num_negatives = len(hole_coords) * 3  # 3x more negatives
        h, w = image.shape[:2]

        for _ in range(num_negatives):
            # Random location
            x = np.random.randint(patch_size, w - patch_size)
            y = np.random.randint(patch_size, h - patch_size)

            # Check it's not too close to a hole
            too_close = False
            for hx, hy in hole_coords:
                if abs(x - hx) < patch_size and abs(y - hy) < patch_size:
                    too_close = True
                    break

            if not too_close:
                patch = image[y-patch_size//2:y+patch_size//2,
                             x-patch_size//2:x+patch_size//2]
                if patch.size > 0:
                    features = self.extract_features(patch)
                    X_train.append(features)
                    y_train.append(0)  # 0 = not hole

        return np.array(X_train), np.array(y_train)

    def train_with_examples(self):
        """
        Train with the examples we have
        Using prova.png as a positive example
        """
        print("\n🎓 TRAINING HOLE DETECTOR")
        print("="*60)

        # We know prova.png contains a hole
        # Let's manually mark where it is
        prova = cv2.imread("../test_images_mesurements/prova.png")
        if prova is not None:
            # The hole is approximately in the center of prova.png
            h, w = prova.shape[:2]
            hole_center = (w//2, h//2)

            print("📸 Using prova.png as training example...")

            # Create training data
            X_positive = []
            y_positive = []

            # Extract the hole region
            patch = prova
            features = self.extract_features(patch)
            X_positive.append(features)
            y_positive.append(1)

            # Create some artificial variations (data augmentation)
            for _ in range(10):
                # Random crop around center
                offset = 10
                x_off = np.random.randint(-offset, offset)
                y_off = np.random.randint(-offset, offset)

                x1 = max(0, x_off)
                y1 = max(0, y_off)
                x2 = min(w, w + x_off)
                y2 = min(h, h + y_off)

                augmented = prova[y1:y2, x1:x2]
                if augmented.size > 0:
                    features = self.extract_features(augmented)
                    X_positive.append(features)
                    y_positive.append(1)

            # Create negative examples (non-holes)
            # Use random patches from ant.jpg
            ant = cv2.imread("../test_images_mesurements/ant.jpg")
            if ant is not None:
                X_negative = []
                y_negative = []

                # Extract random patches as negative examples
                for _ in range(30):
                    x = np.random.randint(50, ant.shape[1] - 100)
                    y = np.random.randint(50, ant.shape[0] - 100)

                    patch = ant[y:y+50, x:x+50]
                    features = self.extract_features(patch)
                    X_negative.append(features)
                    y_negative.append(0)

                # Combine positive and negative
                X_train = np.vstack([X_positive, X_negative])
                y_train = np.hstack([y_positive, y_negative])

                # Train the classifier
                print(f"   Training with {len(X_positive)} positive and {len(X_negative)} negative examples...")
                self.classifier.fit(X_train, y_train)
                self.is_trained = True

                # Training accuracy
                train_score = self.classifier.score(X_train, y_train)
                print(f"   Training accuracy: {train_score:.2%}")

                # Save the model
                with open('hole_detector_model.pkl', 'wb') as f:
                    pickle.dump(self.classifier, f)
                print("   Model saved to hole_detector_model.pkl")

                return True

        return False

    def detect_holes(self, image_path: str, threshold: float = 0.5):
        """
        Detect holes in a new image

        Args:
            image_path: Path to image
            threshold: Probability threshold (0.5 = 50%)
        """
        if not self.is_trained:
            print("⚠️ Detector not trained yet!")
            return []

        image = cv2.imread(image_path)
        if image is None:
            return []

        print(f"\n🔍 Detecting holes in {Path(image_path).name}...")

        holes = []
        h, w = image.shape[:2]

        # Sliding window approach
        window_size = 50
        stride = 25  # Overlap for better detection

        for y in range(0, h - window_size, stride):
            for x in range(0, w - window_size, stride):
                patch = image[y:y+window_size, x:x+window_size]

                # Extract features
                features = self.extract_features(patch).reshape(1, -1)

                # Predict
                prob = self.classifier.predict_proba(features)[0, 1]

                if prob > threshold:
                    holes.append({
                        'position': (x + window_size//2, y + window_size//2),
                        'probability': prob,
                        'bbox': (x, y, window_size, window_size)
                    })

        # Non-maximum suppression to remove duplicates
        holes = self._nms(holes)

        return holes

    def _nms(self, detections, overlap_thresh=0.3):
        """Simple non-maximum suppression"""
        if len(detections) == 0:
            return []

        # Sort by probability
        detections = sorted(detections, key=lambda x: x['probability'], reverse=True)

        keep = []
        for i, det in enumerate(detections):
            should_keep = True
            x1, y1, w1, h1 = det['bbox']

            for kept in keep:
                x2, y2, w2, h2 = kept['bbox']

                # Calculate IoU
                x_overlap = max(0, min(x1+w1, x2+w2) - max(x1, x2))
                y_overlap = max(0, min(y1+h1, y2+h2) - max(y1, y2))
                intersection = x_overlap * y_overlap

                area1 = w1 * h1
                area2 = w2 * h2
                union = area1 + area2 - intersection

                if union > 0:
                    iou = intersection / union
                    if iou > overlap_thresh:
                        should_keep = False
                        break

            if should_keep:
                keep.append(det)

        return keep


def main():
    """Train and test the detector"""

    detector = SimpleHoleDetector()

    # Train with available examples
    if detector.train_with_examples():
        print("\n✅ Detector trained successfully!")

        # Test on ant.jpg
        holes = detector.detect_holes("../test_images_mesurements/ant.jpg", threshold=0.7)

        if holes:
            print(f"\n🎯 Found {len(holes)} potential holes:")
            for i, hole in enumerate(holes[:5]):
                print(f"   {i+1}. Position: {hole['position']}, "
                      f"Confidence: {hole['probability']:.1%}")

            # Visualize
            image = cv2.imread("../test_images_mesurements/ant.jpg")
            for hole in holes:
                x, y, w, h = hole['bbox']
                conf = hole['probability']
                color = (0, 255, 0) if conf > 0.8 else (0, 255, 255)
                cv2.rectangle(image, (x, y), (x+w, y+h), color, 2)
                cv2.putText(image, f"{conf:.0%}", (x, y-5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            cv2.imwrite("trained_detection.png", image)
            print("\n📸 Results saved to trained_detection.png")
        else:
            print("\n❌ No holes detected with current threshold")

    else:
        print("\n❌ Training failed")


if __name__ == "__main__":
    main()