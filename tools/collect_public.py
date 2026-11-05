"""Collect one public metadata source into QARIN receipts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qarin.collector import collect, parse_feed
from qarin.connectors import FeedError, fetch_ct_rows, fetch_rss_rows
from qarin.health import HealthBoard, SourceStatus
from qarin.receipt import now_utc


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect one public QARIN metadata source")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--ct-url", help="crt.sh-style JSON endpoint")
    group.add_argument("--rss-url", help="public RSS or Atom endpoint")
    group.add_argument("--file", help="plain hostnames or newline-delimited JSON")
    parser.add_argument("--observed-at")
    parser.add_argument("--observer", default="public-feed")
    parser.add_argument("--ledger")
    args = parser.parse_args()
    observed_at = args.observed_at or now_utc()
    try:
        if args.ct_url:
            rows = fetch_ct_rows(args.ct_url, observed_at=observed_at)
        elif args.rss_url:
            rows = fetch_rss_rows(args.rss_url, observed_at=observed_at)
        else:
            lines = Path(args.file).read_text(encoding="utf-8").splitlines() if args.file else sys.stdin.read().splitlines()
            rows = parse_feed(lines, observed_at=observed_at)
    except FeedError as exc:
        parser.exit(2, f"collect_public: {exc}\n")
    from qarin.ledger import Ledger
    ledger = Ledger(Path(args.ledger)) if args.ledger else None
    result = collect(rows, observer=args.observer, ledger=ledger)
    source_id = "ct" if args.ct_url else "rss" if args.rss_url else "file"
    output = result.to_dict()
    output["health"] = HealthBoard(
        observed_at, (SourceStatus(source_id, "ok", observed_at, rows_seen=result.rows_seen),)
    ).to_dict()
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
