# Edge Photo Inspection System

Python edge application intended for a Raspberry Pi 5 that captures inspection photos, records short defect annotations, and synchronises data with a backend API.

## Features
- High-resolution photo capture with timestamp overlay using `picamera2`.
- Keyboard-driven workflow for capture, defect flagging, and piece completion.
- Optional 5-second audio note recording with Whisper transcription.
- Local storage management with automatic cleanup and upload retry queue backed by SQLite.
- REST API integration with exponential retry and offline-first behaviour.
- Automatic discovery of the active inspection session via `GET /api/edge/session/current` (no manual config edits).
- Optional status LEDs (green/yellow/red) and lightweight HTTP health check on port 8080.

## Project Layout
```
.
├── api_client.py
├── camera.py
├── config.json
├── config_manager.py
├── health_server.py
├── keyboard_handler.py
├── logging_utils.py
├── main.py
├── queue.db              # created on first run
├── queue_manager.py
├── status_leds.py
├── storage_manager.py
├── upload_worker.py
├── voice_recorder.py
└── logs/
    └── app.log           # created automatically when local logging fallback is used
```

## Hardware Triggers
| Key | Action |
| --- | ------ |
| `1` or `F1` | Capture photo |
| `2` or `F2` | Flag defect (records audio + transcript) |
| `3` or `F3` | Flag potential defect |
| `4` or `F4` | Complete current piece / advance |

## Installation (Raspberry Pi OS)
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3-pip python3-picamera2 python3-pyaudio ffmpeg -y
pip3 install requests pynput python-dotenv openai-whisper Pillow gpiozero
```

Optional: install Whisper dependencies once the virtual environment is ready (the `tiny` model is loaded by default).

## Configuration
Edit `config.json` (or supply an alternate path via `--config`). No session or lot identifiers are required—the device polls the backend for the active assignment every 10 seconds.

```json
{
  "device_secret": "EDGE-tenant-slug-workbench-01-abc123def456",
  "api_base_url": "http://your-api-server:3001",
  "camera_resolution": [1920, 1080],
  "photo_quality": 90
}
```

## Running
```bash
cd /home/pi/edge-device
python3 main.py --config config.json
```

A health endpoint is available at `http://<device-ip>:8080/health`.

## Systemd Service
Install the supplied unit file (`edge-device.service`) into `/etc/systemd/system/`, reload, enable, and start:

```bash
sudo cp edge-device.service /etc/systemd/system/edge-device.service
sudo systemctl daemon-reload
sudo systemctl enable edge-device
sudo systemctl start edge-device
```

## Maintenance Tasks
- Photos and audio clips older than 7 days are pruned automatically.
- When storage usage exceeds 80%, warnings are logged.
- Failed uploads remain in `queue.db` and are retried with exponential backoff.
- Session state lives entirely in RAM; if no active session is found the device pauses capture automatically.
- Media is stored under `/home/pi/edge-photos` by default (configurable inside the code if needed).

## Development Notes
- Logging is written to `/var/log/edge-device.log`; if permissions are insufficient it falls back to `logs/app.log`.
- The application exits if the camera or keyboard libraries are unavailable.
- Voice recording/transcription is optional; failures are logged and defect submissions are skipped when transcripts are unavailable.
