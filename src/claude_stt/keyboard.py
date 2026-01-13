"""Keyboard output: direct injection or clipboard fallback."""

from typing import Optional
import logging
import time

from pynput.keyboard import Controller, Key

from .config import Config, is_wayland
from .sounds import play_sound
from .window import WindowInfo, restore_focus

# Global keyboard controller
_keyboard: Optional[Controller] = None
_injection_capable: Optional[bool] = None
_injection_checked_at: Optional[float] = None
_injection_cache_ttl = 300.0
_logger = logging.getLogger(__name__)


def get_keyboard() -> Controller:
    """Get the global keyboard controller."""
    global _keyboard
    if _keyboard is None:
        _keyboard = Controller()
    return _keyboard


def test_injection() -> bool:
    """Test if keyboard injection works.

    This is a lightweight probe that presses/release a modifier key.
    If it fails, we know injection doesn't work.

    Returns:
        True if injection appears to work, False otherwise.
    """
    global _injection_capable, _injection_checked_at
    now = time.monotonic()
    if (
        _injection_capable is not None
        and _injection_checked_at is not None
        and now - _injection_checked_at < _injection_cache_ttl
    ):
        return _injection_capable

    # On Wayland, injection typically doesn't work
    if is_wayland():
        _injection_capable = False
        _injection_checked_at = now
        return _injection_capable

    try:
        kb = get_keyboard()
        # Try a simple key press/release
        kb.press(Key.shift)
        kb.release(Key.shift)
        _injection_capable = True
        _injection_checked_at = now
        return _injection_capable
    except Exception:
        _injection_capable = False
        _injection_checked_at = now
        return _injection_capable


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
        config = Config.load()

    # Determine output mode
    mode = config.output_mode
    if mode == "auto":
        mode = "injection" if test_injection() else "clipboard"
        _logger.debug("Output mode auto-selected: %s", mode)

    if mode == "injection":
        return _output_via_injection(text, window_info, config)
    else:
        return _output_via_clipboard(text, config)


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
