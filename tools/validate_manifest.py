"""Validate a private rightsholder manifest before publication."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qarin.onboarding import validate_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a QARIN rights-holder manifest")
    parser.add_argument("manifest")
    args = parser.parse_args()
    try:
        data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"validate_manifest: {exc}\n")
    report = validate_manifest(data)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report.ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
