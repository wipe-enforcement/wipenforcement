"""Per-market coverage reporting built on independent detector spans."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .metrics import DetectorSpan, supply_coverage
from .detectors import DetectorRegistry


@dataclass(frozen=True)
class MarketCoverage:
    market: str
    coverage_p50: float | None
    coverage_lo: float | None
    coverage_hi: float | None
    detectors: int
    observed_offerings: int
    status: str
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.status not in ("MEASURED", "INSUFFICIENT_EVIDENCE"):
            raise ValueError(f"unknown coverage status: {self.status}")
        if self.detectors < 0 or self.observed_offerings < 0:
            raise ValueError("coverage counts cannot be negative")

    def to_dict(self) -> dict:
        return {k: v for k, v in {
            "market": self.market, "coverage_p50": self.coverage_p50,
            "coverage_ci": [self.coverage_lo, self.coverage_hi],
            "detectors": self.detectors, "observed_offerings": self.observed_offerings,
            "status": self.status, "reason": self.reason,
        }.items() if v is not None or k in ("coverage_ci", "reason")}


def market_coverage(market: str, spans: Sequence[DetectorSpan]) -> MarketCoverage:
    """Compute one market's supply coverage without crossing market boundaries."""
    result = supply_coverage(spans)
    measured = result.coverage_p50 is not None
    return MarketCoverage(
        market=market, coverage_p50=result.coverage_p50,
        coverage_lo=result.coverage_lo, coverage_hi=result.coverage_hi,
        detectors=result.n_detectors, observed_offerings=result.n_observed,
        status="MEASURED" if measured else "INSUFFICIENT_EVIDENCE",
        reason=None if measured else result.reason,
    )


def coverage_matrix(spans_by_market: Mapping[str, Sequence[DetectorSpan]]) -> tuple[MarketCoverage, ...]:
    """Return deterministic market rows; no market borrows another's denominator."""
    return tuple(market_coverage(market, spans_by_market[market])
                 for market in sorted(spans_by_market))


def registered_market_coverage(market: str, spans: Sequence[DetectorSpan],
                               registry: DetectorRegistry) -> MarketCoverage:
    """Measure only spans belonging to live, non-duplicated detector groups."""
    errors: list[str] = []
    groups: set[str] = set()
    for span in spans:
        detector = registry.get(span.detector)
        if detector is None:
            errors.append(f"detector not registered: {span.detector}")
        elif detector.status != "LIVE":
            errors.append(f"detector not live: {span.detector}")
        elif detector.independence_group in groups:
            errors.append(f"independence group duplicated: {detector.independence_group}")
        else:
            groups.add(detector.independence_group)
    if errors:
        return MarketCoverage(market, None, None, None, len(spans), 0,
                              "INSUFFICIENT_EVIDENCE", "; ".join(errors))
    return market_coverage(market, spans)
