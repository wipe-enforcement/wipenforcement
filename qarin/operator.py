"""Infrastructure clustering: from copies to the businesses that sell them.

Titles do not go to court. **Operators do.** A rightsholder's real problem is
never "there are 4,000 infringing URLs"; it is "there are four businesses, and
each of them runs a thousand URLs". Enforcement against a URL is whack-a-mole by
definition, and the industry has spent two decades demonstrating that. The
actionable unit is the entity, and the entity is discoverable from passive
public data, because infrastructure has to be shared to be cheap.

The signals, roughly in descending order of how much they mean:

- same resolved IP or IP block, same ASN
- same TLS certificate *key* — a shared leaf certificate across unrelated
  businesses is nearly impossible to arrange innocently
- same favicon bytes, same JS/HTML structural fingerprint (template cloning)
- same analytics and ad-network account IDs (``G-XXXX``, ``UA-``, ``pub-``,
  pixel IDs), same payment endpoint, same Telegram bot handle
- same registrar IANA ID, same MX provider, same nameservers, same WHOIS e-mail
- same release group tag in the filename grammar (:mod:`qarin.canonical`)

**The trap, and the reason this module exists as a separate file.** Every one of
those signals is *shared by innocent design* at some prevalence. Cloudflare
fronts hundreds of thousands of domains on a handful of IPs. A quarter of the
Arabic web runs on one analytics account structure. Two sites can share a
registrar, a template, a nameserver and a payment gateway and have nothing
else in common — they are two customers of the same vendor.

Clustering on a prevalent signal does not find operators; it finds *vendors*, and
it produces exactly the false accusation that the whole platform exists to
avoid. So each signal is weighted by **inverse document frequency** over the
corpus:

    w(s) = log(N / n_s)

where ``n_s`` is how many distinct sources carry value ``s``. A value appearing
in one source has maximum information; a value appearing in half the corpus has
almost none. That is not a heuristic borrowed for its sound — it is the correct
measure of how much an observation reduces uncertainty about common ownership,
and it makes the CDN problem quantitative rather than a matter of tuning:
Cloudflare's IPs simply score near zero, automatically, without anyone having to
maintain a blocklist that the next CDN would evade.

On top of IDF there are two hard floors, because a weighted sum can still be
made to cross a threshold by accumulating enough near-nothings:

1. ``MIN_DECISIVE_SIGNAL`` — attribution requires at least one signal whose own
   IDF weight is decisive. Certificate keys, ad-account IDs and favicon bytes
   qualify; ASN, registrar and nameserver do not, however many sites agree on
   them.
2. ``MIN_TOTAL`` — the summed weight must also clear a floor.

Both must hold, and the *reasons* are returned. Below the floors the output is
``CO_HOSTED`` — these things share plumbing — never ``OPERATOR``. The difference
between those two words is the difference between a lead and a libel, and this
module's job is to refuse to blur it.
"""
from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

# --------------------------------------------------------------------------
# signal classes and their base reliability, before corpus prevalence
# --------------------------------------------------------------------------
#: Base strength of a signal *class*, independent of how common its values are.
#: ``1.0`` means "sharing this is close to impossible without common control".
CLASS_WEIGHT: Mapping[str, float] = {
    "tls_cert_key": 1.00,     # same leaf certificate across sites
    "ad_account": 0.95,       # same monetisation account id
    "analytics_id": 0.90,
    "payment_endpoint": 0.90,
    "telegram_bot": 0.90,
    "favicon_bytes": 0.80,
    "struct_fp": 0.75,        # template skeleton, see receipt.structural_fingerprint
    "release_group": 0.70,
    "ip": 0.65,
    "ip_block": 0.50,
    "mx_provider": 0.35,
    "nameserver": 0.30,
    "registrar_iana": 0.25,
    "whois_email": 0.55,
    "asn": 0.20,
    "cdn": 0.15,
    "lang_stack": 0.10,
}

#: A signal may only carry an attribution on its own if its class weight is at
#: least this. ASN, registrar, nameserver and CDN can never be decisive: they
#: are vendor relationships, not evidence of control.
#: A favicon and a template are things you can BUY, from the same catalogue of
#: dozens. They are evidence, never the only evidence, so the decisive floor
#: sits above both. What can be decisive is what cannot be shared innocently:
#: a certificate key, a monetisation account, a payment endpoint, a bot token.
DECISIVE_CLASS_FLOOR = 0.85

#: Minimum IDF for a signal to count as decisive. With the smoothed IDF this
#: floor is never the binding constraint — the vendor zeroing does that work:
#: a zeroed signal is not decisive, whatever its class weight claims.
DECISIVE_IDF_FLOOR = 0.50

#: Absolute floor on the vendor guard. Below this many carriers, prevalence is
#: not estimable and the guard stands down rather than judging zero.
VENDOR_MIN_CARRIERS = 4

#: Minimum summed weight for any cluster to be asserted as one operator.
#: Calibrated against the weakest decisive signal in the smallest admissible
#: corpus: a lone shared certificate at the IDF floor must still clear it, or
#: real operators running two sites each would never be attributed at all.
MIN_TOTAL = 0.65

#: Minimum summed weight to say "co-hosted" rather than "incidental".
MIN_WEAK = 0.30

#: Values occurring in at least this fraction of sources are treated as
#: infrastructure rather than evidence, whatever their class weight claims. This
#: is the explicit vendor guard: it fires on the *corpus*, not on a list of
#: known CDNs, so a new hosting provider cannot evade it by being new.
VENDOR_PREVALENCE_CAP = 0.30


@dataclass(frozen=True)
class Signal:
    """One observed infrastructure fact about one source."""

    cls: str            # a key of CLASS_WEIGHT
    value: str

    def key(self) -> str:
        return f"{self.cls}:{self.value}"


@dataclass
class Evidence:
    """Why two sources were joined, in the units the decision was made of."""

    signal: Signal
    idf: float
    weight: float
    decisive: bool

    def describe(self) -> str:
        return (f"{self.signal.cls}={self.signal.value[:24]} "
                f"idf={self.idf:.2f} w={self.weight:.2f}"
                + (" DECISIVE" if self.decisive else ""))


@dataclass
class Cluster:
    """A set of sources believed to be one operation, with its own confidence."""

    id: str
    sources: frozenset[str]
    total_weight: float
    evidence: tuple[Evidence, ...]
    #: OPERATOR: attribution asserted. CO_HOSTED: shared plumbing, no claim of
    #: common control. INCIDENTAL: below even the weak floor, kept for review.
    verdict: str
    #: The reason a *near*-attribution failed, when it did. Surfaced because
    #: "we declined to accuse" is a product feature, not an absence of one.
    refusal: str | None = None

    @property
    def size(self) -> int:
        return len(self.sources)

    @property
    def attributable(self) -> bool:
        return self.verdict == "OPERATOR"

    def summary(self) -> str:
        dec = [e for e in self.evidence if e.decisive]
        head = dec[0].describe() if dec else (
            self.evidence[0].describe() if self.evidence else "no shared signal")
        return (f"{self.verdict} {self.size} source(s) w={self.total_weight:.2f} "
                f"via {head}")


# --------------------------------------------------------------------------
# union-find with the evidence kept
# --------------------------------------------------------------------------
class _DSU:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:      # path compression
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


# --------------------------------------------------------------------------
# clustering
# --------------------------------------------------------------------------
def _idf_table(signals_by_source: Mapping[str, Sequence[Signal]]) -> dict[str, float]:
    """log(N / n_s) per signal value, with the vendor cap applied afterwards.

    Computed on *distinct sources*, never on occurrences: a site that repeats
    the same analytics ID in nine scripts is one observation, not nine, and
    counting it nine times would make the most-repeated tag look the most
    informative, which is precisely backwards.
    """
    n_sources = len(signals_by_source)
    if n_sources == 0:
        return {}
    carriers: dict[str, set[str]] = defaultdict(set)
    for src, sigs in signals_by_source.items():
        for s in sigs:
            carriers[s.key()].add(src)
    out: dict[str, float] = {}
    for key, holders in carriers.items():
        n_s = len(holders)
        prev = n_s / n_sources
        # A value on more than VENDOR_PREVALENCE_CAP of sources is
        # infrastructure. It is zeroed rather than discounted: discounting a
        # Cloudflare IP still lets it contribute, and the accumulation of many
        # small contributions is exactly how a false cluster gets built.
        #
        # VENDOR_MIN_CARRIERS is the other half of the test, and it is what keeps
        # this guard from eating true evidence. A vendor has many customers; two
        # sources sharing one certificate is not a vendor, it is an operator.
        # Without the absolute floor, a corpus of two sources makes *every*
        # signal 100% prevalent and the method returns nothing at all — which is
        # how this function was first written, and only a test caught it.
        # Prevalence is simply not estimable below a handful of carriers, so the
        # guard declines to judge rather than judging zero.
        if n_s >= VENDOR_MIN_CARRIERS and prev > VENDOR_PREVALENCE_CAP:
            out[key] = 0.0
            continue
        # log(1 + N/n_s) rather than log(N/n_s): the unsmoothed form is
        # identically zero whenever a signal is carried by every source, which in
        # a small corpus is the ordinary case and not a verdict of "vendor".
        out[key] = math.log(1.0 + n_sources / n_s) if n_s else 0.0
    return out


def cluster_offerings(signals_by_source: Mapping[str, Sequence[Signal]],
                      *, min_total: float = MIN_TOTAL,
                      min_weak: float = MIN_WEAK,
                      ) -> list[Cluster]:
    """Group sources into candidate operators.

    Joins are made on *decisive-or-informative* edges only, and each edge's
    weight is the class weight scaled by its IDF. The scaling is multiplicative
    rather than additive-in-the-exponent because the two factors answer different
    questions and a zero in either must annihilate the evidence: ``class_weight``
    asks "if two sites share this, how unusual is that?" and ``idf`` asks "is
    this value shared by everybody anyway?". A shared Cloudflare IP scores 0.15
    on the first and 0.0 on the second, and the product correctly says zero.
    """
    idf = _idf_table(signals_by_source)
    # value -> sources carrying it, restricted to values with any information
    by_value: dict[str, list[str]] = defaultdict(list)
    for src, sigs in signals_by_source.items():
        for s in sigs:
            if idf.get(s.key(), 0.0) > 0.0:
                by_value[s.key()].append(src)

    dsu = _DSU()
    for src in signals_by_source:
        dsu.find(src)
    edges: dict[tuple[str, str], list[Evidence]] = defaultdict(list)
    for key, holders in by_value.items():
        if len(holders) < 2:
            continue
        cls, _, value = key.partition(":")
        cw = CLASS_WEIGHT.get(cls, 0.1)
        w = cw * idf[key]
        decisive = (cw >= DECISIVE_CLASS_FLOOR and idf[key] >= DECISIVE_IDF_FLOOR)
        holders = sorted(holders)
        for i, a in enumerate(holders):
            for b in holders[i + 1:]:
                pair = (a, b) if a <= b else (b, a)
                edges[pair].append(Evidence(Signal(cls, value), idf[key], w, decisive))
                dsu.union(a, b)

    groups: dict[str, list[str]] = defaultdict(list)
    for src in signals_by_source:
        groups[dsu.find(src)].append(src)

    out: list[Cluster] = []
    for n, (root, members) in enumerate(sorted(groups.items()), 1):
        if len(members) < 2:
            continue
        ev: list[Evidence] = []
        for i, a in enumerate(sorted(members)):
            for b in sorted(members)[i + 1:]:
                pair = (a, b) if a <= b else (b, a)
                ev.extend(edges.get(pair, ()))
        # Deduplicate identical evidence: the same shared certificate seen
        # across five members is one fact, not ten.
        seen: set[str] = set()
        uniq: list[Evidence] = []
        for e in sorted(ev, key=lambda x: -x.weight):
            k = e.signal.key()
            if k not in seen:
                seen.add(k)
                uniq.append(e)
        total = sum(e.weight for e in uniq)
        decisive = [e for e in uniq if e.decisive]
        cid = f"cl_{n:03d}_{root[:8]}"
        if decisive and total >= min_total:
            verdict, refusal = "OPERATOR", None
        elif total >= min_weak:
            verdict = "CO_HOSTED"
            refusal = ("no decisive signal above the floors "
                       f"(class>={DECISIVE_CLASS_FLOOR:.2f}, idf>={DECISIVE_IDF_FLOOR:.2f}); "
                       f"best={max((e.weight for e in uniq), default=0.0):.2f}"
                       if not decisive else
                       f"weight {total:.2f} below the attribution floor {min_total:.2f}")
        else:
            verdict, refusal = "INCIDENTAL", (
                f"total weight {total:.2f} below even the weak floor {min_weak:.2f}")
        out.append(Cluster(cid, frozenset(members), round(total, 4),
                           tuple(uniq), verdict, refusal))
    out.sort(key=lambda c: (-c.total_weight, -c.size))
    return out


# --------------------------------------------------------------------------
# attribution of one offering set
# --------------------------------------------------------------------------
@dataclass
class Attribution:
    """The answer to "who runs this?", with its confidence and its limits."""

    cluster_id: str | None
    verdict: str
    confidence: float
    sources: frozenset[str]
    evidence: tuple[Evidence, ...]
    refusal: str | None = None

    @property
    def attributable(self) -> bool:
        return self.verdict == "OPERATOR"

    def describe(self) -> str:
        if self.verdict == "OPERATOR":
            return (f"attributed to one operator ({self.confidence:.2f}) across "
                    f"{len(self.sources)} source(s)")
        return f"not attributed ({self.verdict}): {self.refusal}"


def attribute(source: str, clusters: Sequence[Cluster]) -> Attribution:
    """Look up one source in a computed clustering.

    Returns an explicit ``UN clustered`` verdict rather than ``None`` when a
    source appears in no cluster at all — a singleton is a real finding (this
    operator is running this source alone, or nothing else shares its
    infrastructure) and must not read as missing data.
    """
    for c in clusters:
        if source in c.sources:
            n_dec = sum(1 for e in c.evidence if e.decisive)
            conf = min(1.0, c.total_weight / 3.0) if c.verdict == "OPERATOR" else (
                0.4 if c.verdict == "CO_HOSTED" else 0.1)
            return Attribution(c.id, c.verdict, round(conf, 3), c.sources,
                               c.evidence, c.refusal)
    return Attribution(None, "UNCLUSTERED", 0.0, frozenset({source}), (),
                       "no other source shares any informative signal with this one")


# --------------------------------------------------------------------------
# extraction helpers: turning raw captures into Signals
# --------------------------------------------------------------------------
# No bare "pub-" here: it double-matches inside "ca-pub-", so one AdSense
# account would arrive as both an analytics_id and an ad_account and be counted
# twice toward the weight. The Adsense pattern below owns that string alone.
_RE_ANALYTICS = re.compile(r"\b(?:G-[A-Z0-9]{6,12}|UA-\d{6,}(?:-\d+)?|"
                           r"GTM-[A-Z0-9]{4,8}|AW-\d{6,})\b")
_RE_PIXEL = re.compile(r"\bfb(?:pic|q)|pixel\.facebook\.com/tr\?id=([0-9]+)")
_RE_BOT = re.compile(r"@([A-Za-z][A-Za-z0-9_]{4,31})\b")
_RE_GROUP = re.compile(r"(?:^|[-–—|])\s*([A-Z][A-Za-z0-9]{2,15})\s*$")


def signals_from_html(html: str, *, url: str | None = None,
                      favicon_sha: str | None = None,
                      struct_fp: str | None = None,
                      tls_cert_key: str | None = None,
                      ips: Sequence[str] = (), asn: str | None = None,
                      registrar_iana: str | None = None,
                      nameservers: Sequence[str] = (),
                      whois_email: str | None = None,
                      mx: Sequence[str] = ()) -> list[Signal]:
    """Extract infrastructure signals from one capture.

    Every regex here is deliberately conservative about *what it emits*: a
    false positive in the signal set becomes a false edge in the cluster, and
    edges compound. Nothing is emitted from a guessed pattern.
    """
    out: list[Signal] = []
    if not html:
        html = ""
    for m in _RE_ANALYTICS.finditer(html):
        out.append(Signal("analytics_id", m.group(0)))
    for m in re.finditer(r"facebook\.com/tr\?id=(\d{6,20})", html):
        out.append(Signal("ad_account", "fbpx:" + m.group(1)))
    for m in re.finditer(r"(?:client|publisher|ca)-pub-(\d{9,16})", html):
        out.append(Signal("ad_account", "adsense:" + m.group(1)))
    # Bot tokens are "<id>:<34 chars>" and the secret alphabet includes "-" and
    # "_". Leaving "-" out of the class silently drops every token that has one.
    for m in re.finditer(r"api\.telegram\.org/bot(\d+:[A-Za-z0-9_-]{20,})/", html):
        out.append(Signal("telegram_bot", m.group(1)))
    if favicon_sha:
        out.append(Signal("favicon_bytes", favicon_sha))
    if struct_fp:
        out.append(Signal("struct_fp", struct_fp))
    if tls_cert_key:
        out.append(Signal("tls_cert_key", tls_cert_key))
    for ip in ips:
        out.append(Signal("ip", ip))
        # /24 for v4: adjacent IPs in one rack are one operation, but a whole
        # ASN is a vendor. The block is the honest granularity.
        if ip.count(".") == 3:
            out.append(Signal("ip_block", ".".join(ip.split(".")[:3]) + ".0/24"))
    if asn:
        out.append(Signal("asn", asn))
    if registrar_iana:
        out.append(Signal("registrar_iana", registrar_iana))
    for ns in nameservers:
        out.append(Signal("nameserver", ns.lower().rstrip(".")))
    if whois_email:
        out.append(Signal("whois_email", whois_email.lower()))
    for m in mx:
        out.append(Signal("mx_provider", m.lower().rstrip(".")))
    if url:
        m = _RE_BOT.search(url)
        if m:
            out.append(Signal("telegram_bot", m.group(1)))
    # De-duplicate while preserving order: repeated tags are one fact.
    seen: set[str] = set()
    uniq: list[Signal] = []
    for s in out:
        if s.key() not in seen:
            seen.add(s.key())
            uniq.append(s)
    return uniq
