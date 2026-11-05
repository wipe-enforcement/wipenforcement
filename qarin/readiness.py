"""Launch readiness gate for the Arabic radar ecosystem."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .detectors import DetectorRegistry
from .health import HealthBoard
from .onboarding import OnboardingReport
from .scope import Market


@dataclass(frozen=True)
class ReadinessReport:
    checks: dict[str, bool]
    blockers: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return not self.blockers

    def to_dict(self) -> dict:
        return {"ready": self.ready, "checks": dict(self.checks), "blockers": list(self.blockers)}


def assess(*, markets: Iterable[Market], detectors: DetectorRegistry,
           health: HealthBoard, manifest: OnboardingReport,
           deployment_authorized: bool = False) -> ReadinessReport:
    """Return a fail-closed report; no check is inferred from another check."""
    market_rows = tuple(markets)
    checks = {
        "ten_markets_declared": len(market_rows) >= 10,
        "ten_markets_measured": len(market_rows) >= 10 and all(
            market.status == "MEASURED" for market in market_rows[:10]),
        "independent_detectors": len(detectors.independent_live()) >= 2,
        "source_health_live": health.live,
        "manifest_ready": manifest.ready,
        "deployment_authorized": deployment_authorized,
    }
    return ReadinessReport(checks, tuple(name for name, passed in checks.items() if not passed))
