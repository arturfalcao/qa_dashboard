from __future__ import annotations

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Dict

log = logging.getLogger(__name__)


class HealthServer:
    def __init__(self, host: str, port: int, status_provider: Callable[[], Dict]) -> None:
        self._status_provider = status_provider
        handler = self._build_handler()
        self._httpd = ThreadingHTTPServer((host, port), handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, name="health-server", daemon=True)

    def start(self) -> None:
        log.info("Health server starting on %s:%s", *self._httpd.server_address)
        self._thread.start()

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self._thread.join(timeout=2)
        log.info("Health server stopped")

    def _build_handler(self) -> type[BaseHTTPRequestHandler]:
        status_provider = self._status_provider

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # type: ignore[override]
                if self.path != "/health":
                    self.send_error(404)
                    return
                try:
                    payload = status_provider()
                except Exception as exc:  # pragma: no cover - best effort
                    log.exception("Health status provider failed: %s", exc)
                    payload = {"status": "error", "message": str(exc)}
                body = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args) -> None:  # noqa: A003 - suppress noisy logs
                return

        return Handler


__all__ = ["HealthServer"]
