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
    def __init__(self, resolution: Tuple[int, int], fps: int, exposure: str = "auto", quality: int = 90) -> None:
        self._resolution = resolution
        self._fps = fps
        self._exposure = exposure
        self._camera: Optional[Picamera2] = None
        self._started = False
        self._quality = quality

    def start(self) -> None:
        if Picamera2 is None:
            raise CameraUnavailable("picamera2 library is not available")
        if self._camera:
            return
        picam = Picamera2()
        config = picam.create_still_configuration(main={"size": self._resolution})
        picam.configure(config)
        if self._exposure != "auto":
            picam.set_controls({"AeEnable": False})
        picam.start()
        self._camera = picam
        self._started = True
        log.info("Camera started with resolution=%s fps=%s", self._resolution, self._fps)

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
        self._camera.capture_file(str(path), format='jpeg')
        if overlay_text and Image:
            self._add_overlay(path, overlay_text)
        return path

    def _add_overlay(self, path: Path, text: str) -> None:
        try:
            with Image.open(path) as img:
                draw = ImageDraw.Draw(img)
                width, height = img.size
                font = None
                if ImageFont:
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
                    except OSError:
                        font = ImageFont.load_default()
                draw.rectangle([(0, height - 70), (width, height)], fill=(0, 0, 0, 160))
                draw.text((10, height - 65), text, fill="white", font=font)
                img.save(path, format="JPEG", quality=self._quality)
        except Exception as exc:  # pragma: no cover - best effort overlay
            log.warning("Failed to apply overlay: %s", exc)

    @staticmethod
    def timestamp_overlay() -> str:
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


__all__ = ["CameraController", "CameraUnavailable"]
