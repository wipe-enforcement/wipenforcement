"""Build a rights-aware QARIN radar snapshot from a local manifest."""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qarin.model import AuthorisedChannel, Right, RightsCalendar, Work, WorkKind
from qarin.audience import AudienceRecord
from qarin.radar import build_cell, snapshot


def load_snapshot(manifest: dict) -> dict:
    works = [Work(
        id=item["id"], kind=WorkKind(item["kind"]), titles=item["titles"],
        holder_id=item["holder_id"], produced_year=item.get("produced_year"),
        episode_total=item.get("episode_total"), first_broadcast=item.get("first_broadcast"),
        sponsors=tuple(item.get("sponsors", ())), parent_network=item.get("parent_network"),
        aliases=tuple(item.get("aliases", ())),
    ) for item in manifest.get("works", ())]
    calendar = RightsCalendar(
        works=works,
        rights=[Right(**item) for item in manifest.get("rights", ())],
        channels=[AuthorisedChannel(**item) for item in manifest.get("channels", ())],
    )
    cells = [build_cell(
        calendar, item["work_id"], item["territory"], date.fromisoformat(item["observed_on"]),
        item["pirate_offerings"], source_ids=item.get("source_ids", ()),
        public_views=item.get("public_views"),
        public_views_reason=item.get("public_views_reason", "not collected"),
    ) for item in manifest.get("observations", ())]
    audience = [AudienceRecord(**item) for item in manifest.get("audience", ())]
    return snapshot(
        cells, generated_at=manifest["generated_at"],
        coverage_label=manifest.get("coverage_label", "UNMEASURED"),
        coverage_reason=manifest.get(
            "coverage_reason", "independent detector overlap has not been collected"),
        legal_audience=audience,
    ).to_dict()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a local QARIN radar snapshot")
    parser.add_argument("manifest", help="local JSON rights and observations manifest")
    parser.add_argument("--out", default="site/data/radar.json")
    args = parser.parse_args()
    output = load_snapshot(json.loads(Path(args.manifest).read_text(encoding="utf-8")))
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {target} ({len(output['cells'])} cells, coverage {output['coverage']['label']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
