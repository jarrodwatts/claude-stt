import unittest

from claude_stt.config import Config
from claude_stt import keyboard


class KeyboardOutputTests(unittest.TestCase):
    def test_output_falls_back_when_pynput_missing(self):
        original_available = keyboard._PYNPUT_AVAILABLE
        original_clipboard = keyboard._output_via_clipboard
        original_checked = keyboard._injection_checked_at
        original_capable = keyboard._injection_capable
        try:
            keyboard._PYNPUT_AVAILABLE = False
            keyboard._injection_checked_at = None
            keyboard._injection_capable = None
            captured = {}

            def fake_clipboard(text, config):
                captured["text"] = text
                return True

            keyboard._output_via_clipboard = fake_clipboard
            config = Config(output_mode="auto")
            result = keyboard.output_text("hello", config=config)
            self.assertTrue(result)
            self.assertEqual(captured["text"], "hello")
        finally:
            keyboard._PYNPUT_AVAILABLE = original_available
            keyboard._output_via_clipboard = original_clipboard
            keyboard._injection_checked_at = original_checked
            keyboard._injection_capable = original_capable


if __name__ == "__main__":
    unittest.main()
