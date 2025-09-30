from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional

try:  # optional env overrides
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    def load_dotenv() -> None:  # type: ignore[misc]
        return

from api_client import ApiClient
from camera import CameraController, CameraUnavailable
from config_manager import ConfigManager
from health_server import HealthServer
from keyboard_handler import KeyboardHandler, KeyboardUnavailable
from logging_utils import configure_logging
from queue_manager import QueueManager
from status_leds import StatusLEDs
from storage_manager import StorageManager, StorageStatus
from upload_worker import UploadWorker
from voice_recorder import VoiceRecorder, VoiceRecordingUnavailable

log = logging.getLogger(__name__)


@dataclass
class SessionState:
    session_id: Optional[str] = None
    current_piece_id: Optional[str] = None
    status: str = "inactive"
    lot_code: Optional[str] = None
    updated_at: float = 0.0


class SessionPoller(threading.Thread):
    def __init__(
        self,
        api_client: ApiClient,
        callback: Callable[[Optional[Dict[str, object]]], None],
        stop_event: threading.Event,
        interval: int = 10,
    ) -> None:
        super().__init__(name="session-poller", daemon=True)
        self._api = api_client
        self._callback = callback
        self._stop = stop_event
        self._interval = interval

    def run(self) -> None:  # noqa: D401 - polling loop
        while not self._stop.is_set():
            try:
                payload = self._api.get_current_session()
                self._callback(payload)
            except Exception as exc:
                log.warning("Session poll failed: %s", exc)
            self._stop.wait(self._interval)


class EdgeDeviceApp:
    def __init__(self, config_path: Path) -> None:
        self._config_manager = ConfigManager(config_path)
        config = self._config_manager.config
        storage_path = Path("/home/pi/edge-photos")
        self._storage = StorageManager(storage_path, 5000)
        self._queue = QueueManager(Path("queue.db"))
        self._api_client = ApiClient(config.api_base_url, config.device_secret)
        self._stop_event = threading.Event()
        self._leds = StatusLEDs()
        self._voice: Optional[VoiceRecorder] = None
        self._voice_lock = threading.Lock()
        self._camera = CameraController(
            resolution=tuple(config.camera_resolution),
            fps=30,
            exposure="auto",
            quality=config.photo_quality,
        )
        self._upload_worker = UploadWorker(self._queue, self._api_client, self._stop_event, self._leds)
        self._current_piece_status = "ok"
        self._health_server: Optional[HealthServer] = None
        try:
            self._health_server = HealthServer("0.0.0.0", 8080, self._health_status)
        except OSError as exc:
            log.warning("Health server disabled: %s", exc)
        self._keyboard: Optional[KeyboardHandler] = None
        self._lock = threading.Lock()
        self._session_state = SessionState()
        self._session_poller = SessionPoller(self._api_client, self._apply_session_update, self._stop_event)

    def run(self) -> None:
        log.info("Starting Edge Photo Inspection System")
        self._attach_signals()
        self._storage.cleanup_old_files()
        self._check_storage_levels()
        self._start_camera()
        self._start_health_server()
        self._start_queue_worker()
        self._start_session_poller()
        self._start_keyboard()
        if not self._api_client.ping():
            log.warning("API ping failed; working offline")
        self._leds.set_idle()
        self._stop_event.wait()
        self.shutdown()

    def shutdown(self) -> None:
        log.info("Shutting down application")
        if self._keyboard:
            self._keyboard.stop()
        self._stop_event.set()
        self._upload_worker.join(timeout=5)
        if self._session_poller.is_alive():
            self._session_poller.join(timeout=5)
        if self._health_server:
            self._health_server.stop()
        try:
            self._camera.stop()
        except Exception as exc:
            log.warning("Camera stop failed: %s", exc)
        if self._voice:
            self._voice.close()
        self._leds.close()

    # --- Setup helpers ---

    def _attach_signals(self) -> None:
        signal.signal(signal.SIGTERM, lambda *_: self._stop_event.set())
        signal.signal(signal.SIGINT, lambda *_: self._stop_event.set())

    def _start_camera(self) -> None:
        try:
            self._camera.start()
        except CameraUnavailable as exc:
            log.error("Camera unavailable: %s", exc)
            sys.exit(1)

    def _start_queue_worker(self) -> None:
        self._upload_worker.start()

    def _start_health_server(self) -> None:
        if self._health_server:
            self._health_server.start()

    def _start_session_poller(self) -> None:
        self._refresh_session()
        self._session_poller.start()

    def _start_keyboard(self) -> None:
        keymap = {
            "1": self.take_photo,
            "f1": self.take_photo,
            "2": self.flag_defect,
            "f2": self.flag_defect,
            "3": self.flag_potential_defect,
            "f3": self.flag_potential_defect,
            "4": self.complete_piece,
            "f4": self.complete_piece,
        }
        try:
            self._keyboard = KeyboardHandler(keymap)
            self._keyboard.start()
        except KeyboardUnavailable as exc:
            log.error("Keyboard handler unavailable: %s", exc)
            sys.exit(1)

    # --- Action handlers ---

    def take_photo(self) -> None:
        session = self._session_snapshot()
        if not session.session_id:
            log.warning("Cannot capture photo without active session")
            return
        if session.status != "active":
            log.warning("Cannot capture photo; session status is %s", session.status)
            return
        piece_id = session.current_piece_id
        if not piece_id:
            log.warning("Cannot capture photo; no active piece assigned")
            return
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        photo_path = self._storage.build_photo_path(session.session_id, timestamp)
        overlay = self._camera.timestamp_overlay()
        try:
            self._leds.set_processing()
            self._camera.capture(photo_path, overlay)
            self._queue.enqueue(
                "photo",
                {
                    "path": str(photo_path),
                    "session_id": session.session_id,
                    "piece_id": piece_id,
                },
            )
            self._storage.cleanup_old_files()
            status = self._check_storage_levels()
            if status.usage_ratio > 0.8:
                log.warning("Storage above 80%% (%.2f%%)", status.usage_ratio * 100)
            self._leds.set_success()
            log.info("Photo captured: %s", photo_path)
        except Exception as exc:
            self._leds.set_error()
            log.exception("Failed to capture photo: %s", exc)

    def flag_defect(self) -> None:
        self._handle_defect(status="defect")

    def flag_potential_defect(self) -> None:
        self._handle_defect(status="potential_defect")

    def _handle_defect(self, status: str) -> None:
        session = self._session_snapshot()
        if not session.session_id:
            log.warning("Cannot flag defect without active session")
            return
        piece_id = session.current_piece_id
        if not piece_id:
            log.warning("Cannot flag defect; no active piece assigned")
            return
        transcript = self._collect_transcript(status, session.session_id)
        if not transcript:
            log.warning("Skipping %s; no transcript available", status)
            return
        self._queue.enqueue(
            "flag_defect" if status == "defect" else "flag_potential",
            {"piece_id": piece_id, "transcript": transcript},
        )
        with self._lock:
            self._current_piece_status = status
        log.info("Queued %s for piece %s", status, piece_id)

    def complete_piece(self) -> None:
        session = self._session_snapshot()
        if not session.session_id:
            log.warning("Cannot complete piece without active session")
            return
        piece_id = session.current_piece_id
        if not piece_id:
            log.warning("Cannot complete piece; no active piece assigned")
            return
        with self._lock:
            status = self._current_piece_status
            self._current_piece_status = "ok"
        self._queue.enqueue(
            "complete_piece",
            {
                "session_id": session.session_id,
                "piece_id": piece_id,
                "status": status,
            },
        )
        log.info("Completed piece %s with status %s", piece_id, status)
        self._leds.set_idle()

    # --- Support helpers ---

    def _session_snapshot(self) -> SessionState:
        with self._lock:
            return SessionState(
                session_id=self._session_state.session_id,
                current_piece_id=self._session_state.current_piece_id,
                status=self._session_state.status,
                lot_code=self._session_state.lot_code,
                updated_at=self._session_state.updated_at,
            )

    def _refresh_session(self) -> None:
        try:
            payload = self._api_client.get_current_session()
            self._apply_session_update(payload)
        except Exception as exc:
            log.warning("Initial session fetch failed: %s", exc)

    def _apply_session_update(self, payload: Optional[Dict[str, object]]) -> None:
        with self._lock:
            prev_session = self._session_state.session_id
            prev_piece = self._session_state.current_piece_id
            if payload:
                session_value = payload.get("sessionId") or payload.get("session_id") or payload.get("id")
                session_id = str(session_value) if session_value else None
                piece_value = payload.get("currentPieceId") or payload.get("pieceId")
                piece_id = str(piece_value) if piece_value else None
                status_value = payload.get("status", "active")
                status = str(status_value).lower() if status_value else "active"
                lot_value = payload.get("lot") or payload.get("lotCode") or payload.get("lot_id")
                lot_code = str(lot_value) if lot_value else None
            else:
                session_id = None
                piece_id = None
                status = "inactive"
                lot_code = None

            session_changed = prev_session != session_id
            piece_changed = bool(session_id) and prev_piece != piece_id

            self._session_state.session_id = session_id
            self._session_state.current_piece_id = piece_id
            self._session_state.status = status
            self._session_state.lot_code = lot_code
            self._session_state.updated_at = time.time()
            if session_changed or piece_changed:
                self._current_piece_status = "ok"

        if session_changed:
            if session_id:
                log.info("Session %s active (lot=%s)", session_id, lot_code or "unknown")
            else:
                log.info("No active session")
        elif piece_changed:
            log.info("Piece advanced to %s", piece_id)

    def _collect_transcript(self, label: str, session_id: str) -> Optional[str]:
        recorder = self._ensure_voice_recorder()
        if not recorder:
            return None
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        audio_path = self._storage.build_audio_path(session_id, timestamp)
        try:
            log.info("Recording audio for %s", label)
            recorder.record(duration=5, output_path=audio_path)
        except VoiceRecordingUnavailable as exc:
            log.error("Voice recording failed: %s", exc)
            return None
        transcript = recorder.transcribe(audio_path)
        if transcript:
            log.info("Transcript captured (%s characters)", len(transcript))
        else:
            log.warning("Transcript unavailable for %s", label)
        return transcript or None

    def _ensure_voice_recorder(self) -> Optional[VoiceRecorder]:
        with self._voice_lock:
            if self._voice:
                return self._voice
            try:
                self._voice = VoiceRecorder()
                return self._voice
            except VoiceRecordingUnavailable as exc:
                log.error("Voice recorder unavailable: %s", exc)
                return None

    def _check_storage_levels(self) -> StorageStatus:
        status = self._storage.enforce_capacity()
        return status

    def _health_status(self) -> dict:
        storage_status = self._storage.storage_status()
        session = self._session_snapshot()
        return {
            "status": "ok",
            "sessionId": session.session_id,
            "sessionStatus": session.status,
            "currentPieceId": session.current_piece_id,
            "lotCode": session.lot_code,
            "queuePending": self._queue.pending_count(),
            "storageUsedBytes": storage_status.total_bytes,
            "storageMaxBytes": storage_status.max_bytes,
            "storageUsage": storage_status.usage_ratio,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Edge Photo Inspection Device")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.json"),
        help="Path to config.json",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    log_path = configure_logging()
    log.info("Logging to %s", log_path)
    try:
        app = EdgeDeviceApp(args.config)
    except FileNotFoundError as exc:
        log.error("Configuration error: %s", exc)
        sys.exit(1)
    try:
        app.run()
    except KeyboardInterrupt:
        log.info("Interrupted by user")
        app.shutdown()


if __name__ == "__main__":
    main()
