#!/usr/bin/env python3
"""
DeepFashion2 Landmark Index Mappings for Measurements

This module defines the precise landmark index pairs for measuring
different garment types according to the DeepFashion2 dataset structure.

Each garment category has specific landmark indices that correspond to
measurement points (collar, shoulders, chest, hem, cuffs, etc.)
"""

# DeepFashion2 Landmark Mappings
# Format: measurement_name: [start_landmark_idx, end_landmark_idx]

LANDMARK_MAPPINGS = {
    'short_sleeved_shirt': {
        'collar_width': [2, 6],
        'shoulder_width': [8, 21],
        'chest_width': [13, 19],
        'hem_width': [16, 18],
        'body_length': [3, 17],
        'left_sleeve_length': [8, 11],
        'right_sleeve_length': [21, 24],
        'left_cuff_width': [10, 11],
        'right_cuff_width': [23, 24]
    },

    'long_sleeved_shirt': {
        'collar_width': [27, 31],
        'shoulder_width': [33, 46],
        'chest_width': [38, 44],
        'hem_width': [41, 43],
        'body_length': [28, 42],
        'left_sleeve_length': [33, 36],
        'right_sleeve_length': [46, 49],
        'left_cuff_width': [35, 36],
        'right_cuff_width': [48, 49]
    },

    'short_sleeved_outwear': {
        'collar_width': [60, 64],
        'shoulder_width': [66, 79],
        'chest_width': [71, 77],
        'hem_width': [74, 76],
        'body_length': [61, 75],
        'left_sleeve_length': [66, 69],
        'right_sleeve_length': [79, 82],
        'left_cuff_width': [68, 69],
        'right_cuff_width': [81, 82]
    },

    'long_sleeved_outwear': {
        'collar_width': [91, 95],
        'shoulder_width': [97, 110],
        'chest_width': [102, 108],
        'hem_width': [105, 107],
        'body_length': [92, 106],
        'left_sleeve_length': [97, 100],
        'right_sleeve_length': [110, 113],
        'left_cuff_width': [99, 100],
        'right_cuff_width': [112, 113]
    },

    'vest': {
        'collar_width': [130, 134],
        'shoulder_width': [136, 142],
        'chest_width': [138, 140],
        'hem_width': [139, 141],
        'body_length': [131, 140]
    },

    'sling': {
        'strap_width': [145, 151],
        'chest_width': [147, 149],
        'hem_width': [148, 150],
        'body_length': [146, 149]
    },

    'shorts': {
        'waist_width': [160, 164],
        'hem_width': [162, 166],
        'length': [161, 163]
    },

    'trousers': {
        'waist_width': [170, 174],
        'left_hem_width': [176, 177],
        'right_hem_width': [179, 180],
        'left_length': [171, 177],
        'right_length': [173, 180]
    },

    'skirt': {
        'waist_width': [184, 186],
        'hem_width': [185, 187],
        'length': [184, 187]
    },

    'short_sleeved_dress': {
        'collar_width': [192, 196],
        'shoulder_width': [198, 211],
        'chest_width': [203, 209],
        'waist_width': [205, 207],
        'hem_width': [208, 210],
        'body_length': [193, 209],
        'left_sleeve_length': [198, 201],
        'right_sleeve_length': [211, 214]
    },

    'long_sleeved_dress': {
        'collar_width': [221, 225],
        'shoulder_width': [227, 240],
        'chest_width': [232, 238],
        'waist_width': [234, 236],
        'hem_width': [237, 239],
        'body_length': [222, 238],
        'left_sleeve_length': [227, 230],
        'right_sleeve_length': [240, 243]
    },

    'vest_dress': {
        'collar_width': [258, 262],
        'shoulder_width': [264, 270],
        'chest_width': [266, 268],
        'waist_width': [267, 269],
        'hem_width': [268, 270],
        'body_length': [259, 269]
    },

    'sling_dress': {
        'strap_width': [277, 283],
        'chest_width': [279, 281],
        'waist_width': [280, 282],
        'hem_width': [281, 283],
        'body_length': [278, 282]
    }
}


def get_measurement_landmarks(category: str, measurement_name: str):
    """
    Get landmark indices for a specific measurement

    Args:
        category: Garment category (e.g., 'short_sleeved_shirt')
        measurement_name: Measurement type (e.g., 'collar_width')

    Returns:
        [start_idx, end_idx] or None if not found
    """
    if category not in LANDMARK_MAPPINGS:
        return None

    category_map = LANDMARK_MAPPINGS[category]
    return category_map.get(measurement_name)


def get_all_measurements_for_category(category: str):
    """
    Get all available measurements for a garment category

    Args:
        category: Garment category

    Returns:
        Dictionary of measurement_name: [start_idx, end_idx]
    """
    return LANDMARK_MAPPINGS.get(category, {})


def get_category_offset(category: str):
    """
    Get the starting landmark index offset for a category

    Args:
        category: Garment category

    Returns:
        Starting index for this category in the 294 landmark array
    """
    category_offsets = {
        'short_sleeved_shirt': 0,
        'long_sleeved_shirt': 25,
        'short_sleeved_outwear': 58,
        'long_sleeved_outwear': 89,
        'vest': 128,
        'sling': 143,
        'shorts': 158,
        'trousers': 168,
        'skirt': 182,
        'short_sleeved_dress': 190,
        'long_sleeved_dress': 219,
        'vest_dress': 256,
        'sling_dress': 275
    }
    return category_offsets.get(category, 0)
