import unittest

from claude_stt.config import Config
from claude_stt.engine_factory import build_engine
from claude_stt.errors import EngineError


class EngineFactoryTests(unittest.TestCase):
    def test_unknown_engine_rejected(self):
        config = Config(engine="unknown").validate()
        # validate defaults to moonshine, so force raw config
        config.engine = "unknown"
        with self.assertRaises(EngineError):
            build_engine(config)

    def test_whisper_unimplemented(self):
        config = Config(engine="whisper")
        with self.assertRaises(EngineError):
            build_engine(config)


if __name__ == "__main__":
    unittest.main()
