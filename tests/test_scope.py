from __future__ import annotations

import unittest

from qarin.scope import ARABIC_BASELINE, OPTIONAL_COMPETITOR, scope


class TestScope(unittest.TestCase):
    def test_baseline_has_ten_distinct_markets(self):
        self.assertEqual(10, len(ARABIC_BASELINE))
        self.assertEqual(10, len({market.code for market in ARABIC_BASELINE}))
        self.assertTrue(all(market.status == "NOT_CONFIGURED" for market in ARABIC_BASELINE))

    def test_turkey_is_explicitly_optional(self):
        self.assertNotIn(OPTIONAL_COMPETITOR, scope())
        self.assertIn(OPTIONAL_COMPETITOR, scope(include_optional=True))

    def test_market_status_is_validated(self):
        with self.assertRaisesRegex(ValueError, "unknown market"):
            type(ARABIC_BASELINE[0])("XX", "Unknown", "other", status="LIVE")
