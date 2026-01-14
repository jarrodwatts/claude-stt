import contextlib
import io
import unittest

from claude_stt import __version__
from claude_stt import cli


class CliTests(unittest.TestCase):
    def test_version_flag(self) -> None:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            exit_code = cli.main(["--version"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(buffer.getvalue().strip(), __version__)


if __name__ == "__main__":
    unittest.main()
