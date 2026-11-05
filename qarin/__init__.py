"""QARIN — the shadow catalogue for Arabic audiovisual works.

Design centre: **supply is enumerable, demand is not.** The audience for a
pirated work cannot be counted without modelling, and a modelled audience is a
number a defence lawyer spends an afternoon with. The *copies* can be counted.
They have to be somewhere public to earn anything. So this package counts
copies, clusters them into the businesses that run them, measures those
businesses from the figures they publish about themselves, and prices the
resulting gap at the rightsholder's own tariff.

Modules, in the order the data flows:

- :mod:`qarin.model`     — works, rights, territories, authorised channels, and
  the **rights calendar** that decides whether a copy is a leak, a substitute,
  or an unserved market
- :mod:`qarin.discover`  — the probe lexicon (the supply side's own search
  grammar), brand lineage, and **rotation forecasting** from the observed
  misspelling pattern
- :mod:`qarin.canonical` — Arabic and Latin entity resolution, including the
  episode/season grammar that is the real bottleneck in this ecosystem
- :mod:`qarin.receipt`   — a capture that is born admissible and replayable
- :mod:`qarin.rotation`  — the recogniser: classifies names arriving from
  certificate-transparency and drop feeds, route signatures, and the APK layer
- :mod:`qarin.ledger`    — append-only Merkle chain, anchorable externally
- :mod:`qarin.operator`  — IDF-weighted infrastructure clustering
- :mod:`qarin.metrics`   — coverage, latency, completeness, availability gap
- :mod:`qarin.enforce`   — notice → outcome → reappearance loop
- :mod:`qarin.report`    — evidence packs and tariff quotations
"""

from .model import (  # noqa: F401
    Availability,
    AuthorisedChannel,
    Right,
    Territory,
    Work,
    WorkKind,
)
from .canonical import EpisodeRef, Offer, Resolver, fold_arabic, parse_offering
from .discover import (
    KNOWN_BRANDS,
    ROTATION_TLDS,
    SURFACES,
    Brand,
    BrandRegistry,
    arabic_technical_terms,
    brand_signal,
    build_probes,
    co_occurrence_verdict,
    enumerate_rotation_candidates,
    lineage_edge,
    plan,
)
from .receipt import Receipt, ReplayRecipe, structural_fingerprint
from .rotation import (
    Hit,
    Recogniser,
    Release,
    Version,
    continues_sequence,
    fold_homoglyphs,
    package_to_domains,
    parse_release,
    route_of,
)
from .ledger import Ledger, LedgerError
from .operator import Cluster, Signal, attribute, cluster_offerings
from .metrics import (
    Appearance,
    Coverage,
    DetectorSpan,
    availability_gap,
    catalog_completeness,
    reappearance_latency,
    supply_coverage,
)
from .collector import Collection, FeedRow, collect, parse_feed
from .radar import RadarCell, RadarSnapshot, build_cell, snapshot
from .connectors import FeedError, fetch_ct_rows, fetch_rss_rows
from .audience import AudienceRecord
from .health import HealthBoard, SourceStatus
from .publish import PublishRefused, publish_json
from .scope import ARABIC_BASELINE, OPTIONAL_COMPETITOR, Market, scope
from .market_metrics import MarketCoverage, coverage_matrix, market_coverage, registered_market_coverage
from .onboarding import OnboardingReport, validate_manifest
from .detectors import Detector, DetectorRegistry, declared_fleet
from .readiness import ReadinessReport, assess
from .source_catalog import PublicSource, coverage_sources, public_sources

__all__ = [
    "Work", "WorkKind", "Right", "Territory", "AuthorisedChannel", "Availability",
    "EpisodeRef", "Offer", "Resolver", "fold_arabic", "parse_offering",
    "Brand", "BrandRegistry", "KNOWN_BRANDS", "ROTATION_TLDS", "SURFACES",
    "arabic_technical_terms", "brand_signal", "build_probes", "plan",
    "co_occurrence_verdict", "enumerate_rotation_candidates", "lineage_edge",
    "Receipt", "ReplayRecipe", "structural_fingerprint",
    "Ledger", "LedgerError",
    "Signal", "Cluster", "attribute", "cluster_offerings",
    "Recogniser", "Hit", "Release", "Version", "fold_homoglyphs", "route_of",
    "parse_release", "package_to_domains", "continues_sequence",
    "Appearance", "Coverage", "DetectorSpan", "supply_coverage",
    "reappearance_latency", "catalog_completeness", "availability_gap",
    "FeedRow", "Collection", "parse_feed", "collect",
    "RadarCell", "RadarSnapshot", "build_cell", "snapshot",
    "FeedError", "fetch_ct_rows", "fetch_rss_rows",
    "AudienceRecord",
    "HealthBoard", "SourceStatus",
    "PublishRefused", "publish_json",
    "Market", "ARABIC_BASELINE", "OPTIONAL_COMPETITOR", "scope",
    "MarketCoverage", "market_coverage", "coverage_matrix", "registered_market_coverage",
    "OnboardingReport", "validate_manifest",
    "Detector", "DetectorRegistry", "declared_fleet",
    "ReadinessReport", "assess",
    "PublicSource", "coverage_sources", "public_sources",
]
