"""Configuration management for claude-stt."""

import logging
import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

try:
    import tomli
    import tomli_w
except ImportError:
    tomli = None
    tomli_w = None

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """claude-stt configuration."""

    # Hotkey settings
    hotkey: str = "ctrl+shift+space"
    mode: Literal["push-to-talk", "toggle"] = "toggle"

    # Engine settings
    engine: Literal["moonshine", "whisper"] = "moonshine"
    moonshine_model: str = "moonshine/base"
    whisper_model: str = "medium"

    # Audio settings
    sample_rate: int = 16000
    max_recording_seconds: int = 300  # 5 minutes

    # Output settings
    output_mode: Literal["injection", "clipboard", "auto"] = "auto"

    # Feedback settings
    sound_effects: bool = True

    @classmethod
    def get_config_dir(cls) -> Path:
        """Get the configuration directory path."""
        # Check for Claude plugin directory first
        plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
        if plugin_root:
            return Path(plugin_root)

        # Fall back to ~/.claude/plugins/claude-stt
        return Path.home() / ".claude" / "plugins" / "claude-stt"

    @classmethod
    def get_config_path(cls) -> Path:
        """Get the configuration file path."""
        return cls.get_config_dir() / "config.toml"

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from file, or return defaults."""
        config_path = cls.get_config_path()

        if not config_path.exists():
            return cls()

        if tomli is None:
            logger.warning("tomli not installed; using default config")
            return cls()

        try:
            with open(config_path, "rb") as f:
                data = tomli.load(f)

            stt_config = data.get("claude-stt", {})
            config = cls(
                hotkey=stt_config.get("hotkey", cls.hotkey),
                mode=stt_config.get("mode", cls.mode),
                engine=stt_config.get("engine", cls.engine),
                moonshine_model=stt_config.get("moonshine_model", cls.moonshine_model),
                whisper_model=stt_config.get("whisper_model", cls.whisper_model),
                sample_rate=stt_config.get("sample_rate", cls.sample_rate),
                max_recording_seconds=stt_config.get(
                    "max_recording_seconds", cls.max_recording_seconds
                ),
                output_mode=stt_config.get("output_mode", cls.output_mode),
                sound_effects=stt_config.get("sound_effects", cls.sound_effects),
            )
            return config.validate()
        except Exception:
            # If config is corrupted, return defaults
            logger.exception("Failed to load config; using defaults")
            return cls().validate()

    def save(self) -> None:
        """Save configuration to file."""
        if tomli_w is None:
            logger.warning("tomli-w not installed; config not saved")
            return

        config_path = self.get_config_path()
        config_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "claude-stt": {
                "hotkey": self.hotkey,
                "mode": self.mode,
                "engine": self.engine,
                "moonshine_model": self.moonshine_model,
                "whisper_model": self.whisper_model,
                "sample_rate": self.sample_rate,
                "max_recording_seconds": self.max_recording_seconds,
                "output_mode": self.output_mode,
                "sound_effects": self.sound_effects,
            }
        }

        try:
            with open(config_path, "wb") as f:
                tomli_w.dump(data, f)
        except Exception:
            logger.exception("Failed to save config")

    def validate(self) -> "Config":
        """Validate and normalize configuration values."""
        if not isinstance(self.hotkey, str) or not self.hotkey.strip():
            logger.warning("Invalid hotkey; defaulting to 'ctrl+shift+space'")
            self.hotkey = "ctrl+shift+space"

        if self.mode not in ("push-to-talk", "toggle"):
            logger.warning("Invalid mode '%s'; defaulting to 'toggle'", self.mode)
            self.mode = "toggle"

        if self.engine not in ("moonshine", "whisper"):
            logger.warning("Invalid engine '%s'; defaulting to 'moonshine'", self.engine)
            self.engine = "moonshine"

        if self.moonshine_model not in ("moonshine/tiny", "moonshine/base"):
            logger.warning(
                "Invalid moonshine_model '%s'; defaulting to 'moonshine/base'",
                self.moonshine_model,
            )
            self.moonshine_model = "moonshine/base"

        if self.output_mode not in ("injection", "clipboard", "auto"):
            logger.warning("Invalid output_mode '%s'; defaulting to 'auto'", self.output_mode)
            self.output_mode = "auto"

        if self.max_recording_seconds < 1:
            logger.warning("max_recording_seconds too low; clamping to 1")
            self.max_recording_seconds = 1
        elif self.max_recording_seconds > 600:
            logger.warning("max_recording_seconds too high; clamping to 600")
            self.max_recording_seconds = 600

        if self.sample_rate != 16000:
            logger.warning("sample_rate %s not supported; forcing 16000", self.sample_rate)
            self.sample_rate = 16000

        return self


def get_platform() -> str:
    """Get the current platform identifier."""
    system = platform.system()
    if system == "Darwin":
        return "macos"
    elif system == "Linux":
        return "linux"
    elif system == "Windows":
        return "windows"
    return "unknown"


def is_wayland() -> bool:
    """Check if running under Wayland on Linux."""
    if get_platform() != "linux":
        return False
    return os.environ.get("XDG_SESSION_TYPE") == "wayland"
