
import cv2
import numpy as np
import json
from dataclasses import dataclass, asdict

try:
    # OpenCV >= 4.7 API
    from cv2 import aruco as aruco_mod
    HAVE_NEW_ARUCO = True
except Exception:
    aruco_mod = cv2.aruco
    HAVE_NEW_ARUCO = False


@dataclass
class CalibrationData:
    camera_matrix: list
    dist_coeff: list
    homography: list
    ppm: float                 # pixels per mm
    pixel_to_mm: float         # mm per pixel
    rect_rms_mm: float         # homography reprojection RMS in mm
    bench_width_mm: float
    bench_height_mm: float
    marker_world_mm: dict      # {id: [x,y]} world corner positions (mm)
    marker_size_mm: float

    def to_json(self):
        return json.dumps(asdict(self), indent=2)

    @staticmethod
    def from_json(js: dict):
        return CalibrationData(
            camera_matrix=js["camera_matrix"],
            dist_coeff=js["dist_coeff"],
            homography=js["homography"],
            ppm=js["ppm"],
            pixel_to_mm=js["pixel_to_mm"],
            rect_rms_mm=js.get("rect_rms_mm", 0.0),
            bench_width_mm=js["bench_width_mm"],
            bench_height_mm=js["bench_height_mm"],
            marker_world_mm=js["marker_world_mm"],
            marker_size_mm=js["marker_size_mm"],
        )


class CalibrationTool:
    def __init__(self, dict_name="DICT_6X6_50"):
        if hasattr(aruco_mod, "getPredefinedDictionary"):
            self.dict = getattr(aruco_mod, "getPredefinedDictionary")(getattr(aruco_mod, dict_name))
        else:
            self.dict = aruco_mod.Dictionary_get(getattr(aruco_mod, dict_name))
        # Detector parameters
        if HAVE_NEW_ARUCO and hasattr(aruco_mod, "DetectorParameters"):
            self.params = aruco_mod.DetectorParameters()
            self.detector = aruco_mod.ArucoDetector(self.dict, self.params)
        else:
            self.params = aruco_mod.DetectorParameters_create()
            self.detector = None

        self.data: CalibrationData | None = None

    # --- ArUco detection ---
    def detect_aruco_markers(self, img_bgr):
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY) if img_bgr.ndim == 3 else img_bgr
        if self.detector is not None:
            corners, ids, _ = self.detector.detectMarkers(gray)
        else:
            corners, ids, _ = aruco_mod.detectMarkers(gray, self.dict, parameters=self.params)
        return corners, ids

    # --- Compute homography from specific marker corners ---
    def calculate_homography_from_markers(self, img_bgr, world_corner_ids=(0,1,2,3)):
        corners, ids = self.detect_aruco_markers(img_bgr)
        if ids is None or len(ids) < 4:
            raise RuntimeError("Need all four ArUco ids {0,1,2,3} visible for homography.")

        ids = ids.flatten().tolist()
        id2corners = {int(i): c[0] for c, i in zip(corners, ids)}
        for need in world_corner_ids:
            if need not in id2corners:
                raise RuntimeError(f"Missing required ArUco id {need} for homography.")

        # Use consistent specific corners per tag:
        #   0: TL uses its top-left (index 0)
        #   1: TR uses its top-right (index 1)
        #   2: BR uses its bottom-right (index 2)
        #   3: BL uses its bottom-left (index 3)
        img_pts = np.float32([
            id2corners[0][0],
            id2corners[1][1],
            id2corners[2][2],
            id2corners[3][3],
        ])

        # World points from known bench rectangle (mm)
        # Expect marker_world_mm to contain these ids as exact world coordinates of those corners
        wmap = self.data.marker_world_mm if self.data else None
        if not wmap:
            # Fallback: infer rectangle from bench dimensions with origin at (0,0)
            raise RuntimeError("CalibrationData.marker_world_mm not set. Load or set before computing H.")
        world_pts = np.float32([
            wmap["0"], wmap["1"], wmap["2"], wmap["3"]
        ])

        H, status = cv2.findHomography(img_pts, world_pts, cv2.RANSAC, 3.0)
        if H is None:
            raise RuntimeError("findHomography failed.")

        # Compute RMS reprojection error in mm using the same 4 correspondences
        proj = cv2.perspectiveTransform(img_pts.reshape(-1,1,2), H).reshape(-1,2)
        err = np.linalg.norm(proj - world_pts, axis=1)
        rect_rms_mm = float(np.sqrt(np.mean(err**2)))

        # Derive pixels-per-mm (ppm) from H by projecting unit mm steps;
        # Note: H maps image(px)->world(mm). For ppm, we can invert H to get world->image.
        Hinv = np.linalg.inv(H)
        world_pair_x = np.float32([[[0,0]], [[1,0]]])  # 1 mm in X
        world_pair_y = np.float32([[[0,0]], [[0,1]]])  # 1 mm in Y
        px_pair_x = cv2.perspectiveTransform(world_pair_x, Hinv).reshape(-1,2)
        px_pair_y = cv2.perspectiveTransform(world_pair_y, Hinv).reshape(-1,2)
        ppm_x = float(np.linalg.norm(px_pair_x[1]-px_pair_x[0]))
        ppm_y = float(np.linalg.norm(px_pair_y[1]-px_pair_y[0]))
        ppm = (ppm_x + ppm_y) / 2.0
        pixel_to_mm = 1.0 / ppm if ppm > 1e-9 else 0.0

        # Store
        self.data.homography = H.tolist()
        self.data.ppm = float(ppm)
        self.data.pixel_to_mm = float(pixel_to_mm)
        self.data.rect_rms_mm = rect_rms_mm
        return H, rect_rms_mm, ppm

    # --- Save/Load JSON ---
    def save(self, path):
        if not self.data:
            raise RuntimeError("No calibration data to save.")
        with open(path, "w") as f:
            f.write(self.data.to_json())

    def load(self, path):
        with open(path, "r") as f:
            js = json.load(f)
        self.data = CalibrationData.from_json(js)
        return self.data

    # --- Verify after rectification: scale sanity check using tag centers ---
    def verify_rectified_scale(self, rectified_bgr, expected_dx_mm: float, id_left=0, id_right=1, tol_mm=2.0):
        corners, ids = self.detect_aruco_markers(rectified_bgr)
        if ids is None:
            return False, "No ArUco detected on rectified image."
        ids = ids.flatten().tolist()
        id2corn = {int(i): c[0] for c, i in zip(corners, ids)}
        if id_left not in id2corn or id_right not in id2corn:
            return False, "Missing required ArUco ids for scale check."
        pL = id2corn[id_left].mean(axis=0)
        pR = id2corn[id_right].mean(axis=0)
        dx_mm = float(np.linalg.norm(pR - pL) * self.data.pixel_to_mm)
        ok = abs(dx_mm - expected_dx_mm) <= tol_mm
        msg = f"Scale check: measured {dx_mm:.2f} mm vs expected {expected_dx_mm:.2f} mm, tol ±{tol_mm} mm"
        return ok, msg
