"""Intel loading: the target data lives outside the repository.

The measurement engine is public on purpose — the arithmetic, the refusals, the
evidence discipline. Publishing them costs nothing, because they are the
*standards*, and a competitor copying them would be copying a commitment to being
auditable.

The **intel** is different in kind, not in degree. A machine-readable list of
target brands, the TLD set they were observed buying, the misspelling rules, the
combosquat words, the subdomain prefixes, the route signatures — that is a
description of what this platform monitors. Released publicly, it is worth more
to the operators than to the researchers: it tells them exactly which patterns are
watched, and every pattern not on the list becomes free.

So the intel is loaded from `intel/arabic-intel.json`, which is **gitignored**.
The repository ships `intel/arabic-intel.example.json`, a redacted stub with the
same shape, so the code runs and the tests pass on a fresh clone without carrying
any target data. `INTEL_STATUS` says which file was read, and every consumer that
reports a figure has to surface it, because "measured against 20 brands" and
"measured against the 3-brand public example" are not the same claim and the
reader cannot tell them apart from the numbers alone.

There is a second benefit that was not the reason for doing it: the intel is now
data, not code. Per-market and per-client target sets become a file swap rather
than a fork, which is what a commercial platform needs anyway.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

#: Where to look, in order. The example file is the last resort and is always
#: present in a fresh clone, so the package never fails to import.
_INTEL_FILES = (
    Path("intel/arabic-intel.json"),                  # real, gitignored
    Path(__file__).resolve().parent.parent / "intel" / "arabic-intel.json",
    Path(__file__).resolve().parent.parent / "intel" / "arabic-intel.example.json",
)


@dataclass(frozen=True)
class IntelBrand:
    id: str
    names: tuple[str, ...]
    latin: tuple[str, ...]
    successor_of: tuple[str, ...] = ()
    observed_tlds: tuple[str, ...] = ()
    peak_monthly_visits: int | None = None
    source: str | None = None
    status: str = "ACTIVE"


@dataclass
class Intel:
    """The target set, and an honest label saying which one is loaded."""

    origin: str                      # "private" | "example"
    path: str | None = None
    brands: list[IntelBrand] = field(default_factory=list)
    rotation_tlds: tuple[str, ...] = ()
    rotation_rules: tuple[tuple[str, str], ...] = ()
    combo_words: tuple[str, ...] = ()
    subdomain_prefixes: tuple[str, ...] = ()
    routes: tuple[tuple[str, str, str], ...] = ()
    translit_tech: dict[str, str] = field(default_factory=dict)
    lexicon: dict[str, tuple[str, ...]] = field(default_factory=dict)
    surface_hints: dict[str, str] = field(default_factory=dict)
    apk_platforms: dict[str, str] = field(default_factory=dict)

    @property
    def is_private(self) -> bool:
        return self.origin == "private"

    def label(self) -> str:
        if self.is_private:
            return f"private intel ({len(self.brands)} brands)"
        return (f"EXAMPLE intel ({len(self.brands)} brands) — no real targets; "
                "figures derived from this set are not market measurements")


def _tuples(raw) -> tuple:
    return tuple(tuple(x) if isinstance(x, list) else x for x in raw)


def load(force_example: bool = False) -> Intel:
    """Read the first available intel file. Never invent a substitute.

    ``force_example`` exists for the test suite: tests must run against the
    public stub so a passing suite never depends on data that is not in the
    repository. A test that only passes on a machine holding the private file is
    testing the machine.
    """
    candidates = list(_INTEL_FILES)
    if force_example:
        candidates = [candidates[-1]]
    for p in candidates:
        if not p.exists():
            continue
        raw = json.loads(p.read_text("utf-8"))
        origin = "example" if "example" in p.name else "private"
        return Intel(
            origin=origin, path=str(p),
            brands=[IntelBrand(**{
                      k: (tuple(v) if isinstance(v, list) else v)
                      for k, v in b.items()})
                    for b in raw.get("brands", [])],
            rotation_tlds=tuple(raw.get("rotation_tlds", ())),
            rotation_rules=_tuples(raw.get("rotation_rules", ())),
            combo_words=tuple(raw.get("combo_words", ())),
            subdomain_prefixes=tuple(raw.get("subdomain_prefixes", ())),
            routes=_tuples(raw.get("routes", ())),
            translit_tech=dict(raw.get("translit_tech", {})),
            lexicon={k: tuple(v) for k, v in raw.get("lexicon", {}).items()},
            surface_hints=dict(raw.get("surface_hints", {})),
            apk_platforms=dict(raw.get("apk_platforms", {})),
        )
    # No file at all. Return an empty private-shaped Intel rather than raising:
    # the package must import, and every consumer reports the empty set as
    # "no intel loaded" instead of producing a zero that looks like a measurement.
    return Intel(origin="none")


INTEL = load()

#: The label every report has to carry. Exported as a constant so it cannot be
#: forgotten at a call site, and so a grep for it finds every consumer.
INTEL_STATUS = INTEL.label()
