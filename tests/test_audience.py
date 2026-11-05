from __future__ import annotations

import unittest

from qarin.audience import AudienceRecord


class TestAudienceRecord(unittest.TestCase):
    def valid(self, **changes):
        values = {
            "work_id": "w1", "territory": "EG", "channel_id": "shahid",
            "period_start": "2026-01-01", "period_end": "2026-01-31",
            "unique_viewers": 1200, "watch_hours": 3400.5,
            "source": "owner-export-2026-01", "device_share": {"mobile": .7, "tv": .3},
            "demographic_share": {"18-24": .4, "25-44": .6},
            "sponsor_ids": ("sponsor-a",), "affiliate_ids": ("affiliate-a",),
        }
        values.update(changes)
        return AudienceRecord(**values)

    def test_serialises_aggregate_legal_audience_only(self):
        record = self.valid()
        data = record.to_dict()
        self.assertEqual(1200, data["unique_viewers"])
        self.assertEqual(.7, data["device_share"]["mobile"])
        self.assertNotIn("user_id", data)

    def test_rejects_small_cohort(self):
        with self.assertRaisesRegex(ValueError, "too small"):
            self.valid(cohort_size=29)

    def test_rejects_bad_share_total(self):
        with self.assertRaisesRegex(ValueError, "shares must total"):
            self.valid(device_share={"mobile": .8})

    def test_rejects_negative_totals(self):
        with self.assertRaisesRegex(ValueError, "cannot be negative"):
            self.valid(watch_hours=-1)
