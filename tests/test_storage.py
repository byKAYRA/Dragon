"""Storage katmanı birim testleri."""

import tempfile
import unittest
from pathlib import Path
from core import storage


class TestStorage(unittest.TestCase):

    def test_obfuscation(self):
        plain_key = "AIzaSySecretTestKey12345"
        obfuscated = storage._obfuscate(plain_key)
        self.assertNotEqual(plain_key, obfuscated)
        self.assertTrue(obfuscated.startswith(storage._KEY_PREFIX))

        recovered = storage._deobfuscate(obfuscated)
        self.assertEqual(plain_key, recovered)

    def test_workspace_path(self):
        ws = storage.workspace_path()
        self.assertIsInstance(ws, Path)

    def test_default_settings(self):
        settings = storage.load_settings()
        self.assertIn("model", settings)
        self.assertIn("assistant_name", settings)
        self.assertEqual(settings["assistant_name"], "Dragon")


if __name__ == "__main__":
    unittest.main()
