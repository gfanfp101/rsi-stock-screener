from __future__ import annotations

from datetime import date
from typing import Protocol

from rsi_screener.storage import DailyBar


class DataProvider(Protocol):
    def daily_market(self, day: date) -> list[DailyBar]: ...
