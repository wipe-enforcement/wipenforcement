"""Freshness and failure state for public-source connectors."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceStatus:
    source_id: str
    status: str
    checked_at: str
    rows_seen: int = 0
    error: str | None = None

    def __post_init__(self) -> None:
        if self.status not in ("ok", "error", "stale", "not_configured"):
            raise ValueError(f"unknown source status: {self.status}")
        if self.rows_seen < 0:
            raise ValueError("rows_seen cannot be negative")
        if self.status == "error" and not self.error:
            raise ValueError("error status requires an error reason")

    @property
    def live(self) -> bool:
        return self.status == "ok"

    def to_dict(self) -> dict:
        return {k: v for k, v in {
            "source_id": self.source_id, "status": self.status,
            "checked_at": self.checked_at, "rows_seen": self.rows_seen,
            "error": self.error,
        }.items() if v is not None}


@dataclass(frozen=True)
class HealthBoard:
    checked_at: str
    sources: tuple[SourceStatus, ...]

    @property
    def live(self) -> bool:
        return bool(self.sources) and all(source.live for source in self.sources)

    def to_dict(self) -> dict:
        return {"checked_at": self.checked_at, "live": self.live,
                "sources": [source.to_dict() for source in self.sources]}
