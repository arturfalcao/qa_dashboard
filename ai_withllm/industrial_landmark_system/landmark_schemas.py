"""
Industrial Landmark Skeleton Definitions

Defines precise landmark schemas for flat-lay garment measurement,
optimized for industrial inspection. These schemas are designed to:

1. Cover all critical measurement points for QC
2. Be robust to detection on flat-lay images
3. Map to standard garment measurement specifications
4. Support both width and length measurements

Based on analysis of:
- DeepFashion2 landmark structure (294 keypoints across 13 categories)
- Kim et al. (2022) measurement methodology
- GarmentIQ landmark definitions
- Industry standard garment measurement specs (ASTM D5219)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from enum import Enum


class LandmarkVisibility(Enum):
    """Landmark visibility states"""
    NOT_LABELED = 0
    OCCLUDED = 1
    VISIBLE = 2


class SemanticGroup(Enum):
    """Semantic groupings for landmarks"""
    COLLAR = "collar"
    SHOULDER = "shoulder"
    SLEEVE = "sleeve"
    BODY = "body"
    HEM = "hem"
    WAIST = "waist"
    CROTCH = "crotch"
    LEG = "leg"
    HOOD = "hood"
    POCKET = "pocket"
    CUFF = "cuff"


@dataclass
class LandmarkDefinition:
    """Definition of a single landmark point"""
    id: int
    name: str
    description: str
    semantic_group: SemanticGroup
    min_confidence: float = 0.3
    is_symmetric_pair: bool = False
    symmetric_partner_id: Optional[int] = None
    # DeepFashion2 mapping (if applicable)
    df2_index: Optional[int] = None


@dataclass
class LandmarkSchema:
    """Complete landmark schema for a garment category"""
    category: str
    display_name: str
    num_landmarks: int
    landmarks: Dict[int, LandmarkDefinition]
    skeleton: List[Tuple[int, int]]  # Connections between landmarks
    measurement_pairs: Dict[str, Tuple[int, int]]  # Named measurement point pairs

    def get_landmark(self, landmark_id: int) -> Optional[LandmarkDefinition]:
        return self.landmarks.get(landmark_id)

    def get_landmarks_by_group(self, group: SemanticGroup) -> List[LandmarkDefinition]:
        return [lm for lm in self.landmarks.values() if lm.semantic_group == group]

    def get_symmetric_pairs(self) -> List[Tuple[int, int]]:
        pairs = []
        seen = set()
        for lm in self.landmarks.values():
            if lm.is_symmetric_pair and lm.symmetric_partner_id is not None:
                pair = tuple(sorted([lm.id, lm.symmetric_partner_id]))
                if pair not in seen:
                    pairs.append(pair)
                    seen.add(pair)
        return pairs


# =============================================================================
# T-SHIRT LANDMARK SCHEMA (25 keypoints)
# =============================================================================
TSHIRT_SCHEMA = LandmarkSchema(
    category="tshirt",
    display_name="T-Shirt / Short-Sleeved Shirt",
    num_landmarks=25,
    landmarks={
        # Collar region (5 points)
        0: LandmarkDefinition(
            id=0, name="collar_center_top",
            description="Center top of neckline opening",
            semantic_group=SemanticGroup.COLLAR,
            df2_index=2  # Maps to DF2 short_sleeved_shirt center_collar
        ),
        1: LandmarkDefinition(
            id=1, name="collar_left",
            description="Left edge of collar/neckline",
            semantic_group=SemanticGroup.COLLAR,
            is_symmetric_pair=True, symmetric_partner_id=2,
            df2_index=0
        ),
        2: LandmarkDefinition(
            id=2, name="collar_right",
            description="Right edge of collar/neckline",
            semantic_group=SemanticGroup.COLLAR,
            is_symmetric_pair=True, symmetric_partner_id=1,
            df2_index=4
        ),
        3: LandmarkDefinition(
            id=3, name="collar_bottom_left",
            description="Left bottom of neckline curve",
            semantic_group=SemanticGroup.COLLAR,
            df2_index=1
        ),
        4: LandmarkDefinition(
            id=4, name="collar_bottom_right",
            description="Right bottom of neckline curve",
            semantic_group=SemanticGroup.COLLAR,
            df2_index=3
        ),

        # Shoulder region (4 points)
        5: LandmarkDefinition(
            id=5, name="shoulder_left_outer",
            description="Left shoulder seam endpoint (outermost)",
            semantic_group=SemanticGroup.SHOULDER,
            is_symmetric_pair=True, symmetric_partner_id=6,
            df2_index=8
        ),
        6: LandmarkDefinition(
            id=6, name="shoulder_right_outer",
            description="Right shoulder seam endpoint (outermost)",
            semantic_group=SemanticGroup.SHOULDER,
            is_symmetric_pair=True, symmetric_partner_id=5,
            df2_index=21
        ),
        7: LandmarkDefinition(
            id=7, name="shoulder_left_inner",
            description="Left shoulder near collar",
            semantic_group=SemanticGroup.SHOULDER,
            df2_index=5
        ),
        8: LandmarkDefinition(
            id=8, name="shoulder_right_inner",
            description="Right shoulder near collar",
            semantic_group=SemanticGroup.SHOULDER,
            df2_index=10
        ),

        # Armpit/underarm region (2 points)
        9: LandmarkDefinition(
            id=9, name="armpit_left",
            description="Left underarm junction point",
            semantic_group=SemanticGroup.BODY,
            is_symmetric_pair=True, symmetric_partner_id=10,
            df2_index=13
        ),
        10: LandmarkDefinition(
            id=10, name="armpit_right",
            description="Right underarm junction point",
            semantic_group=SemanticGroup.BODY,
            is_symmetric_pair=True, symmetric_partner_id=9,
            df2_index=19
        ),

        # Sleeve region (6 points - 3 per sleeve)
        11: LandmarkDefinition(
            id=11, name="sleeve_left_top",
            description="Left sleeve top edge",
            semantic_group=SemanticGroup.SLEEVE,
            df2_index=7
        ),
        12: LandmarkDefinition(
            id=12, name="sleeve_left_bottom",
            description="Left sleeve bottom edge (at hem)",
            semantic_group=SemanticGroup.SLEEVE,
            df2_index=9
        ),
        13: LandmarkDefinition(
            id=13, name="sleeve_left_end",
            description="Left sleeve hem center",
            semantic_group=SemanticGroup.SLEEVE,
            is_symmetric_pair=True, symmetric_partner_id=16,
            df2_index=11
        ),
        14: LandmarkDefinition(
            id=14, name="sleeve_right_top",
            description="Right sleeve top edge",
            semantic_group=SemanticGroup.SLEEVE,
            df2_index=22
        ),
        15: LandmarkDefinition(
            id=15, name="sleeve_right_bottom",
            description="Right sleeve bottom edge (at hem)",
            semantic_group=SemanticGroup.SLEEVE,
            df2_index=24
        ),
        16: LandmarkDefinition(
            id=16, name="sleeve_right_end",
            description="Right sleeve hem center",
            semantic_group=SemanticGroup.SLEEVE,
            is_symmetric_pair=True, symmetric_partner_id=13,
            df2_index=23
        ),

        # Body side seam (4 points)
        17: LandmarkDefinition(
            id=17, name="side_left_upper",
            description="Left side seam upper point",
            semantic_group=SemanticGroup.BODY,
            df2_index=12
        ),
        18: LandmarkDefinition(
            id=18, name="side_right_upper",
            description="Right side seam upper point",
            semantic_group=SemanticGroup.BODY,
            df2_index=18
        ),
        19: LandmarkDefinition(
            id=19, name="side_left_lower",
            description="Left side seam lower point (near hem)",
            semantic_group=SemanticGroup.BODY,
            df2_index=14
        ),
        20: LandmarkDefinition(
            id=20, name="side_right_lower",
            description="Right side seam lower point (near hem)",
            semantic_group=SemanticGroup.BODY,
            df2_index=20
        ),

        # Hem region (4 points)
        21: LandmarkDefinition(
            id=21, name="hem_left_corner",
            description="Bottom left corner of garment",
            semantic_group=SemanticGroup.HEM,
            is_symmetric_pair=True, symmetric_partner_id=22,
            df2_index=16
        ),
        22: LandmarkDefinition(
            id=22, name="hem_right_corner",
            description="Bottom right corner of garment",
            semantic_group=SemanticGroup.HEM,
            is_symmetric_pair=True, symmetric_partner_id=21,
            df2_index=18
        ),
        23: LandmarkDefinition(
            id=23, name="hem_center",
            description="Center point of bottom hem",
            semantic_group=SemanticGroup.HEM,
            df2_index=17
        ),

        # Body center (1 point)
        24: LandmarkDefinition(
            id=24, name="body_center",
            description="Center point of garment body",
            semantic_group=SemanticGroup.BODY,
            min_confidence=0.2  # Lower threshold as this is derived
        ),
    },
    skeleton=[
        # Collar outline
        (1, 3), (3, 0), (0, 4), (4, 2),
        # Collar to shoulders
        (1, 7), (7, 5), (2, 8), (8, 6),
        # Shoulders to sleeves
        (5, 11), (11, 13), (13, 12), (12, 9),
        (6, 14), (14, 16), (16, 15), (15, 10),
        # Body sides
        (9, 17), (17, 19), (19, 21),
        (10, 18), (18, 20), (20, 22),
        # Hem
        (21, 23), (23, 22),
        # Cross connections for structure
        (9, 10), (21, 22),
    ],
    measurement_pairs={
        "collar_width": (1, 2),
        "shoulder_width": (5, 6),
        "chest_width": (9, 10),
        "hem_width": (21, 22),
        "body_length": (0, 23),
        "sleeve_length_left": (5, 13),
        "sleeve_length_right": (6, 16),
        "side_length_left": (9, 21),
        "side_length_right": (10, 22),
    }
)


# =============================================================================
# HOODIE/SWEATSHIRT LANDMARK SCHEMA (33 keypoints)
# =============================================================================
HOODIE_SCHEMA = LandmarkSchema(
    category="hoodie",
    display_name="Hoodie / Sweatshirt",
    num_landmarks=33,
    landmarks={
        # Hood region (5 points)
        0: LandmarkDefinition(
            id=0, name="hood_top_center",
            description="Top center of hood",
            semantic_group=SemanticGroup.HOOD
        ),
        1: LandmarkDefinition(
            id=1, name="hood_left_edge",
            description="Left edge of hood opening",
            semantic_group=SemanticGroup.HOOD,
            is_symmetric_pair=True, symmetric_partner_id=2
        ),
        2: LandmarkDefinition(
            id=2, name="hood_right_edge",
            description="Right edge of hood opening",
            semantic_group=SemanticGroup.HOOD,
            is_symmetric_pair=True, symmetric_partner_id=1
        ),
        3: LandmarkDefinition(
            id=3, name="hood_left_outer",
            description="Left outer edge of hood",
            semantic_group=SemanticGroup.HOOD
        ),
        4: LandmarkDefinition(
            id=4, name="hood_right_outer",
            description="Right outer edge of hood",
            semantic_group=SemanticGroup.HOOD
        ),

        # Collar/neckline (where hood meets body) - 3 points
        5: LandmarkDefinition(
            id=5, name="collar_center",
            description="Center of collar/hood opening",
            semantic_group=SemanticGroup.COLLAR,
            df2_index=27  # Maps to DF2 long_sleeved_shirt
        ),
        6: LandmarkDefinition(
            id=6, name="collar_left",
            description="Left collar point",
            semantic_group=SemanticGroup.COLLAR,
            is_symmetric_pair=True, symmetric_partner_id=7
        ),
        7: LandmarkDefinition(
            id=7, name="collar_right",
            description="Right collar point",
            semantic_group=SemanticGroup.COLLAR,
            is_symmetric_pair=True, symmetric_partner_id=6
        ),

        # Shoulder region (4 points)
        8: LandmarkDefinition(
            id=8, name="shoulder_left_outer",
            description="Left shoulder seam endpoint",
            semantic_group=SemanticGroup.SHOULDER,
            is_symmetric_pair=True, symmetric_partner_id=9,
            df2_index=33
        ),
        9: LandmarkDefinition(
            id=9, name="shoulder_right_outer",
            description="Right shoulder seam endpoint",
            semantic_group=SemanticGroup.SHOULDER,
            is_symmetric_pair=True, symmetric_partner_id=8,
            df2_index=46
        ),
        10: LandmarkDefinition(
            id=10, name="shoulder_left_seam",
            description="Left shoulder seam mid-point",
            semantic_group=SemanticGroup.SHOULDER
        ),
        11: LandmarkDefinition(
            id=11, name="shoulder_right_seam",
            description="Right shoulder seam mid-point",
            semantic_group=SemanticGroup.SHOULDER
        ),

        # Armpit region (2 points)
        12: LandmarkDefinition(
            id=12, name="armpit_left",
            description="Left underarm point",
            semantic_group=SemanticGroup.BODY,
            is_symmetric_pair=True, symmetric_partner_id=13,
            df2_index=38
        ),
        13: LandmarkDefinition(
            id=13, name="armpit_right",
            description="Right underarm point",
            semantic_group=SemanticGroup.BODY,
            is_symmetric_pair=True, symmetric_partner_id=12,
            df2_index=44
        ),

        # Sleeve region (8 points - 4 per sleeve for long sleeves)
        14: LandmarkDefinition(
            id=14, name="sleeve_left_upper",
            description="Left sleeve upper point",
            semantic_group=SemanticGroup.SLEEVE
        ),
        15: LandmarkDefinition(
            id=15, name="sleeve_left_elbow",
            description="Left sleeve elbow area",
            semantic_group=SemanticGroup.SLEEVE
        ),
        16: LandmarkDefinition(
            id=16, name="sleeve_left_cuff_outer",
            description="Left cuff outer edge",
            semantic_group=SemanticGroup.CUFF,
            df2_index=35
        ),
        17: LandmarkDefinition(
            id=17, name="sleeve_left_cuff_inner",
            description="Left cuff inner edge",
            semantic_group=SemanticGroup.CUFF,
            df2_index=36
        ),
        18: LandmarkDefinition(
            id=18, name="sleeve_right_upper",
            description="Right sleeve upper point",
            semantic_group=SemanticGroup.SLEEVE
        ),
        19: LandmarkDefinition(
            id=19, name="sleeve_right_elbow",
            description="Right sleeve elbow area",
            semantic_group=SemanticGroup.SLEEVE
        ),
        20: LandmarkDefinition(
            id=20, name="sleeve_right_cuff_outer",
            description="Right cuff outer edge",
            semantic_group=SemanticGroup.CUFF,
            df2_index=48
        ),
        21: LandmarkDefinition(
            id=21, name="sleeve_right_cuff_inner",
            description="Right cuff inner edge",
            semantic_group=SemanticGroup.CUFF,
            df2_index=49
        ),

        # Pocket region (4 points for kangaroo pocket)
        22: LandmarkDefinition(
            id=22, name="pocket_left_top",
            description="Left top corner of pocket",
            semantic_group=SemanticGroup.POCKET
        ),
        23: LandmarkDefinition(
            id=23, name="pocket_right_top",
            description="Right top corner of pocket",
            semantic_group=SemanticGroup.POCKET
        ),
        24: LandmarkDefinition(
            id=24, name="pocket_left_bottom",
            description="Left bottom corner of pocket",
            semantic_group=SemanticGroup.POCKET
        ),
        25: LandmarkDefinition(
            id=25, name="pocket_right_bottom",
            description="Right bottom corner of pocket",
            semantic_group=SemanticGroup.POCKET
        ),

        # Body sides (4 points)
        26: LandmarkDefinition(
            id=26, name="side_left_upper",
            description="Left side upper point",
            semantic_group=SemanticGroup.BODY
        ),
        27: LandmarkDefinition(
            id=27, name="side_right_upper",
            description="Right side upper point",
            semantic_group=SemanticGroup.BODY
        ),
        28: LandmarkDefinition(
            id=28, name="side_left_lower",
            description="Left side lower point",
            semantic_group=SemanticGroup.BODY
        ),
        29: LandmarkDefinition(
            id=29, name="side_right_lower",
            description="Right side lower point",
            semantic_group=SemanticGroup.BODY
        ),

        # Hem/ribbing region (4 points)
        30: LandmarkDefinition(
            id=30, name="hem_left_corner",
            description="Bottom left corner",
            semantic_group=SemanticGroup.HEM,
            is_symmetric_pair=True, symmetric_partner_id=31,
            df2_index=41
        ),
        31: LandmarkDefinition(
            id=31, name="hem_right_corner",
            description="Bottom right corner",
            semantic_group=SemanticGroup.HEM,
            is_symmetric_pair=True, symmetric_partner_id=30,
            df2_index=43
        ),
        32: LandmarkDefinition(
            id=32, name="hem_center",
            description="Center of bottom hem",
            semantic_group=SemanticGroup.HEM,
            df2_index=42
        ),
    },
    skeleton=[
        # Hood outline
        (3, 0), (0, 4), (3, 1), (4, 2), (1, 5), (5, 2),
        # Collar to shoulders
        (6, 10), (10, 8), (7, 11), (11, 9),
        # Shoulders to sleeves
        (8, 14), (14, 15), (15, 16), (16, 17),
        (9, 18), (18, 19), (19, 20), (20, 21),
        # Body sides
        (12, 26), (26, 28), (28, 30),
        (13, 27), (27, 29), (29, 31),
        # Hem
        (30, 32), (32, 31),
        # Pocket
        (22, 23), (22, 24), (23, 25), (24, 25),
        # Cross connections
        (12, 13), (30, 31),
    ],
    measurement_pairs={
        "hood_width": (3, 4),
        "collar_width": (6, 7),
        "shoulder_width": (8, 9),
        "chest_width": (12, 13),
        "hem_width": (30, 31),
        "body_length": (5, 32),
        "sleeve_length_left": (8, 16),
        "sleeve_length_right": (9, 20),
        "cuff_width_left": (16, 17),
        "cuff_width_right": (20, 21),
        "pocket_width": (22, 23),
        "pocket_height": (22, 24),
    }
)


# =============================================================================
# TROUSERS/PANTS LANDMARK SCHEMA (21 keypoints)
# =============================================================================
TROUSERS_SCHEMA = LandmarkSchema(
    category="trousers",
    display_name="Trousers / Pants",
    num_landmarks=21,
    landmarks={
        # Waistband region (5 points)
        0: LandmarkDefinition(
            id=0, name="waist_center",
            description="Center of waistband",
            semantic_group=SemanticGroup.WAIST,
            df2_index=169
        ),
        1: LandmarkDefinition(
            id=1, name="waist_left",
            description="Left edge of waistband",
            semantic_group=SemanticGroup.WAIST,
            is_symmetric_pair=True, symmetric_partner_id=2,
            df2_index=168
        ),
        2: LandmarkDefinition(
            id=2, name="waist_right",
            description="Right edge of waistband",
            semantic_group=SemanticGroup.WAIST,
            is_symmetric_pair=True, symmetric_partner_id=1,
            df2_index=170
        ),
        3: LandmarkDefinition(
            id=3, name="waist_left_inner",
            description="Left inner waistband point",
            semantic_group=SemanticGroup.WAIST
        ),
        4: LandmarkDefinition(
            id=4, name="waist_right_inner",
            description="Right inner waistband point",
            semantic_group=SemanticGroup.WAIST
        ),

        # Hip region (2 points)
        5: LandmarkDefinition(
            id=5, name="hip_left",
            description="Left hip point",
            semantic_group=SemanticGroup.BODY,
            is_symmetric_pair=True, symmetric_partner_id=6,
            df2_index=171
        ),
        6: LandmarkDefinition(
            id=6, name="hip_right",
            description="Right hip point",
            semantic_group=SemanticGroup.BODY,
            is_symmetric_pair=True, symmetric_partner_id=5,
            df2_index=173
        ),

        # Crotch region (3 points)
        7: LandmarkDefinition(
            id=7, name="crotch_left",
            description="Left crotch point",
            semantic_group=SemanticGroup.CROTCH
        ),
        8: LandmarkDefinition(
            id=8, name="crotch_center",
            description="Center crotch point (lowest)",
            semantic_group=SemanticGroup.CROTCH,
            df2_index=172
        ),
        9: LandmarkDefinition(
            id=9, name="crotch_right",
            description="Right crotch point",
            semantic_group=SemanticGroup.CROTCH
        ),

        # Thigh region (2 points)
        10: LandmarkDefinition(
            id=10, name="thigh_left",
            description="Left thigh mid-point",
            semantic_group=SemanticGroup.LEG,
            df2_index=174
        ),
        11: LandmarkDefinition(
            id=11, name="thigh_right",
            description="Right thigh mid-point",
            semantic_group=SemanticGroup.LEG,
            df2_index=178
        ),

        # Knee region (2 points)
        12: LandmarkDefinition(
            id=12, name="knee_left",
            description="Left knee point",
            semantic_group=SemanticGroup.LEG,
            is_symmetric_pair=True, symmetric_partner_id=13,
            df2_index=175
        ),
        13: LandmarkDefinition(
            id=13, name="knee_right",
            description="Right knee point",
            semantic_group=SemanticGroup.LEG,
            is_symmetric_pair=True, symmetric_partner_id=12,
            df2_index=179
        ),

        # Calf region (2 points)
        14: LandmarkDefinition(
            id=14, name="calf_left",
            description="Left calf mid-point",
            semantic_group=SemanticGroup.LEG
        ),
        15: LandmarkDefinition(
            id=15, name="calf_right",
            description="Right calf mid-point",
            semantic_group=SemanticGroup.LEG
        ),

        # Hem/ankle region (5 points)
        16: LandmarkDefinition(
            id=16, name="hem_left_outer",
            description="Left leg hem outer edge",
            semantic_group=SemanticGroup.HEM,
            df2_index=176
        ),
        17: LandmarkDefinition(
            id=17, name="hem_left_inner",
            description="Left leg hem inner edge",
            semantic_group=SemanticGroup.HEM,
            df2_index=177
        ),
        18: LandmarkDefinition(
            id=18, name="hem_right_inner",
            description="Right leg hem inner edge",
            semantic_group=SemanticGroup.HEM,
            df2_index=180
        ),
        19: LandmarkDefinition(
            id=19, name="hem_right_outer",
            description="Right leg hem outer edge",
            semantic_group=SemanticGroup.HEM,
            df2_index=181
        ),
        20: LandmarkDefinition(
            id=20, name="hem_left_center",
            description="Left leg hem center",
            semantic_group=SemanticGroup.HEM
        ),
    },
    skeleton=[
        # Waistband
        (1, 0), (0, 2), (1, 3), (3, 4), (4, 2),
        # Hips
        (1, 5), (2, 6), (5, 7), (6, 9),
        # Crotch
        (7, 8), (8, 9),
        # Left leg
        (5, 10), (10, 12), (12, 14), (14, 16), (16, 17),
        # Right leg
        (6, 11), (11, 13), (13, 15), (15, 18), (18, 19),
        # Inner seam
        (7, 17), (9, 18),
    ],
    measurement_pairs={
        "waist_width": (1, 2),
        "hip_width": (5, 6),
        "thigh_width_left": (5, 7),
        "thigh_width_right": (6, 9),
        "hem_width_left": (16, 17),
        "hem_width_right": (18, 19),
        "outseam_left": (1, 16),
        "outseam_right": (2, 19),
        "inseam_left": (8, 17),
        "inseam_right": (8, 18),
        "front_rise": (0, 8),
        "knee_width_left": (12, 12),  # Single point - needs edge detection
        "knee_width_right": (13, 13),
    }
)


# =============================================================================
# SHORTS LANDMARK SCHEMA (15 keypoints)
# =============================================================================
SHORTS_SCHEMA = LandmarkSchema(
    category="shorts",
    display_name="Shorts",
    num_landmarks=15,
    landmarks={
        # Waistband (3 points)
        0: LandmarkDefinition(
            id=0, name="waist_center",
            description="Center of waistband",
            semantic_group=SemanticGroup.WAIST,
            df2_index=159
        ),
        1: LandmarkDefinition(
            id=1, name="waist_left",
            description="Left edge of waistband",
            semantic_group=SemanticGroup.WAIST,
            is_symmetric_pair=True, symmetric_partner_id=2,
            df2_index=158
        ),
        2: LandmarkDefinition(
            id=2, name="waist_right",
            description="Right edge of waistband",
            semantic_group=SemanticGroup.WAIST,
            is_symmetric_pair=True, symmetric_partner_id=1,
            df2_index=160
        ),

        # Hip region (2 points)
        3: LandmarkDefinition(
            id=3, name="hip_left",
            description="Left hip point",
            semantic_group=SemanticGroup.BODY,
            is_symmetric_pair=True, symmetric_partner_id=4,
            df2_index=161
        ),
        4: LandmarkDefinition(
            id=4, name="hip_right",
            description="Right hip point",
            semantic_group=SemanticGroup.BODY,
            is_symmetric_pair=True, symmetric_partner_id=3,
            df2_index=163
        ),

        # Crotch (3 points)
        5: LandmarkDefinition(
            id=5, name="crotch_left",
            description="Left crotch point",
            semantic_group=SemanticGroup.CROTCH
        ),
        6: LandmarkDefinition(
            id=6, name="crotch_center",
            description="Center crotch point",
            semantic_group=SemanticGroup.CROTCH,
            df2_index=162
        ),
        7: LandmarkDefinition(
            id=7, name="crotch_right",
            description="Right crotch point",
            semantic_group=SemanticGroup.CROTCH
        ),

        # Thigh/side (2 points)
        8: LandmarkDefinition(
            id=8, name="thigh_left",
            description="Left thigh outer point",
            semantic_group=SemanticGroup.LEG
        ),
        9: LandmarkDefinition(
            id=9, name="thigh_right",
            description="Right thigh outer point",
            semantic_group=SemanticGroup.LEG
        ),

        # Hem region (5 points)
        10: LandmarkDefinition(
            id=10, name="hem_left_outer",
            description="Left leg hem outer edge",
            semantic_group=SemanticGroup.HEM,
            df2_index=164
        ),
        11: LandmarkDefinition(
            id=11, name="hem_left_inner",
            description="Left leg hem inner edge",
            semantic_group=SemanticGroup.HEM,
            df2_index=165
        ),
        12: LandmarkDefinition(
            id=12, name="hem_right_inner",
            description="Right leg hem inner edge",
            semantic_group=SemanticGroup.HEM,
            df2_index=166
        ),
        13: LandmarkDefinition(
            id=13, name="hem_right_outer",
            description="Right leg hem outer edge",
            semantic_group=SemanticGroup.HEM,
            df2_index=167
        ),
        14: LandmarkDefinition(
            id=14, name="hem_left_center",
            description="Left hem center",
            semantic_group=SemanticGroup.HEM
        ),
    },
    skeleton=[
        # Waistband
        (1, 0), (0, 2),
        # Hips
        (1, 3), (2, 4),
        # Crotch
        (3, 5), (5, 6), (6, 7), (7, 4),
        # Legs
        (3, 8), (8, 10), (10, 11),
        (4, 9), (9, 13), (13, 12),
        # Inner seam
        (5, 11), (7, 12),
    ],
    measurement_pairs={
        "waist_width": (1, 2),
        "hip_width": (3, 4),
        "hem_width_left": (10, 11),
        "hem_width_right": (12, 13),
        "outseam_left": (1, 10),
        "outseam_right": (2, 13),
        "inseam_left": (6, 11),
        "inseam_right": (6, 12),
        "front_rise": (0, 6),
    }
)


# =============================================================================
# MASTER SCHEMA REGISTRY
# =============================================================================
INDUSTRIAL_LANDMARK_SCHEMAS: Dict[str, LandmarkSchema] = {
    "tshirt": TSHIRT_SCHEMA,
    "short_sleeved_shirt": TSHIRT_SCHEMA,  # Alias
    "hoodie": HOODIE_SCHEMA,
    "sweatshirt": HOODIE_SCHEMA,  # Alias
    "long_sleeved_shirt": HOODIE_SCHEMA,  # Similar structure
    "trousers": TROUSERS_SCHEMA,
    "pants": TROUSERS_SCHEMA,  # Alias
    "jeans": TROUSERS_SCHEMA,  # Alias
    "shorts": SHORTS_SCHEMA,
}


def get_schema_for_category(category: str) -> Optional[LandmarkSchema]:
    """Get the landmark schema for a garment category"""
    # Normalize category name
    normalized = category.lower().replace("-", "_").replace(" ", "_")
    return INDUSTRIAL_LANDMARK_SCHEMAS.get(normalized)


def get_landmark_names(category: str) -> List[str]:
    """Get all landmark names for a category"""
    schema = get_schema_for_category(category)
    if schema is None:
        return []
    return [lm.name for lm in schema.landmarks.values()]


def get_skeleton_connections(category: str) -> List[Tuple[int, int]]:
    """Get skeleton connections for visualization"""
    schema = get_schema_for_category(category)
    if schema is None:
        return []
    return schema.skeleton


def get_measurement_pairs(category: str) -> Dict[str, Tuple[int, int]]:
    """Get measurement landmark pairs for a category"""
    schema = get_schema_for_category(category)
    if schema is None:
        return {}
    return schema.measurement_pairs


# DeepFashion2 index mapping for transfer learning
DF2_TO_INDUSTRIAL_MAPPING = {
    "tshirt": {
        # DF2 index -> Industrial schema index
        0: 1,   # left_collar_tip -> collar_left
        2: 0,   # center_collar -> collar_center_top
        4: 2,   # right_collar_tip -> collar_right
        8: 5,   # left_shoulder -> shoulder_left_outer
        21: 6,  # right_shoulder -> shoulder_right_outer
        13: 9,  # left_armpit -> armpit_left
        19: 10, # right_armpit -> armpit_right
        11: 13, # left_sleeve_cuff_outer -> sleeve_left_end
        23: 16, # right_sleeve_cuff_outer -> sleeve_right_end
        16: 21, # left_hem_corner -> hem_left_corner
        18: 22, # right_hem_corner -> hem_right_corner
        17: 23, # center_hem -> hem_center
    },
    "trousers": {
        168: 1,  # waistband_left -> waist_left
        169: 0,  # waistband_center -> waist_center
        170: 2,  # waistband_right -> waist_right
        171: 5,  # left_hip -> hip_left
        172: 8,  # crotch -> crotch_center
        173: 6,  # right_hip -> hip_right
        176: 16, # left_hem_outer -> hem_left_outer
        177: 17, # left_hem_inner -> hem_left_inner
        180: 18, # right_hem_inner -> hem_right_inner
        181: 19, # right_hem_outer -> hem_right_outer
    },
}


def map_df2_to_industrial(category: str, df2_landmarks: List,
                          df2_confidences: List) -> Tuple[List, List]:
    """
    Map DeepFashion2 294-point landmarks to industrial schema.

    Args:
        category: Garment category
        df2_landmarks: List of (x, y) or None for 294 DF2 landmarks
        df2_confidences: List of confidence scores

    Returns:
        Tuple of (industrial_landmarks, industrial_confidences)
    """
    schema = get_schema_for_category(category)
    if schema is None:
        return [], []

    mapping = DF2_TO_INDUSTRIAL_MAPPING.get(category, {})

    industrial_landmarks = [None] * schema.num_landmarks
    industrial_confidences = [0.0] * schema.num_landmarks

    # Map using explicit mappings
    for df2_idx, ind_idx in mapping.items():
        if df2_idx < len(df2_landmarks) and df2_landmarks[df2_idx] is not None:
            industrial_landmarks[ind_idx] = df2_landmarks[df2_idx]
            industrial_confidences[ind_idx] = df2_confidences[df2_idx]

    # For landmarks without direct mapping, try to use df2_index from schema
    for ind_idx, lm_def in schema.landmarks.items():
        if industrial_landmarks[ind_idx] is None and lm_def.df2_index is not None:
            df2_idx = lm_def.df2_index
            if df2_idx < len(df2_landmarks) and df2_landmarks[df2_idx] is not None:
                industrial_landmarks[ind_idx] = df2_landmarks[df2_idx]
                industrial_confidences[ind_idx] = df2_confidences[df2_idx]

    return industrial_landmarks, industrial_confidences
