"""Network boundaries for public source feeds.

Connectors fetch public metadata only. They do not crawl discovered hosts,
download media, or turn transport failures into zero findings.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .collector import FeedRow


class FeedError(RuntimeError):
    """A public feed could not be fetched or did not match its contract."""


def fetch_ct_rows(url: str, *, observed_at: str, timeout: float = 15.0,
                  opener: Callable[..., Any] = urlopen) -> tuple[FeedRow, ...]:
    """Fetch a crt.sh-style JSON response and return normalised feed rows.

    ``opener`` is injectable so production can use the standard library while
    tests use a deterministic response. The URL is caller-provided because the
    target set is private configuration, not public source code.
    """
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "QARIN-public-feed/0.1"})
    try:
        response = opener(request, timeout=timeout)
        payload = response.read()
    except Exception as exc:
        raise FeedError(f"public feed request failed: {exc}") from exc
    try:
        data = json.loads(payload.decode("utf-8") if isinstance(payload, bytes) else payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FeedError("public feed returned invalid JSON") from exc
    if not isinstance(data, list):
        raise FeedError("public feed response must be a JSON array")
    rows: list[FeedRow] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        value = item.get("name_value")
        if not isinstance(value, str):
            continue
        for name in value.splitlines():
            name = name.strip().lower().rstrip(".")
            if name:
                rows.append(FeedRow(name=name, observed_at=observed_at))
    return tuple(rows)


def fetch_rss_rows(url: str, *, observed_at: str, timeout: float = 15.0,
                   opener: Callable[..., Any] = urlopen) -> tuple[FeedRow, ...]:
    """Fetch public RSS/Atom metadata and return host-only feed rows.

    Only link hostnames are retained. Titles, descriptions, query strings, and
    media URLs are intentionally discarded at the connector boundary.
    """
    request = Request(url, headers={"Accept": "application/rss+xml, application/atom+xml, application/xml", "User-Agent": "QARIN-public-feed/0.1"})
    try:
        response = opener(request, timeout=timeout)
        payload = response.read()
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise FeedError("public feed returned invalid XML") from exc
    except Exception as exc:
        raise FeedError(f"public feed request failed: {exc}") from exc
    rows: list[FeedRow] = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1].lower() != "link":
            continue
        href = (element.attrib.get("href") or element.text or "").strip()
        parsed = urlparse(href)
        host = parsed.hostname
        if parsed.scheme in ("http", "https") and host:
            rows.append(FeedRow(host.lower().rstrip("."), observed_at, "public_feed"))
    return tuple(rows)
