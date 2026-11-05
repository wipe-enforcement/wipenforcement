"""Offline-first Certificate Transparency feed intake."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qarin.collector import collect, parse_feed
from qarin.connectors import FeedError, fetch_ct_rows
from qarin.ledger import Ledger


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify public CT feed rows into QARIN receipts")
    parser.add_argument("feed", nargs="?", help="newline-delimited JSON or hostname file; defaults to stdin")
    parser.add_argument("--url", help="public CT JSON endpoint; mutually exclusive with feed")
    parser.add_argument("--observed-at", help="UTC timestamp used for plain rows")
    parser.add_argument("--ledger", help="append receipts to this JSONL ledger")
    parser.add_argument("--observer", default="ct-feed")
    args = parser.parse_args()

    if args.feed and args.url:
        parser.error("feed and --url are mutually exclusive")
    observed_at = args.observed_at
    if not observed_at:
        from qarin.receipt import now_utc
        observed_at = now_utc()
    try:
        rows = (fetch_ct_rows(args.url, observed_at=observed_at) if args.url else
                parse_feed(Path(args.feed).read_text(encoding="utf-8").splitlines(), observed_at=observed_at)
                if args.feed else parse_feed(sys.stdin.read().splitlines(), observed_at=observed_at))
    except FeedError as exc:
        parser.exit(2, f"collect_ct: {exc}\n")
    ledger = Ledger(Path(args.ledger)) if args.ledger else None
    result = collect(rows, ledger=ledger, observer=args.observer)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
