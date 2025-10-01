from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

log = logging.getLogger(__name__)

try:
    from picamera2 import Picamera2
    from picamera2.outputs import FileOutput
except ImportError:  # pragma: no cover - falls back when not on Pi
    Picamera2 = None
    FileOutput = None

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - optional overlay
    Image = None
    ImageDraw = None
    ImageFont = None


class CameraUnavailable(RuntimeError):
    pass


class CameraController:
    def __init__(
        self,
        resolution: Tuple[int, int],
        fps: int,
        exposure: str = "auto",
        quality: int = 90,
        shutter_speed: int = 10000,
        gain: float = 1.0,
        awb_gains: Tuple[float, float] = (1.0, 1.0),
        denoise: bool = False,
    ) -> None:
        self._resolution = resolution
        self._fps = fps
        self._exposure = exposure
        self._camera: Optional[Picamera2] = None
        self._started = False
        self._quality = quality
        self._shutter_speed = shutter_speed
        self._gain = gain
        self._awb_gains = awb_gains
        self._denoise = denoise

    def start(self) -> None:
        if Picamera2 is None:
            raise CameraUnavailable("picamera2 library is not available")
        if self._camera:
            return
        picam = Picamera2()
        config = picam.create_still_configuration(main={"size": self._resolution})
        picam.configure(config)

        # Apply camera controls
        controls = {
            "ExposureTime": self._shutter_speed,  # Shutter speed in microseconds
            "AnalogueGain": self._gain,
            "AeEnable": False,  # Disable auto exposure
            "AwbEnable": False,  # Disable auto white balance
            "ColourGains": self._awb_gains,
        }

        if self._denoise:
            controls["NoiseReductionMode"] = 1  # Fast denoise
        else:
            controls["NoiseReductionMode"] = 0  # Off

        picam.set_controls(controls)
        picam.start()
        self._camera = picam
        self._started = True
        log.info("Camera started: resolution=%s, shutter=%dus, gain=%.1f, awb=%s, denoise=%s",
                 self._resolution, self._shutter_speed, self._gain, self._awb_gains, self._denoise)

    def stop(self) -> None:
        if self._camera:
            self._camera.stop()
            self._camera.close()
        self._camera = None
        self._started = False
        log.info("Camera stopped")

    def capture(self, path: Path, overlay_text: Optional[str] = None) -> Path:
        if not self._camera or not self._started:
            raise CameraUnavailable("Camera not initialized")
        path.parent.mkdir(parents=True, exist_ok=True)

        # Capture to temporary path first
        temp_path = path.with_suffix('.tmp.jpg')
        self._camera.capture_file(str(temp_path), format='jpeg')

        # Recompress with quality setting and add overlay
        if Image:
            try:
                with Image.open(temp_path) as img:
                    # Add overlay if requested
                    if overlay_text:
                        draw = ImageDraw.Draw(img)
                        width, height = img.size
                        font = None
                        if ImageFont:
                            try:
                                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
                            except OSError:
                                font = ImageFont.load_default()
                        draw.rectangle([(0, height - 70), (width, height)], fill=(0, 0, 0, 160))
                        draw.text((10, height - 65), overlay_text, fill="white", font=font)

                    # Save with quality setting
                    img.save(path, format="JPEG", quality=self._quality, optimize=True)
                temp_path.unlink()  # Remove temp file
            except Exception as exc:
                log.warning("Failed to process image: %s", exc)
                # Fallback: just rename temp file
                temp_path.rename(path)
        else:
            # No PIL available, just rename
            temp_path.rename(path)

        return path

    @staticmethod
    def timestamp_overlay() -> str:
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


__all__ = ["CameraController", "CameraUnavailable"]
