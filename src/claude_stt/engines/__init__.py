"""STT engine implementations."""

from typing import Protocol
import numpy as np


class STTEngine(Protocol):
    """Protocol for STT engines."""

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribe audio to text.

        Args:
            audio: Audio data as numpy array.
            sample_rate: Sample rate of the audio.

        Returns:
            Transcribed text.
        """
        ...

    def is_available(self) -> bool:
        """Check if the engine is available."""
        ...

    def load_model(self) -> bool:
        """Load the model. Returns True if successful."""
        ...
