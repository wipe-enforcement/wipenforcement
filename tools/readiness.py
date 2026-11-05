"""Print the current QARIN launch-readiness report."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qarin.detectors import declared_fleet
from qarin.health import HealthBoard, SourceStatus
from qarin.onboarding import validate_manifest
from qarin.readiness import assess
from qarin.scope import ARABIC_BASELINE, Market


def main() -> int:
    parser = argparse.ArgumentParser(description="Report QARIN launch blockers")
    parser.add_argument("manifest")
    parser.add_argument("--health", help="health-board JSON file")
    parser.add_argument("--measured-markets", nargs="*", default=())
    parser.add_argument("--authorized", action="store_true")
    args = parser.parse_args()
    try:
        manifest_data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        health_data = json.loads(Path(args.health).read_text(encoding="utf-8")) if args.health else {}
    except (OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"readiness: {exc}\n")
    sources = tuple(SourceStatus(
        item["source_id"], item["status"], item["checked_at"],
        item.get("rows_seen", 0), item.get("error"),
    ) for item in health_data.get("sources", ()))
    health = HealthBoard(health_data.get("checked_at", "never"), sources)
    measured = set(args.measured_markets)
    markets = tuple(Market(market.code, market.name, market.region,
                           "MEASURED" if market.code in measured else market.status)
                    for market in ARABIC_BASELINE)
    report = assess(markets=markets, detectors=declared_fleet(), health=health,
                    manifest=validate_manifest(manifest_data),
                    deployment_authorized=args.authorized)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report.ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
