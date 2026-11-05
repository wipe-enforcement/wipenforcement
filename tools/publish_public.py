"""Publish a healthy collector JSON payload to a local snapshot path."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qarin.publish import PublishRefused, publish_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed local QARIN snapshot publisher")
    parser.add_argument("payload", help="collector JSON payload")
    parser.add_argument("--out", default="site/data/public-collection.json")
    args = parser.parse_args()
    try:
        data = json.loads(Path(args.payload).read_text(encoding="utf-8"))
        path = publish_json(data, args.out)
    except (OSError, json.JSONDecodeError, PublishRefused) as exc:
        parser.exit(2, f"publish_public: {exc}\n")
    print(f"published {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
