from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from rsi_screener.rsi import wilder_rsi
from rsi_screener.signal import find_signal
from rsi_screener.metadata import StockMetadata


@dataclass(frozen=True)
class ScreenResult:
    ticker: str
    period_start: date
    period_end: date
    latest_rsi: float
    start_average_rsi: float
    latest_average_rsi: float
    average_rsi_change: float
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
        if match:
            results.append(
                ScreenResult(
                    ticker=ticker,
                    period_start=match.period_start,
                    period_end=match.period_end,
                    latest_rsi=match.latest_rsi,
                    start_average_rsi=match.start_average_rsi,
                    latest_average_rsi=match.latest_average_rsi,
                    average_rsi_change=match.average_rsi_change,
                    market_cap=meta.market_cap if meta else None,
                    pe_ratio=meta.pe_ratio if meta else None,
                    sector=meta.sector if meta else None,
                    industry=meta.industry if meta else None,
                )
            )
    return sorted(results, key=lambda item: (-item.average_rsi_change, item.ticker))
