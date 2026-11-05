from __future__ import annotations

import unittest

from qarin.onboarding import validate_manifest


class TestOnboarding(unittest.TestCase):
    def manifest(self):
        return {
            "works": [{"id": "w1", "titles": {"ar": "عنوان"}}],
            "rights": [{"work_id": "w1", "territory": "EG", "source": "contract-1"}],
            "channels": [{"id": "ch1", "status": "VERIFIED", "source": "owner-registry"}],
            "observations": [{"work_id": "w1", "territory": "EG", "source_ids": ["ct:1"]}],
        }

    def test_valid_manifest_is_ready(self):
        report = validate_manifest(self.manifest())
        self.assertTrue(report.ready)
        self.assertEqual((), report.errors)

    def test_missing_provenance_blocks_ready(self):
        data = self.manifest()
        data["rights"][0].pop("source")
        report = validate_manifest(data)
        self.assertFalse(report.ready)
        self.assertIn("right needs a provenance source", report.errors[0])

    def test_candidate_channel_warns_but_is_not_verified(self):
        data = self.manifest()
        data["channels"][0]["status"] = "CANDIDATE"
        report = validate_manifest(data)
        self.assertTrue(report.ready)
        self.assertTrue(report.warnings)

    def test_viewer_identity_is_rejected_anywhere(self):
        data = self.manifest()
        data["audience"] = {"viewer_id": "never"}
        report = validate_manifest(data)
        self.assertFalse(report.ready)
        self.assertTrue(any("privacy field forbidden" in error for error in report.errors))
