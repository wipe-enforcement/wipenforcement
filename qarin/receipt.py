"""The receipt: a capture that is born admissible, or it is not evidence.

Every piracy system in this industry collects first and thinks about proof
later. The order is wrong, and it is wrong in a specific way: the facts that
make a capture re-verifiable two years from now — which resolver answered, which
TLS certificate was presented, which user agent was sent, what the exact request
bytes were — are the ones that cannot be reconstructed after the fact. The page
will have moved, the certificate will have rotated, the host will have been
repointed. If the capture did not record them at the moment of capture, no
amount of later care can supply them.

So the receipt is the atomic unit of this whole system, and nothing is published
downstream of it that it does not support.

Three properties, in decreasing order of how often they are got wrong:

**Replayability.** :class:`ReplayRecipe` records the request in enough detail to
re-issue it byte-for-byte: method, URL, header order and values, the resolving
resolver, the observing node's own egress location and ASN. A defence expert
re-runs the recipe and gets the same body hash, or gets a different one and
establishes that the site changed — which is itself a finding, and a useful one,
because "it came back" is the fact the 30-minute standard turns on.

**Two hashes, not one.** ``body_sha256`` pins the exact bytes. Alone it is
useless for detecting a mirror farm, because a mirrored site differs from its
original in one copyright year in a footer, and every hash in the corpus is then
distinct. ``structural_fingerprint`` hashes the *tag skeleton* — the document
order of element names, with text and attributes discarded. Template clones share
a skeleton, so the structural fingerprint is simultaneously an integrity device
and an **operator signal** consumed by :mod:`qarin.operator`. One of these
numbers tells you a page did not change; the other tells you two pages are the
same business.

**Sealed at creation.** :meth:`Receipt.seal` freezes the record into a canonical
JSON form and hashes it, so any later edit — including one by this codebase — is
detectable. The hash is what goes into the ledger; the ledger is what makes the
set of hashes tamper-evident as a whole rather than one at a time.

What a receipt deliberately does *not* contain: the infringing media. Metadata,
headers, hashes and a text extraction only. Storing the work would convert an
evidence instrument into a distribution network, and it would hand the operator's
lawyer the only genuinely good argument they have.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

# --------------------------------------------------------------------------
# structural fingerprint
# --------------------------------------------------------------------------
_TAG_RE = re.compile(r"<\s*(/?)\s*([a-zA-Z][a-zA-Z0-9:-]*)")
_VOID = frozenset({"br", "hr", "img", "input", "meta", "link", "source",
                   "area", "base", "col", "embed", "param", "track", "wbr"})
_SCRIPTISH = re.compile(r"<\s*(script|style)\b.*?<\s*/\s*\1\s*>",
                        re.IGNORECASE | re.DOTALL)
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def tag_skeleton(html: str | None, limit: int = 4000) -> tuple[str, ...]:
    """Element names in document order, with text and attributes discarded.

    Comments and the contents of ``script``/``style`` are stripped first: those
    are exactly the regions where two clones of one template are guaranteed to
    differ (analytics IDs, A/B buckets, injected ad markup), and leaving them in
    would make the fingerprint as unstable as the content hash and therefore
    pointless.
    """
    if not html:
        return ()
    s = _COMMENT.sub(" ", html)
    s = _SCRIPTISH.sub(" ", s)
    out: list[str] = []
    for closing, name in _TAG_RE.findall(s):
        n = name.lower()
        if n in _VOID and not closing:
            continue
        out.append(("/" if closing else "") + n)
        if len(out) >= limit:
            break
    return tuple(out)


def structural_fingerprint(html: str | None) -> str:
    """SHA-256 of the tag skeleton. Stable across cosmetic edits, sensitive to
    template changes."""
    sk = tag_skeleton(html)
    return hashlib.sha256("\u0001".join(sk).encode("utf-8")).hexdigest()


def text_extraction(html: str | None) -> str:
    """Visible text only, collapsed. Stored so a human can review a capture
    without re-fetching it, and so the *words* an operator used remain on the
    record as they were at capture time."""
    if not html:
        return ""
    s = _COMMENT.sub(" ", html)
    s = _SCRIPTISH.sub(" ", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"&[a-z#\d]{2,8};", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# --------------------------------------------------------------------------
# canonical JSON + hashing
# --------------------------------------------------------------------------
def canonical_json(obj: Any) -> bytes:
    """Deterministic UTF-8 JSON. The single most important function here.

    Two serialisations of one logical receipt that differ in key order or
    whitespace produce different hashes, and a hash that cannot be reproduced
    independently is not a seal. Sorted keys, no insignificant space, NaN
    rejected, non-ASCII preserved rather than escaped so the Arabic on the
    record hashes identically on any machine in any locale.
    """
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------
# replay recipe
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class ReplayRecipe:
    """Enough to re-issue the request, and to explain why a replay differs.

    ``header_order`` is preserved rather than sorted because some servers vary
    their response on it, and because a replay that silently reorders headers is
    a replay that can be dismissed. ``egress`` records where the observing node
    itself was — which geos, which ASN — since a CDN edge can serve different
    bodies to different observers, and an unqualified "the page said X" is not a
    reproducible claim in the presence of geo-splitting.
    """

    method: str
    url: str
    headers: tuple[tuple[str, str], ...] = ()
    header_order: tuple[str, ...] = ()
    body: str | None = None
    resolving_resolver: str | None = None
    resolved_ips: tuple[str, ...] = ()
    egress: Mapping[str, str] = field(default_factory=dict)
    tls_peer_cert_sha256: str | None = None
    tls_issuer: str | None = None
    tls_not_after: str | None = None
    tls_san: tuple[str, ...] = ()
    http_version: str | None = None
    redirect_chain: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "method": self.method, "url": self.url,
            "headers": list(self.headers), "header_order": list(self.header_order),
            "body": self.body,
            "resolving_resolver": self.resolving_resolver,
            "resolved_ips": list(self.resolved_ips),
            "egress": dict(self.egress),
            "tls": {"peer_cert_sha256": self.tls_peer_cert_sha256,
                    "issuer": self.tls_issuer, "not_after": self.tls_not_after,
                    "san": list(self.tls_san)},
            "http_version": self.http_version,
            "redirect_chain": list(self.redirect_chain),
        }


def _recipe_from(rec: Mapping) -> ReplayRecipe | None:
    """Rebuild a ReplayRecipe from its serialised form, tolerating missing keys."""
    if not rec:
        return None
    # The serialised form nests TLS fields under "tls" with *unprefixed* keys
    # for readability on the wire, so they have to be re-prefixed here. Passing
    # them through with ** would crash on the first round-trip off disk, which
    # is the only path that matters: a receipt that survives sealing but not
    # reloading is no kind of evidence at all.
    tls = rec.get("tls") or {}
    return ReplayRecipe(
        method=rec.get("method", "GET"), url=rec.get("url", ""),
        headers=tuple(tuple(h) for h in rec.get("headers", ())),
        header_order=tuple(rec.get("header_order", ())),
        body=rec.get("body"),
        resolving_resolver=rec.get("resolving_resolver"),
        resolved_ips=tuple(rec.get("resolved_ips", ())),
        egress=dict(rec.get("egress") or {}),
        tls_peer_cert_sha256=tls.get("peer_cert_sha256"),
        tls_issuer=tls.get("issuer"),
        tls_not_after=tls.get("not_after"),
        tls_san=tuple(tls.get("san", ())),
        http_version=rec.get("http_version"),
        redirect_chain=tuple(rec.get("redirect_chain", ())),
    )


# --------------------------------------------------------------------------
# receipt
# --------------------------------------------------------------------------
#: Grades of the capture itself, independent of what it depicts.
#:  C1  automated, single observer, no external anchor
#:  C2  automated, anchored in a ledger with an external timestamp
#:  C3  C2 plus a second independent observer agreeing on the body hash
#:  C4  C3 plus a notary or bonded expert system attesting the chain
CAPTURE_GRADES = ("C1", "C2", "C3", "C4")


@dataclass(frozen=True)
class Receipt:
    """One observation, sealed. Immutable by construction."""

    subject: str                        # what was observed: a URL, a channel post, a stream
    observed_at: str                    # UTC ISO-8601, from the observing clock
    source: str                         # telegram | web | iptv | torrent | app | ugc
    capture_grade: str = "C1"
    body_sha256: str | None = None
    structural_fp: str | None = None
    excerpt: str | None = None
    status_code: int | None = None
    recipe: ReplayRecipe | None = None
    #: Machine-readable work/instalment attribution, filled by canonical.py.
    work_id: str | None = None
    episode: int | None = None
    season: int | None = None
    #: Free-text provenance of the *observer*: which collector, which version,
    #  which config revision. An unattributable observation cannot be audited.
    observer: str | None = None
    collector_version: str | None = None
    tags: tuple[str, ...] = ()
    note: str | None = None
    #: Set when the capture is known to be incomplete or unverifiable. Downgrade,
    #  never delete: a partial capture is still a fact about that moment.
    caveat: str | None = None
    sealed: str | None = None

    def __post_init__(self) -> None:
        if self.capture_grade not in CAPTURE_GRADES:
            raise ValueError(f"unknown capture grade {self.capture_grade!r}")
        if not self.subject:
            raise ValueError("a receipt with no subject is not a receipt")
        if not self.observed_at:
            raise ValueError("a receipt without a timestamp cannot anchor anything")
        # A recipe can arrive as a plain dict from any deserialised path, and
        # payload() calls .to_dict() on it. Coercing here means every reader of
        # a receipt gets the same object graph regardless of whether it came
        # from a live capture or from disk - and a seal computed over one is
        # reproducible from the other.
        if isinstance(self.recipe, Mapping):
            object.__setattr__(self, "recipe", _recipe_from(self.recipe))

    # -- construction -------------------------------------------------------
    @classmethod
    def from_html(cls, url: str, html: str, *, observed_at: str, source: str = "web",
                  status_code: int | None = None, recipe: ReplayRecipe | None = None,
                  excerpt_limit: int = 400, **kw) -> "Receipt":
        """Capture a page. The body hash and structural fingerprint are computed
        here, at the only moment the bytes still certainly existed."""
        return cls(subject=url, observed_at=observed_at, source=source,
                   body_sha256=sha256_hex(html or ""),
                   structural_fp=structural_fingerprint(html),
                   excerpt=text_extraction(html)[:excerpt_limit] or None,
                   status_code=status_code, recipe=recipe, **kw)

    # -- sealing ------------------------------------------------------------
    def payload(self) -> dict:
        """The hashable content of this receipt, excluding the seal itself."""
        d = {
            "subject": self.subject, "observed_at": self.observed_at,
            "source": self.source, "capture_grade": self.capture_grade,
            "body_sha256": self.body_sha256, "structural_fp": self.structural_fp,
            "excerpt": self.excerpt, "status_code": self.status_code,
            "recipe": self.recipe.to_dict() if self.recipe else None,
            "work_id": self.work_id, "episode": self.episode, "season": self.season,
            "observer": self.observer, "collector_version": self.collector_version,
            "tags": list(self.tags), "note": self.note, "caveat": self.caveat,
        }
        return d

    def seal(self) -> "Receipt":
        """Return a copy carrying the hash of its own canonical payload.

        Returns a new object rather than mutating: the dataclass is frozen, and
        more importantly because a seal computed over a payload that already
        contained a seal would be circular and verify for nothing.
        """
        # Copy from self, never from payload(): payload() renders the recipe as
        # a plain dict, and rebuilding from it would silently replace a
        # ReplayRecipe with a dict at the exact moment the receipt was sealed.
        digest = sha256_hex(canonical_json(self.payload()))
        fields = {k: v for k, v in self.__dict__.items() if k != "sealed"}
        fields["recipe"] = self.recipe
        return Receipt(sealed=digest, **fields)

    @property
    def digest(self) -> str:
        if self.sealed:
            return self.sealed
        return sha256_hex(canonical_json(self.payload()))

    def verifies(self) -> bool:
        """Does the seal still match the content? False means the record was
        edited after sealing — by this code, by storage, or by anyone else."""
        if not self.sealed:
            return False
        return self.sealed == sha256_hex(canonical_json(self.payload()))

    def to_dict(self) -> dict:
        return dict(self.payload(), sealed=self.sealed)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Receipt":
        # __post_init__ coerces a mapping recipe, so the dict can travel through
        # the ordinary field path without a special case here.
        return cls(**{k: v for k, v in d.items()
                      if k in cls.__dataclass_fields__})

    # -- derived facts ------------------------------------------------------
    @property
    def replayable(self) -> bool:
        """Can this be re-verified independently? No recipe, no replay, no matter
        how good the hash looks."""
        return self.recipe is not None and bool(self.recipe.url)

    @property
    def admissible_floor(self) -> str:
        """What this capture can support on its own.

        A capture with no replay recipe cannot support an assertion about what a
        site contained, only about what our collector reported. That distinction
        is the difference between evidence and a log line, and it is enforced
        here rather than left to whoever reads the dashboard.
        """
        if not self.replayable:
            return "LOG_ONLY"
        if self.capture_grade == "C1":
            return "SINGLE_OBSERVER"
        return self.capture_grade


def now_utc() -> str:
    return (dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
            .isoformat().replace("+00:00", "Z"))


def receipts_agree(a: Receipt, b: Receipt) -> bool:
    """Two independent observers saw the same bytes. This is what promotes a
    capture from C2 to C3, and it cannot be asserted by one process alone."""
    return (a.subject == b.subject and a.body_sha256 is not None
            and a.body_sha256 == b.body_sha256)
