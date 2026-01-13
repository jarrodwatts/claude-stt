"""Global hotkey detection using pynput."""

import threading
from typing import Callable, Optional

from pynput import keyboard


class HotkeyListener:
    """Listens for global hotkey events.

    Supports both push-to-talk (hold to record) and toggle modes.
    """

    def __init__(
        self,
        hotkey: str = "<ctrl>+<shift>+space",
        on_start: Optional[Callable[[], None]] = None,
        on_stop: Optional[Callable[[], None]] = None,
        mode: str = "push-to-talk",
    ):
        """Initialize the hotkey listener.

        Args:
            hotkey: Hotkey combination string (pynput format).
            on_start: Callback when recording should start.
            on_stop: Callback when recording should stop.
            mode: "push-to-talk" or "toggle".
        """
        self.hotkey_str = hotkey
        self.on_start = on_start
        self.on_stop = on_stop
        self.mode = mode

        self._listener: Optional[keyboard.Listener] = None
        self._hotkey: Optional[keyboard.HotKey] = None
        self._is_recording = False
        self._pressed_keys: set = set()
        self._lock = threading.Lock()

        # Parse the hotkey
        self._hotkey_keys = self._parse_hotkey(hotkey)

    def _parse_hotkey(self, hotkey_str: str) -> set:
        """Parse hotkey string to a set of keys.

        Args:
            hotkey_str: Hotkey like "<ctrl>+<shift>+space" or "ctrl+shift+space".

        Returns:
            Set of key objects.
        """
        keys = set()
        parts = hotkey_str.lower().replace("<", "").replace(">", "").split("+")

        key_map = {
            "ctrl": keyboard.Key.ctrl,
            "control": keyboard.Key.ctrl,
            "shift": keyboard.Key.shift,
            "alt": keyboard.Key.alt,
            "cmd": keyboard.Key.cmd,
            "command": keyboard.Key.cmd,
            "space": keyboard.Key.space,
            "enter": keyboard.Key.enter,
            "return": keyboard.Key.enter,
            "tab": keyboard.Key.tab,
            "esc": keyboard.Key.esc,
            "escape": keyboard.Key.esc,
        }

        for part in parts:
            part = part.strip()
            if part in key_map:
                keys.add(key_map[part])
            elif len(part) == 1:
                # Single character key
                keys.add(keyboard.KeyCode.from_char(part))
            elif part.startswith("f") and part[1:].isdigit():
                # Function key
                try:
                    fkey = getattr(keyboard.Key, part)
                    keys.add(fkey)
                except AttributeError:
                    pass

        return keys

    def _normalize_key(self, key) -> Optional[object]:
        """Normalize a key to a comparable form."""
        if hasattr(key, "char") and key.char:
            return keyboard.KeyCode.from_char(key.char.lower())

        # Handle left/right modifier variants
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            return keyboard.Key.ctrl
        if key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
            return keyboard.Key.shift
        if key in (keyboard.Key.alt_l, keyboard.Key.alt_r):
            return keyboard.Key.alt
        if key in (keyboard.Key.cmd_l, keyboard.Key.cmd_r):
            return keyboard.Key.cmd

        return key

    def _on_press(self, key):
        """Handle key press event."""
        normalized = self._normalize_key(key)
        if normalized is None:
            return

        with self._lock:
            self._pressed_keys.add(normalized)

            # Check if hotkey combination is pressed
            if self._hotkey_keys.issubset(self._pressed_keys):
                if self.mode == "toggle":
                    # Toggle mode: press to start/stop
                    if not self._is_recording:
                        self._is_recording = True
                        if self.on_start:
                            threading.Thread(target=self.on_start).start()
                    else:
                        self._is_recording = False
                        if self.on_stop:
                            threading.Thread(target=self.on_stop).start()
                else:
                    # Push-to-talk: press to start
                    if not self._is_recording:
                        self._is_recording = True
                        if self.on_start:
                            threading.Thread(target=self.on_start).start()

    def _on_release(self, key):
        """Handle key release event."""
        normalized = self._normalize_key(key)
        if normalized is None:
            return

        with self._lock:
            self._pressed_keys.discard(normalized)

            # In push-to-talk mode, release any hotkey key to stop
            if self.mode == "push-to-talk" and self._is_recording:
                if normalized in self._hotkey_keys:
                    self._is_recording = False
                    if self.on_stop:
                        threading.Thread(target=self.on_stop).start()

    def start(self) -> bool:
        """Start listening for hotkeys.

        Returns:
            True if listener started successfully.
        """
        if self._listener is not None:
            return True

        try:
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
            self._listener.start()
            return True
        except Exception as e:
            print(f"Failed to start hotkey listener: {e}")
            return False

    def stop(self):
        """Stop listening for hotkeys."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
            self._pressed_keys.clear()
            self._is_recording = False

    def is_running(self) -> bool:
        """Check if listener is running."""
        return self._listener is not None and self._listener.is_alive()

    @property
    def is_recording(self) -> bool:
        """Check if currently in recording state."""
        return self._is_recording
