from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence


@dataclass(frozen=True)
class SignalMatch:
    period_start: date
    period_end: date
    latest_rsi: float
    start_average_rsi: float
    latest_average_rsi: float
    average_rsi_change: float


def find_signal(
    dated_rsi: Sequence[tuple[date, float]],
    *,
    trend_days: int = 14,
    average_period: int = 14,
    minimum_latest_rsi: float = 65.0,
    maximum_latest_rsi: float = 70.0,
) -> SignalMatch | None:
    """Match a non-decreasing 14-day trend in the SMA of daily RSI values."""
    if trend_days < 2 or average_period < 1:
        raise ValueError("trend_days must be at least 2 and average_period positive")
    required = average_period + trend_days - 1
    if (
        len(dated_rsi) < required
        or dated_rsi[-1][1] <= minimum_latest_rsi
        or dated_rsi[-1][1] > maximum_latest_rsi
    ):
        return None

    source = list(dated_rsi[-required:])
    trend_rsi = source[-trend_days:]
    if any(value > maximum_latest_rsi for _, value in trend_rsi):
        return None
    averages = [
        sum(value for _, value in source[index:index + average_period]) / average_period
        for index in range(trend_days)
    ]
    if any(current < previous for previous, current in zip(averages, averages[1:])):
        return None

    return SignalMatch(
        period_start=source[average_period - 1][0],
        period_end=source[-1][0],
        latest_rsi=source[-1][1],
        start_average_rsi=averages[0],
        latest_average_rsi=averages[-1],
        average_rsi_change=(averages[-1] - averages[0]) / (trend_days - 1),
    )
