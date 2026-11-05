"""Safe ingestion boundaries for public discovery feeds."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterable, Mapping

from .ledger import Ledger
from .receipt import Receipt, now_utc
from .rotation import Hit, Recogniser


@dataclass(frozen=True)
class FeedRow:
    name: str
    observed_at: str
    source: str = "certificate_transparency"


@dataclass(frozen=True)
class Collection:
    rows_seen: int
    hits: tuple[Hit, ...]
    receipts: tuple[Receipt, ...]

    @property
    def actionable(self) -> int:
        return len(self.hits)

    def to_dict(self) -> dict:
        return {"rows_seen": self.rows_seen, "actionable": self.actionable,
                "hits": [hit.to_dict() for hit in self.hits],
                "receipts": [receipt.to_dict() for receipt in self.receipts]}


def _row(raw: str | Mapping, observed_at: str) -> FeedRow | None:
    if isinstance(raw, Mapping):
        name = raw.get("name_value") or raw.get("name") or raw.get("domain")
        timestamp = raw.get("observed_at") or observed_at
    else:
        name, timestamp = raw.strip(), observed_at
    if not isinstance(name, str) or not name.strip():
        return None
    return FeedRow(name=name.strip(), observed_at=str(timestamp))


def parse_feed(lines: Iterable[str], *, observed_at: str | None = None) -> tuple[FeedRow, ...]:
    """Parse newline-delimited JSON or plain hostname rows."""
    stamp = observed_at or now_utc()
    out: list[FeedRow] = []
    for line in lines:
        text = line.strip()
        if not text:
            continue
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            value = text
        for item in (value if isinstance(value, list) else (value,)):
            parsed = _row(item, stamp)
            if parsed:
                out.append(parsed)
    return tuple(out)


def collect(rows: Iterable[FeedRow], *, recogniser: Recogniser | None = None,
            observer: str = "ct-feed", collector_version: str = "0.1.0",
            ledger: Ledger | None = None) -> Collection:
    """Classify feed rows and optionally append sealed receipts to a ledger."""
    rec = recogniser or Recogniser()
    hits: list[Hit] = []
    receipts: list[Receipt] = []
    seen: set[tuple[str, str]] = set()
    materialized = tuple(rows)
    for row in materialized:
        hit = rec.classify(row.name, source=row.source)
        if hit is None or not hit.actionable:
            continue
        key = (row.name.lower().rstrip("."), row.observed_at)
        if key in seen:
            continue
        seen.add(key)
        receipt = Receipt(
            subject=f"ct://{row.name.lower().rstrip('.')}",
            observed_at=row.observed_at, source=row.source,
            excerpt=json.dumps(hit.to_dict(), ensure_ascii=False, sort_keys=True),
            observer=observer, collector_version=collector_version,
            tags=("domain-signal", hit.verdict.lower(), hit.brand_id or "unknown"),
            note="Public certificate name classified by the rotation recogniser; no media fetched.",
            caveat="No replay recipe: this is a feed observation, not a claim about page content.",
        ).seal()
        hits.append(hit)
        receipts.append(receipt)
        if ledger is not None:
            ledger.append(receipt, kind="receipt", ref=hit.brand_id)
    return Collection(len(materialized), tuple(hits), tuple(receipts))
