"""The measurements. All of them are of *supply*, because supply is enumerable.

This module contains no model of audience behaviour, and that is the design
decision everything else follows from. Estimating how many people watched a
pirated copy requires assuming things about people that cannot be observed:
whether they would have paid, at what price, on which device, in a territory
where the work may not even have been sold. Twenty years of industry reports
have produced numbers of that kind and not one of them has survived scrutiny,
because a number with no possible disproof was never a measurement.

What *can* be observed, repeatedly, by an outsider, from public data:

- **how many distinct copies exist** and where they are offered
  (:func:`supply_coverage`)
- **how fast they come back after removal** (:func:`reappearance_latency`)
- **how complete the pirate catalogue is relative to the legal one**
  (:func:`catalog_completeness`)
- **how much unauthorised supply sits in markets nobody serves**
  (:func:`availability_gap`)
- **what the operation publishes about its own price** (in
  :mod:`qarin.report`, priced at the *rightsholder's* tariff, never ours)

Each returns ``None`` when the data cannot support it. There is no default
anywhere in this file, and that is not a stylistic preference: a defaulted
latency, a defaulted completeness, a defaulted coverage each become load-bearing
the moment they are averaged, and an average over fabricated values is
fabricated with more apparent authority than any of its inputs.
"""
from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass, field
from statistics import median, quantiles
from typing import Iterable, Mapping, Sequence

# --------------------------------------------------------------------------
# time helpers
# --------------------------------------------------------------------------
def _ts(x: str | dt.datetime | None) -> dt.datetime | None:
    """Parse an ISO-8601 instant. Returns None rather than raising.

    A malformed timestamp in an evidence corpus is a fact about the record, not
    a reason to abandon a computation, and it must not be silently rounded to
    the epoch or to "now" — both of which would invent latency figures.
    """
    if x is None or x == "":
        return None
    if isinstance(x, dt.datetime):
        return x if x.tzinfo else x.replace(tzinfo=dt.timezone.utc)
    s = str(x).strip().replace("Z", "+00:00")
    try:
        d = dt.datetime.fromisoformat(s)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def minutes(a: dt.datetime, b: dt.datetime) -> float:
    return (b - a).total_seconds() / 60.0


# --------------------------------------------------------------------------
# 1. supply coverage — capture-recapture over *copies*
# --------------------------------------------------------------------------
@dataclass
class DetectorSpan:
    """One detector's observed set of offerings over one window."""

    detector: str
    found: frozenset[str]              # offering ids
    window: tuple[str, str] | None = None


@dataclass
class Coverage:
    """What fraction of the pirate supply the fleet saw, and how sure we are.

    ``blind_pairs`` is the headline number for a fleet owner, not the coverage
    figure. Two live detectors that share not one offering are two pipelines
    pointed at different ecosystems, and no amount of statistical correction can
    recover what neither saw; the fix is architectural, and this field names it.
    """

    n_observed: int
    n_detectors: int
    population_p50: float | None
    coverage_p50: float | None
    coverage_lo: float | None
    coverage_hi: float | None
    per_detector: Mapping[str, int]
    blind_pairs: int
    binding: str | None
    reason: str | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in {
            "n_observed": self.n_observed, "n_detectors": self.n_detectors,
            "population_p50": self.population_p50,
            "coverage_p50": self.coverage_p50,
            "coverage_ci": [self.coverage_lo, self.coverage_hi],
            "per_detector": dict(self.per_detector),
            "blind_pairs": self.blind_pairs, "binding": self.binding,
            "reason": self.reason,
        }.items() if v is not None or k in ("reason", "coverage_ci")}


def _independence_n(marginals: Sequence[int], n_union: int) -> float | None:
    """Multiple-list independence fixed point: ``N = n₊ / (1 − Π(1 − nₖ/N))``.

    Solved by damped iteration rather than closed form, because there is no
    closed form once K > 2 and because the damping is what keeps a pathological
    corpus (one detector seeing nearly everything) from oscillating forever
    instead of returning something defensible.
    """
    if n_union <= 0 or len(marginals) < 2:
        return None
    n = float(n_union)
    for _ in range(400):
        prod = 1.0
        for m in marginals:
            p = min(1.0 - 1e-9, m / n)
            prod *= (1.0 - p)
        miss = 1.0 - prod
        if miss <= 0:
            return None
        nxt = n_union / miss
        if nxt < n_union:
            nxt = float(n_union)
        if abs(nxt - n) <= 1e-10 * max(1.0, n):
            return nxt
        n = 0.5 * n + 0.5 * nxt
    return n


def _chapman(n_a: int, n_b: int, m_ab: int) -> float | None:
    """Two-list Chapman. Finite when the pair shares nothing, unlike Lincoln."""
    if n_a <= 0 or n_b <= 0:
        return None
    return ((n_a + 1) * (n_b + 1)) / (m_ab + 1) - 1.0


def _pairwise_interaction_n(spans: Sequence[DetectorSpan], overlaps: Mapping[str, int],
                            n_union: int) -> tuple[str | None, float | None]:
    """One-two-factor-interaction model, evaluated for every pair.

    This is the correction that matters, and it is worth being exact about why
    the obvious one is not. Positive dependence between two detectors — the same
    channel syndicated to the same fifty sites — makes the independence model
    *understate* the population and therefore *overstate* our own coverage. The
    joint miss probability of a dependent pair is not the product of its
    marginals; it is observed directly:

        P(miss a,b) = 1 − pₐ − p_b + p_ab,   p_ab = m_ab / N

    so the pair's contribution to the fleet's blindness is read off an *actual
    count* rather than inferred from a latent structure. Every pair is
    evaluated and the largest population taken: pairs whose overlap falls below
    the independence expectation shrink N and are discarded by the maximum, so
    the construction can only ever move claimed coverage *down*.

    That asymmetry is deliberate. Selection bias in the upward direction is a
    price paid once, visibly, in exchange for never being able to flatter
    ourselves.
    """
    names = sorted(s.detector for s in spans)
    if len(names) < 3 or n_union <= 0:
        return None, None
    marg = {s.detector: len(s.found) for s in spans}
    best_pair, best = None, None
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            m = overlaps.get(f"{a}|{b}", 0)
            others = [x for x in names if x not in (a, b)]
            n = float(n_union)
            converged = False
            for _ in range(300):
                blk = 1.0 - (marg[a] + marg[b] - m) / n
                if blk <= 0:
                    break
                prod = 1.0
                for k in others:
                    prod *= (1.0 - min(1.0 - 1e-12, marg[k] / n))
                miss = blk * prod
                if miss <= 0:
                    break
                nxt = n_union / (1.0 - miss)
                if nxt < n_union:
                    nxt = float(n_union)
                if abs(nxt - n) <= 1e-10 * max(1.0, n):
                    converged = True
                    n = nxt
                    break
                n = 0.5 * n + 0.5 * nxt
            if converged and (best is None or n > best):
                best, best_pair = n, f"{a}+{b}"
    return best_pair, best


def supply_coverage(spans: Sequence[DetectorSpan], *,
                    min_offerings: int = 8) -> Coverage:
    """Fraction of the unauthorised supply the fleet observed.

    Applied to *offerings*, not to viewers. Capture-recapture on a hidden
    audience is statistically unsound in this domain for a reason worth stating
    plainly: an audience's detection history is determined by the same popularity
    that makes it valuable, so the independence assumption fails structurally and
    in the direction that always inflates reach. An offering's detection history
    is a property of the *fleet's* coverage of infrastructure, which is
    independent by construction — different crawlers, different discovery paths,
    different schedules. Same mathematics, one of the two places it is honest.
    """
    spans = [s for s in spans if s.found]
    names = sorted(s.detector for s in spans)
    union: set[str] = set()
    for s in spans:
        union |= set(s.found)
    marg = {s.detector: len(s.found) for s in spans}
    base = Coverage(len(union), len(names), None, None, None, None,
                    marg, 0, None)
    if len(names) < 2:
        base.reason = (f"{len(names)} live detector(s); coverage needs >= 2 to be "
                       "measurable at all")
        return base
    if len(union) < min_offerings:
        base.reason = (f"{len(union)} distinct offerings < {min_offerings}; any "
                       "figure here would be sampling noise")
        return base

    overlaps: dict[str, int] = {}
    blind = 0
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            sa = next(s.found for s in spans if s.detector == a)
            sb = next(s.found for s in spans if s.detector == b)
            k = len(sa & sb)
            overlaps[f"{a}|{b}"] = k
            if k == 0:
                blind += 1
    base.blind_pairs = blind

    cands: dict[str, float | None] = {
        "independence": _independence_n([marg[n] for n in names], len(union)),
    }
    if len(names) == 2:
        a, b = names
        cands["chapman"] = _chapman(marg[a], marg[b], overlaps[f"{a}|{b}"])
    else:
        _, pw = _pairwise_interaction_n(spans, overlaps, len(union))
        cands["pairwise_interaction"] = pw

    usable = {k: v for k, v in cands.items()
              if v is not None and math.isfinite(v) and v >= len(union)}
    if not usable:
        base.reason = "no population estimator converged"
        return base
    binding = max(usable, key=lambda k: usable[k])
    pop = usable[binding]
    cov = len(union) / pop
    base.population_p50 = pop
    base.coverage_p50 = cov
    base.binding = binding
    base.reason = None
    return base


def detectors_needed(per_detector_reach: float, target: float = 0.95) -> int | None:
    """Independent detectors required for a coverage target.

    ``k >= log(1 − target) / log(1 − p)``. The single most useful number in this
    file for anyone planning a fleet, because it converts "we should see more"
    into a procurement requirement with a specific integer answer — and because
    it shows, immediately, that adding a source that correlates with the ones
    already held buys almost nothing while adding an orthogonal one buys a lot.
    """
    if not (0.0 < per_detector_reach < 1.0) or not (0.0 < target < 1.0):
        return None
    return math.ceil(math.log(1.0 - target) / math.log(1.0 - per_detector_reach) - 1e-12)


def fleet_reach(reaches: Sequence[float]) -> float:
    """Coverage achievable by mutually independent detectors: ``1 − Π(1 − pₖ)``."""
    miss = 1.0
    for p in reaches:
        miss *= (1.0 - min(max(p, 0.0), 1.0 - 1e-12))
    return 1.0 - miss


# --------------------------------------------------------------------------
# 2. reappearance latency — the harm metric that needs no model at all
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Appearance:
    """One continuous period during which an offering was up.

    Built from observations, not from takedown confirmations: an offering is
    *absent* when a detector that previously found it fails to find it, and that
    is observable without any cooperation from the host. Waiting for a removal
    notice to be acknowledged is waiting for an adversary to reply, and 66% of
    the time they will not.
    """

    offering_id: str
    source: str
    first_seen: dt.datetime | None
    last_seen: dt.datetime | None
    removed_at: dt.datetime | None = None
    redeployed_at: dt.datetime | None = None

    @property
    def uptime_minutes(self) -> float | None:
        if not self.first_seen or not self.last_seen:
            return None
        return minutes(self.first_seen, self.last_seen)

    @property
    def takedown_minutes(self) -> float | None:
        """Notice served → actually gone. The number a regulator asks for."""
        if not self.removed_at:
            return None
        ref = self.first_seen
        return None if ref is None else minutes(ref, self.removed_at)

    @property
    def reappearance_minutes(self) -> float | None:
        """Removed → back up. The number that measures the operator, not the page."""
        if not self.removed_at or not self.redeployed_at:
            return None
        return minutes(self.removed_at, self.redeployed_at)


@dataclass
class LatencySummary:
    """Distribution of reappearance latencies, with the 30-minute test attached.

    Reported as a distribution and never as a mean, because the mean of a
    heavy-tailed latency is dominated by a handful of slow operators and
    describes nobody. The median is the typical case; P90 is the *worst* case
    that still happens regularly, and it is P90 that sets the response time an
    enforcement team has to beat to matter.
    """

    n: int
    median_min: float | None
    p90_min: float | None
    max_min: float | None
    within_30min: int
    beyond_30min: int
    share_within_30: float | None
    never_returned: int
    #: Offerings seen again on a *different* source within the window: the
    #: mirror-hop signature, and the reason per-URL takedowns cannot work.
    mirrored_elsewhere: int

    def to_dict(self) -> dict:
        return {k: v for k, v in vars(self).items() if v is not None}


def reappearance_latency(appearances: Sequence[Appearance], *,
                         window_min: float = 30.0) -> LatencySummary:
    """Summarise how quickly removed supply comes back.

    This is the metric the whole platform should be built around, and it is the
    one thing here that requires no model, no assumption about viewer behaviour,
    and no tariff. It is a *measured duration between two observed events*,
    reproducible by any third party from the receipts alone.

    It is also the metric that maps directly onto the harm a rightsholder feels:
    for live sport and simultaneous Ramadan releases, value is destroyed in the
    minutes a copy stays up, so "came back in 4 minutes" is a statement about
    the futility of the current response, not about the size of the audience.
    """
    lats = [a.reappearance_minutes for a in appearances
            if a.reappearance_minutes is not None]
    lats = sorted(l for l in lats if l >= 0)
    never = sum(1 for a in appearances
                if a.removed_at is not None and a.redeployed_at is None)
    within = sum(1 for l in lats if l <= window_min)
    beyond = len(lats) - within

    med = quantiles(lats, n=10, method="inclusive")[8] if len(lats) >= 10 else (
        median(lats) if lats else None)
    p90 = quantiles(lats, n=10, method="inclusive")[8] if len(lats) >= 10 else None
    if len(lats) == 1:
        med = p90 = lats[0]
    elif lats and p90 is None:
        p90 = max(lats)

    # Mirror-hop: same work, removed here, seen there, inside the window.
    by_key: dict[str, list[Appearance]] = {}
    for a in appearances:
        if a.offering_id:
            by_key.setdefault(a.offering_id, []).append(a)
    mirrored = 0
    for group in by_key.values():
        for x in group:
            if not x.removed_at:
                continue
            for y in group:
                if y.source != x.source and y.first_seen and x.removed_at \
                        and 0 <= minutes(x.removed_at, y.first_seen) <= window_min:
                    mirrored += 1
                    break

    return LatencySummary(
        n=len(lats), median_min=None if med is None else round(med, 2),
        p90_min=None if p90 is None else round(p90, 2),
        max_min=None if not lats else round(max(lats), 2),
        within_30min=within, beyond_30min=beyond,
        share_within_30=None if not lats else round(within / len(lats), 4),
        never_returned=never, mirrored_elsewhere=mirrored,
    )


# --------------------------------------------------------------------------
# 3. catalog completeness — the answer to "not one scene goes uncounted"
# --------------------------------------------------------------------------
@dataclass
class Completeness:
    """How much of a work the pirate estate holds, versus the legal estate.

    Episode-level, because that is the granularity at which a Ramadan serial's
    value is actually destroyed: an operator carrying all thirty episodes within
    hours of broadcast is running a different business from one carrying three,
    and only the first competes with a subscription. Counting "items" without the
    denominator of what exists cannot distinguish them.
    """

    work_id: str
    territory: str | None
    legal_episodes: int | None
    pirate_episodes: int | None
    share: float | None
    #: Episodes up *before* their legal availability: the leak set, and the
    #: highest-value evidence in the whole system because it is attributable.
    pre_release_episodes: tuple[int, ...] = ()
    lag_minutes: Mapping[int, float] = field(default_factory=dict)
    reason: str | None = None

    @property
    def complete(self) -> bool:
        return self.share is not None and self.share >= 0.999


def catalog_completeness(work_id: str, legal_eps: Iterable[int] | None,
                         pirate_eps: Mapping[int, dt.datetime] | None,
                         availability: Mapping[int, dt.datetime] | None = None,
                         territory: str | None = None) -> Completeness:
    """Measure the pirate catalogue against the legal one, episode by episode.

    Any missing denominator yields ``None`` fields rather than a ratio. A
    completeness figure computed against a guessed episode count is worse than
    no figure, because it will be believed and it will be wrong in whichever
    direction the guess was wrong.
    """
    le = set(legal_eps or ()) if legal_eps is not None else None
    pe = dict(pirate_eps or {}) if pirate_eps is not None else None
    if not pe:
        return Completeness(work_id, territory, None if le is None else len(le),
                            0 if pe is not None else None,
                            0.0 if (pe is not None and le) else None,
                            reason="no pirate episode observations for this work")
    if le is None:
        return Completeness(work_id, territory, None, len(pe), None,
                            reason="legal episode count unknown; refusing to "
                                   "divide by a guess")
    inter = {e for e in pe if e in le}
    share = len(inter) / len(le) if le else None
    pre = tuple(sorted(e for e in pe
                       if availability and e in availability
                       and pe[e] < availability[e]))
    lag = {e: minutes(availability[e], pe[e]) for e in inter
           if availability and e in availability}
    return Completeness(work_id, territory, len(le), len(pe),
                        round(share, 4) if share is not None else None,
                        pre, {k: round(v, 1) for k, v in lag.items()})


# --------------------------------------------------------------------------
# 4. availability gap — the constructive finding
# --------------------------------------------------------------------------
@dataclass
class Gap:
    """An unserved market, with measured demand sitting in it.

    The most commercially important object in this file, and the one no piracy
    report produces, because producing it requires admitting that some share of
    "piracy" is a distribution failure rather than a crime. That admission is
    worth more to a network than an accusation: it is the only finding here that
    a programming director can act on Monday, and it is unfalsifiable in the
    good sense — the territory either has a verified authorised channel or it
    does not, and both sides of that are auditable.
    """

    work_id: str
    territory: str
    availability: str
    offerings: int
    sources: tuple[str, ...]
    episodes_seen: int | None
    #: The rightsholder's own tariff, echoed back. Never inferred here.
    tariff_unit: str | None = None
    tariff_value: float | None = None
    quoted_value: float | None = None
    note: str = ""

    def sentence(self) -> str:
        """The finding as a sentence a rightsholder can check.

        Deliberately phrased as an arithmetic statement over *their* number and
        *our* count. There is no claim of loss in it, because there is no
        counterfactual to support one, and because the moment this platform
        asserts a loss it becomes contestable on grounds it cannot win.
        """
        v = (f" at your published {self.tariff_unit} of {self.tariff_value}"
             if self.tariff_value is not None else "")
        q = (f" ≈ {self.quoted_value:,.0f}" if self.quoted_value is not None else "")
        return (f"{self.work_id} in {self.territory}: {self.availability}; "
                f"{self.offerings} unauthorised offering(s) across "
                f"{len(self.sources)} source(s){v} ->{q}. {self.note}".strip())


def availability_gap(work_id: str, territory: str, classification: str,
                     offerings: int, sources: Sequence[str],
                     episodes_seen: int | None = None, *,
                     tariff_unit: str | None = None,
                     tariff_value: float | None = None,
                     billable_units: float | None = None) -> Gap:
    """Price the unserved demand at the rightsholder's own tariff.

    ``billable_units`` must be a *measured* quantity — observed views on the
    pirate surface, or an offering count — supplied by the caller from receipts.
    It is never estimated here, and if it is absent no value is quoted at all:
    the gap is still reported, because "nobody sells this here and there are 400
    copies" is a complete finding on its own.

    The multiplication is the whole of the analysis. Everything else in this
    file exists to make ``billable_units`` and ``tariff_value`` two numbers that
    a sceptic can each independently verify, because that is the only structure
    that survives the meeting.
    """
    quoted = None
    note = ""
    if tariff_value is not None and billable_units is not None:
        quoted = round(tariff_value * billable_units, 2)
        note = (f"quoted at the rightsholder's tariff; {billable_units:,.0f} "
                "measured unit(s), arithmetic shown, no loss assumption")
    else:
        note = ("no tariff or no measured billable unit; reported as a count "
                "only, with no value asserted")
    return Gap(work_id, territory, classification, offerings,
               tuple(sorted(set(sources))), episodes_seen, tariff_unit,
               tariff_value, quoted, note)
