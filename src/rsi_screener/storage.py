from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class DailyBar:
    day: date
    ticker: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class PriceStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_prices (
                day TEXT NOT NULL,
                ticker TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                PRIMARY KEY (day, ticker)
            )
            """
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_prices_ticker_day "
            "ON daily_prices(ticker, day)"
        )

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "PriceStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def has_day(self, day: date) -> bool:
        row = self.connection.execute(
            "SELECT 1 FROM daily_prices WHERE day = ? LIMIT 1", (day.isoformat(),)
        ).fetchone()
        return row is not None

    def save(self, bars: Iterable[DailyBar]) -> int:
        rows = [
            (
                bar.day.isoformat(), bar.ticker, bar.open, bar.high,
                bar.low, bar.close, bar.volume,
            )
            for bar in bars
        ]
        self.connection.executemany(
            """
            INSERT INTO daily_prices(day, ticker, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(day, ticker) DO UPDATE SET
              open=excluded.open, high=excluded.high, low=excluded.low,
              close=excluded.close, volume=excluded.volume
            """,
            rows,
        )
        self.connection.commit()
        return len(rows)

    def histories(self, limit: int = 160) -> dict[str, list[tuple[date, float]]]:
        rows = self.connection.execute(
            """
            SELECT ticker, day, close FROM (
              SELECT ticker, day, close,
                     ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY day DESC) n
              FROM daily_prices
            ) WHERE n <= ? ORDER BY ticker, day
            """,
            (limit,),
        )
        histories: dict[str, list[tuple[date, float]]] = {}
        for ticker, day, close in rows:
            histories.setdefault(ticker, []).append(
                (date.fromisoformat(day), float(close))
            )
        return histories
