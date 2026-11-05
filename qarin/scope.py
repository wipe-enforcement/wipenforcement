"""Initial market scope for Arabic online-content measurement."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Market:
    code: str
    name: str
    region: str
    status: str = "NOT_CONFIGURED"
    notes: str = ""

    def __post_init__(self) -> None:
        if self.status not in ("NOT_CONFIGURED", "PARTIAL", "MEASURED"):
            raise ValueError(f"unknown market status: {self.status}")

    def to_dict(self) -> dict:
        return {"code": self.code, "name": self.name, "region": self.region,
                "status": self.status, "notes": self.notes}


ARABIC_BASELINE: tuple[Market, ...] = (
    Market("SA", "Saudi Arabia", "gulf"),
    Market("EG", "Egypt", "north_africa"),
    Market("AE", "United Arab Emirates", "gulf"),
    Market("DZ", "Algeria", "north_africa"),
    Market("MA", "Morocco", "north_africa"),
    Market("IQ", "Iraq", "levant"),
    Market("SD", "Sudan", "north_africa"),
    Market("YE", "Yemen", "gulf"),
    Market("JO", "Jordan", "levant"),
    Market("TN", "Tunisia", "north_africa"),
)

OPTIONAL_COMPETITOR = Market(
    "TR", "Türkiye", "middle_east_competitor",
    notes="Optional comparison market; not part of the Arabic baseline.",
)


def scope(include_optional: bool = False) -> tuple[Market, ...]:
    """Return the declared scope without claiming it is fully measured."""
    return ARABIC_BASELINE + ((OPTIONAL_COMPETITOR,) if include_optional else ())
