import unittest

from rsi_screener.rsi import wilder_rsi


class RsiTests(unittest.TestCase):
    def test_known_wilder_rsi_example(self) -> None:
        closes = [
            44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42,
            45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28,
        ]
        self.assertAlmostEqual(wilder_rsi(closes)[14], 70.46, places=2)


    def test_flat_market_is_neutral(self) -> None:
        self.assertEqual(wilder_rsi([10.0] * 15)[-1], 50.0)


    def test_short_history_is_warmup_only(self) -> None:
        self.assertEqual(wilder_rsi([1.0, 2.0], period=14), [None, None])
