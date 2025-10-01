from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict


@dataclass
class DeviceConfig:
    device_secret: str
    api_base_url: str
    camera_resolution: tuple[int, int]
    photo_quality: int
    camera_shutter_speed: int
    camera_gain: float
    camera_awb_gains: tuple[float, float]
    camera_denoise: bool
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeviceConfig":
        resolution = data.get("camera_resolution", [1920, 1080])
        if isinstance(resolution, list):
            resolution = tuple(int(x) for x in resolution)

        awb_gains = data.get("camera_awb_gains", [1.0, 1.0])
        if isinstance(awb_gains, list):
            awb_gains = tuple(float(x) for x in awb_gains)

        return cls(
            device_secret=data["device_secret"],
            api_base_url=data["api_base_url"],
            camera_resolution=resolution,  # type: ignore[arg-type]
            photo_quality=int(data.get("photo_quality", 90)),
            camera_shutter_speed=int(data.get("camera_shutter_speed", 10000)),
            camera_gain=float(data.get("camera_gain", 1.0)),
            camera_awb_gains=awb_gains,  # type: ignore[arg-type]
            camera_denoise=bool(data.get("camera_denoise", False)),
            raw=data,
        )


class ConfigManager:
    def __init__(self, config_path: Path) -> None:
        self._config_path = config_path
        self._lock = threading.Lock()
        self._config = self._load()

    @property
    def config(self) -> DeviceConfig:
        with self._lock:
            return self._config

    def refresh(self) -> DeviceConfig:
        with self._lock:
            self._config = self._load()
            return self._config

    def _load(self) -> DeviceConfig:
        if not self._config_path.exists():
            raise FileNotFoundError(f"Config file missing: {self._config_path}")
        data = json.loads(self._config_path.read_text())
        return DeviceConfig.from_dict(data)

__all__ = ["ConfigManager", "DeviceConfig"]
