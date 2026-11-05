from __future__ import annotations

import datetime as dt
import unittest

from qarin.model import AuthorisedChannel, RightsCalendar, Right, Work, WorkKind
from qarin.radar import build_cell, snapshot
from qarin.audience import AudienceRecord


class TestRadar(unittest.TestCase):
    def setUp(self):
        self.work = Work("w1", WorkKind.SERIES, {"ar": "مسلسل"}, "holder",
                         first_broadcast=dt.date(2026, 1, 10))
        self.calendar = RightsCalendar(
            works=[self.work],
            rights=[Right("w1", "EG", "holder", "communication",
                           dt.date(2026, 1, 1), dt.date(2026, 12, 31))],
            channels=[AuthorisedChannel("shahid", "Shahid", "mbc", "svod",
                                       ("EG",), works=("w1",), scope="per_title",
                                       status="VERIFIED")],
        )

    def test_cell_keeps_legal_status_separate_from_supply(self):
        cell = build_cell(self.calendar, "w1", "EG", dt.date(2026, 3, 1), 4,
                          source_ids=("telegram:1", "site:2"))
        self.assertEqual("CONCURRENT_UNAUTHORISED", cell.availability.value)
        self.assertEqual(("shahid",), cell.legal_channels)
        self.assertEqual(4, cell.pirate_offerings)
        self.assertIsNone(cell.public_views)
        self.assertEqual("not collected", cell.public_views_reason)

    def test_missing_views_cannot_be_smuggled_in_as_zero(self):
        with self.assertRaises(ValueError):
            build_cell(self.calendar, "w1", "EG", dt.date(2026, 3, 1), 1,
                       public_views=None, public_views_reason="")

    def test_snapshot_exposes_unmeasured_coverage(self):
        cell = build_cell(self.calendar, "w1", "EG", dt.date(2026, 3, 1), 0)
        data = snapshot((cell,), generated_at="2026-11-05T01:00:00Z").to_dict()
        self.assertEqual("UNMEASURED", data["coverage"]["label"])
        self.assertEqual("not collected", data["cells"][0]["public_views_reason"])

    def test_snapshot_carries_legal_audience_separately(self):
        cell = build_cell(self.calendar, "w1", "EG", dt.date(2026, 3, 1), 0)
        audience = AudienceRecord("w1", "EG", "shahid", "2026-03-01", "2026-03-31",
                                  100, 12.5, "owner-export")
        data = snapshot((cell,), generated_at="2026-11-05T01:00:00Z",
                        legal_audience=(audience,)).to_dict()
        self.assertEqual(100, data["legal_audience"][0]["unique_viewers"])
        self.assertEqual([], data["cells"][0].get("legal_audience", []))


if __name__ == "__main__":
    unittest.main()
