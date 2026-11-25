import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import outfit  # noqa: E402


def scenario(name):
    feed = outfit.load_feed(name)
    w = outfit.extract_today(feed, "Meetstation Schiphol")
    return w, outfit.classify(w, outfit.load_config())


class TestScenarios(unittest.TestCase):
    def test_good(self):
        w, (level, _) = scenario("good")
        self.assertEqual(level, "GOOD")
        self.assertIn("Sunglasses & sunscreen", outfit.outfit(w))

    def test_bad(self):
        w, (level, reasons) = scenario("bad")
        self.assertEqual(level, "BAD")
        self.assertTrue(any("rain" in r for r in reasons))
        self.assertIn("Waterproof jacket", outfit.outfit(w))

    def test_severe(self):
        w, (level, reasons) = scenario("severe")
        self.assertEqual(level, "SEVERE")
        msg = outfit.build_message(w, level, reasons)
        self.assertEqual(msg["priority"], 5)
        self.assertIn("KNMI", msg["message"])

    def test_dry_run_cli(self):
        for name in ("good", "bad", "severe"):
            self.assertEqual(outfit.main(["--test", name, "--dry-run"]), 0)

    def test_missing_topic_fails(self):
        import os
        os.environ.pop("NTFY_TOPIC", None)
        real = outfit.load_config
        outfit.load_config = lambda: {k: v for k, v in real().items() if k != "ntfy_topic"}
        try:
            self.assertEqual(outfit.main(["--test", "good"]), 1)
        finally:
            outfit.load_config = real


if __name__ == "__main__":
    unittest.main()
