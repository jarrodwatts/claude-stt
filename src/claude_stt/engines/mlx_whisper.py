"""MLX Whisper STT engine - GPU-accelerated speech-to-text for Apple Silicon."""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

_mlx_whisper_available = False

try:
    import mlx_whisper as _mlx_whisper

    _mlx_whisper_available = True
except ImportError:
    _mlx_whisper = None


class MlxWhisperEngine:
    """Whisper speech-to-text engine backed by mlx-whisper for Apple Silicon."""

    def __init__(self, model_name: str = "mlx-community/whisper-large-v3-turbo"):
        self.model_name = model_name
        self._logger = logging.getLogger(__name__)

    def is_available(self) -> bool:
        return _mlx_whisper_available

    def load_model(self) -> bool:
        if not self.is_available():
            return False
        # mlx-whisper loads the model on first transcribe call and caches it.
        return True

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        if not self.is_available():
            return ""
        try:
            if audio.dtype != np.float32:
                audio = audio.astype(np.float32)

            result = _mlx_whisper.transcribe(
                audio,
                path_or_hf_repo=self.model_name,
            )
            text = result.get("text", "")
            return text.strip()
        except Exception:
            self._logger.exception("MLX Whisper transcription failed")
            return ""
