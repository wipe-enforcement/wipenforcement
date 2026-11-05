from __future__ import annotations

import unittest

from qarin.detectors import Detector, DetectorRegistry, declared_fleet


class TestDetectors(unittest.TestCase):
    def test_query_variants_share_one_independence_group(self):
        registry = DetectorRegistry([
            Detector("search-ar", "search_index", "google-index", "LIVE"),
            Detector("search-en", "search_index", "google-index", "LIVE"),
            Detector("telegram", "telegram", "telegram-public", "LIVE"),
        ])
        self.assertEqual(3, len(registry.live()))
        self.assertEqual(2, len(registry.independent_live()))

    def test_planned_detector_is_not_live(self):
        registry = DetectorRegistry([Detector("ct", "certificate_transparency", "ct")])
        self.assertEqual((), registry.live())
        self.assertEqual(0, registry.to_dict()["independent_live_count"])

    def test_duplicate_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate detector"):
            DetectorRegistry([Detector("ct", "ct", "ct"), Detector("ct", "rss", "rss")])

    def test_unknown_status_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown detector"):
            Detector("ct", "ct", "ct", "RUNNING")

    def test_declared_fleet_matches_surface_taxonomy(self):
        registry = declared_fleet()
        self.assertEqual(17, len(registry.all()))
        self.assertEqual(0, len(registry.live()))
        self.assertEqual(0, len(registry.independent_live()))
