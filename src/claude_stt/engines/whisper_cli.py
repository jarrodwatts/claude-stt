"""Whisper.cpp CLI engine — uses Metal GPU acceleration on Apple Silicon."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np

try:
    import soundfile as sf
    _soundfile_available = True
except ImportError:
    sf = None
    _soundfile_available = False


class WhisperCliEngine:
    """Speech-to-text engine backed by whisper-cli (whisper.cpp).

    Uses Metal GPU acceleration on Apple Silicon for fast inference
    with the ggml-large-v3-turbo model.
    """

    DEFAULT_MODEL_PATHS = [
        "/opt/homebrew/share/whisper-cpp/ggml-large-v3-turbo.bin",
        str(Path.home() / ".cache/whisper/ggml-large-v3-turbo.bin"),
    ]

    def __init__(
        self,
        model_path: Optional[str] = None,
        command: str = "whisper-cli",
    ):
        self.command = command
        self.model_path = model_path or self._find_model()
        self._logger = logging.getLogger(__name__)

    def _find_model(self) -> Optional[str]:
        for path in self.DEFAULT_MODEL_PATHS:
            if os.path.isfile(path):
                return path
        return None

    def is_available(self) -> bool:
        return shutil.which(self.command) is not None and self.model_path is not None

    def load_model(self) -> bool:
        if not self.is_available():
            self._logger.error(
                "whisper-cli not found or model missing (looked for: %s)",
                ", ".join(self.DEFAULT_MODEL_PATHS),
            )
            return False
        # whisper-cli loads the model per invocation, so just verify the file exists
        if not os.path.isfile(self.model_path):
            self._logger.error("Model file not found: %s", self.model_path)
            return False
        self._logger.info("whisper-cli engine ready (model: %s)", self.model_path)
        return True

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        if not self.model_path:
            return ""

        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        max_val = np.abs(audio).max()
        if max_val > 1.0:
            audio = audio / max_val

        tmp_wav = None
        try:
            with tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False
            ) as f:
                tmp_wav = f.name
                if _soundfile_available:
                    sf.write(tmp_wav, audio, sample_rate, subtype="PCM_16")
                else:
                    self._write_wav(tmp_wav, audio, sample_rate)

            result = subprocess.run(
                [
                    self.command,
                    "-m", self.model_path,
                    "-f", tmp_wav,
                    "--no-prints",
                    "--no-timestamps",
                    "-t", "4",
                    "-l", "en",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                self._logger.error("whisper-cli failed: %s", result.stderr.strip())
                return ""

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            self._logger.error("whisper-cli timed out")
            return ""
        except Exception:
            self._logger.exception("whisper-cli transcription failed")
            return ""
        finally:
            if tmp_wav and os.path.exists(tmp_wav):
                os.unlink(tmp_wav)

    @staticmethod
    def _write_wav(path: str, audio: np.ndarray, sample_rate: int) -> None:
        """Write a minimal WAV file without soundfile."""
        import struct

        pcm = (audio * 32767).astype(np.int16)
        data = pcm.tobytes()
        n_channels = 1
        sampwidth = 2

        with open(path, "wb") as f:
            f.write(b"RIFF")
            f.write(struct.pack("<I", 36 + len(data)))
            f.write(b"WAVE")
            f.write(b"fmt ")
            f.write(struct.pack("<I", 16))
            f.write(struct.pack("<HH", 1, n_channels))
            f.write(struct.pack("<I", sample_rate))
            f.write(struct.pack("<I", sample_rate * n_channels * sampwidth))
            f.write(struct.pack("<HH", n_channels * sampwidth, sampwidth * 8))
            f.write(b"data")
            f.write(struct.pack("<I", len(data)))
            f.write(data)
