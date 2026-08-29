from datetime import date, timedelta
import unittest

from rsi_screener.signal import find_signal


START = date(2026, 1, 1)


def series(values: list[float]) -> list[tuple[date, float]]:
    return [(START + timedelta(days=i), value) for i, value in enumerate(values)]


class SignalTests(unittest.TestCase):
    def test_qualifies_when_average_rsi_never_decreases(self) -> None:
        match = find_signal(series(list(range(40, 67))))
        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match.latest_rsi, 66)
        self.assertAlmostEqual(match.average_rsi_change, 1.0)

    def test_rejects_any_decrease_in_average_rsi(self) -> None:
        values = [50.0] * 26 + [49.0, 66.0]
        self.assertIsNone(find_signal(series(values)))

    def test_equal_average_is_allowed(self) -> None:
        self.assertIsNotNone(find_signal(series([66.0] * 27)))

    def test_latest_rsi_must_be_strictly_above_65(self) -> None:
        self.assertIsNone(find_signal(series([65.0] * 27)))
        self.assertIsNotNone(find_signal(series([65.01] * 27)))

    def test_latest_rsi_must_not_exceed_70(self) -> None:
        self.assertIsNotNone(find_signal(series([70.0] * 27)))
        self.assertIsNone(find_signal(series([70.01] * 27)))

    def test_rejects_rsi_above_70_anywhere_in_trend_window(self) -> None:
        values = list(range(40, 67))
        values[-5] = 70.01
        self.assertIsNone(find_signal(series(values)))

    def test_requires_enough_history_for_fourteen_averages(self) -> None:
        self.assertIsNone(find_signal(series([66.0] * 26)))

    def test_invalid_periods_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            find_signal(series([66.0] * 27), trend_days=1)
