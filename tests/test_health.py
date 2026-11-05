from __future__ import annotations

import unittest

from qarin.health import HealthBoard, SourceStatus


class TestHealth(unittest.TestCase):
    def test_all_sources_must_be_healthy_before_board_is_live(self):
        board = HealthBoard("2026-11-05T04:00:00Z", (
            SourceStatus("ct", "ok", "2026-11-05T04:00:00Z", rows_seen=4),
            SourceStatus("rss", "stale", "2026-11-05T03:00:00Z"),
        ))
        self.assertFalse(board.live)
        self.assertFalse(board.to_dict()["live"])

    def test_empty_board_is_not_live(self):
        self.assertFalse(HealthBoard("2026-11-05T04:00:00Z", ()).live)

    def test_error_requires_reason(self):
        with self.assertRaisesRegex(ValueError, "error status"):
            SourceStatus("ct", "error", "2026-11-05T04:00:00Z")

    def test_unknown_status_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown source"):
            SourceStatus("ct", "green", "2026-11-05T04:00:00Z")
