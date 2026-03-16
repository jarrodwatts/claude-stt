"""MLX Whisper STT engine — GPU-accelerated whisper on Apple Silicon."""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

_mlx_whisper_available = False
_transcribe_fn = None

try:
    from mlx_whisper import transcribe as _transcribe_fn
    _mlx_whisper_available = True
except ImportError:
    pass


class MLXWhisperEngine:
    """Whisper speech-to-text engine backed by mlx-whisper for Apple Silicon."""

    def __init__(self, model_name: str = "mlx-community/whisper-large-v3-mlx"):
        self.model_name = model_name
        self._logger = logging.getLogger(__name__)

    def is_available(self) -> bool:
        return _mlx_whisper_available

    def load_model(self) -> bool:
        return self.is_available()

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        if not self.is_available():
            return ""
        try:
            if audio.dtype != np.float32:
                audio = audio.astype(np.float32)
            result = _transcribe_fn(
                audio,
                path_or_hf_repo=self.model_name,
                verbose=False,
            )
            return result.get("text", "").strip()
        except Exception:
            self._logger.exception("MLX Whisper transcription failed")
            return ""
