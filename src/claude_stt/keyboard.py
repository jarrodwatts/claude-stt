"""Keyboard output: direct injection or clipboard fallback."""

import logging
import shutil
import subprocess
import time
from typing import Optional

try:
    from pynput.keyboard import Controller, Key
    _PYNPUT_AVAILABLE = True
    _PYNPUT_IMPORT_ERROR: Exception | None = None
except Exception as exc:
    Controller = None
    Key = None
    _PYNPUT_AVAILABLE = False
    _PYNPUT_IMPORT_ERROR = exc

from .config import Config, is_wayland
from .sounds import play_sound
from .window import WindowInfo, restore_focus

# Global keyboard controller
_keyboard: Optional[Controller] = None
_injection_capable: Optional[bool] = None
_injection_checked_at: Optional[float] = None
_injection_cache_ttl = 300.0
_logger = logging.getLogger(__name__)
_pynput_warned = False


def get_keyboard() -> Controller:
    """Get the global keyboard controller."""
    global _keyboard
    if not _PYNPUT_AVAILABLE:
        raise RuntimeError("pynput unavailable; keyboard injection disabled")
    if _keyboard is None:
        _keyboard = Controller()
    return _keyboard


def _warn_pynput_missing() -> None:
    global _pynput_warned
    if _pynput_warned:
        return
    message = "pynput unavailable; falling back to clipboard output"
    if _PYNPUT_IMPORT_ERROR:
        message = f"{message} ({_PYNPUT_IMPORT_ERROR})"
    _logger.warning(message)
    _pynput_warned = True


def _has_wtype() -> bool:
    """Check if wtype is available for Wayland text input."""
    return shutil.which("wtype") is not None


def _output_via_wtype(text: str, config: Config) -> bool:
    """Output text using wtype (Wayland).

    Args:
        text: The text to type.
        config: Configuration.

    Returns:
        True if successful, False otherwise.
    """
    try:
        result = subprocess.run(
            ["wtype", "--", text],
            capture_output=True,
            timeout=10,
        )
        if result.returncode == 0:
            if config.sound_effects:
                play_sound("complete")
            return True
        _logger.warning("wtype failed: %s", result.stderr.decode(errors="replace"))
        return False
    except subprocess.TimeoutExpired:
        _logger.warning("wtype timed out")
        return False
    except Exception:
        _logger.warning("wtype failed", exc_info=True)
        return False


def test_injection() -> bool:
    """Test if keyboard injection works.

    This is a lightweight probe that presses/release a modifier key.
    If it fails, we know injection doesn't work.

    Returns:
        True if injection appears to work, False otherwise.
    """
    global _injection_capable, _injection_checked_at
    now = time.monotonic()

    # Return cached result if still valid
    if (
        _injection_capable is not None
        and _injection_checked_at is not None
        and now - _injection_checked_at < _injection_cache_ttl
    ):
        return _injection_capable

    def cache_result(capable: bool) -> bool:
        global _injection_capable, _injection_checked_at
        _injection_capable = capable
        _injection_checked_at = now
        return capable

    # On Wayland, check for wtype
    if is_wayland():
        return cache_result(_has_wtype())

    if not _PYNPUT_AVAILABLE:
        _warn_pynput_missing()
        return cache_result(False)

    try:
        kb = get_keyboard()
        kb.press(Key.shift)
        kb.release(Key.shift)
        return cache_result(True)
    except Exception:
        return cache_result(False)


def output_text(
    text: str,
    window_info: Optional[WindowInfo] = None,
    config: Optional[Config] = None,
) -> bool:
    """Output transcribed text using the best available method.

    Args:
        text: The text to output.
        window_info: Optional window to restore focus to before typing.
        config: Configuration (uses default if not provided).

    Returns:
        True if text was output successfully, False otherwise.
    """
    if config is None:
        config = Config.load().validate()

    # Determine output mode
    mode = config.output_mode
    if mode == "auto":
        mode = "injection" if test_injection() else "clipboard"
        _logger.debug("Output mode auto-selected: %s", mode)

    if mode != "injection":
        return _output_via_clipboard(text, config)

    if not _PYNPUT_AVAILABLE:
        _warn_pynput_missing()
        return _output_via_clipboard(text, config)

    return _output_via_injection(text, window_info, config)


def _output_via_injection(
    text: str,
    window_info: Optional[WindowInfo],
    config: Config,
) -> bool:
    """Output text by simulating keyboard input.

    Args:
        text: The text to type.
        window_info: Window to restore focus to before typing.
        config: Configuration.

    Returns:
        True if successful, False otherwise.
    """
    try:
        # On Wayland, use wtype
        if is_wayland():
            if _has_wtype():
                return _output_via_wtype(text, config)
            _logger.warning("wtype not available; falling back to clipboard")
            return _output_via_clipboard(text, config)

        if not _PYNPUT_AVAILABLE:
            _warn_pynput_missing()
            return _output_via_clipboard(text, config)
        # Restore focus to original window if provided
        if window_info is not None:
            if not restore_focus(window_info):
                # Can't restore focus (window closed?), fall back to clipboard
                _logger.warning("Focus restore failed; falling back to clipboard")
                return _output_via_clipboard(text, config)

        # Type the text
        kb = get_keyboard()
        kb.type(text)

        if config.sound_effects:
            play_sound("complete")

        return True
    except Exception:
        # Fall back to clipboard on any error
        _logger.warning("Injection failed; falling back to clipboard", exc_info=True)
        return _output_via_clipboard(text, config)


def _output_via_clipboard(text: str, config: Config) -> bool:
    """Output text by copying to clipboard.

    Args:
        text: The text to copy.
        config: Configuration.

    Returns:
        True if successful, False otherwise.
    """
    try:
        try:
            import pyperclip
        except ImportError:
            _logger.error("pyperclip not installed; clipboard output unavailable")
            return False
        if hasattr(pyperclip, "is_available") and not pyperclip.is_available():
            _logger.error("No clipboard mechanism available")
            return False

        pyperclip.copy(text)

        if config.sound_effects:
            play_sound("complete")

        return True
    except Exception:
        if config.sound_effects:
            play_sound("error")
        _logger.warning("Clipboard output failed", exc_info=True)
        return False


def type_text_streaming(text: str) -> bool:
    """Type text character by character for streaming output.

    This is used during live transcription to show words as they're recognized.

    Args:
        text: The text to type.

    Returns:
        True if successful, False otherwise.
    """
    try:
        kb = get_keyboard()
        kb.type(text)
        return True
    except Exception:
        return False
