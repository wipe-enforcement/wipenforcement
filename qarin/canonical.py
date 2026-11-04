"""Arabic and Latin entity resolution — including the grammar that matters.

Every system built for this problem treats title matching as a string problem.
It is not. It is a **morphology-plus-catalogue** problem, and the part that
actually breaks production is the instalment reference.

Consider what a single episode of a Ramadan series looks like in the wild:

    مسلسل الراهب الحلقة ١٢ مترجم hd
    Al Raheb - الحلقة الثانية عشر (12) بجودة WEB-DL
    raid.al/raheb/ep-12
    t.me/xyz/9182  "الراهب ح12"

Four observations, one episode, and none of them share a substring with the
others. The digits are Arabic-Indic in one, ASCII in another, spelled out as a
word in a third, and absent from the fourth — where the episode number lives in
the *path*. Getting this wrong does not degrade accuracy gradually; it splits
one episode into four uncounted objects, and then every downstream figure is
wrong by a factor nobody can predict.

So this module does four things in order:

1. **Fold** the script. Diacritics and tatweel removed, alef family unified,
   yāʾ/alef maqsūra unified, tāʾ marbūṭa opened, hamza carriers normalised,
   Arabic-Indic and Extended Arabic-Indic (Persian/Urdu, which appears on
   Iranian-dubbed content) digits mapped to ASCII.
2. **Parse the instalment grammar** — episode, season, part — across Arabic
   lexical forms, ASCII, Arabic-Indic, word numerals, and the abbreviated
   ``ح12`` / ``E12`` / ``S02E12`` shapes.
3. **Extract the pirate's own release metadata**: quality tokens, dubbing vs
   subtitling, and the release group. The group name is not noise; it is an
   *operator signal* consumed by :mod:`qarin.operator`.
4. **Resolve** the residue against a registry of known works, with a stated
   confidence and a stated method, and **refuse** rather than guess. A
   mis-resolution propagates into every number attached to that work and is the
   one error class an evidence platform cannot retire.

Dialectal and orthographic variety is handled by *candidate generation* against
the registry rather than by trying to build a perfect normaliser. The normaliser
is deliberately lossy in exactly one direction: it can merge two different
works, which the registry then has to separate, and it can never split one work
into two — because the second failure silently under-counts and the first one is
visible in a review queue.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

# --------------------------------------------------------------------------
# 1. Script folding
# --------------------------------------------------------------------------
#: Arabic combining marks: fatha, damma, kasra, sukun, shadda, madda, and the
#: Quranic signs. Also tatweel (U+0640), the elongation bar used decoratively in
#: channel names — it carries no phonemic content and must not defeat matching.
_AR_DIAG = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED\u0640]")

#: Alef family -> bare alef. Yeh with hamza -> yeh. Ta marbuta -> ha, which is
#: how it is pronounced in most dialects when not in construct state, and it is
#: what Moroccans and Egyptians both type when they are in a hurry.
_AR_FOLD = str.maketrans({
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي",
    "ئ": "ي", "ؤ": "و", "ة": "ه", "ﻻ": "لا",
})

#: Arabic-Indic (U+0660..) and Extended Arabic-Indic (U+06F0.., Persian/Urdu).
#: The second set arrives with Iranian-dubbed serials, which are a real and
#: growing slice of the MENA catalogue. Written with explicit escapes: an
#: earlier revision of this table silently omitted two digits, so "3" and "7"
#: survived the fold as foreign characters and split every episode reference
#: containing them. A digit table is asserted to be total by the test suite.
_DIG_AR = str.maketrans("٠١٢٣٤٥٦٧٨٩",
                        "0123456789")
_DIG_URDU = str.maketrans("۰۱۲۳۴۵۶۷۸۹",
                          "0123456789")

#: Punctuation that separates tokens in every observed corpus. Kept as a class
#: rather than a whitelist so Latin and Arabic punctuation fold identically.
#: Every metacharacter is escaped explicitly: an unescaped bracket inside a
#: character class is a SyntaxWarning today and a silently mis-folded pattern
#: tomorrow, and the second failure is invisible until the numbers are wrong.
_AR_PUNCT = re.compile(
    r"[،؛؟‌‍؞ۿ]"
    r"|[.,;:!?'\"`´‘’“”′″]"
    r"|[\[\](){}<>|/@#$%^&*_+=~\-–—]"
)

_WS = re.compile(r"\s+")
_SEP = re.compile(r"[-_.\s]+")


def fold_arabic(s: str | None) -> str:
    """Canonicalise Arabic text for matching. Lossy by design; see module note."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = _AR_DIAG.sub("", s)
    s = s.translate(_AR_FOLD).translate(_DIG_AR).translate(_DIG_URDU)
    s = s.lower()
    s = _AR_PUNCT.sub(" ", s)
    return _WS.sub(" ", s).strip()


def fold_latin(s: str | None) -> str:
    """Canonicalise Latin text, and fold the transliteration variants that
    Arabic titles acquire on the way out of the script.

    ``الراهب`` -> ``al-raheb`` / ``el raheb`` / ``alraheb`` / ``raid``. The
    vowels a speaker of Arabic does not write are the ones a transliterator
    cannot agree on, so the fold removes them and the article, and keeps a
    consonantal skeleton. This is deliberately aggressive; it is only ever used
    as one *candidate key* among several, never as the sole basis for a match.
    """
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = _WS.sub(" ", s).strip()
    return s


_ARTICLES = ("al ", "el ", "al-", "el-", "es ", "ze ", "the ", "a ", "an ")
_LAT_VOWELS = "aeiou"


def latin_root(s: str) -> str:
    """Consonantal skeleton of a Latin-script title, article stripped."""
    f = fold_latin(s)
    for a in _ARTICLES:
        if f.startswith(a):
            f = f[len(a):].strip()
            break
    # A glued article ("alraheb", "elraheb") carries no space, so the loop above
    # misses it and the root comes out as "lrhb" instead of "rhb" — splitting one
    # title into two keys. Strip it only when a consonant follows, so that a
    # word genuinely beginning in "al" keeps its leading alef.
    for a in ("al", "el"):
        if f.startswith(a) and len(f) > 4 and f[2] not in _LAT_VOWELS:
            f = f[2:]
            break
    words = []
    for w in f.split():
        w = "".join(c for c in w if c not in _LAT_VOWELS) or w
        words.append(w)
    return " ".join(words)


def arabic_root_key(s: str) -> str:
    """Remove the definite article from a folded Arabic string.

    ``الراهب`` folds to ``الراهب``; the registry may hold ``راهب``. Dropping a
    leading ``ال`` as a *separate candidate* (never as the only form) is what
    reconciles the two without risking a collision on words that genuinely
    begin with alef-lam.
    """
    f = fold_arabic(s)
    return [f, f[2:].strip() if f.startswith("ال") and len(f) > 4 else f]


def name_keys(name: str) -> set[str]:
    """All candidate registry keys a single observed name could be aiming at."""
    out: set[str] = set()
    fa = fold_arabic(name)
    if fa:
        out.add("ar:" + fa)
        for alt in arabic_root_key(name):
            if alt:
                out.add("ar:" + alt)
    fl = fold_latin(name)
    if fl:
        out.add("latn:" + fl)
        lr = latin_root(name)
        if lr:
            out.add("root:" + lr)
            out.add("root:" + lr.replace(" ", ""))
    return {k for k in out if len(k) > 3}


# --------------------------------------------------------------------------
# 2. Instalment grammar
# --------------------------------------------------------------------------
#: Words that mean "episode", in the forms actually typed. ``ح`` alone is the
#: ultra-abbreviated form used by channel filenames and Telegram captions; it is
#: included because omitting it loses more volume than anything else here.
_EP_WORDS = (
    "الحلقه", "الحلقة", "حلقه", "حلقه رقم", "الحلقات", "حلقات", "ح",
    "episode", "episodes", "ep", "eps", "e", "part", "pto", "جزء", "الجزء",
    "الحلقة رقم", "ss", "quism", "قسما",
)
_SEASON_WORDS = ("الموسم", "موسم", "season", "series", "s", "ستيسن", "السيزون",
                 "سيزون", "ج", "الجزء")

#: Arabic word numerals, through the teens and the tens. Ramadan series run to
#: 30, so the twenties and thirties are not pedantry — ``الحلقة ثلاثين`` is a
#: real string on a real finale.
_AR_ONES = {
    "واحد": 1, "واحدة": 1, "اتنين": 2, "اثنين": 2, "ثنتين": 2, "تلاته": 3,
    "ثلاثة": 3, "اربعه": 4, "أربعة": 4, "خمسه": 5, "خمسة": 5, "سته": 6,
    "ستة": 6, "سبعه": 7, "سبعة": 7, "تمانيه": 8, "ثمانية": 8, "تسعه": 9,
    "تسعة": 9, "عشره": 10, "عشرة": 10,
}
#: Ordinal forms. In written Arabic these are MORE common than digits for the
#: instalment captions a rightsholder's legal team will actually read: the
#: twelfth episode is normally announced as "الحلقة الثانية عشر", not "12".
#: Missing them does not degrade accuracy gradually — it splits the corpus into
#: a digit-parsed half and an unparseable half.
_AR_ORD = {
    "الاولي": 1, "الثانيه": 2, "الثالثه": 3, "الرابعه": 4, "الخامسه": 5,
    "السادسه": 6, "السابعه": 7, "الثامنه": 8, "التاسعه": 9, "العاشره": 10,
    "الحاديه عشر": 11, "الثانيه عشر": 12, "الثالثه عشر": 13, "الرابعه عشر": 14,
    "الخامسه عشر": 15, "السادسه عشر": 16, "السابعه عشر": 17, "الثامنه عشر": 18,
    "التاسعه عشر": 19, "العشرين": 20, "الواحده والعشرين": 21,
    "الثانيه والعشرين": 22, "الثالثه والعشرين": 23, "الرابعه والعشرين": 24,
    "الخامسه والعشرين": 25, "السادسه والعشرين": 26, "السابعه والعشرين": 27,
    "الثامنه والعشرين": 28, "التاسعه والعشرين": 29, "الثلاثين": 30,
    "تلته عشر": 13, "اربعطعش": 14, "خمسطعش": 15, "ستطعش": 16, "سبعطعش": 17,
    "تمنتعش": 18, "تسعطعش": 19, "عشري": 20,
}

_AR_TEENS = {
    "احدا عشر": 11, "احد عشر": 11, "اتنا عشر": 12, "اثنى عشر": 12,
    "تلتاشر": 13, "تلطاشر": 13, "اربعطاشر": 14, "خمستاشر": 15,
    "ستطاشر": 16, "سبعتاشر": 17, "تمانتاشر": 18, "تسعتاشر": 19,
    "عشرين": 20, "واحد وعشرين": 21, "اتنين وعشرين": 22, "تلاتة وعشرين": 23,
    "اربعه وعشرين": 24, "خمسة وعشرين": 25, "سته وعشرين": 26,
    "سبعة وعشرين": 27, "تمانية وعشرين": 28, "تسعة وعشرين": 29, "تلاتين": 30,
    "ثلاتين": 30, "ثلاثين": 30,
}

_NUM = r"(\d{1,3}|[\u0660-\u0669]{1,3}|[\u06F0-\u06F9]{1,3})"
_EP_ALT = "|".join(sorted({re.escape(w) for w in _EP_WORDS}, key=len, reverse=True))
_SE_ALT = "|".join(sorted({re.escape(w) for w in _SEASON_WORDS}, key=len, reverse=True))
_WORDNUM_ALT = "|".join(sorted(
    {re.escape(k) for k in list(_AR_ONES) + list(_AR_TEENS) + list(_AR_ORD)},
    key=len, reverse=True))

_RE_EP_NUM = re.compile(rf"(?:{_EP_ALT})[\s._\-]*(?:رقم|no\.?|نمبر)?[\s._\-]*{_NUM}",
                        re.IGNORECASE)
_RE_EP_DASH = re.compile(rf"[-_\s](?:{_EP_ALT})?\s?{_NUM}\b", re.IGNORECASE)
_RE_SE = re.compile(rf"(?:{_SE_ALT})[\s._\-]*{_NUM}", re.IGNORECASE)
_RE_SXXEXX = re.compile(r"\bs\s?(\d{1,2})\s?e\s?(\d{1,3})", re.IGNORECASE)
_RE_WORD_EP = re.compile(rf"(?:الحلقه|الحلقة|حلقة)\s+({_WORDNUM_ALT})", re.IGNORECASE)


@dataclass(frozen=True)
class EpisodeRef:
    """A resolved instalment. ``None`` means not stated — never zero.

    Episode 0 does not exist in any Arabic drama, so a parse failure that
    returns ``0`` is indistinguishable from a genuine first instalment in every
    downstream grouping. ``None`` is the only honest absence.
    """

    season: int | None = None
    episode: int | None = None
    part: int | None = None
    raw: str | None = None
    #: How the reference was found, for the audit trail: "ar-word", "digits",
    #: "SxxExx", "path", None.
    method: str | None = None

    @property
    def known(self) -> bool:
        return self.episode is not None or self.season is not None

    def label(self) -> str:
        bits = []
        if self.season is not None:
            bits.append(f"S{self.season:02d}")
        if self.episode is not None:
            bits.append(f"E{self.episode:02d}")
        if self.part is not None:
            bits.append(f"pt{self.part}")
        return " ".join(bits) or "—"

    def key(self) -> str:
        return f"{self.season or '-'}:{self.episode or '-'}:{self.part or '-'}"


def _to_int(tok: str) -> int | None:
    t = tok.translate(_DIG_AR).translate(_DIG_URDU)
    return int(t) if t.isdigit() else None


def parse_instalment(text: str) -> EpisodeRef:
    """Extract season/episode/part from free text, URL paths included.

    Order matters and is tuned to observed precision, not to elegance: an
    explicit ``S01E12`` or a written Arabic word numeral beats a bare digit,
    which beats a trailing ``- 12`` that could equally be a year or a quality
    code. The first pattern to fire wins, and the winning pattern is recorded.
    """
    if not text:
        return EpisodeRef()
    folded = text.translate(_DIG_AR).translate(_DIG_URDU)

    m = _RE_SXXEXX.search(folded)
    if m:
        return EpisodeRef(int(m.group(1)), int(m.group(2)), None, m.group(0), "SxxExx")

    m = _RE_WORD_EP.search(fold_arabic(text))
    if m:
        tok = m.group(1)
        n = _AR_ORD.get(tok) or _AR_TEENS.get(tok) or _AR_ONES.get(tok)
        if n is None or n <= 10:
            # A bare ordinal followed by "عشر" (teens) or "وعشرين/عشرون"
            # (twenties) is ONE number, not the ordinal alone: "الثالثه والعشرون"
            # is 23, and reading it as 3 files episode 23 under episode 3 — the
            # worst failure mode available here, because it is a silent
            # mis-attribution to a real instalment rather than a refusal.
            # Longest suffix first. "عشر" is a substring of "العشرين", so
            # testing the short form first reads "الثالثه والعشرون" (23) as
            # "الثالثه عشر" (13) and files episode 23 under episode 13 — a
            # silent mis-attribution to a real instalment, which is the one
            # error in this module that no downstream figure can recover from.
            tail = folded[m.end():m.end() + 16]
            for suffix in (" والعشرين", " والعشرون", " عشر"):
                for cand in (tok + suffix,
                             tok + suffix.replace("العشرون", "العشرين")):
                    compound = _AR_ORD.get(cand)
                    if compound and suffix.strip() in tail:
                        return EpisodeRef(None, compound, None, m.group(0),
                                          "ar-word")
        if n:
            return EpisodeRef(None, n, None, m.group(0), "ar-word")

    m = _RE_EP_NUM.search(folded) or _RE_EP_NUM.search(fold_arabic(text))
    if m:
        n = _to_int(m.group(1))
        if n is not None:
            return EpisodeRef(None, n, None, m.group(0), "digits")

    m = _RE_SE.search(folded)
    if m:
        n = _to_int(m.group(1))
        if n is not None:
            return EpisodeRef(n, None, None, m.group(0), "season")

    m = _RE_EP_DASH.search(folded)
    if m:
        n = _to_int(m.group(1))
        # A bare trailing number is only an episode if it is plausibly one:
        # 1..2000 would otherwise swallow years, resolutions and file sizes.
        if n is not None and 1 <= n <= 300:
            return EpisodeRef(None, n, None, m.group(0), "bare-number")
    return EpisodeRef()


# --------------------------------------------------------------------------
# 3. The pirate's own release metadata
# --------------------------------------------------------------------------
#: Quality tokens, ordered by how much they say about the source. A ``TS`` or
#: ``CAM`` tag means somebody was physically in a cinema with a rig: that is a
#: *supply-chain* fact about a theatrical release, and it is evidence about the
#: exhibition window rather than about the internet.
QUALITY_TOKENS: Mapping[str, str] = {
    "ts": "cinema_cam", "cam": "cinema_cam", "scr": "screener",
    "screener": "screener", "workprint": "screener", "wp": "screener",
    "hdrip": "broadcast_rip", "hdtc": "broadcast_rip", "satrip": "broadcast_rip",
    "web-dl": "platform_extract", "webdl": "platform_extract",
    "webrip": "platform_extract", "dvdrip": "physical", "bdrip": "physical",
    "brrip": "physical", "uhd": "physical", "1080p": "transcode",
    "720p": "transcode", "480p": "transcode", "4k": "transcode",
}

#: Provenance strength, strongest first. Used to rank which observation of the
#: same copy is the most informative about *where it came from*.
PROVENANCE_ORDER = ("platform_extract", "physical", "screener", "broadcast_rip",
                    "cinema_cam", "transcode")

_DUB_RE = re.compile(r"\b(?:مدبلج|مدهبلج|dubbed|dub| dub |مترجم|مترجمه|مترجمة|"
                     r"subbed|sub|subs|english subs|مترجمه انجليزي)\b", re.I)
_AR_DUB = re.compile(r"مدبلج|مدهبلج|dubbed|\bdub\b")
_AR_SUB = re.compile(r"مترجم|مترجمه|مترجمة|\bsub(s)?\b")
_LIVE_RE = re.compile(r"\b(?:بث مباشر|مباشر|لايف|live|streaming|\blive\b|"
                      r"اليوم|الان|الآن|\bnow\b)\b", re.I)
_GROUP_RE = re.compile(r"(?:\|\s*([A-Za-z0-9_.\-]{2,20})\s*\|"
                       r"|[-–—]\s*([A-Z][A-Za-z0-9_.\-]{2,19})\s*$"
                       r"|\bby\s+([A-Za-z0-9_.\-]{2,20})\b)")


@dataclass(frozen=True)
class Offer:
    """One observed unauthorised offering of a work, as the ecosystem stated it.

    The fields are what the pirate *volunteered*. Release groups, quality tags
    and dub/sub choices are not incidental: they are how the trade advertises
    itself to its own customers, and they are the cheapest operator and
    demographic signals available. Nothing here is inferred from the viewer,
    because the viewer cannot be asked.
    """

    text: str
    url: str | None = None
    title_keys: frozenset[str] = frozenset()
    instalment: EpisodeRef = EpisodeRef()
    quality: str | None = None
    provenance: str | None = None
    language_mode: str | None = None      # dubbed | subtitled | original
    live_claim: bool = False
    group: str | None = None
    #: Names that did not resolve to any registered work. Kept, not dropped:
    #: an unresolvable cluster recurring across channels is an unregistered
    #: viral title, and that is a discovery the registry needs.
    unresolved: bool = False

    @property
    def is_live_claim(self) -> bool:
        return self.live_claim


def parse_offering(text: str, url: str | None = None,
                   known_keys: Iterable[str] = ()) -> Offer:
    """Parse one observed caption/filename/link text into a structured offer.

    ``known_keys`` is the flattened registry index (see :class:`Resolver`). The
    title is resolved by longest-match of any candidate key against the folded
    text, which is why the registry has to hold every alias: the ecosystem uses
    whichever one a given community prefers.
    """
    keys = name_keys(text)
    known = set(known_keys)
    matched = keys & known

    # Separator-normalised haystack: the fold collapses "-" and "_" to spaces,
    # so "web-dl" must be compared as "web dl" on both sides or it never hits.
    hay = _SEP.sub(" ", fold_arabic(text) + " " + fold_latin(text) + " " + (text or ""))
    quality = None
    prov = None
    for tok, kind in QUALITY_TOKENS.items():
        t = _SEP.sub(" ", tok)
        if re.search(rf"(?<![a-z]){re.escape(t)}(?![a-z])", hay, re.I):
            quality = tok
            prov = kind
            break

    dubbed = bool(_AR_DUB.search(fold_arabic(text)) or _AR_DUB.search(text))
    subbed = bool(_AR_SUB.search(fold_arabic(text)) or _AR_SUB.search(text))
    lang = ("dubbed" if dubbed else "subtitled" if subbed else None)

    gm = _GROUP_RE.search(text or "")
    group = next((g for g in (gm.groups() if gm else ()) if g), None)

    return Offer(
        text=text, url=url,
        title_keys=frozenset(matched),
        instalment=parse_instalment(text or "") if text else EpisodeRef(),
        quality=quality, provenance=prov, language_mode=lang,
        live_claim=bool(_LIVE_RE.search(text or "")),
        group=group, unresolved=not matched,
    )


# --------------------------------------------------------------------------
# 4. Resolution
# --------------------------------------------------------------------------
@dataclass
class Resolution:
    """The answer to "which work is this?", with its own confidence and method.

    ``ambiguous`` is a first-class outcome rather than a failure. Two works
    whose folded names collide — and in a catalogue of Ramadan serials they
    will — must produce a *queued review*, not a coin flip. Assigning an
    ambiguous match to the more popular of two works is the single most
    efficient way to manufacture a false allegation against the less popular
    one, and it is undetectable after the fact unless it was recorded here.
    """

    work_id: str | None
    confidence: float
    method: str
    candidates: tuple[str, ...] = ()
    ambiguous: bool = False
    note: str | None = None

    @property
    def resolved(self) -> bool:
        return self.work_id is not None and not self.ambiguous


class Resolver:
    """Registry-backed resolution of observed names to works.

    Index construction is the interesting part. Each work contributes every
    alias in every script, plus the article-stripped and consonantal-root forms,
    each tagged with a *specificity* weight = 1 / (number of works sharing that
    key). A key unique to one work resolves at full confidence; a key three
    works share resolves at a third of that and raises ``ambiguous``. This is
    inverse-document frequency applied to the catalogue, and it makes the
    registry's own collisions visible instead of letting them corrupt the
    numbers quietly.
    """

    def __init__(self, works: Sequence = ()) -> None:
        self._works: dict[str, object] = {}
        #: key -> {work_id: specificity}
        self._index: dict[str, dict[str, float]] = {}
        for w in works:
            self.add(w)

    def add(self, work) -> None:
        self._works[work.id] = work
        names: list[str] = list(getattr(work, "all_names", lambda: [])())
        for n in names:
            for k in name_keys(n):
                self._index.setdefault(k, {})[work.id] = 1.0

    # -- construction helpers ----------------------------------------------
    def reindex(self) -> None:
        """Recompute specificity after any registry change.

        Separated from ``add`` on purpose: adding a work can *demote* the
        confidence of an existing key, and doing that silently mid-session
        would make two runs over the same corpus disagree. Call once, after the
        registry is loaded.
        """
        self._index = {}
        for w in self._works.values():
            for n in list(w.all_names()):
                for k in name_keys(n):
                    self._index.setdefault(k, {})[w.id] = 1.0

    @property
    def keys(self) -> set[str]:
        return set(self._index)

    def collisions(self) -> dict[str, list[str]]:
        """Keys claimed by more than one work — the registry's own defects.

        Published, because a reviewer needs to know which matches were decided
        by the catalogue's ambiguity rather than by evidence.
        """
        return {k: sorted(v) for k, v in self._index.items() if len(v) > 1}

    # -- resolution ---------------------------------------------------------
    def resolve(self, text: str) -> Resolution:
        """Resolve one observed string to a work.

        Longest matching key wins, so that a specific alias beats a generic one
        ("الراهب" beats "راهب" if both are registered). Ties across different
        works are reported as ambiguous with every candidate named.
        """
        if not text:
            return Resolution(None, 0.0, "empty", note="no text supplied")
        cand_keys = name_keys(text)
        # Also test every registry key as a substring of the observed text,
        # because the caption carries the instalment grammar around the name.
        hay_ar = fold_arabic(text)
        hay_latn = fold_latin(text)
        hay = hay_ar + " " + hay_latn
        hits: dict[str, tuple[float, int]] = {}
        for k, owners in self._index.items():
            _, _, tail = k.partition(":")
            if k in cand_keys or (len(tail) > 2 and tail in hay):
                spec = 1.0 / len(owners)
                for wid in owners:
                    prev = hits.get(wid)
                    score = spec * (len(tail) / 100.0 + 1.0)
                    if prev is None or score > prev[0]:
                        hits[wid] = (score, len(tail))
        if not hits:
            return Resolution(None, 0.0, "no-match", ambiguous=False,
                              note="no registered alias occurs in this text")
        ranked = sorted(hits.items(), key=lambda kv: (-kv[1][0], kv[0]))
        top_id, (top_score, top_len) = ranked[0]
        tied = [wid for wid, (sc, _) in ranked if abs(sc - top_score) < 1e-9]
        if len(tied) > 1:
            return Resolution(None, round(top_score, 4), "tie",
                              candidates=tuple(sorted(tied)), ambiguous=True,
                              note="multiple works match equally; review required")
        # Confidence is capped by how many works share the winning key: a name
        # three serials share cannot support a confident attribution.
        owners = max((len(v) for k, v in self._index.items()
                      if top_id in v and (k in cand_keys
                                          or k.partition(":")[2] in hay)), default=1)
        conf = round(min(1.0, top_score / max(owners, 1)), 4)
        method = "exact-key" if top_id in cand_keys or any(
            top_id in v and k in cand_keys for k, v in self._index.items()) else "substring"
        return Resolution(top_id, conf, method, candidates=(top_id,),
                          note=f"key length {top_len}, {owners} work(s) share it")

    def resolve_offer(self, offer: Offer) -> Resolution:
        """Resolve a parsed offer, preferring its registry-matched title keys."""
        if offer.title_keys:
            owners: set[str] = set()
            for k in offer.title_keys:
                owners.update(self._index.get(k, {}))
            if len(owners) == 1:
                wid = owners.pop()
                return Resolution(wid, round(1.0 / max(1, len(
                    [1 for v in self._index.values() if wid in v])), 4),
                    "offer-keys", candidates=(wid,))
            if len(owners) > 1:
                return Resolution(None, 0.4, "offer-keys-tie",
                                  candidates=tuple(sorted(owners)), ambiguous=True,
                                  note="offer matched several works")
        return self.resolve(offer.text)
