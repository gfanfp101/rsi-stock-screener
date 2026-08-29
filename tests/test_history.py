from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest

from rsi_screener.history import ScreenHistoryStore
from rsi_screener.screener import ScreenResult


class ScreenHistoryTests(unittest.TestCase):
    def test_rerun_replaces_same_date_without_duplicates(self) -> None:
        item = ScreenResult("ABC", date(2026, 1, 1), date(2026, 1, 20), 66, 50, 60, 1,
                            market_cap=2_000_000_000)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "history.sqlite3"
            with ScreenHistoryStore(path) as store:
                store.replace_day(date(2026, 1, 20), [item])
                store.replace_day(date(2026, 1, 20), [item])
            db = sqlite3.connect(path)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM screen_results").fetchone()[0], 1)
