from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from qarin.publish import PublishRefused, publish_json


class TestPublish(unittest.TestCase):
    def test_unhealthy_payload_cannot_replace_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "radar.json"
            target.write_text("old", encoding="utf-8")
            with self.assertRaises(PublishRefused):
                publish_json({"health": {"live": False}}, target)
            self.assertEqual("old", target.read_text(encoding="utf-8"))

    def test_healthy_payload_is_written_atomically(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "radar.json"
            publish_json({"health": {"live": True}, "cells": []}, target)
            self.assertEqual({"health": {"live": True}, "cells": []},
                             json.loads(target.read_text(encoding="utf-8")))

    def test_non_live_override_is_explicit(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "radar.json"
            publish_json({"health": {"live": False}}, target, require_live=False)
            self.assertTrue(target.exists())
