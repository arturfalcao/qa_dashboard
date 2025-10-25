#!/usr/bin/env python3
"""
Analyze the landmark schema to understand the excessive landmark count
"""

landmarks = [
    125, 209, 1, 53, 198, 2, 105, 220, 2, 155, 240, 2, 184, 232, 2, 163, 213, 1,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    13, 418, 2, 21, 452, 2,
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    344, 460, 2, 303, 386, 1, 327, 414, 1, 358, 450, 2, 328, 382, 2, 294, 304, 2,
    352, 288, 2, 389, 357, 2, 394, 442, 2, 327, 344, 1, 270, 264, 2
]

print(f"Total elements in landmarks array: {len(landmarks)}")
print(f"Number of landmark positions (total/3): {len(landmarks)//3}")

# Parse landmarks
parsed_landmarks = []
for i in range(0, len(landmarks), 3):
    x, y, v = landmarks[i:i+3]
    parsed_landmarks.append((i//3, x, y, v))

# Count visible vs invisible
visible = [lm for lm in parsed_landmarks if lm[3] > 0]
invisible = [lm for lm in parsed_landmarks if lm[3] == 0]

print(f"\nVisible landmarks (v > 0): {len(visible)}")
print(f"Invisible/unused landmarks (v = 0): {len(invisible)}")
print(f"Ratio: {len(invisible)}/{len(parsed_landmarks)} = {len(invisible)/len(parsed_landmarks)*100:.1f}% unused")

print("\n" + "="*60)
print("VISIBLE LANDMARKS:")
print("="*60)
for idx, x, y, v in visible:
    print(f"  Index {idx:2d}: ({x:3d}, {y:3d}) visibility={v}")

print("\n" + "="*60)
print("INVISIBLE/UNUSED LANDMARK INDICES:")
print("="*60)
unused_ranges = []
start = None
for idx, x, y, v in parsed_landmarks:
    if v == 0:
        if start is None:
            start = idx
    else:
        if start is not None:
            unused_ranges.append((start, idx-1))
            start = None
if start is not None:
    unused_ranges.append((start, len(parsed_landmarks)-1))

for start, end in unused_ranges:
    if start == end:
        print(f"  Index {start}")
    else:
        print(f"  Indices {start}-{end} ({end-start+1} positions)")

print("\n" + "="*60)
print("COMPARISON WITH DEEPFASHION2 STANDARD:")
print("="*60)
print("DeepFashion2 'long sleeve top' typically has 25 keypoints")
print(f"This annotation has {len(parsed_landmarks)} keypoint slots")
print(f"That's {len(parsed_landmarks) - 25} extra unused slots!")
print("\nThis is likely a schema mismatch or annotation tool configuration issue.")
