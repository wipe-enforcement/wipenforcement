"""Declared detector fleet and independence accounting."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .discover import SURFACES


@dataclass(frozen=True)
class Detector:
    detector_id: str
    surface: str
    independence_group: str
    status: str = "PLANNED"
    notes: str = ""

    def __post_init__(self) -> None:
        if self.status not in ("PLANNED", "CONFIGURED", "LIVE", "RETIRED"):
            raise ValueError(f"unknown detector status: {self.status}")


class DetectorRegistry:
    def __init__(self, detectors: Iterable[Detector] = ()) -> None:
        self._detectors: dict[str, Detector] = {}
        for detector in detectors:
            self.add(detector)

    def add(self, detector: Detector) -> None:
        if detector.detector_id in self._detectors:
            raise ValueError(f"duplicate detector id: {detector.detector_id}")
        self._detectors[detector.detector_id] = detector

    def all(self) -> tuple[Detector, ...]:
        return tuple(self._detectors[key] for key in sorted(self._detectors))

    def get(self, detector_id: str) -> Detector | None:
        return self._detectors.get(detector_id)

    def live(self) -> tuple[Detector, ...]:
        return tuple(detector for detector in self.all() if detector.status == "LIVE")

    def independent_live(self) -> tuple[str, ...]:
        groups: dict[str, Detector] = {}
        for detector in self.live():
            groups.setdefault(detector.independence_group, detector)
        return tuple(detector.detector_id for detector in groups.values())

    def to_dict(self) -> dict:
        return {"detectors": [detector.__dict__ for detector in self.all()],
                "live_count": len(self.live()),
                "independent_live_count": len(self.independent_live())}


def declared_fleet() -> DetectorRegistry:
    """Return the complete planned fleet, one detector per declared surface."""
    return DetectorRegistry(
        Detector(surface, surface, surface, "PLANNED") for surface in SURFACES
    )
