from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path
from typing import Optional


DEFAULT_LOG_PATH = Path("/var/log/edge-device.log")
LOCAL_LOG_PATH = Path("logs/app.log")


def configure_logging(log_path: Optional[Path] = None) -> Path:
    target = log_path or DEFAULT_LOG_PATH
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(target, maxBytes=2_000_000, backupCount=5)
    except (PermissionError, FileNotFoundError):
        LOCAL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        target = LOCAL_LOG_PATH
        handler = logging.handlers.RotatingFileHandler(target, maxBytes=1_000_000, backupCount=3)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(threadName)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    return target


__all__ = ["configure_logging"]
