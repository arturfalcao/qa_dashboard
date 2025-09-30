from __future__ import annotations

import logging
import time
from pathlib import Path
from threading import Event, Thread
from typing import Optional

from api_client import ApiClient
from queue_manager import QueueManager
from status_leds import StatusLEDs

log = logging.getLogger(__name__)


class UploadWorker(Thread):
    def __init__(
        self,
        queue: QueueManager,
        api_client: ApiClient,
        stop_event: Event,
        leds: Optional[StatusLEDs] = None,
    ) -> None:
        super().__init__(name="upload-worker", daemon=True)
        self._queue = queue
        self._api = api_client
        self._stop = stop_event
        self._leds = leds

    def run(self) -> None:  # noqa: D401 - thread loop
        while not self._stop.is_set():
            task = self._queue.next_task()
            if not task:
                self._stop.wait(timeout=2)
                continue
            task_id, task_type, payload, retries = task
            try:
                self._set_processing()
                self._dispatch(task_type, payload)
                self._queue.mark_success(task_id)
                self._set_success()
            except Exception as exc:
                log.exception("Task %s failed: %s", task_type, exc)
                self._queue.mark_failure(task_id, str(exc))
                self._set_error()
                delay = min(60, 2 ** min(retries + 1, 6))
                self._stop.wait(timeout=delay)

    def _dispatch(self, task_type: str, payload: dict) -> None:
        if task_type == "photo":
            path = Path(payload["path"])
            if not path.exists():
                raise FileNotFoundError(f"Photo missing: {path}")
            self._api.upload_photo(path, payload["session_id"], payload.get("piece_id"))
        elif task_type == "flag_defect":
            self._api.flag_defect(payload["piece_id"], payload["transcript"])
        elif task_type == "flag_potential":
            self._api.flag_potential(payload["piece_id"], payload["transcript"])
        elif task_type == "complete_piece":
            self._api.complete_piece(payload["session_id"], payload["piece_id"], payload["status"])
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    def _set_processing(self) -> None:
        if self._leds:
            self._leds.set_processing()

    def _set_success(self) -> None:
        if self._leds:
            self._leds.set_success()

    def _set_error(self) -> None:
        if self._leds:
            self._leds.set_error()


__all__ = ["UploadWorker"]
