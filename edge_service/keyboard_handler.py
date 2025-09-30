from __future__ import annotations

import logging
from threading import Event
from typing import Callable, Dict, Optional

log = logging.getLogger(__name__)

try:
    from pynput import keyboard
except ImportError:  # pragma: no cover - runtime dependency on Pi
    keyboard = None


ActionCallback = Callable[[], None]


class KeyboardUnavailable(RuntimeError):
    pass


class KeyboardHandler:
    def __init__(self, keymap: Dict[str, ActionCallback]) -> None:
        if keyboard is None:
            raise KeyboardUnavailable("pynput is not available")
        self._keymap = {k.lower(): v for k, v in keymap.items()}
        self._stop_event = Event()
        self._listener: Optional[keyboard.Listener] = None

    def start(self) -> None:
        if self._listener:
            return
        self._listener = keyboard.Listener(on_press=self._handle_press)
        self._listener.start()
        log.info("Keyboard listener started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._listener:
            self._listener.stop()
            self._listener.join()
            self._listener = None
        log.info("Keyboard listener stopped")

    def _handle_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        if self._stop_event.is_set():
            return
        key_id = self._normalise(key)
        if not key_id:
            return
        action = self._keymap.get(key_id)
        if action:
            log.info("Key %s pressed", key_id)
            try:
                action()
            except Exception as exc:
                log.exception("Action for key %s failed: %s", key_id, exc)

    def _normalise(self, key: keyboard.Key | keyboard.KeyCode) -> Optional[str]:
        if isinstance(key, keyboard.Key):
            return key.name.lower() if key.name else None
        if isinstance(key, keyboard.KeyCode):
            return key.char.lower() if key.char else None
        return None


__all__ = ["KeyboardHandler", "KeyboardUnavailable"]
