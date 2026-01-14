import queue
import time
import unittest

try:
    from pynput import keyboard
    _PYNPUT_AVAILABLE = True
except Exception:
    keyboard = None
    _PYNPUT_AVAILABLE = False

from claude_stt.hotkey import HotkeyListener
from claude_stt.errors import HotkeyError


@unittest.skipUnless(_PYNPUT_AVAILABLE, "pynput unavailable in this environment")
class HotkeyListenerTests(unittest.TestCase):
    def _press_hotkey(self, listener: HotkeyListener) -> None:
        for key in listener._hotkey_keys:
            listener._on_press(key)

    def _release_hotkey(self, listener: HotkeyListener) -> None:
        key = self._primary_key(listener)
        listener._on_release(key)

    def _primary_key(self, listener: HotkeyListener):
        if keyboard.Key.space in listener._hotkey_keys:
            return keyboard.Key.space
        return next(iter(listener._hotkey_keys))

    def _next_event(self, events: "queue.Queue[str]", timeout: float = 0.5) -> str:
        return events.get(timeout=timeout)

    def test_toggle_mode_debounces_hotkey_repeat(self):
        events: "queue.Queue[str]" = queue.Queue()

        listener = HotkeyListener(
            hotkey="ctrl+shift+space",
            mode="toggle",
            on_start=lambda: events.put("start"),
            on_stop=lambda: events.put("stop"),
        )

        self._press_hotkey(listener)
        self.assertEqual(self._next_event(events), "start")

        # Repeat press while still held should not toggle again.
        listener._on_press(self._primary_key(listener))
        time.sleep(0.05)
        self.assertTrue(events.empty())

        self._release_hotkey(listener)
        listener._on_press(self._primary_key(listener))
        self.assertEqual(self._next_event(events), "stop")

    def test_push_to_talk_stops_on_release(self):
        events: "queue.Queue[str]" = queue.Queue()

        listener = HotkeyListener(
            hotkey="ctrl+shift+space",
            mode="push-to-talk",
            on_start=lambda: events.put("start"),
            on_stop=lambda: events.put("stop"),
        )

        self._press_hotkey(listener)
        self.assertEqual(self._next_event(events), "start")

        self._release_hotkey(listener)
        self.assertEqual(self._next_event(events), "stop")

    def test_invalid_hotkey_rejected(self):
        with self.assertRaises(HotkeyError):
            HotkeyListener(hotkey="")
        with self.assertRaises(HotkeyError):
            HotkeyListener(hotkey="ctrl+unknownkey")


if __name__ == "__main__":
    unittest.main()
