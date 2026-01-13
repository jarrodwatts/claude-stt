"""Global hotkey detection using pynput."""

import logging
import queue
import threading
import platform
from typing import Callable, Optional

from pynput import keyboard

from .errors import HotkeyError


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
        self._is_recording = False
        self._pressed_keys: set = set()
        self._hotkey_active = False
        self._lock = threading.Lock()
        self._logger = logging.getLogger(__name__)
        self._event_queue: "queue.Queue[Optional[tuple[str, Optional[Callable[[], None]]]]]" = (
            queue.Queue(maxsize=8)
        )
        self._worker_thread: Optional[threading.Thread] = None
        self._worker_stop = threading.Event()

        # Parse the hotkey
        self._hotkey_keys = self._parse_hotkey(hotkey)
        if not self._hotkey_keys:
            raise ValueError(f"Hotkey '{hotkey}' did not map to any keys")

    def _parse_hotkey(self, hotkey_str: str) -> set:
        """Parse hotkey string to a set of keys.

        Args:
            hotkey_str: Hotkey like "<ctrl>+<shift>+space" or "ctrl+shift+space".

        Returns:
            Set of key objects.
        """
        if not hotkey_str.strip():
            raise HotkeyError("Hotkey cannot be empty")

        try:
            normalized = self._normalize_hotkey_string(hotkey_str)
            keys = keyboard.HotKey.parse(normalized)
        except Exception as exc:
            raise HotkeyError(f"Invalid hotkey '{hotkey_str}': {exc}") from exc

        normalized: set = set()
        for key in keys:
            normalized_key = self._normalize_key(key)
            if normalized_key is not None:
                normalized.add(normalized_key)
        return normalized

    def _normalize_hotkey_string(self, hotkey_str: str) -> str:
        parts = [part.strip() for part in hotkey_str.split("+") if part.strip()]
        if not parts:
            return hotkey_str

        key_map = {
            "ctrl": "<ctrl>",
            "control": "<ctrl>",
            "shift": "<shift>",
            "alt": "<alt>",
            "cmd": "<cmd>",
            "command": "<cmd>",
            "space": "<space>",
            "enter": "<enter>",
            "return": "<enter>",
            "tab": "<tab>",
            "esc": "<esc>",
            "escape": "<esc>",
        }

        normalized_parts = []
        for part in parts:
            lowered = part.lower()
            if lowered.startswith("<") and lowered.endswith(">"):
                normalized_parts.append(lowered)
                continue
            if lowered in key_map:
                normalized_parts.append(key_map[lowered])
                continue
            if lowered.startswith("f") and lowered[1:].isdigit():
                normalized_parts.append(f"<{lowered}>")
                continue
            normalized_parts.append(lowered)

        return "+".join(normalized_parts)

    def _ensure_worker(self) -> None:
        if self._worker_thread and self._worker_thread.is_alive():
            return
        self._worker_stop.clear()
        self._worker_thread = threading.Thread(
            target=self._event_worker,
            name="claude-stt-hotkey-worker",
            daemon=True,
        )
        self._worker_thread.start()

    def _event_worker(self) -> None:
        while not self._worker_stop.is_set():
            try:
                item = self._event_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if item is None:
                return
            label, callback = item
            if not callback:
                continue
            try:
                callback()
            except Exception:
                self._logger.exception("Hotkey callback failed: %s", label)

    def _enqueue_event(self, label: str, callback: Optional[Callable[[], None]]) -> None:
        self._ensure_worker()
        try:
            self._event_queue.put_nowait((label, callback))
        except queue.Full:
            self._logger.warning("Dropping hotkey event '%s'; queue full", label)

    def _normalize_key(self, key) -> Optional[object]:
        """Normalize a key to a comparable form."""
        if hasattr(key, "char") and key.char:
            if key.char == " ":
                return keyboard.Key.space
            if key.char in ("\n", "\r"):
                return keyboard.Key.enter
            return keyboard.KeyCode.from_char(key.char.lower())

        if hasattr(key, "vk") and key.vk is not None:
            if platform.system() == "Darwin":
                mac_vk_map = {
                    49: keyboard.Key.space,
                    36: keyboard.Key.enter,
                    48: keyboard.Key.tab,
                    53: keyboard.Key.esc,
                }
                if key.vk in mac_vk_map:
                    return mac_vk_map[key.vk]

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
                if self._hotkey_active:
                    return
                self._hotkey_active = True
                if self.mode == "toggle":
                    # Toggle mode: press to start/stop
                    if not self._is_recording:
                        self._is_recording = True
                        self._enqueue_event("start", self.on_start)
                    else:
                        self._is_recording = False
                        self._enqueue_event("stop", self.on_stop)
                else:
                    # Push-to-talk: press to start
                    if not self._is_recording:
                        self._is_recording = True
                        self._enqueue_event("start", self.on_start)

    def _on_release(self, key):
        """Handle key release event."""
        normalized = self._normalize_key(key)
        if normalized is None:
            return

        with self._lock:
            self._pressed_keys.discard(normalized)
            if normalized in self._hotkey_keys:
                self._hotkey_active = False

            # In push-to-talk mode, release any hotkey key to stop
            if self.mode == "push-to-talk" and self._is_recording:
                if normalized in self._hotkey_keys:
                    self._is_recording = False
                    self._enqueue_event("stop", self.on_stop)

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
            self._ensure_worker()
            return True
        except Exception as e:
            self._logger.error("Failed to start hotkey listener: %s", e)
            return False

    def stop(self):
        """Stop listening for hotkeys."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
            self._pressed_keys.clear()
            self._is_recording = False
        self._worker_stop.set()
        try:
            self._event_queue.put_nowait(None)
        except queue.Full:
            pass
        if self._worker_thread:
            self._worker_thread.join(timeout=1.0)
            if self._worker_thread.is_alive():
                self._logger.warning("Hotkey worker did not exit cleanly")

    def is_running(self) -> bool:
        """Check if listener is running."""
        return self._listener is not None and self._listener.is_alive()

    @property
    def is_recording(self) -> bool:
        """Check if currently in recording state."""
        return self._is_recording
