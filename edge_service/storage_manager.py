from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List

log = logging.getLogger(__name__)


@dataclass
class StorageStatus:
    total_bytes: int
    max_bytes: int
    usage_ratio: float
    over_capacity: bool


class StorageManager:
    def __init__(self, base_path: Path, max_storage_mb: int) -> None:
        self._base_path = base_path
        self._max_bytes = max_storage_mb * 1024 * 1024
        self._base_path.mkdir(parents=True, exist_ok=True)

    @property
    def base_path(self) -> Path:
        return self._base_path

    def build_photo_path(self, session_id: str, timestamp: str) -> Path:
        session_dir = self._base_path / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir / f"photo_{timestamp}.jpg"

    def build_audio_path(self, session_id: str, timestamp: str) -> Path:
        session_dir = self._base_path / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir / f"voice_{timestamp}.mp3"

    def cleanup_old_files(self, max_age_seconds: int = 7 * 24 * 3600) -> int:
        removed = 0
        cutoff = time.time() - max_age_seconds
        for path in list(self._base_path.rglob("*")):
            if not path.is_file():
                continue
            if path.stat().st_mtime < cutoff:
                try:
                    path.unlink()
                    removed += 1
                except FileNotFoundError:
                    continue
        self._remove_empty_dirs()
        if removed:
            log.info("Removed %s expired files", removed)
        return removed

    def storage_status(self) -> StorageStatus:
        total = self._dir_size(self._base_path)
        ratio = total / self._max_bytes if self._max_bytes else 0.0
        return StorageStatus(total_bytes=total, max_bytes=self._max_bytes, usage_ratio=ratio, over_capacity=ratio > 1.0)

    def enforce_capacity(self) -> StorageStatus:
        status = self.storage_status()
        if not status.over_capacity:
            return status
        log.warning("Storage full, pruning oldest files")
        files: List[Path] = [p for p in self._base_path.rglob("*") if p.is_file()]
        files.sort(key=lambda p: p.stat().st_mtime)
        for path in files:
            path.unlink(missing_ok=True)
            status = self.storage_status()
            if not status.over_capacity:
                break
        self._remove_empty_dirs()
        return status

    def _dir_size(self, path: Path) -> int:
        total = 0
        for root, _, files in os.walk(path):
            for name in files:
                fp = Path(root) / name
                try:
                    total += fp.stat().st_size
                except FileNotFoundError:
                    continue
        return total

    def _remove_empty_dirs(self) -> None:
        for dir_path in sorted(self._base_path.rglob("*"), reverse=True):
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                dir_path.rmdir()


__all__ = ["StorageManager", "StorageStatus"]
