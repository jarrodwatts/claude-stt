"""Custom error types for claude-stt."""


class STTError(Exception):
    """Base error for claude-stt."""


class HotkeyError(STTError):
    """Hotkey parsing or handling error."""


class EngineError(STTError):
    """STT engine initialization or runtime error."""


class RecorderError(STTError):
    """Audio recorder initialization or runtime error."""


class ConfigError(STTError):
    """Configuration error."""


class DaemonError(STTError):
    """Daemon lifecycle error."""
