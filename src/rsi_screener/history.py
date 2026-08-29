from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from rsi_screener.screener import ScreenResult


class ScreenHistoryStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS screen_results (
            screen_date TEXT NOT NULL, rank INTEGER NOT NULL, ticker TEXT NOT NULL,
            market_cap REAL, pe_ratio REAL, sector TEXT, industry TEXT,
            period_start TEXT NOT NULL, period_end TEXT NOT NULL, latest_rsi REAL NOT NULL,
            start_average_rsi REAL NOT NULL, latest_average_rsi REAL NOT NULL,
            average_rsi_change REAL NOT NULL,
            PRIMARY KEY(screen_date, ticker))"""
        )

    def __enter__(self) -> "ScreenHistoryStore": return self
    def __exit__(self, *_: object) -> None: self.connection.close()

    def replace_day(self, screen_date: date, results: list[ScreenResult]) -> None:
        day = screen_date.isoformat()
        self.connection.execute("DELETE FROM screen_results WHERE screen_date=?", (day,))
        self.connection.executemany(
            """INSERT INTO screen_results VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(day, rank, item.ticker, item.market_cap, item.pe_ratio, item.sector,
              item.industry, item.period_start.isoformat(), item.period_end.isoformat(),
              item.latest_rsi, item.start_average_rsi, item.latest_average_rsi,
              item.average_rsi_change)
             for rank, item in enumerate(results, 1)],
        )
        self.connection.commit()
