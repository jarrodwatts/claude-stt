import unittest

from claude_stt.config import Config
from claude_stt.engine_factory import build_engine
from claude_stt.engines.moonshine import MoonshineEngine
from claude_stt.engines.whisper import WhisperEngine
from claude_stt.errors import EngineError


class EngineFactoryTests(unittest.TestCase):
    def test_unknown_engine_rejected(self):
        config = Config(engine="unknown").validate()
        # validate defaults to moonshine, so force raw config
        config.engine = "unknown"
        with self.assertRaises(EngineError):
            build_engine(config)

    def test_whisper_engine_constructed(self):
        config = Config(engine="whisper")
        engine = build_engine(config)
        self.assertIsInstance(engine, WhisperEngine)

    def test_moonshine_engine_receives_models_dir(self):
        config = Config(engine="moonshine", moonshine_models_dir="/tmp/my-models")
        engine = build_engine(config)
        self.assertIsInstance(engine, MoonshineEngine)
        self.assertEqual(engine.models_dir, "/tmp/my-models")

    def test_moonshine_engine_models_dir_none_by_default(self):
        config = Config(engine="moonshine")
        engine = build_engine(config)
        self.assertIsInstance(engine, MoonshineEngine)
        self.assertIsNone(engine.models_dir)


if __name__ == "__main__":
    unittest.main()
