from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from rsi_screener.rsi import wilder_rsi
from rsi_screener.signal import find_signal


@dataclass(frozen=True)
class ScreenResult:
    ticker: str
    crossed_on: date
    reached_60_on: date
    latest_rsi: float
    days_to_60: int


def screen_histories(
    histories: dict[str, list[tuple[date, float]]],
) -> list[ScreenResult]:
    results: list[ScreenResult] = []
    for ticker, history in histories.items():
        scores = wilder_rsi([close for _, close in history], period=14)
        dated_scores = [
            (day, score)
            for (day, _), score in zip(history, scores)
            if score is not None
        ]
        match = find_signal(dated_scores)
        if match and match.crossed_on and match.reached_60_on:
            results.append(
                ScreenResult(
                    ticker=ticker,
                    crossed_on=match.crossed_on,
                    reached_60_on=match.reached_60_on,
                    latest_rsi=match.latest_rsi,
                    days_to_60=match.days_to_60,
                )
            )
    return sorted(results, key=lambda item: (-item.latest_rsi, item.ticker))
