from __future__ import annotations

from datetime import date
import time

import requests

from rsi_screener.storage import DailyBar
from rsi_screener.metadata import StockMetadata, sector_from_sic


class MassiveProvider:
    """Massive (formerly Polygon.io) grouped daily stock aggregates."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.massive.com",
        timeout: float = 30.0,
    ) -> None:
        if not api_key:
            raise ValueError("MASSIVE_API_KEY is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    def daily_market(self, day: date) -> list[DailyBar]:
        url = (
            f"{self.base_url}/v2/aggs/grouped/locale/us/market/stocks/"
            f"{day.isoformat()}"
        )
        response = self.session.get(
            url,
            params={"adjusted": "true", "include_otc": "false"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") not in {"OK", "DELAYED"}:
            raise RuntimeError(f"Massive API error: {payload.get('error', payload)}")
        return [
            DailyBar(
                day=day,
                ticker=item["T"],
                open=float(item["o"]),
                high=float(item["h"]),
                low=float(item["l"]),
                close=float(item["c"]),
                volume=float(item["v"]),
            )
            for item in payload.get("results", [])
            if all(key in item for key in ("T", "o", "h", "l", "c", "v"))
        ]

    def financial_ratios(self, request_delay: float = 0.0) -> list[StockMetadata]:
        url = f"{self.base_url}/stocks/financials/v1/ratios"
        params = {"limit": 100, "sort": "ticker.asc"}
        rows: list[StockMetadata] = []
        while url:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
            for item in payload.get("results", []):
                rows.append(StockMetadata(
                    ticker=item["ticker"], market_cap=item.get("market_cap"),
                    pe_ratio=item.get("price_to_earnings"), cik=item.get("cik"),
                    fundamentals_as_of=date.fromisoformat(item["date"]) if item.get("date") else None,
                ))
            url = payload.get("next_url")
            params = None
            if url and request_delay:
                time.sleep(request_delay)
        return rows

    def classification(self, ticker: str) -> tuple[str | None, str | None]:
        item = self.ticker_details(ticker)
        return item.sector, item.industry

    def ticker_details(self, ticker: str) -> StockMetadata:
        response = self.session.get(
            f"{self.base_url}/v3/reference/tickers/{ticker}", timeout=self.timeout
        )
        response.raise_for_status()
        item = response.json().get("results", {})
        return StockMetadata(
            ticker=ticker,
            market_cap=item.get("market_cap"),
            sector=sector_from_sic(item.get("sic_code")),
            industry=item.get("sic_description"),
            cik=item.get("cik"),
        )

    def active_common_tickers(self) -> set[str]:
        url = f"{self.base_url}/v3/reference/tickers"
        params = {
            "market": "stocks", "active": "true", "type": "CS",
            "limit": 1000, "sort": "ticker",
        }
        tickers: set[str] = set()
        while url:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
            tickers.update(item["ticker"] for item in payload.get("results", []))
            url = payload.get("next_url")
            params = None
        return tickers
