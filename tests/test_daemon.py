import os
import tempfile
import unittest

from claude_stt import daemon


class DaemonPidTests(unittest.TestCase):
    def test_pid_file_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["CLAUDE_STT_CONFIG_DIR"] = temp_dir
            try:
                daemon._write_pid_file(os.getpid())
                data = daemon._read_pid_file()
                self.assertIsNotNone(data)
                self.assertEqual(data["pid"], os.getpid())
                self.assertIn("command", data)
                self.assertIn("created_at", data)
            finally:
                os.environ.pop("CLAUDE_STT_CONFIG_DIR", None)

    def test_pid_file_legacy_format(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["CLAUDE_STT_CONFIG_DIR"] = temp_dir
            try:
                pid_path = daemon.get_pid_file()
                pid_path.parent.mkdir(parents=True, exist_ok=True)
                pid_path.write_text(str(os.getpid()))
                data = daemon._read_pid_file()
                self.assertIsNotNone(data)
                self.assertEqual(data["pid"], os.getpid())
            finally:
                os.environ.pop("CLAUDE_STT_CONFIG_DIR", None)

    def test_stale_pid_file_removed_when_not_claude_stt(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["CLAUDE_STT_CONFIG_DIR"] = temp_dir
            original_get_process_command = daemon._get_process_command
            try:
                daemon._write_pid_file(os.getpid())
                daemon._get_process_command = lambda pid: "python other-process"
                self.assertFalse(daemon.is_daemon_running())
                self.assertFalse(daemon.get_pid_file().exists())
            finally:
                daemon._get_process_command = original_get_process_command
                os.environ.pop("CLAUDE_STT_CONFIG_DIR", None)


if __name__ == "__main__":
    unittest.main()
