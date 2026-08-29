from datetime import date, timedelta
import unittest

from rsi_screener.signal import find_signal


START = date(2026, 1, 1)


def series(values: list[float]) -> list[tuple[date, float]]:
    return [(START + timedelta(days=i), value) for i, value in enumerate(values)]


class SignalTests(unittest.TestCase):
    def test_qualifies_and_accepts_exact_55_hold(self) -> None:
        match = find_signal(series([38, 40, 41, 50, 60, 55, 58, 63]))
        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match.days_to_60, 2)
        self.assertEqual(match.latest_rsi, 63)


    def test_fails_if_rsi_breaks_55_after_target(self) -> None:
        self.assertIsNone(find_signal(series([39, 41, 52, 61, 54, 62])))


    def test_fails_when_target_takes_more_than_30_days(self) -> None:
        values = [39, 41] + [50] * 30 + [60, 61]
        self.assertIsNone(find_signal(series(values)))


    def test_target_on_thirtieth_step_is_allowed(self) -> None:
        values = [39, 41] + [50] * 29 + [60, 57]
        match = find_signal(series(values))
        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match.days_to_60, 30)


    def test_cross_must_be_inside_latest_60_observations(self) -> None:
        values = [39, 41, 60] + [58] * 60
        self.assertIsNone(find_signal(series(values), lookback=60))


    def test_later_valid_cross_can_qualify_after_earlier_failure(self) -> None:
        values = [39, 41, 60, 54, 39, 42, 61, 57]
        match = find_signal(series(values))
        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match.crossed_on, START + timedelta(days=5))


    def test_target_can_be_reached_on_cross_day(self) -> None:
        match = find_signal(series([39, 40, 60, 61]))
        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match.days_to_60, 0)

    def test_latest_rsi_above_70_is_excluded(self) -> None:
        self.assertIsNone(find_signal(series([39, 41, 60, 69, 70.01])))

    def test_latest_rsi_exactly_70_is_allowed(self) -> None:
        self.assertIsNotNone(find_signal(series([39, 41, 60, 55, 70])))

    def test_fails_if_rsi_exceeds_70_after_target_then_returns_below(self) -> None:
        self.assertIsNone(find_signal(series([39, 41, 60, 71, 65])))

    def test_exactly_70_during_hold_is_allowed(self) -> None:
        self.assertIsNotNone(find_signal(series([39, 41, 60, 70, 65])))
