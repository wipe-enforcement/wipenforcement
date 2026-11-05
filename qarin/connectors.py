"""Network boundaries for public source feeds.

Connectors fetch public metadata only. They do not crawl discovered hosts,
download media, or turn transport failures into zero findings.
"""
from __future__ import annotations

import io
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


#: Hard cap on fetched feed body size. XML bombs expand in memory before any
#: parser limit is reached, so we refuse oversized payloads outright.
_MAX_FEED_BYTES = 2 * 1024 * 1024  # 2 MiB
#: Hard cap on elements visited per feed. A billion-laughs document can produce
#: millions of entity expansions; we stop long before that.
_MAX_FEED_ELEMENTS = 100_000
#: Hard cap on nesting depth. Deeply nested XML is another expansion vector.
_MAX_FEED_DEPTH = 256


def fetch_rss_rows(url: str, *, observed_at: str, timeout: float = 15.0,
                   opener: Callable[..., Any] = urlopen) -> tuple[FeedRow, ...]:
    """Fetch public RSS/Atom metadata and return host-only feed rows.

    Only link hostnames are retained. Titles, descriptions, query strings, and
    media URLs are intentionally discarded at the connector boundary.

    The payload is size-capped and parsed with :func:`xml.etree.ElementTree.iterparse`
    under element/depth budgets so a hostile or compromised feed cannot exhaust
    memory (billion-laughs / quadratic entity expansion). Elements are cleared as
    they close so memory stays bounded regardless of feed size.
    """
    request = Request(url, headers={"Accept": "application/rss+xml, application/atom+xml, application/xml", "User-Agent": "QARIN-public-feed/0.1"})
    try:
        response = opener(request, timeout=timeout)
        payload = response.read()
    except Exception as exc:
        raise FeedError(f"public feed request failed: {exc}") from exc
    if len(payload) > _MAX_FEED_BYTES:
        raise FeedError(f"public feed too large: {len(payload)} bytes")
    if isinstance(payload, bytes):
        payload = io.BytesIO(payload)
    else:
        payload = io.StringIO(payload)
    rows: list[FeedRow] = []
    depth = 0
    max_depth = 0
    element_count = 0
    try:
        for event, elem in ET.iterparse(payload, events=("start", "end")):
            element_count += 1
            if element_count > _MAX_FEED_ELEMENTS:
                raise FeedError("public feed too complex: element cap exceeded")
            if event == "start":
                depth += 1
                if depth > max_depth:
                    max_depth = depth
                    if max_depth > _MAX_FEED_DEPTH:
                        raise FeedError("public feed too deeply nested")
            else:  # "end"
                depth -= 1
                if elem.tag.rsplit("}", 1)[-1].lower() == "link":
                    href = (elem.attrib.get("href") or elem.text or "").strip()
                    parsed = urlparse(href)
                    host = parsed.hostname
                    if parsed.scheme in ("http", "https") and host:
                        rows.append(FeedRow(host.lower().rstrip("."), observed_at, "public_feed"))
                elem.clear()
    except ET.ParseError as exc:
        raise FeedError("public feed returned invalid XML") from exc
    except FeedError:
        raise
    except Exception as exc:
        raise FeedError(f"public feed request failed: {exc}") from exc
    return tuple(rows)
