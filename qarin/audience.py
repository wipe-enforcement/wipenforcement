"""Aggregate legal-audience records supplied by verified rights holders.

This layer never accepts viewer identifiers. It stores auditable aggregates so
legal reach can be compared with public unauthorised supply without pretending
that the latter has an equivalent audience counter.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


MIN_COHORT = 30


@dataclass(frozen=True)
class AudienceRecord:
    work_id: str
    territory: str
    channel_id: str
    period_start: str
    period_end: str
    unique_viewers: int
    watch_hours: float
    source: str
    source_grade: str = "A1"
    device_share: Mapping[str, float] = None
    demographic_share: Mapping[str, float] = None
    sponsor_ids: tuple[str, ...] = ()
    affiliate_ids: tuple[str, ...] = ()
    cohort_size: int = MIN_COHORT

    def __post_init__(self) -> None:
        if self.unique_viewers < 0 or self.watch_hours < 0:
            raise ValueError("audience totals cannot be negative")
        if self.cohort_size < MIN_COHORT:
            raise ValueError("cohort is too small to publish safely")
        for label, shares in (("device", self.device_share),
                              ("demographic", self.demographic_share)):
            if shares is None:
                continue
            if any(value < 0 for value in shares.values()):
                raise ValueError(f"{label} shares cannot be negative")
            total = sum(shares.values())
            if abs(total - 1.0) > 0.01:
                raise ValueError(f"{label} shares must total 1.0, got {total:.3f}")
        object.__setattr__(self, "device_share", dict(self.device_share or {}))
        object.__setattr__(self, "demographic_share", dict(self.demographic_share or {}))

    def to_dict(self) -> dict:
        return {
            "work_id": self.work_id, "territory": self.territory,
            "channel_id": self.channel_id, "period": {
                "start": self.period_start, "end": self.period_end},
            "unique_viewers": self.unique_viewers, "watch_hours": self.watch_hours,
            "source": self.source, "source_grade": self.source_grade,
            "device_share": dict(self.device_share),
            "demographic_share": dict(self.demographic_share),
            "sponsor_ids": list(self.sponsor_ids), "affiliate_ids": list(self.affiliate_ids),
            "cohort_size": self.cohort_size,
        }
