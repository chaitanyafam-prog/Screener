import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from backend.src.shared import linking  # noqa: E402


class ScreeningTokenTest(unittest.TestCase):
    def test_round_trip(self):
        token = linking.make_token(42, "test-secret")
        self.assertEqual(linking.read_token(token, "test-secret"), 42)

    def test_invalid_or_expired_token_is_rejected(self):
        token = linking.make_token(42, "test-secret")
        self.assertIsNone(linking.read_token(token, "wrong-secret"))
        self.assertIsNone(linking.read_token(token, "test-secret", max_age=-1))
        self.assertIsNone(linking.read_token("", "test-secret"))


if __name__ == "__main__":
    unittest.main()
