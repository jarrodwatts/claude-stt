"""Moonshine STT engine - fast local speech-to-text."""

from typing import Optional
import logging
import numpy as np

# Try to import moonshine
_moonshine_available = False
_transcribe_fn = None
_MoonshineModel = None

try:
    from moonshine_onnx.transcribe import transcribe as _transcribe_fn
    from moonshine_onnx import MoonshineOnnxModel as _MoonshineModel
    _moonshine_available = True
except ImportError:
    pass


class MoonshineEngine:
    """Moonshine speech-to-text engine.

    Moonshine is optimized for fast, accurate ASR on resource-constrained devices.
    It processes audio ~5x faster than Whisper.

    Models:
        - moonshine/tiny: ~190MB, fastest
        - moonshine/base: ~400MB, better accuracy
    """

    def __init__(self, model_name: str = "moonshine/base"):
        """Initialize the Moonshine engine.

        Args:
            model_name: Model to use ("moonshine/tiny" or "moonshine/base").
        """
        self.model_name = model_name
        self._model: Optional[object] = None
        self._logger = logging.getLogger(__name__)

    def is_available(self) -> bool:
        """Check if Moonshine is available."""
        return _moonshine_available

    def load_model(self) -> bool:
        """Load the Moonshine model.

        The model will be downloaded automatically on first use if not cached.

        Returns:
            True if model loaded successfully.
        """
        if not self.is_available():
            return False

        if self._model is not None:
            return True

        try:
            self._model = _MoonshineModel(model_name=self.model_name)
            return True
        except Exception:
            self._logger.exception("Failed to load Moonshine model")
            return False

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribe audio to text.

        Args:
            audio: Audio data as numpy array (float32, mono, 16kHz recommended).
            sample_rate: Sample rate of the audio.

        Returns:
            Transcribed text, or empty string if transcription fails.
        """
        if not self.load_model():
            return ""

        try:
            # Moonshine expects float32 audio normalized to [-1, 1]
            if audio.dtype != np.float32:
                audio = audio.astype(np.float32)

            # Normalize if needed
            max_val = np.abs(audio).max()
            if max_val > 1.0:
                audio = audio / max_val

            # Use the transcribe function from moonshine_onnx
            result = _transcribe_fn(audio, model=self._model)

            # Result is a list of strings (batch results)
            if isinstance(result, list) and len(result) > 0:
                return result[0].strip()
            elif isinstance(result, str):
                return result.strip()

            return ""

        except Exception:
            self._logger.exception("Transcription failed")
            return ""

    def transcribe_streaming(
        self,
        audio_chunks: list[np.ndarray],
        sample_rate: int = 16000,
    ) -> str:
        """Transcribe accumulated audio chunks.

        For streaming, we accumulate chunks and re-transcribe the whole buffer.
        This gives us updated results as more audio comes in.

        Args:
            audio_chunks: List of audio chunks.
            sample_rate: Sample rate.

        Returns:
            Current transcription of all audio so far.
        """
        if not audio_chunks:
            return ""

        # Concatenate all chunks
        audio = np.concatenate(audio_chunks)

        return self.transcribe(audio, sample_rate)
