"""The ledger: an append-only Merkle chain, and why a hash chain is not enough.

A sealed receipt proves one thing did not change. It does not prove that
something was *omitted* — and omission is the attack that matters here, because
a collector with a grudge, a compromised runner, or a future maintainer pruning
an inconvenient day of data can delete whole captures and leave every remaining
seal perfectly valid.

The chain closes that gap. Each entry commits to its predecessor, so removing
entry *k* breaks the link between *k-1* and *k+1* and is detectable by walking
the chain. The daily Merkle root then commits to the whole day's set at once,
which is what makes it cheap to anchor: one 32-byte hash per day goes to an
external time authority, and that single anchor proves the existence of every
capture beneath it.

Anchoring is the part this module can simulate but not perform. The chain is
self-consistent without an anchor and that is not sufficient — a private chain
can be rewritten wholesale by anyone holding the whole store. The anchor is what
puts the day's root beyond the reach of the parties to a dispute, and the
:func:`anchor_payload` output is exactly what gets submitted to RFC 3161,
OpenTimestamps (Bitcoin), or a notary. Until a day is anchored its captures are
grade C1/C2 and are labelled as such downstream; the ledger refuses to imply a
protection it does not have.

Storage is deliberately a plain JSONL file. A chain that needs a database to be
verified is a chain that cannot be audited after the systems that hosted it have
been decommissioned — and "after" here means years, which is the actual timescale
of litigation.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, Sequence

from .receipt import Receipt, canonical_json, sha256_hex

GENESIS = "0" * 64
_LEAF = b"\x00"
_NODE = b"\x01"


def _pair(a: str, b: str) -> str:
    """Domain-separated concatenation.

    The ``\\x00``/``\\x01`` prefixes stop the second-preimage trick where a
    leaf's own content is parsed as an internal node. It costs nothing and it is
    the difference between a Merkle tree and a hash of concatenated strings that
    someone can forge with a lucky collision structure.
    """
    return hashlib.sha256(_NODE + bytes.fromhex(a) + bytes.fromhex(b)).hexdigest()


def merkle_root(leaves: Sequence[str]) -> str | None:
    """Set-committing root over hex digests.

    Leaves are sorted first, and that is a deliberate departure from the
    textbook indexed Merkle tree. This root commits to *which captures existed
    on a day*, which is the fact an external anchor has to prove; it does not
    commit to the order in which the collector happened to write them down.
    Without the sort, re-exporting one day's records in a different sequence
    yields a different root, and an anchor that moves whenever the export is
    regenerated proves nothing durable.

    Duplicates are kept rather than collapsed: two captures of one URL in one
    second are two observations, and a root that deduplicated them would
    silently under-report how many times we looked.

    Odd levels promote the last node unpaired, the standard construction that
    keeps a leaf from being interpretable as an internal node.
    """
    if not leaves:
        return None
    level = [hashlib.sha256(_LEAF + bytes.fromhex(l)).hexdigest()
             for l in sorted(leaves)]
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            if i + 1 < len(level):
                nxt.append(_pair(level[i], level[i + 1]))
            else:
                nxt.append(level[i])
        level = nxt
    return level[0]


@dataclass(frozen=True)
class Entry:
    """One line of the chain."""

    seq: int
    day: str                    # YYYY-MM-DD, UTC
    digest: str                 # the capture's own seal
    prev: str
    entry_hash: str
    subject: str
    observed_at: str
    kind: str = "receipt"       # receipt | notice | outcome | anchor
    ref: str | None = None      # external anchor id, or the receipt's work id

    def to_line(self) -> str:
        return json.dumps(
            {"seq": self.seq, "day": self.day, "digest": self.digest,
             "prev": self.prev, "entry_hash": self.entry_hash,
             "subject": self.subject, "observed_at": self.observed_at,
             "kind": self.kind, "ref": self.ref},
            sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def from_line(cls, line: str) -> "Entry":
        d = json.loads(line)
        return cls(**d)


class LedgerError(Exception):
    """The chain does not verify. Never recover from this silently."""


@dataclass
class Ledger:
    """Append-only chain over receipts, grouped into anchorable days."""

    path: Path | None = None
    _entries: list[Entry] = field(default_factory=list)

    # -- construction -------------------------------------------------------
    @classmethod
    def open(cls, path: str | Path) -> "Ledger":
        p = Path(path)
        lg = cls(path=p)
        if p.exists():
            for i, line in enumerate(p.read_text("utf-8").splitlines()):
                if not line.strip():
                    continue
                e = Entry.from_line(line)
                if e.seq != i:
                    raise LedgerError(
                        f"sequence break at line {i}: entry claims seq {e.seq}. "
                        "A gap here means lines were removed from the file.")
                lg._entries.append(e)
        return lg

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def head(self) -> str:
        return self._entries[-1].entry_hash if self._entries else GENESIS

    # -- appending ----------------------------------------------------------
    def append(self, receipt: Receipt, *, kind: str = "receipt",
               ref: str | None = None) -> Entry:
        """Append a sealed receipt. Appending an unsealed one seals it here so
        the chain never contains a digest nobody can reproduce."""
        if not receipt.sealed:
            receipt = receipt.seal()
        seq = len(self._entries)
        day = receipt.observed_at[:10]
        prev = self.head
        payload = canonical_json({"seq": seq, "day": day, "digest": receipt.digest,
                                  "prev": prev, "subject": receipt.subject,
                                  "observed_at": receipt.observed_at,
                                  "kind": kind, "ref": ref})
        e = Entry(seq=seq, day=day, digest=receipt.digest, prev=prev,
                  entry_hash=sha256_hex(payload), subject=receipt.subject,
                  observed_at=receipt.observed_at, kind=kind, ref=ref)
        self._entries.append(e)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(e.to_line() + "\n")
        return e

    # -- verification -------------------------------------------------------
    def verify(self) -> tuple[bool, str]:
        """Walk the chain. Returns (ok, explanation).

        Checks three separate things, because they fail for different reasons
        and an operator needs to know which one broke: sequence continuity
        (deletion), prev-linkage (rewriting), and entry-hash consistency
        (in-content editing).
        """
        if not self._entries:
            return True, "empty ledger"
        prev = GENESIS
        for i, e in enumerate(self._entries):
            if e.seq != i:
                return False, f"sequence break at index {i}: entry claims seq {e.seq}"
            if e.prev != prev:
                return False, (f"broken chain at seq {i}: prev is {e.prev[:12]}…, "
                               f"expected {prev[:12]}… — an entry was rewritten "
                               "or removed")
            expect = canonical_json({"seq": e.seq, "day": e.day, "digest": e.digest,
                                     "prev": e.prev, "subject": e.subject,
                                     "observed_at": e.observed_at, "kind": e.kind,
                                     "ref": e.ref})
            if sha256_hex(expect) != e.entry_hash:
                return False, f"content hash mismatch at seq {i}: the entry was edited"
            prev = e.entry_hash
        return True, f"{len(self._entries)} entries verify"

    # -- days and anchors ---------------------------------------------------
    def days(self) -> dict[str, list[Entry]]:
        out: dict[str, list[Entry]] = {}
        for e in self._entries:
            out.setdefault(e.day, []).append(e)
        return out

    def day_root(self, day: str) -> str | None:
        """Merkle root of one day's capture digests — the thing to anchor."""
        return merkle_root([e.digest for e in self._days().get(day, [])
                            if e.kind == "receipt"])

    def _days(self) -> dict[str, list[Entry]]:
        return self.days()

    def roots(self) -> dict[str, str | None]:
        d = self.days()
        return {day: merkle_root([e.digest for e in es if e.kind == "receipt"])
                for day, es in sorted(d.items())}

    def anchor_payload(self, day: str, *, ledger_label: str = "qarin") -> dict:
        """The exact object to submit to a time authority.

        ``nonce`` binds the request to this ledger, so an anchor that comes back
        cannot be reinterpreted as proof of some other party's chain. This is
        the detail that gets skipped and then costs someone a hearing.
        """
        root = self.day_root(day)
        if root is None:
            raise LedgerError(f"no receipts on {day}")
        return {
            "label": ledger_label, "day": day, "root": root,
            "nonce": sha256_hex(canonical_json(
                {"label": ledger_label, "day": day, "root": root,
                 "head": self.head}))[:32],
            "n_receipts": sum(1 for e in self.days().get(day, [])
                              if e.kind == "receipt"),
            "hash_algorithm": "sha256",
            "structure": "merkle over per-receipt seals, domain-separated leaves",
        }

    def record_anchor(self, day: str, anchor_id: str, *,
                      authority: str = "opentimestamps") -> Entry:
        """Write the anchor reference back into the chain.

        The anchor id itself goes in as a ``kind="anchor"`` entry so that the
        external proof becomes part of the internal history: a reader of the
        ledger alone can see which days are covered and which are not.
        """
        seq = len(self._entries)
        prev = self.head
        payload = canonical_json({"seq": seq, "day": day, "digest": "anchor",
                                  "prev": prev, "subject": f"anchor:{day}",
                                  "observed_at": dt.datetime.now(dt.timezone.utc)
                                  .replace(microsecond=0).isoformat()
                                  .replace("+00:00", "Z"),
                                  "kind": "anchor", "ref": f"{authority}:{anchor_id}"})
        e = Entry(seq=seq, day=day, digest="anchor", prev=prev,
                  entry_hash=sha256_hex(payload), subject=f"anchor:{day}",
                  observed_at=payload_obj(payload)["observed_at"],
                  kind="anchor", ref=f"{authority}:{anchor_id}")
        self._entries.append(e)
        if self.path is not None:
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(e.to_line() + "\n")
        return e

    def anchored_days(self) -> set[str]:
        return {e.day for e in self._entries if e.kind == "anchor"}

    def unanchored_days(self) -> list[str]:
        """Days whose root exists only inside this file.

        Reported rather than hidden, because it is the difference between
        evidence and a database. A day here can be wholesale-rewritten by anyone
        with the file, and any figure derived from it must carry that caveat.
        """
        anchored = self.anchored_days()
        return sorted(d for d in self.days() if d not in anchored)

    # -- reading ------------------------------------------------------------
    def entries(self, *, day: str | None = None,
                kind: str | None = None) -> Iterator[Entry]:
        for e in self._entries:
            if day is not None and e.day != day:
                continue
            if kind is not None and e.kind != kind:
                continue
            yield e

    def subjects(self) -> set[str]:
        return {e.subject for e in self._entries if e.kind == "receipt"}

    def coverage_grade(self, day: str) -> str:
        """C2 once the day's root is computed, C3-capable once anchored.

        Kept as a method on the ledger rather than as a constant on the receipt
        because the grade is a property of the *day*, not of the capture: one
        anchored day lifts every receipt inside it, and one unanchored day
        caps every receipt inside it.
        """
        if day in self.anchored_days():
            return "C2"
        return "C1"


def payload_obj(raw: bytes) -> dict:
    return json.loads(raw.decode("utf-8"))
