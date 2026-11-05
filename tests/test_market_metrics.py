from __future__ import annotations

import unittest

from qarin.market_metrics import coverage_matrix, market_coverage, registered_market_coverage
from qarin.detectors import Detector, DetectorRegistry
from qarin.metrics import DetectorSpan


class TestMarketMetrics(unittest.TestCase):
    def test_thin_market_is_not_reported_as_zero_or_95_percent(self):
        result = market_coverage("EG", [DetectorSpan("ct", frozenset({"a"}))])
        self.assertEqual("INSUFFICIENT_EVIDENCE", result.status)
        self.assertIsNone(result.coverage_p50)
        self.assertIsNotNone(result.reason)

    def test_independent_spans_produce_market_specific_coverage(self):
        first = frozenset(f"offer-{index}" for index in range(30))
        second = frozenset(f"offer-{index}" for index in range(15, 45))
        result = market_coverage("SA", [
            DetectorSpan("ct", first),
            DetectorSpan("rss", second),
        ])
        self.assertEqual("MEASURED", result.status)
        self.assertIsNotNone(result.coverage_p50)
        self.assertEqual(2, result.detectors)

    def test_matrix_is_sorted_and_does_not_pool_markets(self):
        rows = coverage_matrix({
            "SA": [DetectorSpan("a", frozenset({"x"}))],
            "EG": [DetectorSpan("a", frozenset({"x"}))],
        })
        self.assertEqual(("EG", "SA"), tuple(row.market for row in rows))
        self.assertTrue(all(row.status == "INSUFFICIENT_EVIDENCE" for row in rows))

    def test_unregistered_or_duplicate_detectors_cannot_enter_coverage(self):
        registry = DetectorRegistry([
            Detector("ct", "ct", "ct", "LIVE"),
            Detector("rss", "rss", "ct", "LIVE"),
        ])
        spans = [DetectorSpan("ct", frozenset({"a"})), DetectorSpan("rss", frozenset({"b"}))]
        result = registered_market_coverage("EG", spans, registry)
        self.assertEqual("INSUFFICIENT_EVIDENCE", result.status)
        self.assertIn("duplicated", result.reason)

    def test_planned_detector_is_rejected_before_measurement(self):
        registry = DetectorRegistry([Detector("ct", "ct", "ct")])
        result = registered_market_coverage("EG", [DetectorSpan("ct", frozenset({"a"}))], registry)
        self.assertIn("not live", result.reason)
