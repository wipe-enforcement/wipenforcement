"""Explicit inventory of public source contracts."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PublicSource:
    source_id: str
    kind: str
    endpoint: str
    cadence_minutes: int
    detector_group: str
    contributes_to_coverage: bool
    requires_private_query: bool = False

    def __post_init__(self) -> None:
        if self.kind not in {"rss", "ct"}:
            raise ValueError(f"unsupported source kind: {self.kind}")
        if self.cadence_minutes < 1:
            raise ValueError("cadence_minutes must be positive")
        if not self.source_id or not self.detector_group:
            raise ValueError("source_id and detector_group are required")
        if "password" in self.endpoint.lower() or "token" in self.endpoint.lower():
            raise ValueError("source endpoints cannot contain credentials")


PUBLIC_SOURCES: tuple[PublicSource, ...] = (
    PublicSource("bbc-arabic-rss", "rss", "https://feeds.bbci.co.uk/arabic/rss.xml",
                 30, "legal-context", False),
    PublicSource("certificate-transparency", "ct",
                 "https://crt.sh/?q={private_query}&output=json", 15,
                 "certificate-transparency", True, requires_private_query=True),
)


def public_sources() -> tuple[PublicSource, ...]:
    """Return the immutable public inventory for scheduler discovery."""
    return PUBLIC_SOURCES


def coverage_sources() -> tuple[PublicSource, ...]:
    """Return only sources eligible to support coverage measurement."""
    return tuple(source for source in PUBLIC_SOURCES if source.contributes_to_coverage)
