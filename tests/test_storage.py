from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from rsi_screener.storage import PriceStore


class PriceStoreTests(unittest.TestCase):
    def test_records_downloaded_day_even_when_it_has_no_bars(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "prices.sqlite3"
            with PriceStore(path) as store:
                day = date(2026, 7, 3)
                self.assertFalse(store.has_day(day))
                store.mark_day_downloaded(day, 0)
                self.assertTrue(store.has_day(day))
                self.assertEqual(store.latest_day(), day)
