from __future__ import annotations

import logging
from typing import Optional

log = logging.getLogger(__name__)

try:
    from gpiozero import LED, BadPinFactory
except ImportError:  # pragma: no cover - optional hardware
    LED = None
    BadPinFactory = Exception  # type: ignore[assignment]


class StatusLEDs:
    def __init__(self, green_pin: int = 17, yellow_pin: int = 27, red_pin: int = 22) -> None:
        self._enabled = LED is not None
        if not self._enabled:
            log.info("GPIO LEDs not available; skipping setup")
            self._green = self._yellow = self._red = None
            return
        try:
            self._green = LED(green_pin)
            self._yellow = LED(yellow_pin)
            self._red = LED(red_pin)
        except (BadPinFactory, RuntimeError, Exception) as exc:  # pragma: no cover - depends on hardware
            log.warning("GPIO LEDs disabled: %s", exc)
            self._enabled = False
            self._green = self._yellow = self._red = None
            return
        self.set_idle()

    def set_idle(self) -> None:
        if not self._enabled:
            return
        self._set_states(green=True, yellow=False, red=False)

    def set_processing(self) -> None:
        if not self._enabled:
            return
        self._set_states(green=False, yellow=True, red=False)

    def set_error(self) -> None:
        if not self._enabled:
            return
        self._set_states(green=False, yellow=False, red=True)

    def set_success(self) -> None:
        if not self._enabled:
            return
        self._set_states(green=True, yellow=False, red=False)

    def close(self) -> None:
        for led in (self._green, self._yellow, self._red):
            if led:
                led.close()

    def _set_states(self, green: bool, yellow: bool, red: bool) -> None:
        if not self._enabled:
            return
        if not self._green or not self._yellow or not self._red:
            return
        self._green.value = 1 if green else 0
        self._yellow.value = 1 if yellow else 0
        self._red.value = 1 if red else 0


__all__ = ["StatusLEDs"]
