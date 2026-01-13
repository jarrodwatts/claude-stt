"""STT engine construction and validation."""

from .config import Config
from .engines import STTEngine
from .engines.moonshine import MoonshineEngine
from .errors import EngineError


def build_engine(config: Config) -> STTEngine:
    """Create an engine instance for the configured engine."""
    if config.engine == "moonshine":
        return MoonshineEngine(model_name=config.moonshine_model)
    if config.engine == "whisper":
        raise EngineError("Whisper engine not implemented")
    raise EngineError(f"Unknown engine '{config.engine}'")
