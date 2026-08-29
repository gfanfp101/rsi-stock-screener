from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


@dataclass(frozen=True)
class StockMetadata:
    ticker: str
    market_cap: float | None = None
    pe_ratio: float | None = None
    sector: str | None = None
    industry: str | None = None
    cik: str | None = None
    fundamentals_as_of: date | None = None


SIC_SECTORS = {
    "0": "Agriculture, Forestry & Fishing",
    "1": "Mining & Construction",
    "2": "Manufacturing",
    "3": "Manufacturing",
    "4": "Transportation & Utilities",
    "5": "Wholesale & Retail Trade",
    "6": "Finance, Insurance & Real Estate",
    "7": "Services",
    "8": "Services",
    "9": "Public Administration",
}


def sector_from_sic(sic_code: str | None) -> str | None:
    return SIC_SECTORS.get(sic_code[0]) if sic_code else None


class MetadataStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS stock_metadata (
              ticker TEXT PRIMARY KEY,
              market_cap REAL,
              pe_ratio REAL,
              sector TEXT,
              industry TEXT,
              cik TEXT,
              fundamentals_as_of TEXT,
              updated_at TEXT NOT NULL
            )
            """
        )

    def __enter__(self) -> "MetadataStore": return self
    def __exit__(self, *_: object) -> None: self.connection.close()

    def fundamentals_are_fresh(self, max_age_days: int = 7) -> bool:
        row = self.connection.execute("SELECT MAX(updated_at) FROM stock_metadata").fetchone()
        if not row or not row[0]: return False
        updated = datetime.fromisoformat(row[0])
        return updated >= datetime.now(timezone.utc) - timedelta(days=max_age_days)

    def save_ratios(self, rows: list[StockMetadata]) -> int:
        now = datetime.now(timezone.utc).isoformat()
        self.connection.executemany(
            """
            INSERT INTO stock_metadata(ticker, market_cap, pe_ratio, cik,
              fundamentals_as_of, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET market_cap=excluded.market_cap,
              pe_ratio=excluded.pe_ratio, cik=excluded.cik,
              fundamentals_as_of=excluded.fundamentals_as_of,
              updated_at=excluded.updated_at
            """,
            [(r.ticker, r.market_cap, r.pe_ratio, r.cik,
              r.fundamentals_as_of.isoformat() if r.fundamentals_as_of else None, now)
             for r in rows],
        )
        self.connection.commit(); return len(rows)

    def save_classification(self, ticker: str, sector: str | None, industry: str | None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.connection.execute(
            """INSERT INTO stock_metadata(ticker, sector, industry, updated_at)
            VALUES (?, ?, ?, ?) ON CONFLICT(ticker) DO UPDATE SET
            sector=excluded.sector, industry=excluded.industry""",
            (ticker, sector, industry, now),
        ); self.connection.commit()

    def save_details(self, rows: list[StockMetadata]) -> int:
        now = datetime.now(timezone.utc).isoformat()
        self.connection.executemany(
            """INSERT INTO stock_metadata(ticker, market_cap, sector, industry, cik, updated_at)
            VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(ticker) DO UPDATE SET
            market_cap=excluded.market_cap, sector=excluded.sector,
            industry=excluded.industry, cik=excluded.cik, updated_at=excluded.updated_at""",
            [(r.ticker, r.market_cap, r.sector, r.industry, r.cik, now) for r in rows],
        )
        self.connection.commit()
        return len(rows)

    def missing_classifications(self, tickers: list[str]) -> list[str]:
        if not tickers: return []
        found = {row[0] for row in self.connection.execute(
            f"SELECT ticker FROM stock_metadata WHERE sector IS NOT NULL AND ticker IN ({','.join('?' for _ in tickers)})",
            tickers,
        )}
        return [ticker for ticker in tickers if ticker not in found]

    def all(self) -> dict[str, StockMetadata]:
        result = {}
        for row in self.connection.execute(
            "SELECT ticker,market_cap,pe_ratio,sector,industry,cik,fundamentals_as_of FROM stock_metadata"
        ):
            result[row[0]] = StockMetadata(*row[:6], date.fromisoformat(row[6]) if row[6] else None)
        return result
