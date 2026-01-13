"""Configuration management for claude-stt."""

import os
import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

try:
    import tomli
    import tomli_w
except ImportError:
    tomli = None
    tomli_w = None


@dataclass
class Config:
    """claude-stt configuration."""

    # Hotkey settings
    hotkey: str = "ctrl+shift+space"
    mode: Literal["push-to-talk", "toggle"] = "push-to-talk"

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
            return cls()

        try:
            with open(config_path, "rb") as f:
                data = tomli.load(f)

            stt_config = data.get("claude-stt", {})
            return cls(
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
        except Exception:
            # If config is corrupted, return defaults
            return cls()

    def save(self) -> None:
        """Save configuration to file."""
        if tomli_w is None:
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

        with open(config_path, "wb") as f:
            tomli_w.dump(data, f)


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
