from __future__ import annotations

import unittest

from qarin.detectors import Detector, DetectorRegistry
from qarin.health import HealthBoard, SourceStatus
from qarin.onboarding import OnboardingReport
from qarin.readiness import assess
from qarin.scope import ARABIC_BASELINE, Market


class TestReadiness(unittest.TestCase):
    def healthy_inputs(self):
        detectors = DetectorRegistry([
            Detector("ct", "ct", "ct", "LIVE"), Detector("rss", "rss", "rss", "LIVE")])
        health = HealthBoard("2026-11-05T07:00:00Z",
                            (SourceStatus("ct", "ok", "2026-11-05T07:00:00Z", 12),))
        return detectors, health, OnboardingReport(())

    def test_default_is_not_ready(self):
        detectors, health, manifest = self.healthy_inputs()
        report = assess(markets=ARABIC_BASELINE, detectors=detectors,
                        health=health, manifest=manifest)
        self.assertFalse(report.ready)
        self.assertIn("ten_markets_measured", report.blockers)
        self.assertIn("deployment_authorized", report.blockers)

    def test_all_checks_can_be_satisfied_explicitly(self):
        detectors, health, manifest = self.healthy_inputs()
        markets = tuple(Market(market.code, market.name, market.region, "MEASURED")
                        for market in ARABIC_BASELINE)
        report = assess(markets=markets, detectors=detectors, health=health,
                        manifest=manifest, deployment_authorized=True)
        self.assertTrue(report.ready)
        self.assertEqual((), report.blockers)

    def test_stale_source_blocks_even_with_live_detectors(self):
        detectors, _, manifest = self.healthy_inputs()
        health = HealthBoard("2026-11-05T07:00:00Z",
                             (SourceStatus("ct", "stale", "2026-11-05T06:00:00Z"),))
        report = assess(markets=ARABIC_BASELINE, detectors=detectors,
                        health=health, manifest=manifest, deployment_authorized=True)
        self.assertIn("source_health_live", report.blockers)
