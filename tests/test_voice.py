"""Voice temizleme ve ses motoru yardımcı fonksiyon testleri."""

import unittest
from core.voice import clean_text_for_speech


class TestVoiceSpeechCleaning(unittest.TestCase):

    def test_clean_empty(self):
        self.assertEqual(clean_text_for_speech(""), "")
        self.assertEqual(clean_text_for_speech(None), "")

    def test_clean_markdown_formatting(self):
        text = "**Kalın metin**, *italik metin* ve `inline kod`."
        expected = "Kalın metin, italik metin ve inline kod."
        self.assertEqual(clean_text_for_speech(text), expected)

    def test_clean_code_block(self):
        text = "İşte Python örneği:\n```python\ndef test():\n    return 42\n```\nUmarım yardımcı olmuştur."
        result = clean_text_for_speech(text)
        self.assertNotIn("def test", result)
        self.assertNotIn("```", result)
        self.assertIn("İlgili kod bloğunu ekrana yansıttım efendim.", result)
        self.assertIn("Umarım yardımcı olmuştur.", result)

    def test_clean_urls_and_headers(self):
        text = "## Başlık\nDetaylar için https://example.com/api sayfasına bakın."
        result = clean_text_for_speech(text)
        self.assertNotIn("##", result)
        self.assertNotIn("https://", result)
        self.assertIn("Başlık", result)
        self.assertIn("bağlantı adresi", result)

    def test_clean_emojis(self):
        text = "🐉 Merhaba efendim ✨ sistemler hazır 🚀"
        result = clean_text_for_speech(text)
        self.assertNotIn("🐉", result)
        self.assertNotIn("✨", result)
        self.assertNotIn("🚀", result)
        self.assertEqual(result, "Merhaba efendim sistemler hazır")

    def test_long_text_truncation(self):
        long_paragraph = "Bu birinci cümledir. " + ("Bu çok önemli bir detaydır. " * 30)
        result = clean_text_for_speech(long_paragraph)
        self.assertLess(len(result), 750)
        self.assertIn("Devamını ekrandan okuyabilirsiniz efendim.", result)


class TestVoiceEngine(unittest.TestCase):

    def test_voice_engine_defaults(self):
        from core.voice import VoiceEngine

        engine = VoiceEngine()
        self.assertEqual(engine.tts_backend, "edge")
        self.assertEqual(engine.tts_voice, "tr-TR-EmelNeural")
        self.assertEqual(engine.tts_rate, "+0%")
        self.assertEqual(engine.tts_pitch, "+0Hz")
        self.assertEqual(engine.tts_speaking_rate, 1.0)
        self.assertEqual(engine.google_tts_pitch, 0.0)

    def test_voice_pitch_normalization(self):
        import asyncio
        from unittest.mock import AsyncMock, patch
        from core.voice import VoiceEngine
        from pathlib import Path

        engine = VoiceEngine(tts_pitch="-15Hz", tts_rate="-8%")
        # Mock Communicate to verify that rate and pitch were normalized to natural human speech (+0% / +0Hz)
        with patch("edge_tts.Communicate") as mock_comm:
            mock_instance = AsyncMock()
            mock_comm.return_value = mock_instance
            p = Path("dummy.mp3")
            with patch.object(Path, "exists", return_value=True), patch.object(Path, "stat") as mock_stat:
                mock_stat.return_value.st_size = 100
                asyncio.run(engine._save_tts("Merhaba", p))
            
            # verify Communicate was called with normalized rate and pitch
            mock_comm.assert_called_with("Merhaba", voice="tr-TR-EmelNeural", rate="+0%", pitch="+0Hz")


if __name__ == "__main__":
    unittest.main()
