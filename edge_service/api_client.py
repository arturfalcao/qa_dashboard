from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests

log = logging.getLogger(__name__)


class ApiError(RuntimeError):
    pass


class ApiClient:
    def __init__(self, base_url: str, device_secret: str, timeout: int = 15) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {"X-Device-Secret": device_secret}
        self._session = requests.Session()
        self._timeout = timeout

    def ping(self) -> bool:
        try:
            self._request("GET", "/edge/ping")
            return True
        except Exception as exc:
            log.error("Ping failed: %s", exc)
            return False

    def get_current_session(self) -> Optional[Dict[str, Any]]:
        try:
            response = self._request_raw("GET", "/edge/session/current")
        except ApiError:
            raise
        except Exception as exc:
            raise ApiError(f"Failed to fetch current session: {exc}") from exc
        try:
            if response.status_code in (204, 304):
                return None
            if response.status_code >= 400:
                if response.status_code in (404, 409):
                    return None
                raise ApiError(f"HTTP {response.status_code}: {response.text[:200]}")
            if response.headers.get("content-type", "").startswith("application/json"):
                return response.json()
            return None
        finally:
            response.close()

    def upload_photo(self, photo_path: Path, session_id: str, piece_id: Optional[str]) -> Dict[str, Any]:
        files = {"photo": open(photo_path, "rb")}
        data = {"sessionId": session_id, "pieceId": piece_id}
        try:
            return self._request("POST", "/edge/photo/upload", files=files, data=data)
        finally:
            files["photo"].close()

    def flag_defect(self, piece_id: str, transcript: str) -> Dict[str, Any]:
        body = {"pieceId": piece_id, "audioTranscript": transcript}
        return self._request("POST", "/edge/defect/flag", json=body)

    def flag_potential(self, piece_id: str, transcript: str) -> Dict[str, Any]:
        body = {"pieceId": piece_id, "audioTranscript": transcript}
        return self._request("POST", "/edge/defect/potential", json=body)

    def complete_piece(self, session_id: str, piece_id: str, status: str) -> Dict[str, Any]:
        body = {"sessionId": session_id, "pieceId": piece_id, "status": status}
        return self._request("POST", "/edge/piece/complete", json=body)

    def _request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        url = f"{self._base_url}{path}"
        headers = kwargs.pop("headers", {})
        headers.update(self._headers)
        backoff = 1
        for attempt in range(3):
            try:
                response = self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    timeout=self._timeout,
                    **kwargs,
                )
                if response.status_code >= 400:
                    raise ApiError(f"HTTP {response.status_code}: {response.text[:200]}")
                if response.headers.get("content-type", "").startswith("application/json"):
                    return response.json()
                return {"status": "ok"}
            except Exception as exc:
                log.warning("API %s failed (%s/%s): %s", path, attempt + 1, 3, exc)
                if attempt == 2:
                    raise
                time.sleep(backoff)
                backoff *= 2
        raise ApiError("unreachable")

    def _request_raw(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = f"{self._base_url}{path}"
        headers = kwargs.pop("headers", {})
        headers.update(self._headers)
        return self._session.request(
            method=method,
            url=url,
            headers=headers,
            timeout=self._timeout,
            **kwargs,
        )


__all__ = ["ApiClient", "ApiError"]
