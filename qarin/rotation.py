"""The recogniser: classify what actually arrived, and never emit a target.

This module is the inverse of :func:`qarin.discover.enumerate_rotation_candidates`,
and the inversion is the whole point. That enumerator exists to *validate* the
rotation grammar — it proves the rules were induced correctly by reproducing the
domains that were actually recorded at the last three shutdowns of one network.
It is not a production path. Generating hypothetical lookalike names is noisy
(most are unregistered, so watching them is watching nothing) and it is dual-use
in a way that a classifier is not.

What the fleet runs in production is this: consume two feeds the platform does not
control, and ask of each incoming name only whether the grammar explains it.

**Certificate transparency is the surface that matters most here.** A name appears
in a CT log the moment a certificate is issued for it, which is *before* the site
serves anything and independently of whether anything was newly registered. That
closes the one rotation technique the WHOIS feed cannot see at all: subdomain
rotation. ``w<n>.<brand>.<tld>`` → ``w<n+1>.<brand>.<tld>`` produces no registration
event whatsoever, because the apex domain was never touched — the operator only
needs a certificate, and there is no way to serve TLS without one.

**The drop list is the other half.** A brand-adjacent name reaching redemption is
a name about to change hands. That is the acquisition moment, not its
consequence, and it is the only surface on which an operator's *next*
infrastructure can be seen before they have decided to use it.

Both feeds are public, both are passive, and neither requires anybody's
cooperation — which is what makes them worth more than any amount of clever
searching, because searching reaches only what a search engine has already
indexed, and an index is a record of the past.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .discover import (
    Brand,
    BrandRegistry,
    COMBO_WORDS,
    HOMOGLYPHS,
    SUBDOMAIN_PREFIXES,
    _ROTATION_RULES,
)

# ==========================================================================
# homoglyph folding
# ==========================================================================
def fold_homoglyphs(s: str) -> str:
    """Map confusable glyphs onto their Latin lookalikes before comparing.

    Done at the boundary rather than inside each matcher, because every consumer
    of a brand token has to do it or the entire class is invisible: "ATLAS PR0"
    is Atlas Pro, and a string comparison sees two unrelated products. The fold
    is strictly one-directional (lookalike -> intended Latin), and that is not a
    simplification — generating homoglyphs *from* a clean brand would explode
    the candidate space with no increase in recall, which is exactly the failure
    mode this module was created to avoid.
    """
    # HOMOGLYPHS maps lookalike -> intended Latin ("0" looks like "o"), so the
    # fold must run lookalike -> Latin. An earlier revision tested `ch == real`
    # and appended `look`, which folded Latin INTO the confusables: "mycima"
    # became "mуcіm@" with a Cyrillic у, a Cyrillic с and an at-sign.
    #
    # It survived every other test here because exact matching corrupts both
    # sides identically and still compares equal — so the inverted fold broke
    # only the *approximate* cases (edit distance, combo stripping), which are
    # the entire reason it exists. A fold that is a bijection on its own output
    # is the failure nobody notices, and it is asserted against directly below.
    out = []
    for ch in s.lower():
        out.append(HOMOGLYPHS.get(ch, ch))
    return "".join(out)


# ==========================================================================
# edit distance, capped
# ==========================================================================
def _edits(a: str, b: str, cap: int = 2) -> int:
    """Levenshtein, capped at ``cap``.

    The cap is not an optimisation detail, it is the design: this has to run
    over every name in a CT feed, millions a day, against every brand, in pure
    Python. Early exit on both the length difference and the running row minimum
    keeps it at a handful of operations per pair, and the classification bands
    stop at two edits anyway, so anything beyond that returns the same verdict
    however long it runs.
    """
    if a == b:
        return 0
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
        if min(cur) > cap:
            return cap + 1
        prev = cur
    return prev[-1]


def _which_rule(obs: str, want: str, alt_wants: frozenset[str] = frozenset()) -> str:
    """Name the transformation that explains an observed name.

    The rule is the product, not the verdict. "This looks like your brand" is an
    assertion anyone can make; "this is mycima with the i doubled on a novelty
    gTLD, which is the exact construction recorded at the last three shutdowns of
    this network" is evidence — falsifiable per name, and it accumulates into a
    fingerprint of how this particular operation buys longevity.
    """
    if obs == want:
        return "exact"
    # Collapse repeated substitutions, because the observed constructions double
    # a letter more than once (myciiima is mycima with the i doubled *and* the
    # second i retained; weciima likewise). Testing a single replace() reports
    # these as "unexplained", which loses the exact rule that makes them
    # recognisable as this operator's habit rather than as a random typo.
    for a, b in _ROTATION_RULES:
        if b in obs:
            collapsed = obs
            for _ in range(4):
                nxt = collapsed.replace(b, a)
                if nxt == collapsed:
                    break
                collapsed = nxt
            if collapsed == want:
                return f"{a}->{b}"
    # The collapse above only explains a name relative to *this one* spelling.
    # Brands in this corpus are registered with several spellings at once
    # (mycima, myciima, mycyma), and the observed stock is a doubling of the
    # non-canonical one — so explaining "myciiima" against "myciima" fails here
    # and the hit reports "unexplained-edit" even though the distance and the
    # verdict are right. Callers pass the whole spelling set so the rule can be
    # named against whichever spelling the construction actually applies to.
    for a, b in _ROTATION_RULES:
        if b not in obs:
            continue
        collapsed = obs
        for _ in range(4):
            nxt = collapsed.replace(b, a)
            if nxt == collapsed:
                break
            collapsed = nxt
        if collapsed in alt_wants:
            return f"{a}->{b}"
    for i in range(len(want)):
        if want[:i] + want[i + 1:] == obs:
            return f"omission:{want[i]}@{i}"
        if i + 1 < len(want) and (want[:i] + want[i + 1] + want[i]
                                  + want[i + 2:]) == obs:
            return f"transposition@{i}"
    for w in COMBO_WORDS:
        if obs == f"{want}-{w}":
            return f"combosquat:suffix-{w}"
        if obs == f"{w}{want}":
            return f"combosquat:prefix-{w}"
        if obs == f"{want}{w}":
            return f"combosquat:glue-{w}"
    return "unexplained-edit"


#: Distance bands. Three edits is "unrelated" however similar it looks to the
#: eye, and the band has to stop early or the false-positive rate on a feed of
#: millions of names makes the output unusable.
_BANDS = {0: "EXACT", 1: "ROTATION_STOCK", 2: "LOOKALIKE"}


@dataclass(frozen=True)
class Hit:
    """One observed name, classified against the brand grammar."""

    name: str
    brand_id: str | None
    verdict: str
    edits: int
    rule: str
    tld: str | None = None
    combo: str | None = None
    subdomain: str | None = None
    source: str | None = None      # certificate_transparency | whois_drop

    @property
    def actionable(self) -> bool:
        """Worth a human look.

        ``LOOKALIKE`` is recorded and *not* escalated: at two edits the innocent
        explanation — a different brand, a coincidence, a name that predates
        this one — is live, and escalating it is how a brand-protection feed
        becomes noise that gets muted inside a week.
        """
        return self.verdict in ("EXACT", "ROTATION_STOCK")

    def to_dict(self) -> dict:
        return {k: v for k, v in {
            "name": self.name, "brand": self.brand_id, "verdict": self.verdict,
            "edits": self.edits, "rule": self.rule, "tld": self.tld,
            "combo": self.combo, "subdomain": self.subdomain,
            "source": self.source, "actionable": self.actionable,
        }.items() if v is not None}


# ==========================================================================
# the recogniser
# ==========================================================================
class Recogniser:
    """Classifies incoming names against the brand grammar.

    Holds a precomputed brand-token set so the per-name cost is a scan over
    brands rather than over every generated variant — the enumerator is for
    validation, and this is the thing that runs at feed volume.
    """

    def __init__(self, reg: "BrandRegistry | None" = None, *,
                 intel: object | None = None) -> None:
        """``intel`` builds the brand set from a specific :class:`qarin.intel.Intel`.

        Needed because the test suite has to run the *same* machinery against two
        different target sets — the private intel and the public example — and a
        constructor that only accepted a registry would force the tests to reach
        into module globals to do it. Reading the globals instead would make the
        suite depend on which file happens to be on disk, and a test that passes
        only on one machine is testing the machine.
        """
        if reg is None and intel is not None:
            reg = BrandRegistry(Brand(
                id=b.id, names=b.names, latin=b.latin,
                successor_of=b.successor_of, observed_tlds=b.observed_tlds,
                peak_monthly_visits=b.peak_monthly_visits, source=b.source,
                status=b.status) for b in intel.brands)
        self.reg = reg or BrandRegistry()
        #: brand id -> {folded latin spellings}
        self._want: dict[str, set[str]] = {
            bid: {fold_homoglyphs(x) for x in b.latin}
            for bid, b in self.reg.brands.items()}
        self._tlds = {t for b in self.reg.brands.values() for t in b.observed_tlds}

    def classify(self, name: str, *, source: str | None = None) -> Hit | None:
        """Classify one hostname or app name. ``None`` means the grammar does
        not touch it — which is *not* a verdict of "unrelated", because the
        absence of a match says nothing about this brand and must never be
        counted as a finding in the aggregate.
        """
        if not name:
            return None
        host = name.strip().lower().rstrip(".")
        parts = host.split(".")
        if len(parts) < 2:
            return None
        tld = parts[-1]

        # Strip a known subdomain prefix before measuring distance, so
        # ``w<n>.<brand>.<tld>`` is judged on the brand label and the prefix is reported
        # separately. Without this, subdomain rotation reads as a four-edit
        # distance and falls out of the bands entirely — the operator's most
        # frequent move would be the one the grammar cannot see.
        # A fixed prefix list cannot work here, and it is worth stating because
        # the list is the intuitive approach: w13 is not in the observed set, so
        # the operator's single most mechanical move — incrementing a counter —
        # was invisible until the list was widened to nothing. So no list is
        # consulted for the *decision*. Every candidate label is judged and the
        # best classification wins; the prefix set is used only to name which
        # label was treated as a subdomain in the report. That is a weaker claim
        # about intent and a strictly stronger one about recall.
        sub = None
        zones = [parts[0]] + ([parts[1]] if len(parts) >= 3 else [])

        best: Hit | None = None
        for zone in zones:
            folded = fold_homoglyphs(zone)
            # Combosquatting is detected by *stripping a known word off the
            # observed label*, never by rebuilding the label from itself: an
            # earlier revision tested `folded == f"{folded}-{w}"`, which cannot
            # be true, so every brand-official.com name fell through to "no
            # match" — the single most productive construction in the documented
            # literature was invisible.
            combo, bare = None, folded
            for w in COMBO_WORDS:
                if len(bare) <= len(w) + 2:
                    continue
                if bare.endswith(f"-{w}"):
                    combo, bare = w, bare[:-(len(w) + 1)].strip("-")
                    break
                if bare.startswith(f"{w}-"):
                    combo, bare = w, bare[len(w) + 1:].strip("-")
                    break
                if bare.startswith(w) and len(bare) - len(w) >= 4:
                    combo, bare = w, bare[len(w):].strip("-")
                    break
                if bare.endswith(w) and len(bare) - len(w) >= 4:
                    combo, bare = w, bare[:-len(w)].strip("-")
                    break

            if sub is None and len(parts) >= 3 and zone != parts[0]:
                sub = zone if parts[0] in SUBDOMAIN_PREFIXES else parts[0]
            for cand in {folded, bare, folded.replace("-", ""),
                         bare.replace("-", "")}:
                if not cand:
                    continue
                for bid, wants in self._want.items():
                    for want in wants:
                        e = _edits(cand, want)
                        band = _BANDS.get(e + (1 if combo else 0))
                        if band is None:
                            continue
                        hit = Hit(host, bid, band, e,
                                  _which_rule(cand, want, wants),
                                  tld, combo, sub, source)
                        # Tie-break order matters and is not obvious: prefer
                        # fewer edits, then an EXACT verdict, then — only among
                        # equals — a hit whose rule actually explains the
                        # construction. Without the third key, a brand registered
                        # with several spellings (mycima / myciima / mycyma) can
                        # be matched by the *less* informative spelling first and
                        # report "unexplained-edit", which throws away the one
                        # thing the classification was built to produce: the
                        # operator's own habit. Set iteration made this
                        # non-deterministic, so it also had to be settled here
                        # rather than by luck.
                        key = (hit.edits, hit.verdict != "EXACT",
                               hit.rule == "unexplained-edit")
                        if best is None or key < (best.edits,
                                                  best.verdict != "EXACT",
                                                  best.rule == "unexplained-edit"):
                            best = hit
        return best

    def scan(self, names, *, source: str | None = None):
        """Classify a stream, yielding only the actionable hits.

        A generator, because a CT feed is unbounded and the useful output is a
        trickle: at 15M names a day the actionable set is tens, and anything
        that materialises the whole feed into a list has built a memory leak and
        called it an index.
        """
        for n in names:
            h = self.classify(n, source=source)
            if h is not None and h.actionable:
                yield h


# ==========================================================================
# route signature: the supplier behind the software
# ==========================================================================
#: Application routes observed across *different* brand families in one pass:
#:
#:     w<n>.<brand>.<tld>/watch.php?vid=<hex9>
#:     w<n>.<brand>.<tld>/video.php?vid=<hex9>      (four hosts, two brand families)
#:
#: Same script names, same query parameter, same fixed-width hex id shape, across
#: two apparently unrelated brands. That is not coincidence and it is not proof
#: of one owner either — it is the signature of a **piracy-as-a-service product**,
#: which the MPA documents directly ("pirate sites and IPTV operators build
#: off-the-shelf streaming operations": Vidsrc, WHMCS Smarters, HydraHD).
#:
#: So a route attributes to the *supplier*, not the operator, and that is a
#: different and usually far better enforcement target: one notice to a PaaS
#: vendor takes a hundred sites down, where one notice to a site takes one down.
#: It is kept out of :mod:`qarin.operator` for that reason — the two answer
#: different questions, and folding a shared vendor into a shared-owner cluster
#: is precisely the false-accusation failure the IDF guard exists to prevent.
ROUTES: tuple[tuple[str, str, str], ...] = (
    (r"(?:watch|video)\.php\?vid=[0-9a-f]{8,12}", "paas_player", "supplier"),
    (r":1935/live/[a-z0-9_\-]+/(?:chunklist|playlist|m3u8)", "rtmp_hls_panel",
     "supplier"),
    (r"/live/[a-z0-9_\-]+/chunklist", "rtmp_hls_panel", "supplier"),
    (r"\.m3u8?\?token=", "tokenised_hls", "operator"),
    (r"/player/[0-9a-f]{8}\.html", "embed_player_shell", "supplier"),
)


@dataclass(frozen=True)
class Route:
    """What a URL says about the software behind it, and who supplied that."""

    url: str
    product: str
    target: str
    pattern: str

    def to_dict(self) -> dict:
        return {"url": self.url, "product": self.product, "target": self.target}


def route_of(url: str) -> Route | None:
    """Identify the streaming application behind a URL, from the URL alone.

    Free, passive, available at the same instant as the receipt, and requiring
    neither a fetch nor a certificate — the highest yield per byte in the whole
    discovery layer. Worth keeping distinct from content hashing for a specific
    reason: a template redesign never touches a route, so a route *change* means
    the operator moved supplier, which is itself a finding, and one that arrives
    with no new observation at all.
    """
    if not url:
        return None
    u = url.lower()
    for pat, product, target in ROUTES:
        if re.search(pat, u):
            return Route(url, product, target, pat)
    return None


# ==========================================================================
# the APK layer: the most stable operator key available
# ==========================================================================
#: Android package naming is conventionally the reversed domain the developer
#: controls, so a package id is a leaked apex domain — and unlike a domain it is
#: essentially never rotated, because changing it breaks every existing install
#: and every auto-update path. Observed in this corpus:
#: ``com.aflamtvmaroc.moviesdarija`` ("Aflam Maghribia", Moroccan Darija films,
#: marketed as "a free alternative to Netflix in Morocco").
#:
#: Three consequences, which are why this small surface outperforms its size:
#:   1. it is the most stable operator key anywhere in the system;
#:   2. it discloses the domain controlled *at authoring time*, which may have
#:      been surrendered years ago and may resolve to nothing today;
#:   3. it is searchable in the official stores, where enforcement is a policy
#:      ticket rather than litigation in a foreign jurisdiction.
_RE_PACKAGE = re.compile(r"\b(?:[a-z][a-z0-9_]*\.){2,}[a-z][a-z0-9_]*\b")
_RE_VERSION = re.compile(r"\bv\s?(\d{1,3})\.(\d{1,2})(?:\.(\d{1,3}))?([a-z]?)",
                         re.IGNORECASE)
_RE_SHORTENER = re.compile(r"\b(?:bit\.ly|cutt\.(?:ly|us)|tinyurl\.com|"
                           r"short\.link|rebrand\.ly|ow\.ly|t\.cn|lnkiy\.com|"
                           r"exe\.io|411\.ai|droplink\.co|shorturl\.at)\b")
#: Products in this corpus are named after the legal platforms they pirate:
#: SHAHID PLUS, ALIFLIX, MTNTV, BLADEUHD, VICTV, CRYSTAL OTT, STORM ONE,
#: ATLAS PR0. Recorded as a *legal-brand* impersonation table, distinct from
#: KNOWN_BRANDS, because the enforcement path is completely different.
_LEGAL_PLATFORMS = {
    "shahid": "Shahid (MBC Group)", "mbc": "MBC Group", "osn": "OSN+",
    "bein": "beIN", "netflix": "Netflix", "starz": "STARZPLAY",
    "viu": "Viu", "qtv": "Qatar TV", "art": "ART", "rotana": "Rotana",
}


@dataclass(frozen=True)
class Version:
    """A parsed release version.

    ``explicit_minor`` is not derivable from the numbers and has to be carried:
    "v11.0" and "v11.0.0" are the same version written two ways, and collapsing
    them loses which one the operator used — a detail that matters because the
    spelling of a version string is itself a fingerprint of the same developer
    across a rebrand.
    """

    major: int
    minor: int
    patch: int
    suffix: str = ""
    explicit_patch: bool = False

    def key(self) -> tuple:
        return (self.major, self.minor, self.patch)

    def __str__(self) -> str:
        core = (f"{self.major}.{self.minor}.{self.patch}" if self.explicit_patch
                else f"{self.major}.{self.minor}")
        return core + self.suffix


@dataclass(frozen=True)
class Release:
    """One app release, as the Telegram layer states it.

    Posting convention in this corpus is rigid enough to parse without any
    cooperation: app name, version, size, Android compatibility, then a
    shortener link (observed on @Expert_Net, @xonetvplus, @apkmodsfrreee,
    @ameer_droid, @androidone01).

    The version string is the interesting field, and not for its own sake:
    ``V4.1`` → ``V4.1a`` → ``V10.0`` → ``V11.0.0`` is a *development history*,
    and an app that rebrands while continuing the sequence is the same
    developer. That makes version monotonicity an operator key nearly as durable
    as the package id, and available even when the package is changed.
    """

    app: str | None
    version: Version | None
    package: str | None
    impersonates: str | None
    shortener: bool
    channel: str | None = None
    size_mb: float | None = None
    raw: str | None = None

    @property
    def version_key(self) -> str | None:
        return None if self.version is None else str(self.version)

    def to_dict(self) -> dict:
        return {k: v for k, v in {
            "app": self.app, "version": self.version_key, "package": self.package,
            "impersonates": self.impersonates, "shortener": self.shortener,
            "channel": self.channel, "size_mb": self.size_mb,
        }.items() if v is not None}


def parse_release(text: str, *, channel: str | None = None) -> Release | None:
    """Read one app-release post into structured fields.

    ``impersonates`` is the commercially important output. Impersonating a
    registered mark is actionable in an app store on its own merits — it needs
    no proof of a single act of infringement, no foreign jurisdiction, no
    certificate and no takedown of anything. It is the fastest removal route in
    the entire system, and it is available against the *same* operations that
    are otherwise the hardest to touch.
    """
    if not text:
        return None
    low = text.lower()

    package = None
    for m in _RE_PACKAGE.finditer(text):
        cand = m.group(0)
        # A package id must have at least three labels and its last label must
        # not look like a public-suffix domain, or the "package" is really a
        # hostname mentioned in the post.
        if cand.count(".") >= 2 and not re.search(r"\.(com|net|org)$", cand):
            package = cand
            break

    vm = _RE_VERSION.search(text)

    sm = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:mb|ميجا|ميجا بايت)", low)
    size = None
    if sm:
        try:
            size = float(sm.group(1).replace(",", "."))
        except ValueError:
            pass

    imp = None
    for key, label in _LEGAL_PLATFORMS.items():
        if key in low:
            imp = label
            break

    # The suffix is part of the name. "SHAHID PLUS" is the impersonating
    # product, and capturing only "SHAHID" would report the victim as the
    # accused — which is the one inversion in this file that produces an
    # allegation against the party we are trying to help.
    am = re.search(r"\b([A-Z][A-Z0-9_]{2,20}\s*(?:PLUS|PRO|PR0|HD|TV|LIX|ONE|"
                   r"UHD|VIP|OTT))\b", text)
    # ``explicit_minor`` records whether the third component was written at all,
    # which is not the same as whether it is zero: "v11.0.0" must round-trip as
    # 11.0.0 and not collapse to 11.0. Deriving it from the numbers alone is
    # what made the first revision emit "11.0" for a three-part version.
    return Release(app=am.group(1) if am else None,
                   version=(Version(int(vm.group(1)), int(vm.group(2)),
                                    int(vm.group(3) or 0),
                                    (vm.group(4) or "").lower(),
                                    vm.group(3) is not None)
                            if vm else None),
                   package=package, impersonates=imp,
                   shortener=bool(_RE_SHORTENER.search(low)), channel=channel,
                   size_mb=size, raw=text[:400])


def continues_sequence(earlier: Release, later: Release) -> bool | None:
    """Does the later release look like the same developer's next version?

    Returns ``None`` when either side has no version, because "cannot tell" is
    the honest answer and a bool here would be read as evidence either way.

    This is the cheapest operator link available on the app surface: it needs no
    infrastructure overlap at all, so it survives a full domain *and* package
    *and* template rotation. The strictness is deliberate — a major-version jump
    with no minor continuity is not enough on its own, because independent
    developers both go v4 → v10 constantly.
    """
    if not earlier.version or not later.version:
        return None
    a, b = earlier.version.key(), later.version.key()
    if b <= a:
        return False
    # Adjacency in any one component, with the rest reset, is the signature of
    # one version train: 4.1.0 -> 4.1.1, 4.1.0 -> 4.2.0, 4.1.0 -> 5.0.0.
    if a[0] == b[0]:
        return b[1] - a[1] in (0, 1) or (b[1] == a[1] and b[2] >= a[2])
    return b[0] - a[0] == 1 and b[1] == 0 and b[2] == 0


def package_to_domains(package: str) -> tuple[str, ...]:
    """Recover the apex domains a package id implies, per Android naming custom.

    ``com.aflamtvmaroc.moviesdarija`` implies ``aflamtvmaroc.com``. The mapping
    is not guaranteed — developers use ``app.``, ``tv.``, ``io.`` and plain
    ``com.`` inconsistently — so these are *candidates* for lookup in the
    registration and drop feeds, not assertions, and the lookup is what decides.

    What makes it worth doing is that the implied domain may have expired years
    ago. The package id is then a fossil record of the operator's earlier
    infrastructure, and expired brand-adjacent names are exactly what the
    drop-list surface watches — so an app installed today can name a domain that
    becomes available next month.
    """
    if not package:
        return ()
    parts = package.split(".")
    if len(parts) < 3:
        return ()
    # Reject the shapes that are not package ids at all. A trailing "apk" means
    # the string is a filename rather than a manifest id; a middle label of one
    # or two characters means the reverse-domain convention is not what is in
    # front of us. Expanding those into candidate domains produces confident
    # nonsense — the first revision turned "com.shahid.plus.apk" into plus.com,
    # plus.app and seven other names that belong to nobody in this corpus.
    tail = parts[-1].lower()
    mid = [p for p in parts[1:-1] if len(p) >= 3]
    if not mid or tail in ("apk", "exe", "zip", "jar", "pro", "mod", "vip"):
        return ()
    out = {f"{p}.{tail}" for p in mid}
    out |= {f"{p}.{t}" for p in mid
            for t in ("com", "net", "tv", "app", "io", "live", "xyz", "me",
                      "online", "site")}
    return tuple(sorted(o for o in out if len(o.split(".")[0]) >= 3))
