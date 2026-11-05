"""Fail-closed local publication for validated collection payloads."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Mapping


class PublishRefused(RuntimeError):
    """The payload is not healthy enough to replace the public snapshot."""


def publish_json(payload: Mapping, target: str | Path, *, require_live: bool = True) -> Path:
    """Atomically publish a JSON payload after checking source health."""
    health = payload.get("health") or {}
    if require_live and health.get("live") is not True:
        raise PublishRefused("source health is not live; public snapshot was not replaced")
    destination = Path(target)
    destination.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    handle, temporary = tempfile.mkstemp(prefix=f".{destination.name}.",
                                         dir=destination.parent, text=True)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    return destination
