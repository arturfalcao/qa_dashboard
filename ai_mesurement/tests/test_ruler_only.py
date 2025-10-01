"""Quick test of ruler detection only"""

import cv2
from ruler_detection_smart import SmartRulerDetector

image = cv2.imread('../test_images_mesurements/anti.jpg')
print(f"Image loaded: {image.shape}")

detector = SmartRulerDetector(known_length_cm=31.0, debug=True)
ruler_info = detector.detect_ruler(image)

print(f"\nRuler Info:")
print(f"  Method: {ruler_info['method']}")
print(f"  Length: {ruler_info['length_pixels']:.0f} pixels")
print(f"  Scale: {ruler_info['pixels_per_cm']:.2f} px/cm")
print(f"  Confidence: {ruler_info.get('confidence', 0):.2f}")
