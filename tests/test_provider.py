from datetime import date
import unittest
from unittest.mock import Mock

from rsi_screener.providers.massive import MassiveProvider


class ProviderTests(unittest.TestCase):
    def test_massive_maps_grouped_daily_response(self) -> None:
        provider = MassiveProvider("secret")
        response = Mock()
        response.json.return_value = {
            "status": "OK",
            "results": [{"T": "ABC", "o": 1, "h": 3, "l": 0.5, "c": 2, "v": 100}],
        }
        response.raise_for_status.return_value = None
        provider.session.get = Mock(return_value=response)
        bars = provider.daily_market(date(2026, 8, 27))
        self.assertEqual(len(bars), 1)
        self.assertEqual(bars[0].ticker, "ABC")
        self.assertEqual(bars[0].close, 2.0)
        self.assertEqual(
            provider.session.get.call_args.kwargs["params"]["adjusted"], "true"
        )
        self.assertNotIn("apiKey", provider.session.get.call_args.kwargs["params"])
        self.assertEqual(provider.session.headers["Authorization"], "Bearer secret")
