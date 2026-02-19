import unittest

from claude_stt.config import Config


class ConfigTests(unittest.TestCase):
    def test_config_validation_clamps_invalid_values(self):
        config = Config(
            mode="bad",
            engine="nope",
            output_mode="wat",
            moonshine_model="moonshine/huge",
            max_recording_seconds=0,
            sample_rate=8000,
        ).validate()

        self.assertEqual(config.mode, "toggle")
        self.assertEqual(config.engine, "moonshine")
        self.assertEqual(config.output_mode, "auto")
        self.assertEqual(config.moonshine_model, "moonshine/huge")
        self.assertEqual(config.max_recording_seconds, 1)
        self.assertEqual(config.sample_rate, 16000)

    def test_moonshine_models_dir_default_is_none(self):
        config = Config()
        self.assertIsNone(config.moonshine_models_dir)

    def test_moonshine_models_dir_tilde_expansion(self):
        config = Config(moonshine_models_dir="~/my-models").validate()
        self.assertNotIn("~", config.moonshine_models_dir)
        self.assertTrue(config.moonshine_models_dir.startswith("/"))

    def test_moonshine_models_dir_none_skipped_in_validate(self):
        config = Config(moonshine_models_dir=None).validate()
        self.assertIsNone(config.moonshine_models_dir)


if __name__ == "__main__":
    unittest.main()
