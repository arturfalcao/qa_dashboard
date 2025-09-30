from __future__ import annotations

import logging
import subprocess
import wave
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

try:
    import pyaudio
except ImportError:  # pragma: no cover - optional feature
    pyaudio = None

try:
    import whisper
except ImportError:  # pragma: no cover - optional feature
    whisper = None


class VoiceRecordingUnavailable(RuntimeError):
    pass


class VoiceRecorder:
    def __init__(
        self,
        rate: int = 16_000,
        channels: int = 1,
        chunk: int = 1024,
        device_index: Optional[int] = None,
    ) -> None:
        if pyaudio is None:
            raise VoiceRecordingUnavailable("pyaudio is not available")
        self._rate = rate
        self._channels = channels
        self._chunk = chunk
        self._device_index = device_index
        self._pa = pyaudio.PyAudio()
        self._whisper_model = None

    def record(self, duration: int, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_wav = output_path.with_suffix(".wav")
        stream = self._pa.open(
            format=pyaudio.paInt16,
            channels=self._channels,
            rate=self._rate,
            input=True,
            frames_per_buffer=self._chunk,
            input_device_index=self._device_index,
        )
        frames = []
        try:
            for _ in range(0, int(self._rate / self._chunk * duration)):
                data = stream.read(self._chunk, exception_on_overflow=False)
                frames.append(data)
        finally:
            stream.stop_stream()
            stream.close()

        with wave.open(str(tmp_wav), "wb") as wf:
            wf.setnchannels(self._channels)
            wf.setsampwidth(self._pa.get_sample_size(pyaudio.paInt16))
            wf.setframerate(self._rate)
            wf.writeframes(b"".join(frames))

        self._convert_to_mp3(tmp_wav, output_path)
        tmp_wav.unlink(missing_ok=True)
        log.info("Voice clip stored at %s", output_path)
        return output_path

    def transcribe(self, audio_path: Path, model_size: str = "tiny") -> Optional[str]:
        if whisper is None:
            log.warning("Whisper not installed; skipping transcription")
            return None
        if self._whisper_model is None:
            self._whisper_model = whisper.load_model(model_size)
        result = self._whisper_model.transcribe(str(audio_path))
        return result.get("text", "").strip()

    def close(self) -> None:
        self._pa.terminate()

    def _convert_to_mp3(self, input_path: Path, output_path: Path) -> None:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-codec:a",
            "libmp3lame",
            str(output_path),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as exc:
            raise VoiceRecordingUnavailable(f"ffmpeg conversion failed: {exc.stderr}") from exc


__all__ = ["VoiceRecorder", "VoiceRecordingUnavailable"]
