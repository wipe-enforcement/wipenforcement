"""Rights-aware, live-ready radar records.

Radar cells deliberately keep four things separate: legal availability,
observed unauthorised supply, public counters, and modeled estimates. A missing
counter is represented as ``None`` with a reason, never as zero.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Mapping, Sequence

from .model import Availability, RightsCalendar
from .audience import AudienceRecord


@dataclass(frozen=True)
class RadarCell:
    work_id: str
    territory: str
    observed_on: str
    availability: Availability
    legal_channels: tuple[str, ...]
    pirate_offerings: int
    public_views: int | None = None
    public_views_reason: str = "not collected"
    source_ids: tuple[str, ...] = ()
    calendar_reason: str = ""

    def __post_init__(self) -> None:
        if self.pirate_offerings < 0:
            raise ValueError("pirate_offerings cannot be negative")
        if self.public_views is not None and self.public_views < 0:
            raise ValueError("public_views cannot be negative")
        if self.public_views is not None and self.public_views_reason != "":
            raise ValueError("a measured public view count cannot have a missing-data reason")
        if self.public_views is None and not self.public_views_reason:
            raise ValueError("missing public views require a reason")

    @property
    def legal(self) -> bool:
        return self.availability == Availability.AUTHORISED

    def to_dict(self) -> dict:
        return {
            "work_id": self.work_id,
            "territory": self.territory,
            "observed_on": self.observed_on,
            "availability": self.availability.value,
            "legal_channels": list(self.legal_channels),
            "pirate_offerings": self.pirate_offerings,
            "public_views": self.public_views,
            "public_views_reason": self.public_views_reason,
            "source_ids": list(self.source_ids),
            "calendar_reason": self.calendar_reason,
        }


@dataclass(frozen=True)
class RadarSnapshot:
    generated_at: str
    cells: tuple[RadarCell, ...]
    coverage_label: str
    coverage_reason: str
    legal_audience: tuple[AudienceRecord, ...] = ()

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "coverage": {"label": self.coverage_label, "reason": self.coverage_reason},
            "cells": [cell.to_dict() for cell in self.cells],
            "legal_audience": [record.to_dict() for record in self.legal_audience],
        }


def build_cell(calendar: RightsCalendar, work_id: str, territory: str,
               observed_on: dt.date, pirate_offerings: int, *,
               source_ids: Sequence[str] = (), public_views: int | None = None,
               public_views_reason: str = "not collected") -> RadarCell:
    entry = calendar.classify(work_id, territory, observed_on)
    return RadarCell(
        work_id=work_id, territory=territory, observed_on=observed_on.isoformat(),
        availability=entry.availability, legal_channels=entry.authorised_channels,
        pirate_offerings=pirate_offerings, public_views=public_views,
        public_views_reason=public_views_reason, source_ids=tuple(source_ids),
        calendar_reason=entry.reason,
    )


def snapshot(cells: Sequence[RadarCell], *, generated_at: str,
             coverage_label: str = "UNMEASURED",
             coverage_reason: str = "independent detector overlap has not been collected",
             legal_audience: Sequence[AudienceRecord] = ()) -> RadarSnapshot:
    """Create a publishable snapshot without turning missing coverage into 100%."""
    return RadarSnapshot(generated_at, tuple(cells), coverage_label, coverage_reason,
                         tuple(legal_audience))
