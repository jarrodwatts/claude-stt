"""Keyboard output: direct injection or clipboard fallback."""

import time
from typing import Optional

from pynput.keyboard import Controller, Key

from .config import Config, is_wayland
from .sounds import play_sound
from .window import WindowInfo, restore_focus

# Global keyboard controller
_keyboard: Optional[Controller] = None


def get_keyboard() -> Controller:
    """Get the global keyboard controller."""
    global _keyboard
    if _keyboard is None:
        _keyboard = Controller()
    return _keyboard


def test_injection() -> bool:
    """Test if keyboard injection works.

    This is a simple test that attempts to type a zero-width space
    and immediately delete it. If it fails, we know injection doesn't work.

    Returns:
        True if injection appears to work, False otherwise.
    """
    # On Wayland, injection typically doesn't work
    if is_wayland():
        return False

    try:
        kb = get_keyboard()
        # Try a simple key press/release
        kb.press(Key.shift)
        kb.release(Key.shift)
        return True
    except Exception:
        return False


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
                return _output_via_clipboard(text, config)

        # Type the text
        kb = get_keyboard()
        kb.type(text)

        if config.sound_effects:
            play_sound("complete")

        return True
    except Exception:
        # Fall back to clipboard on any error
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
        import pyperclip

        pyperclip.copy(text)

        if config.sound_effects:
            play_sound("complete")

        return True
    except Exception:
        if config.sound_effects:
            play_sound("error")
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
