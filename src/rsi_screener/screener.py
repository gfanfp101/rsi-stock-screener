from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from rsi_screener.rsi import wilder_rsi
from rsi_screener.signal import find_signal
from rsi_screener.metadata import StockMetadata


@dataclass(frozen=True)
class ScreenResult:
    ticker: str
    crossed_on: date
    reached_60_on: date
    latest_rsi: float
    days_to_60: int
    market_cap: float | None = None
    pe_ratio: float | None = None
    sector: str | None = None
    industry: str | None = None


def screen_histories(
    histories: dict[str, list[tuple[date, float]]],
    metadata: dict[str, StockMetadata] | None = None,
    min_market_cap: float | None = None,
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
        meta = (metadata or {}).get(ticker)
        if min_market_cap is not None and (not meta or meta.market_cap is None or meta.market_cap < min_market_cap):
            continue
        if match and match.crossed_on and match.reached_60_on:
            results.append(
                ScreenResult(
                    ticker=ticker,
                    crossed_on=match.crossed_on,
                    reached_60_on=match.reached_60_on,
                    latest_rsi=match.latest_rsi,
                    days_to_60=match.days_to_60,
                    market_cap=meta.market_cap if meta else None,
                    pe_ratio=meta.pe_ratio if meta else None,
                    sector=meta.sector if meta else None,
                    industry=meta.industry if meta else None,
                )
            )
    if min_market_cap is not None:
        return sorted(results, key=lambda item: (-(item.market_cap or 0), item.ticker))
    return sorted(results, key=lambda item: (-item.latest_rsi, item.ticker))
