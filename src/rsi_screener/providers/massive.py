from __future__ import annotations

from datetime import date

import requests

from rsi_screener.storage import DailyBar


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
