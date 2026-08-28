from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Sequence


@dataclass(frozen=True)
class SignalMatch:
    crossed_on: date | None
    reached_60_on: date | None
    latest_rsi: float
    days_to_60: int


def find_signal(
    dated_rsi: Sequence[tuple[date, float]],
    *,
    lookback: int = 60,
    max_days_to_target: int = 30,
    cross_level: float = 40.0,
    target_level: float = 60.0,
    hold_level: float = 55.0,
) -> SignalMatch | None:
    """Find the most recent qualifying momentum sequence.

    A cross is `previous <= cross_level` and `current > cross_level`. The first
    target reading after that cross must occur within max_days_to_target index
    steps, and every reading from the target through the latest must hold.
    """
    if not dated_rsi:
        return None
    window = list(dated_rsi[-lookback:])
    if len(window) < 2:
        return None

    for cross_index in range(len(window) - 1, 0, -1):
        previous = window[cross_index - 1][1]
        current = window[cross_index][1]
        if not (previous <= cross_level < current):
            continue
        last_target_index = min(
            len(window) - 1, cross_index + max_days_to_target
        )
        target_index = next(
            (
                index
                for index in range(cross_index, last_target_index + 1)
                if window[index][1] >= target_level
            ),
            None,
        )
        if target_index is None:
            continue
        if all(value >= hold_level for _, value in window[target_index:]):
            return SignalMatch(
                crossed_on=window[cross_index][0],
                reached_60_on=window[target_index][0],
                latest_rsi=window[-1][1],
                days_to_60=target_index - cross_index,
            )
    return None
