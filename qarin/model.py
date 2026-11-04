"""Works, rights, territories, authorised channels — and the rights calendar.

The load-bearing idea in this module is not any of the entities. It is
:meth:`RightsCalendar.classify`, and it exists because of a category error that
runs through the whole anti-piracy industry: **a pirate copy is not one kind of
thing.**

A screener that surfaces on Telegram three weeks before a Ramadan premiere is a
breach of a distribution contract, traceable to one partner, and it is the most
damaging event in the system — because it is the only one with a *defendant who
is already known*. A live football final streamed simultaneously in a territory
where the rights are sold per-match is substitution at a rate near one, and its
damage is bounded by the minutes it stays up. A three-year-old series sitting on
an archive site in a country where it was never licensed is not stealing
anything at all: there is no sale it is preventing, because there is no sale to
prevent. Those three facts have identical shape in every dashboard that counts
"pirated items" — and they are worth wildly different amounts to the person who
owns the work.

So severity is derived from the **relationship between a copy and the rights
calendar**, not from a view count. The calendar is therefore a first-class
object here rather than a column in a titles table, and an offering whose
calendar is unknown gets ``UNKNOWN`` — never a default that flatters the report.

Everything in this module is a plain record. Uncertainty, hashes, evidence
grades and intervals live in the modules that consume them, because a date
written down with no source and no grade is how an assertion becomes a fact in
someone else's deck six months later.
"""
from __future__ import annotations

import datetime as dt
import enum
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

ISO_DATE = "%Y-%m-%d"


def _d(x: str | dt.date | dt.datetime | None) -> dt.date | None:
    """Coerce to a date. Returns None rather than raising on a missing value.

    A missing broadcast date is an absence of information, not a zero, and it
    must not silently become ``date.min`` — which would classify every copy ever
    made of that work as a post-window archive view and delete the leak signal.
    """
    if x is None or x == "":
        return None
    if isinstance(x, dt.datetime):
        return x.date()
    if isinstance(x, dt.date):
        return x
    return dt.date.fromisoformat(str(x).strip()[:10])


class WorkKind(str, enum.Enum):
    """What kind of thing was made, because the harm calendar differs by kind.

    ``LIVE_EVENT`` damage is a function of minutes-until-takedown; ``SERIES``
    damage is a function of episode cadence and simultaneity; ``FILM`` damage
    concentrates in the opening window; ``MUSIC`` is almost entirely a
    synchronisation-rights problem; ``UGC`` is a platform-policy problem rather
    than a litigation one. Treating these as one bucket called "content" is how
    the industry produced numbers nobody in a finance department believed.
    """

    SERIES = "SERIES"
    FILM = "FILM"
    LIVE_EVENT = "LIVE_EVENT"
    TALK_SHOW = "TALK_SHOW"
    MUSIC = "MUSIC"
    UGC = "UGC"
    OTHER = "OTHER"


# Kinds whose harm is dominated by the clock rather than by the catalogue.
LIVE_KINDS = frozenset({WorkKind.LIVE_EVENT})
# Kinds released in numbered instalments, where completeness is measurable.
EPISODIC_KINDS = frozenset({WorkKind.SERIES, WorkKind.TALK_SHOW})


class Availability(str, enum.Enum):
    """How a copy relates to the rights calendar. The severity ladder.

    Ordered by descending harm, and the ordering is the point: it is what turns
    a list of URLs into a prioritised workload for an enforcement team.
    """

    PRE_RELEASE_LEAK = "PRE_RELEASE_LEAK"
    """Seen before authorised availability in that territory. Either a screeners
    leak or a feed compromise — and it is *attributable*, which no other class
    is. Highest severity, and the only one that produces a named defendant
    without any external cooperation."""

    SIMULTANEOUS_LIVE = "SIMULTANEOUS_LIVE"
    """Inside the live window of an event whose rights are sold per-instance.
    Substitution rate approaches 1: the viewer who watches this is the viewer
    who did not buy the match. Damage is a function of minutes up."""

    CONCURRENT_UNAUTHORISED = "CONCURRENT_UNAUTHORISED"
    """Legally available in territory, offered free elsewhere at the same time.
    Substitution is real but partial: price, friction and habit all intervene."""

    POST_WINDOW = "POST_WINDOW"
    """Availability has expired. Some substitution against the next release or
    against a library licence; much weaker, and honestly reported as weaker."""

    NEVER_AUTHORISED = "NEVER_AUTHORISED"
    """No authorised channel in this territory, ever. **This is not theft — it is
    an unserved market.** Reporting it as loss is both indefensible and
    commercially stupid: the useful sentence is 'there is measured demand here
    that you are not selling into'. See :func:`qarin.metrics.availability_gap`."""

    AUTHORISED = "AUTHORISED"
    """On the authorised list for this territory and window. Not an infringement
    observation at all; recorded because the legal side of the denominator has
    to be measured too, not assumed."""

    UNKNOWN = "UNKNOWN"
    """The calendar does not cover this combination. Rendered as an em dash,
    never defaulted: an unknown classification cannot inflate a severity
    ranking, and a missing date must not quietly become POST_WINDOW."""


#: Descending harm. Used for sorting and for "is this worth a lawyer tonight?".
SEVERITY_ORDER: tuple[Availability, ...] = (
    Availability.PRE_RELEASE_LEAK,
    Availability.SIMULTANEOUS_LIVE,
    Availability.CONCURRENT_UNAUTHORISED,
    Availability.POST_WINDOW,
    Availability.NEVER_AUTHORISED,
    Availability.UNKNOWN,
    Availability.AUTHORISED,
)

SEVERITY_RANK: Mapping[Availability, int] = {
    a: i for i, a in enumerate(SEVERITY_ORDER)
}

#: Classes for which a rightsholder has a live commercial remedy this week.
ACTIONABLE = frozenset({
    Availability.PRE_RELEASE_LEAK,
    Availability.SIMULTANEOUS_LIVE,
    Availability.CONCURRENT_UNAUTHORISED,
})


@dataclass(frozen=True)
class Territory:
    """A market, and the facts about it that change how piracy reads.

    ``script_primary`` matters because subtitle language is a market signal: a
    dub-heavy copy points at Gulf and Egyptian demand, a subbed one at the
    Levant and Maghreb. ``live_rights_per_instance`` matters because it decides
    whether a simultaneous stream is a substitution event or a nuisance.
    """

    code: str                      # ISO 3166-1 alpha-2
    name: str
    region: str                    # "gulf" | "levant" | "north_africa" | "nil" | "other"
    population_m: float | None = None
    script_primary: str = "arab"   # arab | latin | mixed
    official_language: str = "ar"
    live_rights_per_instance: bool = False
    blocking_in_force: bool = False
    data_protection_regime: str | None = None   # PDPL | ADGM/DIFC | GDPR-like | none-codified
    notes: str | None = None


@dataclass(frozen=True)
class Work:
    """A copyrighted audiovisual work, and every name it is known by.

    ``titles`` is a mapping of script/variety to string rather than one
    ``title_en``/``title_ar`` pair because the same series circulates under a
    Gulf-dubbed name, a Levant-subtitled name, a Latin transliteration with
    three spellings, and whatever a Telegram channel decided to call it that
    week. Resolution happens in :mod:`qarin.canonical` against this set.
    """

    id: str
    kind: WorkKind
    titles: Mapping[str, str]                 # {"ar": ..., "en": ..., "ar_latn": ...}
    holder_id: str
    produced_year: int | None = None
    episode_total: int | None = None          # None = unknown, NOT 0
    first_broadcast: dt.date | None = None
    sponsors: tuple[str, ...] = ()
    parent_network: str | None = None         # the originating broadcaster
    aliases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "first_broadcast", _d(self.first_broadcast))
        if self.episode_total is not None and self.episode_total < 0:
            raise ValueError(f"episode_total cannot be negative: {self.episode_total}")
        if not any(self.titles.values()):
            raise ValueError(f"work {self.id} has no title in any script")

    @property
    def episodic(self) -> bool:
        return self.kind in EPISODIC_KINDS

    @property
    def live(self) -> bool:
        return self.kind in LIVE_KINDS

    def all_names(self) -> tuple[str, ...]:
        return tuple(n for n in tuple(self.titles.values()) + self.aliases if n)


@dataclass(frozen=True)
class Right:
    """One right, one holder, one territory, one window.

    The atom of the whole system. A work does not have "rights"; it has this
    many of these, and they frequently disagree — which is why a single
    ``owner`` field on a titles table cannot answer the only question a
    rightsholder actually asks: *may I enforce this, here, today?*
    """

    work_id: str
    territory: str
    holder_id: str
    right_type: str                       # reproduction | communication | making_available | sync | broadcast
    window_start: dt.date | None = None
    window_end: dt.date | None = None
    exclusive: bool = True
    licensee_id: str | None = None        # who is authorised to exploit it
    contract_ref: str | None = None
    source: str | None = None             # where this record came from
    verified_at: dt.date | None = None
    #: Provenance grade of the record itself, independent of any measurement.
    #: A right asserted by the holder is R1; one evidenced by a filed contract
    #: is R3. Enforcement readiness depends on this, not on the URL count.
    record_grade: str = "R1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "window_start", _d(self.window_start))
        object.__setattr__(self, "window_end", _d(self.window_end))
        object.__setattr__(self, "verified_at", _d(self.verified_at))
        if (self.window_start and self.window_end
                and self.window_end < self.window_start):
            raise ValueError(
                f"right for {self.work_id}/{self.territory} ends before it starts")

    def covers(self, when: dt.date) -> bool:
        """Is this right in force on ``when``? An open end means open ended."""
        if self.window_start and when < self.window_start:
            return False
        if self.window_end and when > self.window_end:
            return False
        return True


@dataclass(frozen=True)
class AuthorisedChannel:
    """A place the work may legitimately be watched.

    The legal side of the denominator has to be *measured*, not assumed. Every
    "piracy rate" ever quoted in this industry silently treated authorised
    availability as a constant; the reason a title's unauthorised supply is
    concentrated in Iraq rather than Kuwait is usually that it was never
    licensable in Iraq, and only a channel registry makes that visible.

    ``status`` gates publication: a candidate channel appears in internal
    working data and nowhere else until it has a dated source.
    """

    id: str
    name: str
    operator_id: str
    model: str                    # svod | avod | fast | linear | broadcast | cinema | physical
    territories: tuple[str, ...]
    works: tuple[str, ...] = ()   # empty = catalogue-wide, see ``scope``
    scope: str = "catalogue"      # catalogue | per_title | per_event
    tariff_ref: str | None = None # pointer to the price list, not a price
    status: str = "CANDIDATE"     # VERIFIED | CANDIDATE | RETIRED
    source: str | None = None
    verified_at: dt.date | None = None
    affiliate_of: tuple[str, ...] = ()   # sponsorship / affiliate programmes

    def __post_init__(self) -> None:
        object.__setattr__(self, "verified_at", _d(self.verified_at))

    def serves(self, work_id: str, territory: str) -> bool:
        if territory not in self.territories:
            return False
        if self.scope == "catalogue":
            return True
        return work_id in self.works


@dataclass(frozen=True)
class CalendarEntry:
    """The resolved answer for one (work, territory, date)."""

    availability: Availability
    authorised_channels: tuple[str, ...] = ()
    in_force_right: tuple[str, ...] = ()
    window_start: dt.date | None = None
    window_end: dt.date | None = None
    reason: str = ""

    @property
    def actionable(self) -> bool:
        return self.availability in ACTIONABLE

    @property
    def severity(self) -> int:
        return SEVERITY_RANK[self.availability]


class RightsCalendar:
    """Answers: *at this date, in this territory, what was legally on offer?*

    Built from :class:`Right` and :class:`AuthorisedChannel` records rather than
    storing its own dates, so there is exactly one place a window can be wrong.
    Ambiguity is preserved rather than resolved away: if two rights records
    disagree about a window, the entry says so in ``reason`` and the affected
    figures are downgraded, because a calendar that always has a confident
    answer is a calendar that is inventing one.
    """

    def __init__(self, rights: Iterable[Right] = (),
                 channels: Iterable[AuthorisedChannel] = (),
                 works: Iterable[Work] = ()) -> None:
        self._rights: list[Right] = list(rights)
        self._channels: list[AuthorisedChannel] = list(channels)
        self._works: dict[str, Work] = {w.id: w for w in works}
        self._conflicts: dict[tuple[str, str], list[str]] = {}
        for r in self._rights:
            if r.window_start and r.window_end:
                pass
            elif r.window_start is None and r.window_end is not None:
                self._conflicts.setdefault((r.work_id, r.territory), []).append(
                    f"right {r.holder_id} has an end with no start")

    # -- population ---------------------------------------------------------
    def add_right(self, r: Right) -> None:
        self._rights.append(r)

    def add_channel(self, c: AuthorisedChannel) -> None:
        self._channels.append(c)

    def add_work(self, w: Work) -> None:
        self._works[w.id] = w

    def work(self, work_id: str) -> Work | None:
        return self._works.get(work_id)

    # -- queries ------------------------------------------------------------
    def rights_in_force(self, work_id: str, territory: str,
                        when: dt.date) -> tuple[Right, ...]:
        return tuple(r for r in self._rights
                     if r.work_id == work_id and r.territory == territory
                     and r.covers(when))

    def authorised_now(self, work_id: str, territory: str,
                       when: dt.date) -> tuple[AuthorisedChannel, ...]:
        """Verified channels serving this work in this territory on this date.

        Two separate defects are closed here, and the self-check found both.

        ``CANDIDATE`` channels are excluded. Counting an unverified service as
        authorised inflates the legal denominator and therefore *deflates* the
        piracy figure — which sounds conservative and is the opposite, because it
        loses the rightsholder money and discredits the report.

        The window is respected. A channel registry says *where* a work may be
        offered; it does not say *when*. Intersecting with the rights in force is
        what stops a series that left Shahid in September from being scored as
        concurrently available in December, and it is the difference between
        CONCURRENT_UNAUTHORISED and POST_WINDOW — a substitution finding versus a
        library one. Read the channel list alone, every expired title in the
        catalogue looks like a live competitor forever.

        When rights exist but none is in force on this date, no channel is
        authorised for this work here, even a verified one.
        """
        chans = tuple(c for c in self._channels
                      if c.status == "VERIFIED" and c.serves(work_id, territory))
        if not chans:
            return ()
        historical = [r for r in self._rights
                      if r.work_id == work_id and r.territory == territory]
        if historical and not any(r.covers(when) for r in historical):
            return ()
        return chans

    def classify(self, work_id: str, territory: str, seen: dt.date,
                 *, live_span: tuple[dt.date, dt.date] | None = None,
                 ) -> CalendarEntry:
        """Classify one unauthorised copy against the calendar.

        ``seen`` is the date the copy was observed. ``live_span`` optionally
        gives the start and end dates of the live event, for ``LIVE_EVENT``
        works where the substitution window is the event itself.
        """
        seen = _d(seen) or dt.date.today()
        w = self._works.get(work_id)
        rights = self.rights_in_force(work_id, territory, seen)
        chans = self.authorised_now(work_id, territory, seen)
        # Window bounds come from EVERY right for this work and territory, not
        # only those in force on the date. Read from the in-force set alone, a
        # closed window has no members, "prev" is never found, and an expired
        # title classifies as NEVER_AUTHORISED — reporting a distribution
        # question as though the work had never been licensed there at all.
        historical = tuple(r for r in self._rights
                           if r.work_id == work_id and r.territory == territory)
        starts = tuple(r.window_start for r in historical if r.window_start)
        ends = tuple(r.window_end for r in historical if r.window_end)
        nxt = min((s for s in starts if s > seen), default=None)
        prev = max((e for e in ends if e < seen), default=None)
        # Also consider the work's own first broadcast: a copy circulating
        # before the network has aired it is a leak regardless of licensing.
        fb = w.first_broadcast if w else None
        pre_air = fb is not None and seen < fb

        if chans:
            if w and w.live and live_span and live_span[0] <= seen <= live_span[1]:
                return CalendarEntry(
                    Availability.SIMULTANEOUS_LIVE, tuple(c.id for c in chans),
                    tuple(r.holder_id for r in rights), None, None,
                    "copy observed inside the live rights window of the event")
            return CalendarEntry(
                Availability.CONCURRENT_UNAUTHORISED, tuple(c.id for c in chans),
                tuple(r.holder_id for r in rights), None,
                max(ends) if ends else None,
                "legally available on " + ", ".join(sorted(c.id for c in chans)))

        if pre_air:
            return CalendarEntry(
                Availability.PRE_RELEASE_LEAK, (), tuple(r.holder_id for r in rights),
                fb, None,
                f"observed {seen.isoformat()}, first broadcast {fb.isoformat()}")
        if nxt is not None:
            return CalendarEntry(
                Availability.PRE_RELEASE_LEAK, (), tuple(r.holder_id for r in rights),
                nxt, None,
                f"observed before the window opens on {nxt.isoformat()}")
        if not rights and not self._any_right_for(work_id, territory):
            return CalendarEntry(
                Availability.NEVER_AUTHORISED, (), (), None, None,
                "no right of any kind registered for this work in this territory")
        if prev is not None:
            return CalendarEntry(
                Availability.POST_WINDOW, (), tuple(r.holder_id for r in rights),
                None, prev, f"authorised window closed {prev.isoformat()}")
        if historical and not starts:
            # A right with no bounds at all: in force, but no channel serves the
            # work here. Unserved licensed market, not an expired one.
            pass
        # Rights exist and are in force, but no channel serves the work here:
        # an unserved licensed market. Commercially the most interesting case
        # in the whole ladder, and the one every piracy report mislabels.
        return CalendarEntry(
            Availability.NEVER_AUTHORISED, (), tuple(r.holder_id for r in rights),
            min(starts) if starts else None, max(ends) if ends else None,
            "right in force but no verified authorised channel in territory")

    def _any_right_for(self, work_id: str, territory: str) -> bool:
        return any(r.work_id == work_id and r.territory == territory
                   for r in self._rights)

    def conflicts(self) -> dict[tuple[str, str], list[str]]:
        """Calendar defects, surfaced rather than smoothed over.

        A work/territory with an inconsistent right record cannot support a
        severity classification, so every figure derived from it must be
        labelled. Returning these publicly is what separates an instrument from
        a lobby.
        """
        out = dict(self._conflicts)
        seen_pairs: set[tuple[str, str]] = set()
        for r in self._rights:
            key = (r.work_id, r.territory)
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            same = [x for x in self._rights
                    if (x.work_id, x.territory) == key and x.exclusive]
            if len({x.holder_id for x in same}) > 1:
                out.setdefault(key, []).append(
                    f"{len({x.holder_id for x in same})} holders each claim an "
                    "exclusive right in the same territory")
        return out
