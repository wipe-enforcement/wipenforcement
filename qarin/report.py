"""Evidence packs and tariff quotations.

Two documents, because there are two audiences and they want incompatible things.

A **regulator or a platform's abuse desk** wants a bounded, dated, reproducible
statement about an *entity*: who, what infrastructure, how long, how they
responded. It does not want a number of viewers, and it would discount any pack
that volunteered one.

A **rightsholder's commercial team** wants to know what a market is worth to
them. It does not want a loss figure it has to defend internally; it wants the
arithmetic laid out with its own tariff in it, so the only assumption in the
whole calculation is one it supplied itself.

This module produces both from the same receipts and refuses, in both cases, to
say anything the receipts do not support. A pack with no anchored day says so on
its first line rather than on page nine. A quotation with no tariff supplied by
the rightsholder emits a count and stops.
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from .ledger import Ledger
from .metrics import Appearance, Gap, LatencySummary, supply_coverage, DetectorSpan
from .model import Availability, RightsCalendar, SEVERITY_ORDER
from .operator import Cluster
from .receipt import Receipt

#: What a pack must never contain, checked before emission.
PROHIBITED_KEYS = frozenset({
    "media", "video_file", "audio_file", "stream_url", "download_url",
    "torrent_file", "magnet", "viewer_identity", "subscriber_phone",
})


class PackRefused(Exception):
    """The pack cannot be issued honestly. Better nothing than this."""


@dataclass
class EvidencePack:
    """One bounded statement about one suspected operation."""

    cluster_id: str
    verdict: str
    sources: tuple[str, ...]
    receipts: tuple[Receipt, ...]
    anchored: bool
    unanchored_days: tuple[str, ...]
    coverage: Mapping
    latency: Mapping
    calendar_notes: tuple[str, ...] = ()
    generated_at: str = ""
    caveats: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "cluster_id": self.cluster_id, "verdict": self.verdict,
            "sources": list(self.sources),
            "n_receipts": len(self.receipts),
            "anchored": self.anchored,
            "unanchored_days": list(self.unanchored_days),
            "coverage": dict(self.coverage), "latency": dict(self.latency),
            "calendar_notes": list(self.calendar_notes),
            "generated_at": self.generated_at, "caveats": list(self.caveats),
            "statement": self.statement(),
        }

    def statement(self) -> str:
        """The paragraph that leads the document, written for a non-technical
        reader, and containing no number that is not in the body."""
        verb = ("operated as a single entity across" if self.verdict == "OPERATOR"
                else "co-hosted with, but not attributed to one owner across")
        head = (f"{len(self.sources)} distinct source(s) {verb} "
                f"{self.cluster_id}.")
        if not self.anchored:
            head += (" No day of this record is externally anchored, so it "
                     "evidences what our collector reported and nothing more.")
        return head

    def markdown(self) -> str:
        lines = [f"# Evidence pack — {self.cluster_id}",
                 f"_generated {self.generated_at}_", "",
                 "## Statement", "", self.statement(), "",
                 "## Sources", ""]
        lines += [f"- `{s}`" for s in self.sources]
        lines += ["", "## Receipts", "",
                  "| observed at | subject | grade | replayable | body sha256 |",
                  "|---|---|---|---|---|"]
        for r in self.receipts[:200]:
            lines.append(f"| {r.observed_at} | `{r.subject[:48]}` | "
                         f"{r.capture_grade} | {'yes' if r.replayable else 'no'} | "
                         f"`{(r.body_sha256 or '')[:16]}…` |")
        lines += ["", "## Coverage of the supply we claim to have measured", "",
                  "```json", json.dumps(self.coverage, indent=1,
                                        ensure_ascii=False, default=str), "```",
                  "", "## Reappearance latency", "",
                  "```json", json.dumps(self.latency, indent=1,
                                        ensure_ascii=False, default=str), "```"]
        if self.calendar_notes:
            lines += ["", "## Rights calendar", ""]
            lines += [f"- {n}" for n in self.calendar_notes]
        if self.caveats or self.unanchored_days:
            lines += ["", "## Caveats — read before relying on any figure", ""]
            lines += [f"- {c}" for c in self.caveats]
            if self.unanchored_days:
                lines.append("- Days not externally anchored: "
                             + ", ".join(self.unanchored_days))
        return "\n".join(lines) + "\n"


def build_pack(cluster: Cluster, receipts: Sequence[Receipt], ledger: Ledger,
               *, spans: Sequence[DetectorSpan] = (),
               appearances: Sequence[Appearance] = (),
               latency: LatencySummary | None = None,
               calendar: RightsCalendar | None = None,
               work_id: str | None = None,
               territory: str | None = None) -> EvidencePack:
    """Assemble a pack, and refuse if it would misrepresent its own provenance."""
    bad = [r for r in receipts if not r.verifies() and r.sealed]
    if bad:
        raise PackRefused(
            f"{len(bad)} receipt(s) fail their own seal; the record was edited "
            "after capture and cannot be issued")
    anchored = ledger.anchored_days()
    days = {r.observed_at[:10] for r in receipts}
    unanchored = tuple(sorted(d for d in days if d not in anchored))
    cov = supply_coverage(spans) if spans else None
    lat = latency or (reappearance_latency_from(appearances) if appearances else None)
    notes: list[str] = []
    if calendar and work_id and territory:
        e = calendar.classify(work_id, territory, dt.date.today())
        notes.append(f"{work_id}/{territory}: {e.availability.value} — {e.reason}")
        for (w, t), probs in sorted(calendar.conflicts().items()):
            if w == work_id:
                notes.append(f"calendar defect at {w}/{t}: " + "; ".join(probs))
    caveats: list[str] = []
    nr = sum(1 for r in receipts if not r.replayable)
    if nr:
        caveats.append(f"{nr} of {len(receipts)} receipt(s) carry no replay "
                       "recipe: they evidence our collector's report, not the "
                       "content of the page.")
    if cov and cov.reason:
        caveats.append(f"coverage not measurable: {cov.reason}")
    if cov and cov.blind_pairs:
        caveats.append(f"{cov.blind_pairs} detector pair(s) share no offering at "
                       "all — a guaranteed blind spot in the fleet, disclosed "
                       "rather than corrected.")
    return EvidencePack(
        cluster.id, cluster.verdict, tuple(sorted(cluster.sources)),
        tuple(receipts), bool(anchored and not unanchored), unanchored,
        cov.to_dict() if cov else {}, lat.to_dict() if lat else {},
        tuple(notes), dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
        .isoformat().replace("+00:00", "Z"), tuple(caveats),
    )


def reappearance_latency_from(appearances: Sequence[Appearance]):
    from .metrics import reappearance_latency
    return reappearance_latency(appearances)


@dataclass
class Quotation:
    """A tariff quotation: their number, our count, the arithmetic in between."""

    gaps: tuple[Gap, ...]
    total_quoted: float | None
    basis: str
    refused: tuple[str, ...] = ()

    def markdown(self) -> str:
        out = ["# Availability gap quotation", "",
               "This is **not a loss figure**. Each line multiplies a count we "
               "measured by a tariff you supplied, and prints both.", ""]
        for g in self.gaps:
            out.append(f"- {g.sentence()}")
        if self.refused:
            out += ["", "## Markets deliberately left unpriced", ""]
            out += [f"- {r}" for r in self.refused]
        out += ["", f"**Total quoted: "
                + (f"{self.total_quoted:,.2f}" if self.total_quoted is not None
                   else "—") + f"**  \n_{self.basis}_"]
        return "\n".join(out) + "\n"

    def to_dict(self) -> dict:
        return {"gaps": [vars(g) for g in self.gaps],
                "total_quoted": self.total_quoted, "basis": self.basis,
                "refused": list(self.refused)}


def quote_gaps(gaps: Sequence[Gap]) -> Quotation:
    """Sum only the gaps that are actually priced, and list the ones that are not.

    The unpriced list is the honest part. A total that silently omits four
    markets is a total that will be quoted as if it covered eight, and the way
    to prevent that is to print the omission next to the sum rather than in a
    footnote nobody reads.
    """
    priced = [g for g in gaps if g.quoted_value is not None]
    total = round(sum(g.quoted_value for g in priced), 2) if priced else None
    refused = tuple(
        f"{g.work_id}/{g.territory}: {g.offerings} offering(s), no tariff or no "
        f"measured unit — {g.note}" for g in gaps if g.quoted_value is None)
    basis = (f"{len(priced)} of {len(gaps)} market(s) priced; the remainder are "
             "reported as counts only" if gaps else "no gaps supplied")
    return Quotation(tuple(gaps), total, basis, refused)


def scan_for_prohibited(doc: Mapping) -> list[str]:
    """Guard rail against the pack itself becoming a distribution channel.

    Checked on emission, not on authoring, because the failure mode is a
    well-meaning later edit that pastes a stream URL into an evidence field to
    make a point "clearer for the lawyer".
    """
    hits: list[str] = []
    stack = [doc]
    while stack:
        cur = stack.pop()
        if isinstance(cur, Mapping):
            for k, v in cur.items():
                if str(k).lower() in PROHIBITED_KEYS and v:
                    hits.append(str(k))
                stack.append(v)
        elif isinstance(cur, (list, tuple)):
            stack.extend(cur)
    return hits
