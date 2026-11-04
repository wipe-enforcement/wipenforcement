"""The enforcement loop: notice → outcome → reappearance → recalibration.

Measurement without a loop is a grievance with a dashboard. This module closes
the circuit: every action taken produces an outcome, every outcome is measured
against the same instruments that measured the original supply, and the
collection schedule is then adjusted by what the outcomes say.

The three things it encodes that most enforcement tooling does not:

**Priority follows the rights calendar, not the view count.** A live final with
five hundred simultaneous viewers outranks a three-year-old series with five
million, because the first is substitution at a rate near one inside a window
that closes in minutes and the second is an unserved market. ``route()`` orders
by :data:`qarin.model.SEVERITY_RANK` first and by observed magnitude second.

**Absence of response is an outcome, not a missing value.** When a host does not
reply, the record is ``IGNORED`` — a measured fact with a date attached, and the
single most useful datum for a regulatory filing. Systems that leave it blank
destroy the one piece of evidence that makes non-compliance visible at scale.

**Escalation targets the entity, once.** Sending forty notices for forty URLs
belonging to one operator is forty acts of whack-a-mole; sending one evidence
pack naming the operator, with the infrastructure clustering that ties the
forty URLs to it, is an act against a business. ``escalation_target()``
implements that reduction, and it is the reason
:mod:`qarin.operator` exists at all.
"""
from __future__ import annotations

import datetime as dt
import enum
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

from .metrics import Appearance, LatencySummary, minutes, reappearance_latency
from .model import ACTIONABLE, Availability, CalendarEntry, SEVERITY_RANK


class NoticeState(str, enum.Enum):
    """Outcome of one notice. ``IGNORED`` and ``REJECTED`` are findings."""

    PENDING = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    REMOVED = "REMOVED"
    IGNORED = "IGNORED"
    REJECTED = "REJECTED"
    COUNTERNOTICED = "COUNTERNOTICED"

    @property
    def terminal(self) -> bool:
        return self in (NoticeState.REMOVED, NoticeState.REJECTED,
                        NoticeState.COUNTERNOTICED)


#: Who is being asked, and what leverage the asking carries. Ordered by how
#: likely the recipient is to act on a *business* incentive rather than a legal
#: one — which, empirically, is the stronger of the two.
CHANNEL_PRIORITY = ("payment_processor", "ad_network", "cdn_host", "registrar",
                    "app_store", "telegram", "search_index", "jurisdiction_regulator",
                    "direct_operator")


@dataclass
class Notice:
    """One request to one intermediary about one thing."""

    id: str
    target: str                    # the source being reported
    channel: str                   # a key of CHANNEL_PRIORITY
    work_id: str | None = None
    territory: str | None = None
    availability: Availability | None = None
    served_at: dt.datetime | None = None
    responded_at: dt.datetime | None = None
    state: NoticeState = NoticeState.PENDING
    evidence_digests: tuple[str, ...] = ()
    operator_cluster: str | None = None
    legal_basis: str | None = None   # DMCA 512(c)(3) | local statute | contract
    note: str | None = None

    @property
    def response_minutes(self) -> float | None:
        if not self.served_at or not self.responded_at:
            return None
        return minutes(self.served_at, self.responded_at)

    @property
    def within_standard(self) -> bool | None:
        """Did this meet the 30-minute live-event window? None if not measurable
        yet — which is reported, never defaulted to False."""
        r = self.response_minutes
        return None if r is None else r <= 30.0


@dataclass
class Routed:
    """One item of a prioritised workload, with the reason it sits there."""

    rank: int
    target: str
    availability: Availability
    why: str
    work_id: str | None = None
    territory: str | None = None
    cluster: str | None = None
    sla_minutes: float | None = None


#: Response deadline by class, in minutes. Derived from the harm clock, not from
#: convenience: a pre-release leak is about *attribution*, which decays as copies
#: proliferate and the earliest copies are the ones still traceable to a screener
#: watermark; a live event is about the event itself.
SLA_MINUTES: Mapping[Availability, float] = {
    Availability.PRE_RELEASE_LEAK: 15.0,
    Availability.SIMULTANEOUS_LIVE: 5.0,
    Availability.CONCURRENT_UNAUTHORISED: 240.0,
    Availability.POST_WINDOW: 1440.0,
    Availability.NEVER_AUTHORISED: None,   # type: ignore[dict-item]
    Availability.UNKNOWN: None,            # type: ignore[dict-item]
}


def route(items: Sequence[Routed | tuple], *,
          include_non_actionable: bool = False) -> list[Routed]:
    """Order an enforcement workload.

    Sorts by severity class first, then by cluster size — because an item
    belonging to a twenty-source operator is worth more attention than one
    belonging to a loner, and acting on the bigger operation displaces more
    supply per notice. Magnitude of audience never enters the ordering, because
    it is the one input here that would have to be modelled.

    ``UNKNOWN`` classifications sort last by construction and are excluded unless
    asked for: an item whose rights calendar is unresolved cannot be prioritised
    honestly, and putting it at the top of a queue would be a guess wearing a
    ranking.
    """
    out: list[Routed] = []
    for i, it in enumerate(items, 1):
        if isinstance(it, tuple):
            it = Routed(i, *it)
        if not include_non_actionable and it.availability not in ACTIONABLE:
            continue
        out.append(it)
    out.sort(key=lambda r: (SEVERITY_RANK[r.availability],
                            -(len(r.cluster.split(":")) if r.cluster else 1),
                            r.target))
    for n, r in enumerate(out, 1):
        r.rank = n
        if r.sla_minutes is None:
            r.sla_minutes = SLA_MINUTES.get(r.availability)
    return out


def escalation_target(notices: Sequence[Notice]) -> dict[str, list[Notice]]:
    """Group notices by the entity that can actually be moved.

    The reduction that matters: forty URLs become one operator, one evidence
    pack, one letter to one payment processor. Keyed by cluster when known,
    otherwise by channel — and the ``None`` cluster case is kept distinct from
    an empty string so an unattributed item never silently merges into a
    cluster it does not belong to.
    """
    out: dict[str, list[Notice]] = {}
    for n in notices:
        key = n.operator_cluster or f"unattributed:{n.channel}"
        out.setdefault(key, []).append(n)
    return out


@dataclass
class LoopReport:
    """What the last cycle of action achieved, and what it should change."""

    served: int
    responded: int
    ignored: int
    removed: int
    median_response_min: float | None
    within_30: int
    compliance_rate: float | None
    latency: LatencySummary | None
    #: Channels whose own behaviour makes them worth escalating to before the
    #: operator is contacted at all — the highest-yield ordering available.
    recommended_channel: str | None = None
    recalibration: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        d = {"served": self.served, "responded": self.responded,
             "ignored": self.ignored, "removed": self.removed,
             "median_response_min": self.median_response_min,
             "within_30": self.within_30,
             "compliance_rate": self.compliance_rate,
             "recommended_channel": self.recommended_channel,
             "recalibration": list(self.recalibration)}
        if self.latency:
            d["latency"] = self.latency.to_dict()
        return d


def close_loop(notices: Sequence[Notice], appearances: Sequence[Appearance],
               *, window_min: float = 30.0) -> LoopReport:
    """Measure the cycle and derive the next cycle's schedule.

    The recalibration rules are deliberately simple and printed, not learned. A
    self-modifying collection policy cannot be described to a regulator, and the
    whole value of this platform rests on being explicable. What is learned is
    *where to look harder*, not *what to believe*.
    """
    served = [n for n in notices if n.served_at]
    responded = [n for n in served if n.responded_at]
    ignored = [n for n in served if n.state is NoticeState.IGNORED
               or n.responded_at is None]
    removed = [n for n in served if n.state is NoticeState.REMOVED]
    resp = sorted(r for r in (n.response_minutes for n in responded) if r is not None)
    med = resp[len(resp) // 2] if resp else None
    within = sum(1 for r in resp if r <= window_min)
    lat = reappearance_latency(appearances, window_min=window_min)

    calib: list[str] = []
    if lat.n and lat.share_within_30 is not None and lat.share_within_30 < 0.25:
        calib.append(
            f"{lat.share_within_30:.0%} of removals stayed down for {window_min:.0f}"
            f" min or less: per-URL notices are not the instrument here. Escalate "
            f"by operator cluster and shorten the re-detection interval on these "
            f"sources to below {window_min:.0f} min.")
    if lat.mirrored_elsewhere:
        calib.append(
            f"{lat.mirrored_elsewhere} offering(s) reappeared on a different "
            "source: the mirror set must be enumerated *before* the first "
            "takedown or the removal is cosmetic.")
    if served and len(ignored) / len(served) > 0.5:
        calib.append(
            f"{len(ignored)}/{len(served)} notices drew no reply: record the "
            "non-response as the finding, and route to the payment and ad "
            "layers where silence is not an option.")

    chan = None
    if ignored and len(ignored) / max(1, len(served)) > 0.4:
        chan = "payment_processor"
    elif lat.mirrored_elsewhere:
        chan = "cdn_host"
    elif served:
        chan = "direct_operator"

    return LoopReport(
        served=len(served), responded=len(responded), ignored=len(ignored),
        removed=len(removed),
        median_response_min=None if med is None else round(med, 2),
        within_30=within,
        compliance_rate=None if not served else round(len(removed) / len(served), 4),
        latency=lat, recommended_channel=chan, recalibration=tuple(calib),
    )
