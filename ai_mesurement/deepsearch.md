Garment Measurement System: End-to-End Pipeline Design
1. System Architecture (Diagram + Narrative)

Imaging Geometry: We mount a 16–20 MP camera (Arducam with IMX519/IMX477 sensor) on a rigid overhead frame, looking straight down at the 120 × 80 cm bench. A 6 mm focal length lens (~60° horizontal FOV) at ~1.2 m height covers the entire area with margin, yielding ~0.25–0.35 mm/pixel resolution
mdpi.com
. This working distance balances coverage and accuracy: a shorter lens (wider FOV) would introduce more distortion and lower pixel density, while a longer lens would require impractically high mounting. The lens is focused at the bench plane; a moderate f-stop (f/4–f/5.6 if available) ensures sufficient depth of field to keep the garment in focus corner-to-corner. If the lens has fixed aperture, adding an ND filter can allow slower shutter or wider aperture to increase depth-of-field without overexposure. A circular polarizer on the lens is used when cross-polarized lighting is employed (see below). The camera is mounted with minimal tilt (≤0.5°) and on vibration-damped supports to maintain calibration. Fiducials for scaling: Four high-accuracy markers (AprilTags or ArUco) are affixed at the corners of the measurement area (e.g. 110 × 70 cm rectangle). These markers have known IDs and positions in a world coordinate system (e.g. (0,0), (1100,0), (0,700) mm, etc.), providing reference points for perspective correction and scale. They are printed on dimensional stable material (or engraved) to Class I accuracy (±1.1 mm over 10 m
en.wikipedia.org
, i.e. ±0.13 mm over our ~1 m span) so that the reference scale error is negligible. As a backup scale reference, a metal ruler strip (class I) is embedded along one edge of the bench; this also serves as a secondary check on pixel-to-mm conversion. The fiducials are placed just outside the garment area to avoid occlusion by clothing, and a thin foam underlay ensures they sit in the same plane as the garment (eliminating parallax). These markers enable “virtual backlighting” by clearly defining the plane and scale even under varying camera positions
forum.opencv.org
.

Lighting Setup: We provide diffuse, uniform illumination combined with raking lights for edge enhancement. A overhead LED panel or ring light is mounted around the camera, providing ~2,000 lux at the bench with high CRI (>95) for true color and consistent contrast. This primary light is cross-polarized when needed: we fit a linear polarizing film over the LED source and a perpendicular polarizer on the camera lens, which eliminates specular glare from shiny fabrics or buttons
advancedillumination.com
. (Note: cross-polarization reduces light ~80%, so we increase exposure or use more intense LEDs to compensate
advancedillumination.com
.) In addition, two linear LED bar lights are placed at opposite sides of the table at a low angle (~20° above the plane) to produce dark-field/raking illumination. These graze the surface, casting small shadows at garment edges and wrinkles, boosting edge contrast against the dark background. The bar lights are diffuse (frosted) and set ~ at 45° inward toward the center, providing even coverage without hotspots. Each light bank is ~50 cm long with a 30°–60° beam spread, ensuring the entire garment is within their combined light field. We target ~1000 lux from the raking lights in addition to the overhead 2000 lux, which yields sufficient brightness for fast shutter speeds (~1/250 s) at ISO 100–200 and aperture ~f/4. Such settings virtually eliminate motion blur from operator handling or vibrations. The LED drivers are DC or high-frequency to avoid flicker; we also configure the camera for 50 Hz mains anti-flicker mode (on the Raspberry Pi, use exposure times in multiples of 10 ms to avoid aliasing 50 Hz lights, if any). Polarization & Filters: In normal operation, the cross-polarizer is engaged to suppress glare on glossy prints or synthetic fabrics, revealing true fabric edges. We include a UV/IR-cut filter on the lens to maintain consistent color and avoid IR interference from the high-CRI LEDs (which have some IR component). If dark garments on dark background prove challenging, we can optionally use near-IR flood lighting plus an IR-pass filter: many dark fabrics reflect IR more than visible, boosting contrast with a dark backdrop. (This is an optional mode using the Pi 5’s IR sensitivity when needed.)

Mechanical Setup: The bench surface is a matte, dark gray (near black) laminate that is non-reflective to maximize garment/background contrast
mdpi.com
. We avoid pure black (which would hide black garments); the chosen gray (~5% reflectance) provides just enough illumination on black fabric to differentiate it from background when lit with raking light. For white or light garments, the high exposure from lighting still keeps the background relatively low in the image histogram, aiding threshold-based segmentation. If extremely light garments are common, we can swap in an alternate background (e.g. matte blue or green) – the lighting and calibration markers are designed to be indifferent to background color. Garment Positioning: To ensure the garment lies flat and planar, the bench includes reference alignment guides and gentle restraints. We use a set of small flat magnets or weights (with felt bottom) that an operator can place at the garment’s corners/edges (e.g. sleeve ends, bottom hem corners) to pull it taut. These magnets are color-marked and easily identifiable so that if they encroach into the imaging area, the vision software can ignore their known color/shape. Alternatively, a lightweight frame with elastic cords can be placed around the garment’s perimeter to stretch out wrinkles – for v1, simple weights are more pragmatic. The garment should be oriented roughly aligned to the table axes (not skewed drastically), using a printed grid or rulers on the table edges as a visual guide for the operator. The background is kept free of texture or clutter; only the calibration markers and optional scale ruler are visible on the surface. Any logos or text on the bench are outside the camera FOV to prevent false edges. Geometry and Lens Trade-offs: The 6 mm lens on the Pi’s sensor yields roughly a 1.0 m working distance as noted. This gives about ±3 px (±1 mm) distortion at image corners after correction – an acceptable trade-off for a single-camera setup. A longer lens (e.g. 12 mm) at 2 m distance would reduce distortion and perspective, but would need a taller mount and brighter lighting (due to distance and smaller FOV per lux). We opt for the 6 mm setup as it meets the accuracy and is easier to install in a factory station. If needed, the architecture allows adding a second camera: for instance, a side-angle camera mounted horizontally at table level (orthogonal view) could capture thickness or folded hems or help measure inseam on pants if the inner crotch point is obscured. This second view (triggered simultaneously) can improve accuracy on complex 3D shapes by providing another angle for a bundle adjustment or verifying that the garment is fully flat (any lift/wrinkle would be seen in the side view). However, the baseline system achieves the required ±2 mm accuracy with the top-down camera alone, so the two-view setup is optional unless specialized garments demand it.

In summary, the architecture comprises: a Raspberry Pi 5 with HQ camera module (16 MP) on an overhead rig (~1.2 m above a 120×80 cm matte bench), four fixed ArUco/AprilTag fiducials defining the measurement plane and scale, a combination of cross-polarized diffuse lighting and angled raking lights (~2000+ 1000 lux, CRI 95) to maximize edge contrast, and mechanical aids (magnets, guides) to ensure the garment lies flat and aligned. This physical setup provides a stable, controlled imaging environment – a prerequisite for sub-2 mm measurement accuracy
mdpi.com
mdpi.com
 while maintaining throughput and ease of use in the factory.

2. Calibration Suite

Intrinsic Camera Calibration: We perform a one-time intrinsic calibration of the Pi 5 camera + lens using OpenCV’s Zhang method
mdpi.com
. Using a printed checkerboard or ChArUco board (e.g. 6×9 grid, 30 mm squares) placed on the bench, we capture ~15–20 images at different positions and orientations. The OpenCV routine cv2.calibrateCamera yields the camera matrix (focal lengths fx, fy and principal point cx, cy) and lens distortion coefficients (k₁,k₂,p₁,p₂,k₃)
learnopencv.com
learnopencv.com
. For example, the JSON output might be:

{
  "camera_matrix": [
    [3120.5, 0.0, 2016.3],
    [0.0, 3125.7, 1523.4],
    [0.0, 0.0, 1.0]
  ],
  "dist_coeff": [-0.321, 0.148, -0.0005, 0.0003, -0.042],
  "rms_error": 0.22
}


This indicates focal length ~3123 px (given sensor pixel size, ~3.4 mm actual focal length) and slight barrel distortion (k₁ negative). The RMS reprojection error of ~0.22 px confirms a precise calibration. These intrinsics correct raw images for fisheye distortion, ensuring that measurements won’t be skewed at the edges. After calibration, we fix the focus and zoom of the camera (using a locking ring on the lens) to maintain these intrinsics over time. We store the intrinsics JSON on the Pi and the server.

Extrinsic Calibration & Homography: Next, we calibrate the extrinsic relationship between the camera and the bench plane. Using the four corner fiducials (or a large checkerboard covering the table), we determine the planar homography that maps image pixels to real-world millimeters on the bench. For example, suppose the four ArUco markers at the corners of the 1100 mm × 700 mm rectangle are detected with image coordinates p₁…p₄ and known world coordinates P₁…P₄ (e.g. (0,0), (1100,0), (1100,700), (0,700) in mm). We compute a perspective transform H such that H * p = P for these points. In practice we use cv2.findHomography(imagePoints, worldPoints) which yields a 3×3 matrix H. This H encompasses camera orientation (tilt) and scale. We incorporate lens distortion correction before homography: i.e., we undistort marker corners then find H. The result is that H can be used to rectify images to a true top-down view: if we warp the image with cv2.warpPerspective using H, an object of true size L mm will measure L pixels in the rectified image (we define output pixel pitch = 1 mm for convenience). Alternatively, we skip producing a warped image and directly use H to transform points and distances: a point at image (u,v) can be mapped to (x,y) mm via (x,y,w) = H * (u,v,1) (then divide by w). This enables metric measurements from a single view
forum.opencv.org
. We verify the homography by measuring known distances between markers: e.g., adjacent corner markers 1100 mm apart should measure within <0.5 mm error in the transformed coordinates. Our goal is sub-pixel homography accuracy; typical marker detection errors of ~0.1–0.2 px lead to ~±0.2 mm uncertainty over a 1 m span, which is an order smaller than our ±2 mm goal.

If we enable an optional two-view calibration (top + side camera), we perform a stereo calibration (finding both cameras’ intrinsics and their relative pose) or a 3D bundle adjustment. For instance, the side camera can help determine any slight out-of-plane deformation (like a lifted wrinkle) by triangulating points. In a bundle adjustment, we would include both cameras’ observations of multi-view calibration targets (e.g. a wand with markers) to refine the 3D pose of each camera. However, for flat garment measurements, we typically treat the garment as planar, so a single homography suffices.

Pixel-to-mm Derivation: We implement two parallel methods to convert pixel measurements to millimeters, cross-checking them for reliability: (a) Using the known homography H, we convert pixel coordinates of extracted points directly to mm. For example, if two points have image distance d_pixels, we transform them to world coords and compute Euclidean distance in mm. (b) Using a known reference length in each image as a scale. For instance, if a 100 mm reference marker or a ruler is visible, we can compute an empirical pixels-per-mm. This is a sanity check: if method (a) is accurate, the derived scale from (b) will match to within ~0.1%. We might include a small printed scale bar (100 mm long) in the image; after processing, if the bar doesn’t measure ~100 mm ±0.5 mm, the system flags a calibration drift. In initial tests, we expect <0.2% scale error (e.g. 500 mm could measure 499 mm) which we can correct in software if systematic. The calibration module runs a short routine each day: the operator places a calibration board (with ArUco markers or a checker) on the bench and triggers a “calibration check” image. The software re-computes intrinsics (if needed) or at least verifies extrinsic alignment by measuring known distances on the board. If any error exceeds a threshold (e.g. >0.5 mm over 300 mm, or homography reprojection error >0.5 px), the system will prompt re-calibration or alert the team.

Re-calibration Cadence and Drift Handling: Because the camera is fixed and environment stable, full intrinsic re-calibration is needed only if the camera or lens is adjusted. Extrinsic (homography) calibration may be redone more frequently if there’s potential drift (e.g. if the camera rig can be knocked or thermal expansion in mounting). As a precaution, we schedule an automatic homography check every 1000 garments or weekly. This uses the permanent corner markers: the software compares the current marker positions against their initial calibrated positions in pixels. Any shift indicates either camera movement or marker movement. For example, a 5 px marker shift would equate to ~1.5 mm error – exceeding our tolerance. In such case, the system can auto-compute a new homography (since the marker world positions are known) and update the calibration on the fly, then log this event. All calibration events (with date, new parameters, and perhaps a test measurement result) are logged to JSON (with fields like "homography": [[...],[...],[...]], "updated": "2025-10-07T09:45Z", "check_error_mm": 0.3). The JSON file could also maintain a history of RMS errors or scale factors for trend analysis.

We also incorporate fail-fast tests: for each image, the presence and correctness of at least two reference markers are confirmed. If a marker is missing (e.g. covered by a garment), or the measured distance between markers deviates beyond a small epsilon, the system aborts measurement for that piece and notifies the operator (e.g. “Calibration markers not detected – please clear corners or recalibrate”). This ensures we never output measurements from an uncalibrated perspective. In summary, our calibration suite ensures that pixel measurements are reliably mapped to real units with overall scale uncertainty on the order of 0.1–0.2% (well below the 0.3% tolerance target), by combining classic camera calibration
mdpi.com
 with robust planar homography and continuous verification.

3. Imaging Protocol

Operator Workflow (Step-by-Step): The process is designed to be simple and quick, on the order of tens of seconds per garment, to achieve ~300–600 pieces/day throughput. A typical workflow:

Prep and Place: The operator ensures the bench is clear of debris and that the lighting is on and warmed up (LEDs stabilized to avoid intensity drift). If switching garment color drastically (e.g. a run of black garments after white), they may swap the background mat or adjust exposure presets (though our auto-settings handle moderate changes). The operator lays the garment front-side up (unless back measurements are needed; we assume consistent side for now) on the bench, roughly centered under the camera. They smooth out the garment, aligning it to the reference guides – for a T-shirt, they’ll align the center front roughly to a midline guide and the shoulder line horizontally. They use their hands or provided squeegee tools to eliminate major wrinkles, especially around measurement points (chest, waist). Key parts like sleeves and hem are pulled straight. If needed, magnets/weights are placed at corners: e.g. at the sleeve ends and bottom hem corners of a shirt, or at pant hems and waist sides, to hold them taut. The operator also places the reference object if any (though we have fixed markers, an optional small calibration ruler could be placed for additional verification). This entire placement step is about ~10–15 seconds (for a simple garment) — far faster than manual measuring which takes ~5 minutes per piece
spesa.org
.

Capture: The operator triggers the camera via a foot pedal or keyboard (to avoid shaking the rig). The Raspberry Pi (or attached trigger system) captures a full-resolution image (e.g. 16 MP) with locked camera settings optimized for the lighting. We disable any auto-exposure or auto-whitebalance once the system is configured, to ensure consistency. The camera settings are pre-determined: for instance, shutter 1/250 s, ISO 200, analog gain 1.0, daylight white balance (or a custom white balance using a gray card at setup). We also turn off any camera auto-sharpening or compression that could alter measurements – instead we capture RAW or high-quality JPEG and do sharpening in software if needed (to avoid non-linear pixel effects). The Pi camera can stream a low-res preview to the operator’s screen to assist placement, but uses full-res for analysis. After capture, the high-res image is immediately transmitted to the processing server (the powerful GPU machine) via Gigabit Ethernet or WiFi. This transfer is done in the background (~0.5–1 s for a JPEG image), allowing the operator to start preparing the next garment if needed.

Auto-QC Overlay: As soon as the image is processed (see Vision Pipeline below), the system returns a visual overlay to the operator’s station. This overlay is the original garment image (or a rectified top-down view) with measurement lines and landmarks drawn (in a distinct color, e.g. green) and dimension labels (in mm) next to each measured segment. The operator can glance at this overlay on a screen to verify that, for example, the measured lines correspond to the correct points (chest line across the underarms, etc.) and that no part of the garment was missed. This serves as immediate QA – if the overlay shows a sleeve not detected or a warped contour, the operator can re-adjust the garment and retake the photo before accepting the data. The overlay also highlights any out-of-tolerance dimensions in red. For instance, if chest width spec was 500 mm ± 3 mm and the measured is 508 mm, that line might be labeled in red “508 mm (Fail)” to alert the operator. This happens within ~2–3 seconds of capture (the server GPU accelerates the analysis, trading hardware cost for speed since accuracy is priority and we want minimal slow-down on the line)
spesa.org
. An average cycle might be ~10 s of handling + 2 s processing – easily meeting the 6 s fully-automated measurement machine benchmark
spesa.org
 when considering human steps in parallel.

Record & Next: The measured data (all key dimensions, plus images) are automatically logged in the SaaS dashboard database. The operator doesn’t need to manually input anything – eliminating transcription errors
spesa.org
. If the garment passes all measurements, it’s marked Pass and the system can optionally print a label or update the QC report. If it fails a measurement, the dashboard flags it and the operator might set it aside for re-check or rejection. The operator then removes the garment, places the next one, and repeats.

Camera Settings and Image Quality: We fine-tune camera parameters to ensure robust image analysis:

Exposure: We aim for a histogram where the background is low (near black) and the garment midtones are well-exposed without clipping. The ideal histogram might have the background around 5–10% intensity and garment around 50–80%, leaving headroom for white areas. We achieve this via manual exposure: for example, 1/250 s at f/4, ISO 200 under ~3000 lux lighting yields a medium-gray garment (reflectance ~20%) exposing at ~128 out of 255 in the image – good contrast while avoiding saturation on white garments (which would hit ~240 out of 255). We also enable anti-flicker 50 Hz mode on the Pi (or simply use continuous DC light) to avoid any banding in images.

White Balance: Locked to a known setting (e.g. 5000 K daylight) or calibrated using a neutral gray target under our lights. This prevents shifts in color that could affect color-based segmentation (if we ever use color cues to separate garment from background).

Focus & Sharpness: The lens is focused for the bench plane. We test focus by placing a high-contrast object (like a printed text) at each corner of the area and adjusting until all corners are acceptably sharp. Depth of field at f/4 covers a few cm above and below the plane, which is enough given garments are flat (even buttons are just a few mm height). We disable in-camera sharpening to avoid artifacts on edges; instead, if needed, we apply a slight unsharp mask in preprocessing to boost edge clarity for segmentation. The camera’s MTF (Modulation Transfer Function) should be high enough to resolve ~1 px details (given ~0.3 mm/px, that’s ~0.3 mm detail). We set a focus target such that edges of a resolution chart have at least 50% contrast at 2 px frequency – this ensures sub-mm edge precision.

Motion Blur Check: Since the shutter is fast (1/250), blur is minimal. But as a safety, after capture we compute a focus/blurry metric. We use the variance of Laplacian or similar focus measure on the image. For example, if the variance of the Laplacian is below a threshold (say <1000 in our image scale – determined empirically), it indicates a blurry image (could be out of focus or camera shake). The system would then warn “Image possibly blurred, please retake.” In testing, we adjust this threshold so that a sharp image of a garment yields a high variance (lots of high-frequency edge content, especially at garment edges and textures), whereas a blurred one (out of focus or moved) drops significantly. This ensures we don’t proceed with a low-quality image that could skew measurements.

Anti-Noise: With good lighting and low ISO, noise is minimal. We avoid high ISO (>400) since noise could cause false edges in segmentation. If more exposure is needed, we prefer to increase LED intensity rather than ISO, to preserve SNR. The Pi 5 camera allows controlling analog gain and digital gain separately; we keep analog gain <=4×.

Triggering and Sync: The system is capable of strobe if needed – e.g. we could flash the lights at capture to allow even faster shutter (1/1000 s) without increasing continuous brightness (useful if motion was an issue). For now, continuous lighting suffices. The capture is triggered either by the software (once garment detected in preview) or by operator input, depending on UI design.

Target Image Quality and Examples: We expect images ~4608×3472 px (16 MP). A typical t-shirt might occupy ~3000 px across in the image (if chest ~500 mm, that’s ~1670 px after distortion correction, plus margins). That gives ample resolution for sub-2 mm accuracy (1 mm ~ 2–4 px). For quality control, we could overlay a semi-transparent live edge detection in preview to help the operator see if the garment edges are clearly visible (especially for dark on dark). If the system detects e.g. a black hoodie on the dark background and edge contrast is low, it might suggest turning on an auxiliary light or placing a light contrasting sheet under the garment edges (though cross-lighting should suffice normally). These protocols, combined with the stable hardware, ensure consistent high-quality images entering the vision pipeline every time.

4. Vision Pipeline (Algorithms + Pseudocode)

Once an image is captured and calibrated, the software pipeline processes it to extract the garment outline, key landmarks, and measurements. Below we outline each stage and provide pseudocode snippets using OpenCV and NumPy (all runnable on the server with GPU acceleration where applicable, but kept to basic libraries for clarity):

Preprocessing

a. Undistortion: First, we correct lens distortion using the intrinsic calibration.

# Load calibration
calib = json.load(open("calibration.json"))
mtx = np.array(calib["camera_matrix"])
dist = np.array(calib["dist_coeff"])
# Undistort image
undistorted = cv2.undistort(image, mtx, dist, None, mtx)


This produces an image free of barrel distortion, where straight lines remain straight – crucial for accurate edge detection.

b. Perspective Rectification: Next, we warp the image to an orthographic view using the homography H obtained in calibration. We define an output canvas in real-world units (for example, 1200 mm × 800 mm area at 1 px/mm scale, or we can use a scaling like 2 px/mm for higher detail). We apply:

H = np.array(calib["homography"])
# Define output size in pixels covering the bench area
out_w, out_h = 1200, 800  # 1 px = 1 mm for simplicity
topdown = cv2.warpPerspective(undistorted, H, (out_w, out_h))


Now topdown is a bird’s-eye view image where the garment is undistorted and true to scale: distances in pixels correspond directly to millimeters. (We will still maintain the original image for overlay, but do processing on the rectified image for ease of measurement math.)

If memory or speed is a concern with full 16 MP warping, we can downsample moderately (e.g. to 300 dpi equivalent ~ about 5 px/mm, meaning ~6000×4000 px canvas for 1200×800 mm – but 1 px/mm (1200×800) might be too low resolution, so in practice we might use 2 px/mm = 2400×1600 output, balancing detail vs. size). Regardless of scale, all measurements will be converted to mm using the known scale factor.

c. Denoising and Normalization: Although our imaging is clean, we apply a gentle denoise to remove any speckle that could interfere with thresholding. A bilateral filter or median blur (kernel ~3 px) is effective as it preserves edges:

gray = cv2.cvtColor(topdown, cv2.COLOR_BGR2GRAY)
gray = cv2.medianBlur(gray, 3)


We convert to grayscale since shape segmentation doesn’t need color (except when separating similar-colored garment/background; more on that in Edge Cases). We also normalize lighting if needed: if there’s any slight vignetting or uneven lighting, we could do a background subtraction by modeling the background intensity. For example, we can assume that areas outside the garment (background) should ideally be uniform; we can sample the corners of the image (which should be background only) to estimate any gradient, or use a large morphological opening to estimate the illumination field and divide it out. In practice, our lighting setup yields sufficiently uniform background, so a simple global normalization (e.g. histogram equalization or scaling) suffices. We ensure the background remains darker than the garment via exposure tuning, so we often do not need complex shading correction.

d. Shadow suppression: Raking light can introduce shadows inside the garment region (e.g. along a fold). To avoid misidentifying shadows as edges, we can apply an adaptive illumination correction: e.g., use a rolling-ball algorithm (common in image analysis) to separate shading from reflectance. Simplistically, we can take a large kernel (like 50 px) median blur of the grayscale to get a smooth illumination image, then do gray = cv2.divide(gray, illum) to flatten lighting. This is optional; we will also handle shadows in segmentation logic by focusing on outer contours.

Segmentation (Garment vs Background)

Now we separate the garment from the background. Because we engineered the background to contrast the garment
mdpi.com
, we can use a combination of thresholding and edge detection:

a. Initial Mask via Color/Intensity Threshold: We know the background is dark matte and the garment is typically lighter (or at least differently colored). A good starting point is Otsu’s threshold on the grayscale:

_, mask0 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)


This will choose an optimal intensity cut separating the darker background (likely mode near 0) from brighter foreground. However, if the garment is black or very dark, Otsu could fail (it might threshold everything as background). In such cases, we can incorporate color: since background is uniform gray, a colored or textured garment will differ in chroma. We convert to HSV or Lab color space and threshold on saturation or a/b channels to catch colored garments on gray background. For a black garment on black background (worst case), we rely on edge detection next.

b. Edge-based Mask Refinement: We run Canny edge detection to find the outline:

edges = cv2.Canny(gray, 50, 150)  # tune thresholds as needed


This will produce a crisp outline at the garment boundary, thanks to the lighting. We then fill the interior. One method: take the largest closed contour from these edges. We find contours on the edge map:

contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
contours = sorted(contours, key=cv2.contourArea, reverse=True)
main_contour = contours[0]  # largest contour by area


We assume the garment forms the largest contiguous contour (which should hold if background is clear and the garment isn’t highly disjoint). We then create a mask from that contour:

mask_edge = np.zeros_like(gray, dtype=np.uint8)
cv2.drawContours(mask_edge, [main_contour], -1, color=255, thickness=cv2.FILLED)


Now mask_edge is a filled silhouette of the garment as determined by edges. We combine this with the threshold mask: mask = mask0 OR mask_edge as a binary mask of the garment. We then clean it with morphological operations: a closing (e.g. cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel=5)) to fill small gaps, and an opening to remove noise speckles not connected to the main region. The result is a binary mask where 1 = garment, 0 = background.

For more complex situations (dark on dark, or very similar tones), we have an alternative segmentation mode: GrabCut or a lightweight CNN. GrabCut (graph-cut segmentation) can use an initialization rectangle around the garment. Since we know the garment is roughly centered and takes up a large portion, we can initialize GrabCut with the entire image and mark a small border around edges as “background” (since beyond the garment it’s definitely background) and perhaps the center as “foreground”. This can refine the mask especially around fuzzy edges (like frills or lace). However, in our controlled setup, simple threshold + contour is typically sufficient and faster.

If we had to segment via ML, we could deploy a small U-Net or DeepLab model pre-trained on fashion images to get a mask. But given the project timeline (<6 weeks), we favor classical methods first, with possibly using ML if needed for edge cases (discussed later). We ensure the mask covers all garment pixels and only the garment. If there are holes (like a neck hole or open jacket front), those will show up as interior contours – we can decide if we want to treat them as “not garment”. Usually, for measurement, we care about the outer silhouette. So if a neck hole is detected, we can fill it in the mask (since the tape measure would measure across that gap in a real scenario if laid flat). However, for some measurements (like neck circumference) we might actually want that inner contour – but those are typically secondary. For now, we fill any small holes in the mask by another morphology fill or by analyzing contour hierarchy (fill any child contours whose area is below a threshold like <20% of main area).

c. Contour Extraction: From the final mask, we extract the precise garment contour:

contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_L1)
# (TC89_L1 is a Teh-Chin chain approx which can give smoother output)
garment_contour = contours[0]


We use a contour approximation technique to reduce noise: e.g. cv2.approxPolyDP(garment_contour, epsilon=2.0, True) which will simplify the contour with a tolerance of 2 pixels (~2 mm). We also apply a custom smoothing: since garments have relatively smooth curves (except at corners like armpit, shoulder), we can fit a spline. One approach is to fit a B-spline through the contour points or perform moving average on the coordinate sequence. We must be careful not to oversmooth critical points (like corners). A pragmatic approach: use a Gaussian filter on the sequence of points (treat x and y as separate sequences around the perimeter). We might apply a sigma of ~1–2 pixels, which removes jaggies from thresholding but retains overall shape.

The result is our final outer boundary of the garment in image coordinates (which, recall, is rectified to metric space). Each point in this contour is effectively at some (x_mm, y_mm) coordinate on the garment plane.

Contour Analysis & Landmark Detection

With the contour coordinates, we proceed to identify key landmarks required for measurements: HPS points, sleeve ends, underarm points, etc. We incorporate both algorithmic rules and heuristics (and can fall back on symmetry or defaults if something is ambiguous).

Let’s define some coordinate shorthand: because the image is rectified, the y-axis is aligned with garment length (top to bottom) and x-axis with garment width (left to right), assuming the garment was roughly aligned. Even if not perfectly aligned, since we measure distances between specific landmarks, slight rotation won’t affect distance but we might need to find directions (like “across chest” means a horizontal measure across the body width). We may align the contour by principal axes if needed: e.g., for analysis, rotate the contour so that the longest dimension aligns with horizontal if we think that corresponds to width. However, because garments like pants have length >> width, principal axis would align vertically for pants, horizontally for shirts – which matches intuitive orientation. So we might not need to rotate if we can infer orientation from shape (which we can, using bounding box aspect ratio).

a. Basic Extrema: We find extreme points as a starting reference:

xs = garment_contour[:,0,0]; ys = garment_contour[:,0,1]
left_idx = np.argmin(xs); right_idx = np.argmax(xs)
top_idx = np.argmin(ys); bottom_idx = np.argmax(ys)
leftmost = garment_contour[left_idx][0]; rightmost = garment_contour[right_idx][0]
topmost = garment_contour[top_idx][0]; bottommost = garment_contour[bottom_idx][0]


These give the outer bounds of the garment. For example, topmost might be the tip of a collar or shoulder. bottommost is typically the bottom hem midpoint (if the garment is oriented straight). For symmetric garments, leftmost and rightmost are at the sleeve or side seam extremities.

b. High-Point Shoulder (HPS): The HPS is where shoulder seam meets neck. On a typical shirt, this is slightly inward from the shoulder edge. However, on the silhouette, a reasonable proxy for HPS is the point at the top of the shoulder curve before it dips into the neck. We find it by looking for local maxima near the top on each side. Concretely, we can do this: take the upper portion of the contour (say all points with y within 5% of the topmost Y). Among these, find the two clusters on left and right. The highest points on each cluster are roughly the shoulder-high points. Another approach: find the neck concavity and shoulder convexity intersection. We can leverage curvature: compute the curvature (second derivative) along the contour; HPS will often correspond to a point of high curvature on the upper outline (transition from neck to shoulder line). Given time constraints, a simpler heuristic: split the contour into left and right halves by the centroid or by the x-midpoint. Then for each half, find the point with minimum y (highest) – that is the HPS on that side. This works provided the neckline doesn’t have a point higher than the shoulder. In many crewneck shirts, the shoulder seam at neck is actually the highest point, slightly higher than the center of the collar. If a collar is very protruding (like a collar on a button shirt might stick up), we might need to adjust, but assuming garment is laid such that collar is flat, the HPS corners are highest.

Thus we get HPS_left and HPS_right. We will use (probably) the left HPS as reference for length measurement (or both and average if needed).

c. Shoulder Points (Shoulder Width): Shoulder width is measured between the shoulder “tips” – where sleeve attaches to body at the upper arm. On the contour, these are the points at the top of each sleeve outer edge. Often they coincide with the local maxima of x (for left shoulder, a local minimum x at top region; for right, local maximum x at top region). We can find them by scanning from the HPS along the contour towards the sleeve. A more direct method: find the point on each side contour that is farthest out (leftmost on left side, rightmost on right side) within some range of the top. For example, restrict to points with y within, say, 15% from top, then take min x (left side) and max x (right side) among those. That will yield something near the sleeve upper edge. That could be slightly below the actual shoulder seam if the shoulder slopes downward. Alternatively, we could define shoulder width as the straight line between left and right HPS – but that’s usually smaller than the actual shoulder seam length. Many spec sheets define shoulder width across back between sleeve seams. In our case, since we may not see the seam, we approximate it as the distance between the outer contour points at the upper arm. Let’s call these shoulder_left and shoulder_right.

We can refine by looking at curvature: the sleeve-body junction often has a concave corner (from the body side) and convex corner (from the sleeve side). We could find where the convex hull of the contour differs from the contour – likely around the armhole. But simpler: since the top part of a shirt is roughly horizontal, the shoulder points can be identified as the points on the contour with the maximum x-distance on the top quarter of the garment height.

d. Armhole/Underarm Points (Chest width): The chest width is typically measured just below the armholes
designersnexus.com
. On the contour, the “underarm” points are where the sleeve opening meets the body side seam – a distinct concave corner under the arm. This often appears as a sharp inward notch on each side of the contour. We can find them via convexity defects: if we compute the convex hull of the contour and look at points where the actual contour falls inside the hull, the deepest such indentation on each side is the armhole (underarm). Using OpenCV’s cv2.convexityDefects on the contour can identify these points. For example:

hull = cv2.convexHull(garment_contour, returnPoints=False)
defects = cv2.convexityDefects(garment_contour, hull)
underarm_left = None; underarm_right = None
max_depth_left = 0; max_depth_right = 0
for i in range(defects.shape[0]):
    start_idx, end_idx, far_idx, depth = defects[i,0]
    far_point = garment_contour[far_idx][0]
    if far_point[1] < centroid_y:  # upper half of garment
        continue  # underarm will be roughly mid-height, skip top and bottom defects
    # left side vs right side based on x position relative to center
    if far_point[0] < centroid_x and depth > max_depth_left:
        max_depth_left = depth; underarm_left = far_point
    if far_point[0] > centroid_x and depth > max_depth_right:
        max_depth_right = depth; underarm_right = far_point


Convexity defect far_point gives the deepest inward point between a start and end on the hull – which for a garment is often the underarm. We might get the cuff as defect too, but restricting by y (underarm tends to be around mid-high of garment, not near bottom or extreme top) helps. Once we have underarm_left and underarm_right, we compute Chest Width as the horizontal distance between them. Given the garment is rectified, this is just abs(underarm_right.x - underarm_left.x) in mm (since 1 px = 1 mm in our rectified image). We will refine this measure by possibly adjusting vertically: many spec conventions measure chest “1 inch below armhole”
designersnexus.com
. We could thus measure at a point a fixed offset below the underarm. Alternatively, since we have the actual underarm points, measuring straight between them is effectively the minimum width at that juncture, which corresponds well to how chest is defined. We can easily adjust to spec: for example, measure at 25 mm below those points if needed (we have full contour, so we can just find the intersection of the contour with a horizontal line 25 mm below underarm). But for now, underarm-to-underarm is our chest measurement line.

e. Sleeves and Cuffs: For sleeve length, we need the point at the shoulder/sleeve seam (which could be the same as shoulder_left for left sleeve) and the cuff end point. The cuff point is at the end of the sleeve, which on the contour is likely the farthest point from the shoulder along that sleeve. Alternatively, it’s the lowest point on the sleeve’s end. We can find it by looking at the contour on the sleeve side: e.g. for left sleeve, consider points left of the body (x much less than centroid_x). The bottom-most among those might be the sleeve end. But if the garment has a long sleeve, the cuff might not be simply bottom-most globally (because the torso bottom might be lower). For a long-sleeve shirt, the sleeve cuff is typically lower than the body hem for a laid-out shirt front view? Actually, if arms are spread out to sides, cuffs might be at similar vertical level to the hem or higher, depending on angle laid. We may instruct to place sleeves such that they are straight out or slightly down.

We can identify sleeve cuffs by curvature too: the cuff is an open end, which appears as a line or semi-circle on the contour. One robust way: separate the contour into logical sections. We could find the “armpit” points (underarm we have) and the shoulder points; these divide the contour of the shirt’s one side into: shoulder to underarm (armhole curve on body), then underarm to shoulder along the sleeve edge. The sleeve edge from underarm to presumably top of sleeve and back to shoulder tip – within that, the farthest point (in geodesic distance from the underarm) is the cuff end. Alternatively, we can just find the contour point with maximum distance from the underarm point along that section.

A simpler approach: take the left half of the contour (split by centroid_x or midline) and find the point with the largest y (lowest) – that could either be bottom hem corner or sleeve cuff, whichever is lower. If the sleeve is angled down it might be lower than the hem. We can differentiate by x coordinate: the sleeve cuff on left will be significantly leftwards (small x), whereas the bottom hem corner will be nearer the middle x. So maybe find the lowest point with x less than some percentile (say < 20th percentile of x). That likely yields the sleeve cuff. Similarly for right.

Thus, define cuff_left (x very low, y max among those) and cuff_right (x very high, y max). With hoodies or long sleeves, that should catch the cuffs.

Once we have shoulder_left and cuff_left, we measure Sleeve Length. This could be a straight line distance, but more properly it should follow the sleeve curve (especially if sleeve is slightly bent). To measure along the sleeve centerline, one approach: extract the contour section from shoulder to cuff along the top of sleeve and from cuff back to underarm along bottom of sleeve. But that’s complicated. For small curvature, a straight line from shoulder to cuff suffices; difference is negligible at our tolerance. However, our spec target is ±2 mm, so if the sleeve is angled 45°, the straight line vs along sleeve (which goes out and down) might differ by maybe a few mm. Perhaps we do a polyline measure: break it into two segments – from shoulder to underarm along armhole (not needed) or from shoulder to cuff through elbow. But since garment is flat, usually sleeve is either straight or gently curved.

A practical solution: measure along the outer edge of the sleeve from shoulder point to cuff. We can do that by traversing the contour between those points. We know the indices in the contour array for shoulder_left and cuff_left (we can find their indices when we identified them). We ensure we take the path along the sleeve edge, not the body side. Since the contour is continuous, we need to decide direction: presumably, going from shoulder_left through the sleeve outer edge to cuff_left is one direction, and going the other way around goes via neckline and body which is wrong. We can determine that the arc length along contour from shoulder to cuff in one direction will be much smaller (the sleeve route) than the entire rest of the garment, so take the shorter path. Summing distances along those contour segments gives sleeve length along the edge. If we wanted the midline of sleeve, we could subtract half the cuff width, but that’s splitting hairs; spec typically measures a straight line on top of sleeve from armhole seam to cuff, which is effectively the outer edge length if laid flat with minor difference if sleeve is tapered.

So we’ll compute arc length between shoulder and cuff on the contour for each side. That yields Left Sleeve Length and Right Sleeve Length. We might output both to see if symmetry is off by more than a tolerance (the QC output even listed sleeve length symmetry
spesa.org
). In an ideal garment, they should be equal; our system can detect if one sleeve was folded or something if they differ significantly.

f. Hem and Length: For body length (HPS to hem): We use the HPS (say left HPS) we found and find the bottom hem directly below it. If the garment is roughly aligned, the “directly below” means same x coordinate as HPS, down to the contour at bottom. But if garment is slightly rotated, the straight down might not hit the hem at the same x. It might be safer to measure HPS to bottom in vertical distance. Typically, spec measures length along the center front or back
designersnexus.com
 or from HPS vertically. Actually, spec often says “HPS to Bottom” as a straight-line distance following the garment, not necessarily perpendicular to hem if hem is curved. Usually it’s taken along the garment front (which in our top-down is vertical). So we can simply take the y-coordinate difference between HPS and the lowest point of the hem. But HPS is near side of neck, so dropping directly might miss if the hem curves (like shirt tails). Actually, for accuracy: measure from HPS point to bottom hem along that same side (imagine a tape measure held at HPS and going straight down). If the hem is roughly horizontal, this is just vertical difference (y_bottom - y_HPS). If the hem is shaped (like a shirttail, lower in middle), then which point do we take? Likely the spec measure would be at the same point of garment (e.g. front length at side vs center can differ). Typically, they measure front length at center front or at HPS depending on tech pack. The user question specifically lists “length HPS” – that implies the measurement from HPS straight down to hem at front. Often that is done at the HPS point itself (the tape goes from that shoulder point to bottom edge directly, which would be at an angle if the HPS is not above bottom edge due to curved hem). But likely they mean vertical length.

Given potential confusion, we can calculate both and decide: front-center length (from a point at neckline center straight down to hem) and HPS length (from HPS to hem diagonal). However, since they explicitly say HPS, we’ll do that: measure the distance from the left HPS to the bottom hem directly below it (which might not be exactly bottommost point if the hem curves up at sides, but we assume relatively straight hem).

Implementation: find bottom_left_hem – the intersection of the contour on left half with the vertical line from HPS. Since we rectified perspective, vertical in image corresponds to vertical in garment. We can simply take same x as HPS_left and find the contour point at that x (the bottom). E.g., scan the contour for the point with the same x coordinate (within a few px) that has max y. Or just project: since our contour is filled, we could do a ray-cast: iterate y from HPS.y downwards until we hit mask edge. Simpler: take the mask image and look at the column corresponding to HPS.x and find the lowest ‘on’ pixel in that column. That is the hem point under HPS. That yields a length in pixels.

Alternatively, measure HPS to bottommost point (which might be center if shirt has a dip). But I think HPS to straight bottom at that side is fine, given many shirts have even hem.

Thus Length_HPS = y_bottom_at_HPS - y_HPS (converted to mm). If the garment had a shaped hem (like a curved shirt tail), we might be under-measuring slightly if HPS is at shoulder and hem dips lower at center. But the term “HPS to hem” usually implies measure along a line straight down from HPS, not following garment shape (some tech packs even say measure at center front if needed).

We can clarify in documentation: measure from HPS vertically to level of bottom hem (if hem not straight, measure to the lowest point of front hem).

g. Other Points: For Waist and Hip widths (for shirts/dresses): If specified, we need to measure horizontal width at defined positions down from HPS
designersnexus.com
. For example, if we know the waist is at 400 mm from HPS on a particular garment type, we measure the width across the garment at that y level. We can determine these positions either by a percentage of total length (e.g. waist ~50% down in many dresses) or by using pattern knowledge (the spec might provide “Waist is 300 mm below HPS in size M” – perhaps not in this problem, but it’s implied "waist, hip" are needed). For a general solution, we could attempt to find natural pinch points: e.g. in a fit-and-flare dress, the waist is the narrowest part of contour below chest. We could find the minimum width along vertical scanlines. But for now, since garments include pants and skirts, likely waist and hip refer to those. Let’s address pants:

For Pants/Skirts:

Waist width: The top of the garment. We detect it by the top contour on left and right at the waistband. If pants are laid with waistband aligned horizontally, the top-left and top-right corners of the contour are the waist corners. The distance between them is waist width (half waist if spec is half). If the waistband is curved, we measure straight across width. Implementation: we can find contour points at the very top on each side (maybe previously found leftmost and rightmost might have been at cuff, not relevant here; rather, for pants, topmost would be top of waistband if oriented normally). But likely the pants might be placed rotated so that the outseam runs vertical in the image, so waist might not be perfectly horizontal. We can simply measure distance between the two upper corners of the contour. Or find the leftmost and rightmost points in the upper 5% of the height.

Hip width: Typically ~20 cm below the waist for women’s, or the widest point below waist. We could find it by scanning down from waist until contour width stops increasing, often the max width of pants above the crotch is at hip. Or use a standard measure: e.g. 200 mm below waist. For a general solution, we might compute horizontal widths at many vertical slices and pick the maximum between waist and crotch as hip width. That will handle different sizes.

Outseam length: For pants, this is from top of waist (at side) to bottom hem (ankle) along the side seam. On the contour, the side seam corresponds to the outermost left and right edges of the pants. We can measure from the top of that side to bottom along the contour. But easier: since we have rectified coordinates, outseam is essentially the full height of the pants if laid straight. Actually, if the pants are laid with both legs side by side, outseam is just the y-difference between waist and hem on one side. We can take the left side seam: e.g. distance between top-left waist corner and bottom-left leg hem corner (straight line or along contour if there’s curvature at hip, but since pants side seam might curve slightly at hip, following contour is more accurate). We likely measure straight line for simplicity – error negligible if slight curve.

Inseam length: This runs from crotch to ankle along inner leg seam
designersnexus.com
. The crotch point can be identified as the point where the two legs meet – typically a sharp inward corner in the contour at the center bottom of the crotch arch. We can find the crotch point by looking for the highest point (lowest y value) in the interior of the contour between the legs. If pants are laid with one leg on each side (slight gap or touching at crotch), the crotch might not be on the outer contour at all (if legs slightly separated, the crotch is an interior point). If they’re touching, the contour goes around both legs so the crotch might be a concave defect on the contour interior. Either way, we can detect it: perhaps by finding the convexity defect at the bottom (like between legs). Yes, convexity defects can catch the crotch as a deep indent if the legs form a concave shape at that junction.

Alternatively, since we may not trust convexity defect if legs closed, we could instruct to slightly separate legs at crotch for clarity. If not, a two-view would help but we prefer one view. Let’s assume we can identify crotch. Once we have crotch and the ankle (hem end) for that leg (say left leg inner hem point), we measure along the inner seam. This likely requires following the contour from crotch along inner leg to hem. This is similar to sleeve logic: follow contour path for inseam. Because inseam is definitely a curved path (it curves around thigh), a straight line underestimates length by a noticeable amount (could be ~10 mm for big pants). So we do want to follow the actual seam curve. The contour representing inner seam will start at crotch, go down inside of leg to ankle. We gather those points and sum distances (polyline length). That gives Inseam.

We would do it for left and right leg; likely they want just one (they listed inseam and outseam singular, assuming both legs same, so maybe measure one side).

We should also measure waist to waist across (just waist width, done), hip width as needed similarly by either formula or scanning for max width around crotch level.

h. Landmark summary: To recap, the landmarks we identify (with fallback logic in comments):

HPS_left and HPS_right: highest points on each shoulder side (fallback: use topmost on each half of contour).

shoulder_left & shoulder_right: outer shoulder/sleeve edge points (fallback: points of max X extent near top).

underarm_left & underarm_right: lowest points of armhole curve (can be via convexity defect or min Y around upper-mid region).

cuff_left & cuff_right: sleeve end points (fallback: bottom-most on each side beyond certain X).

hem_left & hem_right: bottom corners of shirt (which might coincide with leftmost and rightmost bottom points).

bottommost: lowest point (likely center if hem is even).

For pants: waist_left, waist_right (top corners), crotch: inner crotch, ankle_left, ankle_right: bottom of legs on inner side or outer side as needed.

We also compute the centroid or use known splits to differentiate left vs right side.

If any of these fail (e.g., convexityDefects might not find underarm if garment shape is convex there, like a drop-shoulder with no sharp pit), we have fallback: chest width can then be measured by simply taking width at 50% of height. Not perfect, but many garments (like a poncho with no defined armhole) we would measure width at half height as chest. We can also ask operator to specify garment type to adjust logic (e.g. “raglan sleeve mode” might skip looking for a corner and instead measure between mid-arm curves).

Measurement Computation

Using the landmarks, we compute each required spec dimension. All distances are computed in millimeters, using either our known scale (1 px = 1 mm in rectified image) or by transforming pixel differences via homography (which effectively we already did by warping).

For clarity, assume 1 px = 1 mm after rectification below:

Chest Width: Horizontal distance between underarm points. If underarm points are $(x_{uaL}, y_{uaL})$ and $(x_{uaR}, y_{uaR})$, then

ChestWidth
=
∣
𝑥
𝑢
𝑎
𝑅
−
𝑥
𝑢
𝑎
𝐿
∣
.
ChestWidth=∣x
uaR
	​

−x
uaL
	​

∣.
We may also take an average of their y and ensure we measure exactly horizontally. If the underarm points are slightly mislevel (within a few mm), it’s usually because of asymmetry or minor placement tilt. We could average their y and sample the contour or mask at that average y for left and right edges to get a perfectly horizontal measure at that level. But given tolerances, using the direct points is fine. We output chest width as, say, 520 mm.

Body Length (HPS to Hem): We find the vertical distance from HPS to the bottom hem directly below it. If HPS_left = (x_hps, y_hps) and bottom hem directly below is (x_hps, y_bottom), then
\text{HPS_Length} = |y_bottom - y_hps|.
We find y_bottom by scanning the mask at column x_hps as described. (If hem is uneven, possibly take the max y of that column or a small neighborhood). This might yield, say, 700 mm for a hoodie.

Shoulder Width: Distance between shoulder points (approx seam to seam). If we identified shoulder_left (x_sl, y_sl) and shoulder_right (x_sr, y_sr), we compute the distance:

ShoulderWidth
=
(
𝑥
𝑠
𝑟
−
𝑥
𝑠
𝑙
)
2
+
(
𝑦
𝑠
𝑟
−
𝑦
𝑠
𝑙
)
2
.
ShoulderWidth=
(x
s
	​

r−x
s
	​

l)
2
+(y
s
	​

r−y
s
	​

l)
2
	​

.
Since ideally they’re nearly horizontal, this is roughly horizontal distance. If the image is well aligned, y difference is small. We could also project it horizontally if needed. Output e.g. 460 mm.

Sleeve Length: We calculate along contour. Suppose the contour indices from shoulder_left_idx to cuff_left_idx trace the outer sleeve. We compute arc length:

pts = garment_contour[shoulder_left_idx : cuff_left_idx + 1]  # slice along one direction
sleeve_len_left = 0.0
for i in range(len(pts)-1):
    dx = pts[i+1][0] - pts[i][0]
    dy = pts[i+1][1] - pts[i][1]
    sleeve_len_left += math.hypot(dx, dy)


If the contour array ordering doesn’t conveniently give that segment, we might need to reorder or choose the shorter path as mentioned. We do similarly for right sleeve. Result e.g. 620 mm. (For short sleeves, this will just measure a short distance.)

We also can compute Sleeve Opening (cuff width) if needed (distance between two points at the ends of the cuff on front and back side, but not requested explicitly except maybe indirectly in “cuff width symmetry” mentioned in the article snippet
spesa.org
).

Waist Width (tops or bottoms): For tops (if applicable), measure at a specified point or the narrowest. If we have a known spec point (say 300 mm down from HPS as waist for jackets), we take that y = y_hps + 300, then find left and right intersection of contour at that y. Because our contour is polygonal, we can find where it crosses that horizontal line. An easy way: take the mask and find min and max x at that y-row (since rectified, scanning a row gives garment edges). So:

y_waist = y_hps + 300
row = mask[int(y_waist), :]  # binary row
xs = np.where(row > 0)[0]
waist_width = xs.max() - xs.min()


That yields mm. For bottoms (pants/skirts), waist width is just top width: we can take xs of top few rows of mask and subtract. That would give waist band width flat (which is half waistband circumference physically).

Hip Width: For pants, either measure at 200 mm below waist or find max width in a region. We might do:

heights = range(int(y_top+50), int(y_crotch))  # skip very top and go to crotch
max_width = 0; hip_y = None
for yy in heights:
    xs = np.where(mask[yy, :] > 0)[0]
    width = xs.max() - xs.min() if xs.size>0 else 0
    if width > max_width:
        max_width = width; hip_y = yy
hip_width = max_width


Then hip_y indicates where that max occurred (just for info). This captures actual max width, which for human body correspond to hip typically. We ensure not to include a flared pant leg bottom which could be wider than hip – hence limit to above crotch.

Inseam: Having crotch point and ankle, measure along inner contour. Identify contour segment from crotch down inside leg to hem. We can find crotch by perhaps the point of contour that has minimal radius or something in crotch area. If the legs are separated, crotch might be two points (left and right crotch where each leg meets at center). If together, one point with a sharp angle. We might just manually pick by scanning bottom center upward until width exceeds some threshold. Actually, if pants legs are together up to some point, the point they join is crotch. We can detect where the binary mask splits into two separate blobs if we were to cut at that row. But given complexity, for initial pipeline, possibly require operator to slightly offset legs or rely on the convexity defect at crotch.

Once crotch is found, we proceed similarly to sleeve: traverse contour from crotch to ankle along inner side. Or easier: since rectified, we could approximate inseam by vertical distance from crotch to ankle if pant is straight, but pants often have curvature at thigh so better follow contour. The difference might be a couple mm; we want accuracy so do contour length.

Compute arc length for inseam as:

# assume we got contour index for crotch and for inner ankle
pts = garment_contour[crotch_idx : ankle_idx + 1]
inseam = 0.0
for i in range(len(pts)-1):
    inseam += np.hypot(pts[i+1][0]-pts[i][0], pts[i+1][1]-pts[i][1])


If the contour indexing doesn’t directly slice that way (maybe goes the other direction around), we might need to reverse slice or split contour at crotch into two parts (one for each leg).

We’d do similarly for other leg if needed. But presumably inseam is same both, so one side is fine.

Outseam: This can be done as vertical distance from waist to hem along side. Or along contour outer side of leg. The outer contour from waist to ankle – we sum that if we want precise. But difference from straight line might be minor unless there’s a significant hip curve. Perhaps we sum if we want to be thorough. But if hip curves out by 1 cm, measuring straight vs along curve could differ ~ a few mm. We can afford to just do straight if time, but to be safe, do like inseam: follow outer contour from waist side point to hem side point. That yields outseam per side.

Others: Collar width or depth (not explicitly asked), but we have collar points possibly. If needed, measure neck opening as distance between HPS points or so. The user didn’t ask, but the article snippet listed collar width/depth – we likely skip since not requested.

We then compile all these measurements. We must remember to output them likely as both half-measurements (flat width) or full circumference? Typically, garment specs use flat measurements (half chest, etc.), which is what we are doing (since garment laid flat, chest width = half circumference). We will assume that’s what they want (since ±2 mm implies flat measure). So we provide those values.

All measurements are given with a tolerance (target ≤±2 mm). We will later attach an uncertainty to each.

Pseudocode Outline:

Below is a high-level pseudocode incorporating the above:

def process_garment_image(image):
    # 1. Calibration: undistort and rectify
    undist = cv2.undistort(image, camera_matrix, dist_coeff)
    topdown = cv2.warpPerspective(undist, H, (OUT_W, OUT_H))
    gray = cv2.cvtColor(topdown, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 3)

    # 2. Segmentation
    # Initial threshold mask
    _, mask_thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    # Edge mask
    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if len(contours)==0:
        raise Exception("No contour found - segmentation failed")
    main_contour = max(contours, key=cv2.contourArea)
    mask_edge = np.zeros_like(gray); cv2.drawContours(mask_edge, [main_contour], -1, 255, -1)
    # Combine and clean
    mask = cv2.bitwise_or(mask_thresh, mask_edge)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5,5), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3,3), np.uint8))
    # Final garment contour
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_L1)
    garment_contour = max(contours, key=cv2.contourArea)
    garment_contour = cv2.approxPolyDP(garment_contour, epsilon=2.0, closed=True)

    # 3. Landmark detection
    pts = garment_contour[:,0,:]  # Nx2 array of points
    # Basic extrema
    x = pts[:,0]; y = pts[:,1]
    left_idx = np.argmin(x); right_idx = np.argmax(x)
    top_idx = np.argmin(y); bottom_idx = np.argmax(y)
    leftmost = pts[left_idx]; rightmost = pts[right_idx]
    topmost = pts[top_idx]; bottommost = pts[bottom_idx]
    centroid_x = np.mean(x); centroid_y = np.mean(y)
    # HPS (highest on each half)
    left_half = pts[x < centroid_x]
    right_half = pts[x > centroid_x]
    HPS_left = left_half[np.argmin(left_half[:,1])]
    HPS_right = right_half[np.argmin(right_half[:,1])]
    # Shoulder points (max X near top)
    shoulder_left = left_half[np.argmax(left_half[:,0])]  # farthest outward on left half
    shoulder_right = right_half[np.argmin(right_half[:,0])] # farthest outward on right half (since right_half's min x relative to centroid, might invert logic)
    # Actually for right, farthest outward means max x:
    shoulder_right = right_half[np.argmax(right_half[:,0])]
    # Underarms via convexity defects
    hull = cv2.convexHull(garment_contour, returnPoints=False)
    defects = cv2.convexityDefects(garment_contour, hull)
    underarm_left = None; underarm_right = None
    if defects is not None:
        max_depth_L = 0; max_depth_R = 0
        for (s,e,f,d) in defects[:,0]:
            fx, fy = pts[f]
            if fy > centroid_y:  # likely lower half (skip bottom hem as that could also be a defect if big curve)
                # skip bottom area, we want near upper/mid
                pass
            if fx < centroid_x and d > max_depth_L:
                max_depth_L = d; underarm_left = (fx, fy)
            if fx > centroid_x and d > max_depth_R:
                max_depth_R = d; underarm_right = (fx, fy)
    if underarm_left is None or underarm_right is None:
        # Fallback: take point of max curvature on each side around mid-height
        # (For brevity, not implementing here - could approximate by scanning horizontal slices)
        underarm_left = pts[np.argmax(y * (x < centroid_x))]  # not exactly but assume left bottom of armhole
        underarm_right = pts[np.argmax(y * (x > centroid_x))]
    # Sleeve cuffs:
    # find lowest point far on left and far on right
    cuff_left = left_half[np.argmax(left_half[:,1])]
    cuff_right = right_half[np.argmax(right_half[:,1])]
    # Also ensure these are beyond a certain x distance: (optionally, check x quantile)

    # If pants vs shirt differentiation could go here, but assume detection logic per garment type
    # For demonstration, focusing on tops.
    
    # 4. Measurements
    measures = {}
    # Chest width
    cw = abs(underarm_right[0] - underarm_left[0])
    measures["ChestWidth"] = cw
    # HPS length
    col = int(HPS_left[0])
    # find bottom of garment at that column
    col_pixels = mask[:, col]
    y_bottom = np.max(np.where(col_pixels > 0))
    HPS_length = abs(y_bottom - HPS_left[1])
    measures["HPS_Length"] = HPS_length
    # Shoulder width (straight distance)
    shw = math.hypot(shoulder_right[0]-shoulder_left[0], shoulder_right[1]-shoulder_left[1])
    measures["ShoulderWidth"] = shw
    # Sleeve length (outer edge)
    # Find indices of shoulder_left and cuff_left in contour array
    idx_sl = np.argmin(np.linalg.norm(pts - shoulder_left, axis=1))
    idx_cl = np.argmin(np.linalg.norm(pts - cuff_left, axis=1))
    # Determine direction (assuming idx_sl < idx_cl for correct ordering; if not, swap)
    sleeve_len = 0.0
    if idx_sl < idx_cl:
        section = pts[idx_sl:idx_cl+1]
    else:
        section = np.concatenate([pts[idx_sl:], pts[:idx_cl+1]])
    for i in range(len(section)-1):
        dx = section[i+1,0]-section[i,0]; dy = section[i+1,1]-section[i,1]
        sleeve_len += math.hypot(dx, dy)
    measures["SleeveLength_left"] = sleeve_len
    # Similarly for right sleeve
    idx_sr = np.argmin(np.linalg.norm(pts - shoulder_right, axis=1))
    idx_cr = np.argmin(np.linalg.norm(pts - cuff_right, axis=1))
    sleeve_len_r = 0.0
    if idx_sr < idx_cr:
        section = pts[idx_sr:idx_cr+1]
    else:
        section = np.concatenate([pts[idx_sr:], pts[:idx_cr+1]])
    for i in range(len(section)-1):
        sleeve_len_r += math.hypot(section[i+1,0]-section[i,0], section[i+1,1]-section[i,1])
    measures["SleeveLength_right"] = sleeve_len_r
    # ... (other measures similarly)
    return measures, (garment_contour, landmarks)


The above pseudocode identifies key points and computes some measurements. In practice, we would refine those computations and add logic for different garment types (e.g., if pants detected by aspect ratio of contour, run a pants-specific routine for waist/hip/inseam/outseam).

Uncertainty Estimation

At each measurement, we calculate an uncertainty based on known variance sources:

Segmentation Uncertainty: We can estimate how much a slight change in the contour affects the measure. For example, we can dilate and erode the mask by 1 pixel (±1 mm) and re-measure to see sensitivity. The variation between those gives a rough ± error due to edge ambiguity. For most measures, this is on the order of ±1 mm or less (since a one-pixel inward shift on each side of a width reduces width by ~2 mm worst-case). We formalize: for each measurement, consider if it spans both left and right edges (like chest width uses two edges, so error could be compounded). We assign ±1 px per edge if edges are a bit uncertain. So chest width might get ±2 px (~±0.6 mm if px=0.3 mm; but in our setup px is 1 mm, but in actual hi-res maybe 0.3 mm, we can convert properly).

Calibration Uncertainty: Our homography and pixel scale may introduce error. We know our marker-based scale is very accurate (<0.1%), so for a 500 mm measure, scale error is ±0.5 mm. We include that as a systematic uncertainty on all measurements: e.g. ±0.2 mm + 0.1% of length as calibration uncertainty.

Measurement repeatability: Some dimensions like HPS length could vary if garment placement shifts (the garment might be pulled more or less flat). We can’t measure that from a single image, but from our Gauge R&R tests (see section 6) we might have an empirical value. Suppose repeated placements vary length by ±1 mm (std). We incorporate that as well if relevant.

We then combine uncertainties (assuming independence) in quadrature (root-sum-square). For example, chest width uncertainty might have segmentation ±0.5 mm and calibration ±0.5 mm, combined ~±0.7 mm (95% confidence perhaps doubling that to ~±1.4 mm). We will present these as ± intervals.

We can programmatically do a small random perturbation analysis: jitter contour points by ±1 px in random directions (within reason) and recompute measures to see distribution. This Monte Carlo gives a more robust estimate especially for composite measurements like circumferences.

Finally, we package results, e.g.:

{
  "ChestWidth": {"value": 520.0, "uncertainty": 1.0},
  "HPS_Length": {"value": 700.0, "uncertainty": 1.2},
  ...
}


These uncertainties represent ~95% confidence intervals based on our error budget (discussed next).

We also overlay the landmarks and lines on the original image for the operator. For instance, drawing a line between underarm points labeled “Chest = 520 mm”. This uses cv2.line and cv2.putText as mentioned. Example for chest:

cv2.line(preview_img, underarm_left, underarm_right, (0,255,0), 2)
mid_x = (underarm_left[0] + underarm_right[0])//2
mid_y = (underarm_left[1] + underarm_right[1])//2
cv2.putText(preview_img, f"Chest {cw:.0f} mm", (mid_x, mid_y-10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)


We do similar for each measurement line (vertical line for length, etc.), creating a comprehensive annotated image.

This completes the pipeline from image to measurements with pseudocode for core steps. The result is a robust algorithmic approach that can be implemented with OpenCV and Numpy, possibly leveraging the GPU for any CNN if we later integrate one for segmentation or landmark detection (not strictly necessary in v1).

5. Edge Cases & Recovery

Real production will encounter non-ideal scenarios. We plan for these and implement detection or mitigation strategies:

Wrinkles or Folding: If a garment is not perfectly flat, minor wrinkles could cause the contour to be irregular or measurements to be slightly off (a wrinkle might shorten a length). Our first line of defense is prevention: instruct the operator to smooth the garment (the UI overlay could detect wrinkles by looking at internal edges: if we see significant internal edge lines or high texture variance where there shouldn’t be, we flag it). For example, after segmentation, we can run cv2.Canny inside the garment area. If a lot of edges appear (above a threshold) not belonging to features (like button placket is a feature, but random crumples are not), then we output a warning: “Garment not flat – please re-smooth (e.g. sleeve)”. We specifically check areas around measurement zones: e.g., if the sleeve length path detection found the sleeve edge inside (meaning sleeve is folded under?), or if multiple contours appear (like part of garment folded creating a double edge). In such cases, the measurement might be lower than actual. We therefore prefer to catch and have the operator fix it. The system can also attempt small corrections: if a fold is minor, our segmentation might still capture the outermost silhouette (since lighting from both sides can sometimes penetrate shallow folds). But large folds would break silhouette (e.g. a big pleat). Those should be caught and not measured.

Partial Occlusion: If something covers part of the garment (e.g. a tag, or the calibration marker sticker overlaps the garment edge slightly, or an operator’s hand inadvertently in frame), our contour might have a bite or an extra bump. We can detect anomalies like a very sharp spike or indentation in the contour that doesn’t match garment patterns. For example, if a hand is present, the system might see an extra contour extension. We can either automatically remove small extrusions by ignoring any contour sections that deviate strongly from expected shape (like a small region protruding outward that’s too small to be a garment part). Or simpler: detect any non-garment colored object via color segmentation (e.g. operator glove which might be skin-toned or bright, distinct from garment usually). If found, we alert and maybe segment it out if possible (since it likely doesn’t connect fully to garment region). The safe approach: prompt “Foreign object detected – please remove and retake.”

Black Garments on Dark Background: This is a classic hard case
mdpi.com
. Our lighting strategy helps: raking light will create a highlight or shadow along the edge of even a black fabric on black background, giving the edge some contrast. Also, cross-polarization can be turned off in this scenario – we might allow a bit of reflection because a slight sheen on black fabric can make it distinguishable from a truly matte black background. Additionally, we could use a background swap: place a thin colored film or even a light-colored border underneath the edges of a black garment. Another trick: sprinkle a few white chalk dots around the garment’s perimeter before shooting (which can be later ignored in software) – but that’s messy for production. Instead, in software, if initial segmentation fails (the mask might be blank if Otsu threshold can’t separate), we switch to a more sensitive method: perhaps use background subtraction. If we have a reference image of the empty background (with same lighting), we can subtract the current image from it; the difference will highlight the garment area (especially for dark on dark, any difference in reflectance or lighting will show up). That difference image can then be thresholded. We can also amplify using different wavelength: e.g. use IR lighting if available – many black dyes reflect IR more than visible, so to the camera (if IR filter removed or using Pi NoIR cam) the black garment might appear lighter than a truly black background. This requires hardware adjustments, so as a simpler fallback: instruct operator to switch to the optional light background for very dark garments. If a white or light gray board is available, placing the black garment on it yields high contrast (the system can detect the background color by looking at calibration markers – if they are on a board that’s white vs black, we adjust threshold logic accordingly).

White Garments on White Background: Our default background is dark, chosen to avoid this. But if for some reason a very light pastel garment is used on a light gray background, we invert the strategies: use dark-field lighting to create shadow outlines. The raking lights, especially from all sides, will cast a slight shadow outward from the garment edges onto the background, effectively outlining it. Our segmentation can then pick up the shadow edge. We must be cautious to not confuse the actual garment edge vs the shadow edge; but typically the shadow will be just outside the true edge. We could shrink the mask slightly to compensate. Also, cross-polarization doesn’t matter as much for white on white; we might allow more direct lighting to create contrast by difference in texture. Best is to avoid white on white by using the dark mat.

Highly Textured or Logo garments: A big logo or graphic on the shirt could create internal contrast that might confuse a naive threshold. Our method primarily uses edges and largest contour, so it should ignore interior patterns. But if the logo is the same darkness as background (say a black logo on a white tee might create holes in a simple threshold mask thinking background shows through). To avoid that, we fill holes in the mask. E.g., after initial threshold, the interior logo might appear as a “background” area inside the garment region – we can detect that as an enclosed contour within the main contour and fill it (since we know background can’t be enclosed completely by garment – that must be something on garment). So our pipeline explicitly fills internal mask holes below a certain size. For extreme cases (mesh or lace garments that are full of holes), that’s a separate challenge – possibly needing multiple images or just measure overall bounding box. But typical logos, prints, stripes, etc., we handle by morphological closing and by preferring edge-based detection.

Drawstrings and Straps: A hoodie drawstring or a belt hanging off could be detected as part of the contour if it extends beyond the main silhouette. Ideally, the operator should tuck in or straighten drawstrings. If one is sticking out, our contour might get a spur. We can automatically remove narrow extrusions: if a portion of contour has a very high curvature and looks like a thin line (e.g., drawstring 5 mm thick extending 100 mm out), we could identify that by checking the local contour segment length vs end-to-end distance (it will be almost a line, likely recognized as a narrow triangular spike). We can trim such spikes by cutting the contour at the base of the spike. Alternatively, we ignore any contour sections that have width below a threshold and area too small to affect measurements. Since drawstrings don’t contribute to garment measurements, removing them won’t harm. If a drawstring causes confusion around, say, waist measure on sweatpants, instruct to tuck it inside waist or at least not crossing edges.

Hood Shadows and Overlaps: If a hoodie’s hood is not spread out, it might lie on the chest creating a double layer outline, or cast a dark shadow. We advise laying hoods either completely flat and included in outline (if measuring overall length including hood? Usually not), or off the side. For QC of body dimensions, they should likely exclude the hood from measurement. So we treat the hood as an extra piece that shouldn’t alter chest/length. If a hood falls within front outline (like a double layer on chest), our camera likely sees it as part of thicker silhouette (or might fill neck hole). This can be tricky. Ideally, we ask operator to pull hood outside the body outline (spread above the shirt if measuring it, or aside). If not, we can detect it: a hood on chest would create an interior edge as well as raise thickness (less relevant in silhouette directly). Possibly beyond v1 scope to solve algorithmically – easier to add to instructions.

Buttons/Zippers: These usually don’t affect the outer silhouette (except a button sticking out doesn’t change 2D outline). But they can create bright spots that Otsu threshold might think are background (if background is dark and a shiny button is bright, in grayscale it could appear similar to background brightness if inverted scenario). However, since our background is dark, a shiny metal button appears bright – which just makes it clearly part of garment in threshold (garment area will have bright spots but still counted as garment). There’s a small risk the threshold could classify extremely bright specular highlight as “background” if using a naive Otsu, but since background is dark, Otsu will put those highlights with garment. So not an issue. If using cross-polarization, those highlights would be gone anyway.

Asymmetry (Raglan sleeves, Dropped shoulder): Raglan sleeves mean no distinct shoulder point; the shoulder line is diagonal from neck to underarm. Our algorithm might still find an HPS (neck-shoulder) similarly, but “shoulder width” concept is different (there is no true shoulder seam point). In spec, often they measure “across shoulder” only for set-in sleeves, and for raglan they might measure differently (like from neck to sleeve end as a single measure). We can detect raglan by the absence of a convex shoulder point: if the curvature from neck to underarm is smooth without a clear corner at shoulder, our convexity defect method for underarm might still get underarm, but shoulder point detection (max X at top) might be lower relative to neck. Possibly we identify garment type via pattern recognition (we could train a small classifier on sleeve type based on contour shape). In v1, we might simply allow the user to specify “raglan” vs “set-in” style. If raglan, we won’t output shoulder width; or we define shoulder width as distance between imaginary points where a set-in seam would be – maybe not needed. We could skip or mark N/A to avoid confusion. Similarly, dropped shoulders (seam off-shoulder, sleeve starts lower on arm): the actual shoulder seam is lower than HPS vertically. Our algorithm might pick the outer contour point as shoulder (which would actually be on arm, not at shoulder seam). That would overestimate shoulder width. Perhaps we refine by looking at sleeve vs body angles: if the slope at the supposed shoulder point is shallow (horizontal), it’s likely actual shoulder seam; if it’s steep, we might be down the arm. Without advanced ML, a heuristic: if the shoulder point we found is more than, say, 5% of garment height below HPS, then it might be a dropped shoulder style. In that case, we could attempt to find the true shoulder seam by looking for a slight angle change along that upper arm curve. This might be too detailed; instead, we might measure the “across sleeve” width and note it. Possibly beyond pilot scope – we can handle normal shoulders and note that extreme dropped designs might need a manual check.

Garment Larger than Bench: If an item (like an extra-long coat or XXL pants) exceeds the 120×80 cm area, parts will be out of view. The system should detect this (markers allow us to see if garment extends beyond them – e.g., if contour touches image border). If so, we immediately warn “Garment too large for frame – cannot measure fully.” A partial measure could be done by repositioning (like measure top then bottom and sum), but that’s not automated in v1. The solution is to get a larger imaging area or fold the garment in a known way. For a pilot, we’ll assume garments fit the area (XS–XL as stated, likely fine).

Automation Aids: The system can prompt the operator with corrective suggestions:

If segmentation finds multiple disjoint large regions (maybe a piece folded such that two separate blobs), prompt “Ensure garment is fully spread (no double layers visible).”

If a reference marker isn’t found: “Marker not visible – check lighting or marker placement.”

If the measured symmetry is off beyond expectation (e.g. left vs right sleeve length differ by >5 mm): “Garment placement may be skewed (left sleeve appears longer); please adjust and recapture.”

If any key landmark can’t be found or measurement seems implausible (like negative or zero if something failed), the system should not output wrong numbers silently – it should flag “Measurement failed for [specific measure], please retake or measure manually.”

Each error prompt is designed to be understandable by a floor operator (simple language, ideally with an image highlight of the issue). Over time, as the model improves, these prompts may rarely trigger, but in pilot they are invaluable to catch issues early rather than propagate bad data.

We also maintain an operator override possibility: if the system consistently fails on a tricky garment (say black lace), the operator can press a key to switch to a manual assist mode. For example, they can draw the outline quickly on a touchscreen or place a physical white sheet behind lace areas to get the outline. Those are fallback plans to ensure production isn’t stuck.

6. Validation & Metrology Plan

To guarantee the system meets accuracy requirements, we implement a rigorous validation strategy based on golden samples and Gage R&R principles:

Golden Sample Set: We select a set of, say, 10 garments representing the variety of types (a t-shirt, a hoodie, a button shirt, a pair of pants, a skirt, etc., including small and large sizes). These garments are first measured manually by expert QC using calibrated tools (tape measure class I, or height gauge for lengths) to establish “true” values. Each dimension (chest, length, etc.) is measured 3 times and averaged to minimize human error. These become our ground-truth references. We then run our imaging system on these samples multiple times to see how close we get. We expect systematic differences < ±1 mm and random variability < ±1 mm. If any bias is found (e.g. system consistently measures 2 mm shorter on length because maybe garments aren’t perfectly taut compared to manual stretching), we will see that in the data and can apply a correction factor or update the procedure (for example, instructing to stretch flat could eliminate that bias).

We construct an error budget table listing all sources of error with their estimated magnitudes, to ensure the combined uncertainty is within spec. For instance:

Error Source	Type	Est. ± (mm)	Notes
Camera Intrinsic Distortion	systematic	±0.2 mm	After calibration, residual ~0.1 px (at edges ~0.2 mm)
mdpi.com
. Negligible in center, 0.2 mm at worst edges.
Homography/Perspective	systematic	±0.5 mm	Marker detection ~0.2 px → ~0.2 mm; plus table not perfectly flat ±0.3 mm. Combined ~0.5 mm max.
Pixel Quantization	random	±0.3 mm	1 px ~1 mm (or 0.5 mm if hi-res output) – subpixel interpolation on contour yields ~±0.3 mm.
Segmentation (edge finding)	random	±0.5 mm	Edge can shift ±1 px depending on threshold shadows. Up to ±1 mm on a width (left+right edges) = ±0.5 mm per side.
Contour smoothing approximation	systematic	±0.2 mm	Spline fitting error vs true edge <0.2 mm (we keep raw data mostly).
Landmark identification	random	±0.5 mm	Keypoint placement might vary ~1 px between runs (e.g. underarm point on a slightly different pixel).
Garment placement (repeatability)	random	±1.0 mm	If garment not placed same tension each time, a dimension might vary ~1 mm. E.g., chest could vary if garment is skewed by operator.
Environmental (temp, lighting)	systematic	±0.2 mm	Minimal – markers thermal expansion (carbon fiber or similar) negligible at these sizes; lighting no effect on geom.
Combined (RSS)	–	±1.3 mm	Combined standard uncertainty ~0.65 mm, for 95% confidence multiply ~2: ≈ ±1.3 mm.

This budget indicates we expect ~±1.3 mm (95% CI) accuracy on a typical measurement ~500 mm (that’s 0.26% error), which meets the ≤±2 mm requirement. For larger spans (1000 mm), error might slightly increase (scale uncertainty 0.1% adds 1 mm at 1000 mm, so ~±1.5 mm total), still within ±0.3% criterion. For very small spans (50 mm cuff width), absolute error ~±1 mm is 2% – might be slightly high in percentage but acceptable in absolute. We will specifically test a small span (like a cuff or collar of ~100 mm) to ensure we hit ±1 mm there; if not, we may need higher-res imaging or local ROI zoom.

Gauge R&R Study: We conduct a formal Gage Repeatability and Reproducibility test to quantify the measurement system variation relative to garment variation. For example, take 5 garments of varying dimensions (covering small to large). Have 3 different operators measure each garment 2 times with the system (randomizing order to avoid learning bias). That yields 30 measurements. We then use standard GRR analysis: calculate the variance due to repeatability (within operator), reproducibility (between operators), and part-to-part. We aim for %GRR (the ratio of measurement variance to tolerance or to process variance) to be low. Specifically, if tolerance for a dimension is ±2 mm (total range 4 mm), we want the GRR (6σ of measurement system) to be <10% of that, i.e. <0.4 mm. This is very stringent – it may not be fully achievable immediately, but we target it. More realistically for pilot, %GRR <20% (meaning ~0.8 mm 6σ measurement variation on a 4 mm tolerance) is acceptable. For dimensions with wider tolerances (like ±5 mm allowed on some spec), our fixed ±1 mm error is even smaller in %.

We will examine the GRR results: If one operator consistently gets slightly different results, that may indicate a procedural difference (maybe how they place magnets). We then unify the procedure or retrain. If the system itself has variation (repeatability) of ~0.5 mm SD as predicted, that is fine.

We will also check linearity and bias: measure across the size range to ensure no scaling bias (e.g. small vs large garments both accurate). Using the golden samples, plot measured vs actual for each dimension – expect ~1:1 line with <1 mm offset. If any bias is found (say lengths always 1 mm short), we can apply a global correction offset in software or find cause (maybe gravity sag, etc.).

SPC and Ongoing Monitoring: Once deployed, we integrate Statistical Process Control charts into the SaaS dashboard. For each measurement type, we track ongoing results. For example, we might use an X-bar and R chart for a stable reference item measured periodically, or individual charts for trending. Concretely, we could keep one of the golden samples as a control garment at the station. Each morning, the operator measures it once. The system logs the key dimensions and plots them over time with control limits (e.g. mean ±2 mm). If it ever goes out of control (say suddenly length reads 3 mm different), that indicates a calibration drift or hardware issue, prompting investigation.

For production data, we also show charts of measured dimensions for each batch or style. If we see unusual variance in measurements of the same SKU, it could mean either manufacturing variation or measurement issues. Since our system is consistent, spikes might indicate something like a lighting change (if segmentation started failing subtly it might add jitter). The dashboard can highlight if the variability within a batch exceeds expected (we know our measurement repeatability ~0.5 mm, so if we see 3 mm range on a supposedly identical batch, either the garments truly vary that much or measurement had an outlier).

Acceptance Criteria: We define thresholds for the system’s validation: All of the golden sample measurements should be within ±1 mm of true on average (bias) and within ±2 mm at worst case. The GRR % (using tolerance-based) should ideally be <10%, but we accept up to 20% for this pilot. If any dimension fails these, we refine and re-test. Once validated, we lock down the system settings and move to production use.

We also consider traceability: the calibration markers can be periodically checked against a NIST-traceable ruler to ensure no physical shift. We document the calibration and validation results in a short report for our QA system, so stakeholders trust the measurements (critical when replacing manual measures
spesa.org
spesa.org
).

Finally, the system’s output on the dashboard will indicate both the measured value and the tolerance. For each piece, an instant Pass/Fail result is shown for each spec (like the example machine output listing 15 dimensions in 6 seconds
spesa.org
). We emulate that: our software will compare measured values to the spec sheet values loaded for that SKU and flag any out-of-tolerance in red. It will also compute derived metrics like symmetry (difference between left and right sleeve etc.) and flag if beyond threshold (as in the example “shoulder width symmetry” etc.
spesa.org
).

In summary, by following this comprehensive validation and monitoring plan, we ensure the garment measurement pipeline is accurate, reliable, and stays in control over time. Any drift or issue will be caught by our calibrations checks or SPC alerts. This gives confidence to proceed with the v1 pilot and then scale up usage, knowing that automated measurements will meet the strict quality requirements that previously only manual methods could (and with far less labor and error)