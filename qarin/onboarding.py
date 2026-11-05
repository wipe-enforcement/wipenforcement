"""Validation for private rightsholder onboarding manifests."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class OnboardingReport:
    errors: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {"ready": self.ready, "errors": list(self.errors), "warnings": list(self.warnings)}


def validate_manifest(manifest: Mapping) -> OnboardingReport:
    """Validate structure without storing or echoing private values."""
    errors: list[str] = []
    warnings: list[str] = []
    works = manifest.get("works", ())
    work_ids = [item.get("id") for item in works if isinstance(item, Mapping)]
    if len(work_ids) != len(set(work_ids)):
        errors.append("works must have unique ids")
    if any(not item.get("titles") for item in works if isinstance(item, Mapping)):
        errors.append("every work needs at least one title")
    for item in manifest.get("rights", ()):
        if not item.get("source"):
            errors.append("every right needs a provenance source")
    for item in manifest.get("channels", ()):
        if item.get("status") == "VERIFIED" and not item.get("source"):
            errors.append("verified channels need a provenance source")
        if item.get("status") == "CANDIDATE":
            warnings.append("candidate channel excluded from legal denominator")
    for item in manifest.get("observations", ()):
        if item.get("work_id") not in work_ids:
            errors.append("observation references an unknown work")
        if not item.get("source_ids"):
            errors.append("observation needs at least one source id")
    forbidden = {"user_id", "viewer_id", "email", "phone", "ip_address"}

    def scan(value: object, path: str = "manifest") -> None:
        if isinstance(value, Mapping):
            for key, nested in value.items():
                if str(key).lower() in forbidden:
                    errors.append(f"privacy field forbidden at {path}.{key}")
                scan(nested, f"{path}.{key}")
        elif isinstance(value, (list, tuple)):
            for index, nested in enumerate(value):
                scan(nested, f"{path}[{index}]")

    scan(manifest)
    return OnboardingReport(tuple(dict.fromkeys(errors)), tuple(dict.fromkeys(warnings)))
