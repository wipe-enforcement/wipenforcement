"""Run one public collection and publish only if its health is live."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qarin.collector import collect, parse_feed
from qarin.connectors import FeedError, fetch_ct_rows, fetch_rss_rows
from qarin.health import HealthBoard, SourceStatus
from qarin.publish import PublishRefused, publish_json
from qarin.receipt import now_utc


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one fail-closed QARIN collection")
    sources = parser.add_mutually_exclusive_group(required=True)
    sources.add_argument("--ct-url")
    sources.add_argument("--rss-url")
    sources.add_argument("--file")
    parser.add_argument("--out", default="site/data/public-collection.json")
    parser.add_argument("--observed-at")
    parser.add_argument("--observer", default="scheduled-public-feed")
    args = parser.parse_args()
    observed_at = args.observed_at or now_utc()
    source_id = "ct" if args.ct_url else "rss" if args.rss_url else "file"
    try:
        if args.ct_url:
            rows = fetch_ct_rows(args.ct_url, observed_at=observed_at)
        elif args.rss_url:
            rows = fetch_rss_rows(args.rss_url, observed_at=observed_at)
        else:
            rows = parse_feed(Path(args.file).read_text(encoding="utf-8").splitlines(), observed_at=observed_at)
    except (FeedError, OSError) as exc:
        parser.exit(2, f"run_once: {exc}\n")
    result = collect(rows, observer=args.observer)
    health = HealthBoard(observed_at, (
        SourceStatus(source_id, "ok", observed_at, rows_seen=result.rows_seen),
    ))
    payload = result.to_dict()
    payload["health"] = health.to_dict()
    try:
        destination = publish_json(payload, args.out)
    except PublishRefused as exc:
        parser.exit(2, f"run_once: {exc}\n")
    print(json.dumps({"published": str(destination), "health": health.to_dict()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
