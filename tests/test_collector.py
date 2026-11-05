from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from qarin.collector import collect, parse_feed
from qarin.intel import load
from qarin.ledger import Ledger
from qarin.rotation import Recogniser


class TestCollector(unittest.TestCase):
    def setUp(self):
        self.recogniser = Recogniser(intel=load(force_example=True))

    def test_parse_accepts_plain_and_json_rows(self):
        rows = parse_feed([
            "alpha.com",
            json.dumps({"name_value": "alphaa.net", "observed_at": "2026-11-05T00:00:00Z"}),
            json.dumps([{"name": "alpha-official.xyz"}, {"domain": ""}]),
            "",
        ], observed_at="2026-11-05T01:00:00Z")
        self.assertEqual(("alpha.com", "alphaa.net", "alpha-official.xyz"),
                         tuple(row.name for row in rows))
        self.assertEqual("2026-11-05T00:00:00Z", rows[1].observed_at)

    def test_invalid_rows_do_not_become_negative_findings(self):
        rows = parse_feed([json.dumps({"unexpected": "value"}), "not a domain"],
                          observed_at="2026-11-05T01:00:00Z")
        result = collect(rows, recogniser=self.recogniser)
        self.assertEqual(1, result.rows_seen)
        self.assertEqual(0, result.actionable)
        self.assertEqual((), result.receipts)

    def test_actionable_hits_become_metadata_only_receipts(self):
        rows = parse_feed(["alphaa.example", "recipes.net"],
                          observed_at="2026-11-05T01:00:00Z")
        result = collect(rows, recogniser=self.recogniser, observer="test")
        self.assertEqual(2, result.rows_seen)
        self.assertEqual(1, result.actionable)
        receipt = result.receipts[0]
        self.assertTrue(receipt.verifies())
        self.assertEqual("LOG_ONLY", receipt.admissible_floor)
        self.assertEqual("test", receipt.observer)
        self.assertNotIn("media", receipt.payload())

    def test_duplicate_rows_are_idempotent_for_one_observation(self):
        rows = parse_feed(["alphaa.example", "alphaa.example"],
                          observed_at="2026-11-05T01:00:00Z")
        result = collect(rows, recogniser=self.recogniser)
        self.assertEqual(2, result.rows_seen)
        self.assertEqual(1, result.actionable)
        self.assertEqual(1, len(result.receipts))

    def test_ledger_append_is_verifiable(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = Ledger(Path(folder) / "ledger.jsonl")
            rows = parse_feed(["alphaa.example"], observed_at="2026-11-05T01:00:00Z")
            collect(rows, recogniser=self.recogniser, ledger=ledger)
            self.assertEqual((True, "1 entries verify"), ledger.verify())
