"""Discovery: the query lexicon, the surfaces, and the rotation forecast.

This module exists because of a finding, not a guess. Searching the public Arabic
web for how Arabic film pages are titled returns this, from a page on one of the
largest networks in the region:

    "نمط عناوين البحث الشائعة: اسم الفيلم + السنة + «مدبلج» + «HD أون لاين» +
     أسماء مواقع المشاهدة (ماي سيما، شاهد فور يو، عرب سيد) للظهور في نتائج البحث"

    "the common search-title pattern: film name + year + 'dubbed' + 'HD online'
     + the names of streaming sites (MyCima, Shahid For You, ArabSeed), in order
     to appear in search results"

The pirate's own SEO is *film name + Arabic/English keyword mix + competitor
brand names*. An expert searcher finds more infringing content by writing queries
the same way for exactly that reason: they are not searching for the work, they
are searching the way the supply side advertises it. That is why the technique
works, and it is why this module treats it as a **first-class probe generator**
rather than a folk trick.

It also means the technique has a second application its practitioners did not
intend, and which is worth more to an enforcement platform than the searching:

1. **Brand co-occurrence is an operator signal, not just a search trick.** A
   lookalike domain ``eegebest.com`` was found carrying keyword metadata for the
   whole family — egybest, mycima, wecima, cima4u, arabseed, akwam, faselhd.
   Nobody who owns one site stuffs six competitors' brands into their own meta
   tags. Whoever registers rotation stock for a network advertises for all of it.
   So the co-occurrence *is* the attribution — IDF-guarded, because the brands
   themselves are high-prevalence tokens.

2. **The misspelling is systematic, so the next domain is predictable.** When
   Egypt shut MyCima down (Alexandria; ~12,000 films, ~26,000 series, ~50m visits
   a month) it was back within days as WeCima on ``wecima.tube``, with roughly
   seventy near-identical domains in circulation — ``myciiima.autos``, ``.bond``,
   ``.boats``, ``.makeup``, ``.monster`` — and the ``weciima.*`` replacements
   *pre-registered before the rebrand*. Vowel doubling plus a recognisable set of
   cheap new gTLDs. That is a generative grammar, and a grammar can be enumerated
   ahead of time: the fleet can watch domains that have not been pointed at
   anything yet, which converts enforcement from reactive to anticipatory.

**The refinement this module exists to impose.** A thousand clever queries are
not a thousand detectors. Every one of them is a probe of *one* surface — the
Google index — and :func:`qarin.metrics.supply_coverage` treats correlated probes
as a single trapping occasion, correctly. So keyword variety buys **recall within
a surface** and nothing at all in fleet coverage. Coverage is bought with
surfaces, and the surfaces are distinct in kind, not in wording:

    search index · site crawl · link/SEO farms · Telegram public channels ·
    m3u/IPTV manifests · app stores · torrent swarms · UGC platforms ·
    WHOIS-new-domain feed · paste sites

The bookkeeping here is therefore per-surface, and :class:`QueryPlan` refuses to
report a coverage contribution that the independence arithmetic does not support.
Getting this wrong is how a fleet convinces itself it has 95% visibility while it
has rephrased one crawler nine different ways.

Policy, unchanged from the platform's rules and enforced here: probes are for
observation only. Nothing in this module fetches, stores or re-publishes a copy of
any work. Candidate domains are surfaced for *checking*, and every finding is a
receipt with a hash and a timestamp, never a media file.
"""
from __future__ import annotations

import datetime as dt
import itertools
import re
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

from .canonical import fold_arabic, fold_latin
from .intel import INTEL as _INTEL, INTEL_STATUS, load as load_intel

# ==========================================================================
# 1. The vocabulary
# ==========================================================================
#: Technical terms the Arabic pirate ecosystem writes in Arabic *script* rather
#: than translating them. This is the single most distinctive feature of the
#: corpus and the one generic Arabic NLP misses entirely: the vocabulary is
#: transliterated English, not translated Arabic.
#:
#: "اتش دي" is HD, "بلوراي" is BluRay, "بوكس اوفيس" is box office. A parser that
#: looks for the Arabic translation of these words finds nothing, because nobody
#: uses it.
#: Loaded from intel. Tuned per market alongside the target set, because the
#: transliterated-technical vocabulary is dialect- and region-specific.
TRANSLIT_TECH: Mapping[str, str] = _INTEL.translit_tech


#: Arabic functional vocabulary, grouped by what the word is doing in the string.
#: Derived from observed page titles and meta blocks, not from a dictionary.
LEXICON: Mapping[str, tuple[str, ...]] = _INTEL.lexicon


#: Arabic-script words that mean a thing exists on a *surface* rather than a
#: work, and are therefore discovery anchors rather than noise.
SURFACE_HINTS: Mapping[str, str] = _INTEL.surface_hints


def arabic_technical_terms(text: str) -> set[str]:
    """Map transliterated-English technical terms written in Arabic script to
    their Latin canonical form. The inverse of what :mod:`qarin.canonical` does
    for titles, and it is what makes the quality/format grammar readable."""
    f = fold_arabic(text)
    out: set[str] = set()
    for ar, latn in TRANSLIT_TECH.items():
        if fold_arabic(ar) in f:
            out.add(latn)
    return out


# ==========================================================================
# 2. Brands, lineage, and the rotation grammar
# ==========================================================================
@dataclass(frozen=True)
class Brand:
    """A pirate brand, and what it descends from.

    Lineage matters because a takedown does not end a network, it renames it:
    MyCima became WeCima in a matter of days, and the successor marketed itself
    explicitly as "بديل ماي سيما" — *the alternative to MyCima* — and as the
    heir to EgyBest's audience while EgyBest was down. A platform that counts
    brands counts *increases*; a platform that tracks lineage counts one
    operator continuing.
    """

    id: str
    names: tuple[str, ...]                 # every script/spelling in use
    latin: tuple[str, ...]                 # how it appears in domains
    successor_of: tuple[str, ...] = ()     # brands this one absorbed
    observed_tlds: tuple[str, ...] = ()
    first_observed: str | None = None
    peak_monthly_visits: int | None = None  # third-party, dated, never ours
    source: str | None = None
    status: str = "ACTIVE"                  # ACTIVE | TAKEDOWN | ROTATED


#: The target set and the rotation vocabulary. Both are **intel, not
#: method**: a machine-readable list of who is being watched, with their observed
#: TLDs, misspelling rules, combosquat words and subdomain prefixes, is a
#: description of what this platform monitors. Released publicly it is worth more
#: to the operators than to the researchers, because every pattern absent from
#: the list becomes free. Loaded from the gitignored intel file — see
#: :mod:`qarin.intel` for the reasoning and :data:`qarin.intel.INTEL_STATUS` for
#: the labelling rule that keeps an example-set figure from being read as a
#: market measurement.
KNOWN_BRANDS: tuple[Brand, ...] = tuple(
    Brand(id=b.id, names=b.names, latin=b.latin, successor_of=b.successor_of,
          observed_tlds=b.observed_tlds, peak_monthly_visits=b.peak_monthly_visits,
          source=b.source, status=b.status)
    for b in _INTEL.brands
)

#: Confusable glyphs. Generic typosquatting literature, NOT intel: the table says
#: nothing about who is being watched, only that a Cyrillic а and a Latin a are
#: the same character to a user scanning a URL at speed. It stays in the code
#: because publishing it costs an operator nothing, and withholding it would
#: simply break the fold for anyone running the engine on their own target set.
#: The line between method and intel is drawn here, not asserted in a document.
HOMOGLYPHS: dict[str, str] = {
    "0": "o", "1": "l", "3": "e", "5": "s", "7": "t", "@": "a", "$": "s",
    "а": "a", "е": "e", "о": "o", "р": "p",
    "с": "c", "х": "x", "у": "y", "к": "k",
    "і": "i", "һ": "h",
}

ROTATION_TLDS: tuple[str, ...] = _INTEL.rotation_tlds
_ROTATION_RULES: tuple[tuple[str, str], ...] = _INTEL.rotation_rules
COMBO_WORDS: tuple[str, ...] = _INTEL.combo_words
SUBDOMAIN_PREFIXES: tuple[str, ...] = _INTEL.subdomain_prefixes


@dataclass
class BrandRegistry:
    """Brands, their lineage, and the token→brand index used for attribution."""

    brands: dict[str, Brand] = field(default_factory=dict)

    def __init__(self, brands: Iterable[Brand] = KNOWN_BRANDS) -> None:
        self.brands = {}
        for b in brands:
            self.brands[b.id] = b

    def tokens(self) -> dict[str, str]:
        """Every spelling of every brand → brand id. Includes the Arabic forms,
        so a page title in Arabic script is matchable without transliterating
        the brand name first."""
        out: dict[str, str] = {}
        for b in self.brands.values():
            for n in b.names:
                out[n.lower()] = b.id
            for n in b.latin:
                out[n.lower()] = b.id
            out[fold_arabic(b.names[0])] = b.id
        return out

    def successors_of(self, brand_id: str) -> tuple[str, ...]:
        return tuple(b.id for b in self.brands.values()
                     if brand_id in b.successor_of)

    def ancestors_of(self, brand_id: str) -> tuple[str, ...]:
        b = self.brands.get(brand_id)
        return b.successor_of if b else ()


def _stems(brand: "Brand") -> set[str]:
    """Every near-identical spelling of a brand's Latin forms.

    Doubling and substitution from the recorded grammar, plus omission and
    transposition — the two registration typos a user makes while already
    intending to visit the brand, which makes them the cheapest stock there is.
    Shared with :mod:`qarin.rotation` so the enumerator that *validates* the
    grammar and the recogniser that *applies* it can never drift apart: two
    copies of a rule set is how a validation pass starts certifying a grammar
    the production path does not implement.
    """
    out: set[str] = set(brand.latin)
    for stem in list(brand.latin):
        for old, new in _ROTATION_RULES:
            if old in stem:
                out.add(stem.replace(old, new, 1))
        for i in range(len(stem)):
            out.add(stem[:i] + stem[i + 1:])
            if i + 1 < len(stem):
                out.add(stem[:i] + stem[i + 1] + stem[i] + stem[i + 2:])
    return {t for t in out if len(t) >= 4}


def enumerate_rotation_candidates(brand_id: str, reg: BrandRegistry | None = None,
                                  *, max_tlds: int | None = None,
                                  ) -> list[str]:
    """Predict the domain names an operator will hold in reserve.

    This is the anticipatory half of discovery, and it is the direct consequence
    of the MyCima finding: the ``weciima.*`` replacements were registered *before*
    the rebrand, and roughly seventy near-identical domains were in circulation
    around a single network. Rotation stock is bought in bulk and in advance, so
    it is enumerable from the brand alone — and a domain that is registered, in
    the rotation-TLD set, carrying a known brand token, and resolving to nothing
    yet, is a *scheduled* appearance. Watching the WHOIS new-domain feed for this
    set gives notice measured in days before the traffic moves.

    The output is a list of names to observe, not to use: nothing here is fetched,
    and the value is entirely in the registration event.
    """
    reg = reg or BrandRegistry()
    b = reg.brands.get(brand_id)
    if not b:
        return []
    tlds = list(b.observed_tlds) + [t for t in ROTATION_TLDS
                                    if t not in b.observed_tlds]
    if max_tlds:
        tlds = tlds[:max_tlds]
    return sorted(f"{s}.{t}" for s in _stems(b) for t in tlds)


# ==========================================================================
# 3. The probe generator — the expert's method, formalised
# ==========================================================================
#: Surfaces, in the order a fleet should be built. Each is an *independent
#: trapping occasion* only against the others, never against itself: this is the
#: bookkeeping that keeps a coverage figure honest.
SURFACES: tuple[str, ...] = (
    "search_index",     # Google/Bing/Yandex SERPs — one detector, any number of queries
    "site_crawl",       # the enumerated domains themselves
    "seo_farm",         # link/redirect blogs, Blogspot/Tumblr keyword stuffing
    "telegram",         # public channel posts and their view counters
    "iptv_manifest",    # m3u playlists and panel markers
    "torrent_swarm",    # DHT info_hashes
    "app_store",        # APK sideload stores and the official stores
    "ugc",              # YouTube/Facebook/TikTok re-uploads and clips
    "new_domain_feed",  # WHOIS/RMRD registrations matching the rotation grammar
    "paste_site",       # paste.*/telegra.ph drop zones
    # Only public artefacts count here. A closed WhatsApp group is out of reach
    # of every passive method and is a flow problem, not a measurement one; see
    # docs/THESIS.md section 9.1. The surface is declared so a hit on it is
    # recorded as partial coverage rather than as invisibility.
    "messaging",
    # --- added after the 2026-11-04 source pass. Each is independent of the
    # --- search index, which is the only thing that makes it worth anything in
    # --- coverage terms; a new query on an old surface is worth zero.
    "certificate_transparency",  # CT logs: a name appears here before the site
                                 # resolves, and it is the ONLY surface that
                                 # sees subdomain rotation
    "whois_drop",                # expiring names about to change hands: the
                                 # acquisition moment, not its consequence
    "discord",                   # public server directories (DISBOARD) list
                                 # North-African movie hubs by drop cadence,
                                 # subtitle language and Maghreb/Darija focus
    "apk_package",               # Android package ids, which outlive every
                                 # domain, brand and template a network rotates
    "url_shortener",             # this corpus distributes via shorteners, not
                                 # store links: one account ties many
                                 # otherwise-unrelated releases together
    "telegram_hashtag",          # t.me/s/<ch>?q=%23افلام — the public preview
                                 # is hashtag-searchable with no API at all
)

#: Which surfaces a query string can actually reach. A probe is charged to every
#: surface it can see, and independence is computed over that set.
_SURFACE_OF_INDEX = "search_index"


@dataclass(frozen=True)
class Probe:
    """One generated search string, with its provenance and its surface."""

    query: str
    surface: str
    template: str
    script: str                    # ar | latn | mixed
    brand_tokens: tuple[str, ...] = ()
    lexicon_slots: tuple[str, ...] = ()
    #: Whether this probe's result set is expected to be *independent* of the
    #: other probes on its surface. Almost always False for search_index, and
    #: that is the point of the field rather than a footnote.
    independent: bool = False

    def key(self) -> str:
        return f"{self.surface}|{self.template}|{self.query}"


def build_probes(title_ar: str | None, title_en: str | None,
                 *, year: str | None = None,
                 unit: str = "فيلم",
                 brands: Sequence[str] | None = None,
                 include_brand: bool = True,
                 max_per_slot: int = 3,
                 ) -> list[Probe]:
    """Generate the query set the way the supply side advertises.

    Reproduces the documented pattern — *name + year + dubbed/translated +
    quality + competitor brand names* — and mixes Arabic and English in one
    string, because that is how the pages are titled and because a monolingual
    query misses the bidirectional titles entirely (``Sherlock Holmes: A Game of
    Shadows hd`` sitting inside Arabic text is a real observed page title).

    ``include_brand`` is the expert's edge and it is opt-out rather than opt-in:
    adding a famous pirate site name to a title query is what surfaces the SEO
    layer, because the pirate networks bid on each other's names. It also
    pollutes precision, which is why every brand-bearing probe records *which*
    brands it carried — so a hit can be attributed to the brand term or to the
    title, and a false positive on "mycima" alone is not logged as an
    infringement of the work.
    """
    out: list[Probe] = []
    names = [n for n in (title_ar, title_en) if n]
    if not names:
        return out
    # The default brand set comes from the loaded corpus, not from a literal in
    # the signature. A hardcoded default silently degrades to *zero* brand-bearing
    # probes on any other corpus — the function still returns a large probe set,
    # so nothing fails, and the one shape the source describes as the expert's
    # actual contribution simply stops being generated. That is the difference
    # between a default that is convenient and a default that lies.
    if brands is None:
        brands = tuple(b.id for b in _INTEL.brands)
    slots = {k: v[:max_per_slot] for k, v in LEXICON.items()}
    brand_names = []
    reg = BrandRegistry()
    for bid in brands:
        b = reg.brands.get(bid)
        if b:
            brand_names.append((b.id, b.names[0], b.latin[0]))

    for name in names:
        is_ar = bool(re.search(r"[\u0600-\u06FF]", name))
        script = "ar" if is_ar else "latn"
        # The core shape: name + unit + one qualifier from each of a few slots.
        for combo in itertools.product(
                slots["watch"], slots["translated"] if is_ar else slots["quality"],
                slots["free"]):
            parts = [name, unit, combo[0], combo[1]]
            if combo[2]:
                parts.append(combo[2])
            if year:
                parts.append(year)
            q = " ".join(p for p in parts if p)
            out.append(Probe(q, _SURFACE_OF_INDEX, "name+unit+watch+qual+free",
                             script, (), ("watch", "translated", "free")))
        # Quality/format stacking, including the transliterated tech vocabulary.
        for qual in slots["quality"][:3]:
            out.append(Probe(f"{name} {year or ''} {qual}".replace("  ", " ").strip(),
                             _SURFACE_OF_INDEX, "name+year+quality", script, (),
                             ("quality",)))
        # The dub/sub split, which is a *market* signal as much as a search term.
        for mode in ("مدبلج", "مترجم"):
            out.append(Probe(f"{name} {mode} {year or ''} HD".replace("  ", " ").strip(),
                             _SURFACE_OF_INDEX, "name+mode+hd", script, (),
                             ("dubbed",)))
        # Instalment grammar for episodic works.
        for ep in ("الحلقة 1", "الحلقة الاخيرة", "الموسم 1"):
            out.append(Probe(f"{name} {ep}", _SURFACE_OF_INDEX, "name+instalment",
                             script, (), ("unit",)))
        # The brand-stacked shape, which is the expert's actual contribution.
        if include_brand:
            for bid, ar_name, latn_name in brand_names:
                out.append(Probe(f"{name} {year or ''} {ar_name}".replace("  ", " ").strip(),
                                 _SURFACE_OF_INDEX, "name+brand_ar", script,
                                 (bid,), ("brand",)))
                out.append(Probe(f"{name} {latn_name} online free",
                                 _SURFACE_OF_INDEX, "name+brand_latn", "mixed",
                                 (bid,), ("brand",)))
                # Mixed-script, as observed on the real pages.
                out.append(Probe(f"{name} {ar_name} {latn_name} 1080p",
                                 _SURFACE_OF_INDEX, "name+brand_both", "mixed",
                                 (bid,), ("brand", "quality")))
            # The stacked form, which is what the source actually describes:
            # "اسم الفيلم + السنة + مدبلج + HD اون لاين + أسماء مواقع المشاهدة
            # (ماي سيما، شاهد فور يو، عرب سيد)". Plural brands, in one title.
            # It matters beyond fidelity: a page matching on three brands at
            # once is the rotation-stock signature in brand_signal(), so the
            # stacked probe is the one that finds the *pre-registration* layer.
            stack_ar = " ".join(b[1] for b in brand_names[:3])
            stack_latn = " ".join(b[2] for b in brand_names[:3])
            out.append(Probe(
                f"{name} {year or ''} مدبلج HD اون لاين {stack_ar}".replace("  ", " ").strip(),
                _SURFACE_OF_INDEX, "name+year+dubbed+hd+brandstack_ar", "mixed",
                tuple(b[0] for b in brand_names[:3]), ("brand", "dubbed", "quality")))
            out.append(Probe(
                f"{name} {year or ''} dubbed HD {stack_latn}".replace("  ", " ").strip(),
                _SURFACE_OF_INDEX, "name+year+dubbed+hd+brandstack_latn", "mixed",
                tuple(b[0] for b in brand_names[:3]), ("brand", "dubbed", "quality")))
    # De-duplicate on the query string, keeping the first template that made it.
    seen: set[str] = set()
    uniq: list[Probe] = []
    for p in out:
        k = fold_arabic(p.query) + "|" + fold_latin(p.query)
        if k not in seen:
            seen.add(k)
            uniq.append(p)
    return uniq


@dataclass
class QueryPlan:
    """A probe set, accounted for by surface rather than by count."""

    probes: tuple[Probe, ...]
    per_surface: Mapping[str, int]
    #: Distinct surfaces touched. This — not the probe count — is what
    #: :func:`qarin.metrics.supply_coverage` charges as trapping occasions.
    n_surfaces: int
    brand_bearing: int

    def independence_note(self) -> str:
        if self.n_surfaces <= 1:
            return (f"{len(self.probes)} probes on {self.n_surfaces} surface: "
                    "this is ONE detector, however clever the wording. Coverage "
                    "gain is ~zero; recall gain is real but unmeasurable here.")
        return (f"{len(self.probes)} probes across {self.n_surfaces} surfaces; "
                f"independent trapping occasions = {self.n_surfaces}.")

    def to_dict(self) -> dict:
        return {"n_probes": len(self.probes), "per_surface": dict(self.per_surface),
                "n_surfaces": self.n_surfaces, "brand_bearing": self.brand_bearing,
                "note": self.independence_note()}


def plan(probes: Sequence[Probe]) -> QueryPlan:
    per: dict[str, int] = {}
    for p in probes:
        per[p.surface] = per.get(p.surface, 0) + 1
    return QueryPlan(tuple(probes), per, len(per),
                     sum(1 for p in probes if p.brand_tokens))


# ==========================================================================
# 4. Brand co-occurrence as an operator signal
# ==========================================================================
#: How many distinct brands must co-occur in one document's metadata before the
#: co-occurrence is evidence of common control rather than of ordinary SEO.
#:
#: One is not evidence: an Arabic film blog legitimately mentions "mycima" as a
#: comparison, and a review site names several. Two is weak. Three or more brand
#: tokens in *one meta block* is the documented signature of rotation stock —
#: ``eegebest.com`` carried the whole family at once, and no innocent party has
#: any reason to bid on six competitors.
CO_OCCURRENCE_MIN = 3


def brand_signal(text: str, *, reg: BrandRegistry | None = None,
                 minimum: int = CO_OCCURRENCE_MIN) -> tuple[str, ...]:
    """Brands named in one document, for :mod:`qarin.operator` to weigh.

    Returns the brand ids, and the caller is responsible for the IDF: a brand
    token is a *high-prevalence* string across this whole corpus, so it must
    never be decisive on its own no matter how confidently it matches. What is
    informative is the *combination*, and the combination is only visible if the
    individual tokens are reported first and weighted afterwards. That ordering
    is why this returns ids rather than a verdict.
    """
    reg = reg or BrandRegistry()
    f = fold_arabic(text) + " " + fold_latin(text)
    hits: set[str] = set()
    for token, bid in reg.tokens().items():
        t = (fold_arabic(token) if re.search(r"[\u0600-\u06FF]", token)
             else fold_latin(token))
        if t and t in f:
            hits.add(bid)
    return tuple(sorted(hits)) if len(hits) >= 1 else ()


def co_occurrence_verdict(brands: Sequence[str]) -> str:
    """Classify a brand set the way :mod:`qarin.operator` classifies a cluster.

    Three tiers, and the middle one exists so that a weak signal is *recorded*
    without being *asserted* — the same discipline that keeps a shared template
    from becoming an accusation.
    """
    n = len(set(brands))
    if n >= CO_OCCURRENCE_MIN:
        return "ROTATION_STOCK"
    if n == 2:
        return "CORROBORATING"
    if n == 1:
        return "MENTION_ONLY"
    return "NONE"


def lineage_edge(new_id: str, old_id: str, brands: Sequence[str],
                 reg: BrandRegistry | None = None) -> bool:
    """Does this document's brand set support a *succession* claim?

    Succession is the strongest single operator finding available without any
    cooperation from anyone, because it is a documented public event: the
    successor advertises itself as the heir (``بديل ماي سيما``). Detecting it
    turns two apparently unrelated networks into one continuing operation, which
    is the difference between a takedown and an interruption.
    """
    reg = reg or BrandRegistry()
    b = reg.brands.get(new_id)
    if not b or old_id not in b.successor_of:
        return False
    return old_id in set(brands) and new_id in set(brands)
