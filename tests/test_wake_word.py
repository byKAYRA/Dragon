"""Wake-word modülü testleri."""

import unittest
from core.wake_word import WakeWordListener


class TestWakeWord(unittest.TestCase):

    def test_initial_state_and_muted(self):
        listener = WakeWordListener(on_wake=lambda _text: None)
        self.assertFalse(listener._running)
        self.assertFalse(listener.muted)

        listener.muted = True
        self.assertTrue(listener.muted)

        listener.muted = False
        self.assertFalse(listener.muted)


if __name__ == "__main__":
    unittest.main()
