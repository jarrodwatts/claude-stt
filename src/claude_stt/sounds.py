"""Audio feedback using native system sounds."""

import logging
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Literal

SoundEvent = Literal["start", "stop", "complete", "error", "warning"]
_logger = logging.getLogger(__name__)

# macOS system sounds
MACOS_SOUNDS = {
    "start": "/System/Library/Sounds/Blow.aiff",
    "stop": "/System/Library/Sounds/Pop.aiff",
    "complete": "/System/Library/Sounds/Glass.aiff",
    "error": "/System/Library/Sounds/Basso.aiff",
    "warning": "/System/Library/Sounds/Sosumi.aiff",
}

# Linux sound paths (common locations)
LINUX_SOUNDS = {
    "start": "/usr/share/sounds/freedesktop/stereo/device-added.oga",
    "stop": "/usr/share/sounds/freedesktop/stereo/device-removed.oga",
    "complete": "/usr/share/sounds/freedesktop/stereo/complete.oga",
    "error": "/usr/share/sounds/freedesktop/stereo/dialog-error.oga",
    "warning": "/usr/share/sounds/freedesktop/stereo/dialog-warning.oga",
}


def play_sound(event: SoundEvent) -> None:
    """Play a native system sound for the given event.

    Args:
        event: The type of sound event to play.
    """
    system = platform.system()

    try:
        if system == "Darwin":
            _play_macos_sound(event)
        elif system == "Linux":
            _play_linux_sound(event)
        elif system == "Windows":
            _play_windows_sound(event)
    except Exception:
        # Silently fail if sound playback doesn't work
        pass


def _play_macos_sound(event: SoundEvent) -> None:
    """Play sound on macOS using afplay."""
    sound_file = MACOS_SOUNDS.get(event)
    if not sound_file:
        return
    if not Path(sound_file).exists():
        _logger.debug("Sound file missing: %s", sound_file)
        return
    if shutil.which("afplay") is None:
        _logger.debug("afplay not available")
        return
    subprocess.Popen(
        ["afplay", sound_file],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _play_linux_sound(event: SoundEvent) -> None:
    """Play sound on Linux using paplay or aplay."""
    sound_file = LINUX_SOUNDS.get(event)
    if not sound_file:
        return
    if not Path(sound_file).exists():
        _logger.debug("Sound file missing: %s", sound_file)
        return

    # Try paplay first (PulseAudio/PipeWire)
    if shutil.which("paplay"):
        subprocess.Popen(
            ["paplay", sound_file],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return

    # Fall back to aplay (ALSA)
    if shutil.which("aplay"):
        subprocess.Popen(
            ["aplay", "-q", sound_file],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def _play_windows_sound(event: SoundEvent) -> None:
    """Play sound on Windows using winsound."""
    try:
        import winsound

        # Map events to Windows system sounds
        sound_map = {
            "start": winsound.MB_OK,
            "stop": winsound.MB_OK,
            "complete": winsound.MB_OK,
            "error": winsound.MB_ICONHAND,
            "warning": winsound.MB_ICONEXCLAMATION,
        }

        sound_type = sound_map.get(event, winsound.MB_OK)
        winsound.MessageBeep(sound_type)
    except ImportError:
        _logger.debug("winsound not available")
