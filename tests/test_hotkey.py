import queue
import time
import unittest

from pynput import keyboard

from claude_stt.hotkey import HotkeyListener
from claude_stt.errors import HotkeyError


class HotkeyListenerTests(unittest.TestCase):
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

        listener._on_press(keyboard.Key.ctrl)
        listener._on_press(keyboard.Key.shift)
        listener._on_press(keyboard.Key.space)
        self.assertEqual(self._next_event(events), "start")

        # Repeat press while still held should not toggle again.
        listener._on_press(keyboard.Key.space)
        time.sleep(0.05)
        self.assertTrue(events.empty())

        listener._on_release(keyboard.Key.space)
        listener._on_press(keyboard.Key.space)
        self.assertEqual(self._next_event(events), "stop")

    def test_push_to_talk_stops_on_release(self):
        events: "queue.Queue[str]" = queue.Queue()

        listener = HotkeyListener(
            hotkey="ctrl+shift+space",
            mode="push-to-talk",
            on_start=lambda: events.put("start"),
            on_stop=lambda: events.put("stop"),
        )

        listener._on_press(keyboard.Key.ctrl)
        listener._on_press(keyboard.Key.shift)
        listener._on_press(keyboard.Key.space)
        self.assertEqual(self._next_event(events), "start")

        listener._on_release(keyboard.Key.space)
        self.assertEqual(self._next_event(events), "stop")

    def test_invalid_hotkey_rejected(self):
        with self.assertRaises(HotkeyError):
            HotkeyListener(hotkey="")
        with self.assertRaises(HotkeyError):
            HotkeyListener(hotkey="ctrl+unknownkey")


if __name__ == "__main__":
    unittest.main()
