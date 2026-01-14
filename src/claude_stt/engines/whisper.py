"""Whisper STT engine using faster-whisper."""

from __future__ import annotations

import logging
import os
from typing import Optional

import numpy as np

_whisper_available = False
_WhisperModel = None

try:
    from faster_whisper import WhisperModel as _WhisperModel

    _whisper_available = True
except ImportError:
    pass


class WhisperEngine:
    """Whisper speech-to-text engine backed by faster-whisper."""

    def __init__(
        self,
        model_name: str = "medium",
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
    ):
        self.model_name = model_name
        self.device = device or os.environ.get("CLAUDE_STT_WHISPER_DEVICE", "cpu")
        self.compute_type = compute_type or os.environ.get(
            "CLAUDE_STT_WHISPER_COMPUTE_TYPE",
            "int8",
        )
        self._model: Optional[object] = None
        self._logger = logging.getLogger(__name__)

    def is_available(self) -> bool:
        return _whisper_available

    def load_model(self) -> bool:
        if not self.is_available():
            return False
        if self._model is not None:
            return True
        try:
            self._model = _WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
            return True
        except Exception:
            self._logger.exception("Failed to load Whisper model")
            return False

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        if not self.load_model():
            return ""
        try:
            if audio.dtype != np.float32:
                audio = audio.astype(np.float32)
            segments, _info = self._model.transcribe(audio, sample_rate=sample_rate)
            text = " ".join(segment.text.strip() for segment in segments)
            return text.strip()
        except Exception:
            self._logger.exception("Whisper transcription failed")
            return ""
