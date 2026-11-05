# WIPE Enforcement

**Measured evidence of unauthorised distribution of Arabic and MENA audiovisual
content.** Not an audience estimate — a count of the copies, an attribution of
the businesses running them, and a quotation of the gap at the rightsholder's own
tariff.

🌐 **[wipenforcement.org](https://wipenforcement.org)** ·
`enforcement@wipenforcement.org`

---

## The premise

Twenty years of anti-piracy reporting has produced audience estimates nobody can
disprove — which is the same as nobody believing them. The reason is structural:
counting a hidden audience requires assuming a counterfactual no one can observe
(*would they have paid?*), and the entire spread of published "loss" figures is
explained by where each vendor sets that dial.

> **Demand is uncountable. Supply is enumerable.**

Every unauthorised offering must be public somewhere in order to earn anything.
A paywall, an ad slot, a reseller catalogue, a Telegram premium channel and an
IPTV panel are all advertisements. So we measure that instead:

| | The industry | WIPE |
|---|---|---|
| Question | how many people watched illegally | where is it offered, who runs it, what does it earn |
| Requires assuming viewer behaviour | yes, unavoidably | **no instrument here does** |
| Falsifiable by a hostile third party | nobody, ever | from our receipts alone |

A claim that can be broken is a claim you can win.

## What is in here

```
qarin/            the measurement core (Python, standard library only)
  model.py        works, rights, territories, authorised channels, rights calendar
  discover.py     probe lexicon, brand lineage, rotation forecasting
  canonical.py    Arabic/Latin entity resolution + instalment grammar
  receipt.py      a capture that is born admissible, and replayable
  ledger.py       append-only Merkle chain, externally anchorable
  operator.py     IDF-weighted infrastructure clustering with two hard floors
  metrics.py      supply coverage, reappearance latency, completeness, gaps
  enforce.py      notice → outcome → reappearance → recalibration
  report.py       evidence packs and tariff quotations
  collector.py    public CT feed intake -> classified, metadata-only receipts
  connectors.py   public JSON feed adapters with explicit transport failures
                  plus RSS/Atom host extraction for independent public signals
  audience.py     aggregate legal audience, demographic, device, sponsor data
  health.py       source freshness and fail-closed live status board
  publish.py      atomic local publication with health gating
  scope.py        declared ten-market Arabic baseline and optional competitor
index.html        the public page (single self-contained HTML file, served by Pages)
docs/             THESIS.md · SOURCES.md · METHOD notes
  tests/            236 unit tests
tools/            one-command contract check
```

## Run it

```bash
python tools/qarin_selfcheck.py     # 82 contract checks + the unit suite
python -m unittest discover -s tests
```

The first collector boundary is offline-first and accepts either plain
hostnames or newline-delimited JSON from a public Certificate Transparency
feed. It classifies names, emits only actionable hits, and can append sealed
metadata-only receipts to a JSONL ledger:

```bash
python tools/collect_ct.py feed.ndjson --ledger vault/ct-ledger.jsonl
python tools/collect_ct.py --url 'https://crt.sh/?q=%25.example.org&output=json'
python tools/build_radar.py private/radar-manifest.json --out site/data/radar.json
python tools/collect_public.py --rss-url 'https://example.org/public-feed.xml'
python tools/run_once.py --file public-fixture.ndjson --out site/data/public-collection.json
```

The radar manifest is the local onboarding boundary for works, rights,
verified legal channels, observations, and source IDs. The example manifest
contains no real titles or measurements. Scheduling and publishing it requires
an explicit operator deployment decision because the resulting snapshot may
contain private rights and enforcement intelligence.

Legal audience imports use `AudienceRecord`: only aggregate exports are accepted,
cohorts below 30 are rejected, and device/demographic shares must reconcile to
100%. These figures remain separate from public piracy observations; they are
not used to invent an illegal-view denominator.

`HealthBoard.live` is true only when at least one configured source exists and
every source is healthy. Empty, stale, errored, and unconfigured feeds remain
visible as non-live states.

`collect_public.py` includes that health payload beside every collection result,
so an orchestrator can reject stale or partial runs before they reach radar.

`publish_public.py` is the final local handoff. It refuses to replace the
snapshot unless `health.live` is true, writes through a temporary file, fsyncs,
and atomically replaces the destination. External scheduling and deployment
remain an explicit operator decision.

The initial scope is ten explicitly named Arabic markets. They are labelled
`NOT_CONFIGURED` until source coverage is actually measured; the list is not a
ranking and must not be read as one. Türkiye is available as an optional
comparison market, not silently mixed into the Arabic baseline.

`market_coverage()` computes the 95% target separately for each market from
independent detector spans. One detector, a thin corpus, or a blind pair yields
`INSUFFICIENT_EVIDENCE`; it never borrows another market's denominator.

`run_once.py` composes the complete local cycle and is the intended entry point
for an operator-approved scheduler. It accepts exactly one source per run,
publishes only healthy output, and leaves the previous snapshot untouched on
transport or parsing failure.

The collector never fetches a hostname, stores audiovisual media, identifies a
viewer, or turns an unrecognised row into a negative finding. Feed observations
without a replay recipe remain `LOG_ONLY` until a second independent observer
or an external anchor upgrades them.

No dependencies. No network at test time. Deterministic. Exits non-zero if
anything fails, so it is the CI gate (`.github/workflows/validate.yml`) and the
answer to *"how do I know this instrument is honest?"* — printed, not asserted.

```
ALL 15 CONTRACT SECTIONS PASSED — 82 checks, of which 35 are refusals — 236 UNIT TESTS GREEN
```

## The three ideas worth knowing before you read the code

**1. Severity comes from the rights calendar, never from size.** A live final
with 500 simultaneous viewers outranks a three-year-old series with 5 million,
because the first is substitution at a rate near one inside a window closing in
minutes. `PRE_RELEASE_LEAK` — a copy circulating before you broadcast it — is the
only class with a defendant you already know by name, traceable without anybody's
cooperation. `NEVER_AUTHORISED` is reported as an unserved market, not as theft.

**2. The supply side publishes its own search method.** One of the largest
networks in the region describes its own titling convention in its own meta
description: *film name + year + "dubbed" + "HD online" + the names of rival
sites, in order to appear in search results*. An expert searcher finds more by
querying the same way because they are reading how the trade advertises — and
that reading has two applications nobody intended. Brand co-occurrence is
attribution (a lookalike `eegebest.com` carrying keyword metadata for seven
rivals is not an accident), and the misspelling is a **grammar**:

```python
>>> enumerate_rotation_candidates("mycima")[:5]      # 396 candidates in total
['myciiima.autos', 'myciiima.beauty', 'myciiima.biz', 'myciiima.boats',
 'myciiima.bond']
```

Induced from the observed pairs, tested against the record: it reproduces **5 of
5 of the documented MyCima rotation stock** from the brand name alone. Rotation is
bought in bulk and in advance, so a registered-but-unresolved domain in that set
is a *scheduled appearance* — which is the only moment a network can be
interrupted rather than merely observed.

**3. Titles do not go to court; operators do.** Sources cluster on shared
infrastructure, weighted by inverse document frequency, so a Cloudflare IP scores
approximately zero automatically — no blocklist for the next provider to evade by
being new. Two hard floors sit on top of the weighting, because a sum can always
be coaxed over a line by accumulating near-nothings. A favicon and a template are
things you can **buy from the same catalogue of dozens**, so they corroborate and
never decide. Below the floors the word is `CO_HOSTED`, not `OPERATOR`. The
distance between those two words is the distance between a lead and a libel.

## What it refuses

The refusals are the product, and they are tested harder than the measurements:

- **No revenue-loss figure.** No counterfactual could support one. The money
  output is a *quotation*: your tariff × our measured count, arithmetic shown,
  unpriced markets listed beside the total.
- **No accusation on one signal.** Ever.
- **No number without a receipt** — hash, timestamp, resolver, replay recipe.
- **No extrapolation without measured coverage.** A missing divisor is never 1.0;
  that is the same as claiming perfect visibility.
- **No probe count read as coverage.** 110 clever queries on one surface is
  **one detector**. Keyword variety buys recall inside a surface and nothing at
  all in fleet coverage; coverage is bought with surfaces, of which 17 are declared.
- **No media stored.** Metadata, structural fingerprints and hashes only.
- **No learned collection policy.** What adapts is *where to look*, printed as a
  sentence. A self-modifying policy cannot be described to a regulator.
- **No individual viewers identified.**

## Standard library only, deliberately

No PyMC, no ClickHouse, no Neo4j, no Kafka — whatever an enterprise architecture
would prefer. Not from thrift, but because **an estimator nobody can re-run on
their own machine is not evidence, it is a receipt from a vendor.** Hierarchical
Bayesian pooling is replaced by method-of-moments empirical Bayes, re-derivable by
hand from one printed formula, with τ² floored openly so four-to-eight-territory
samples do not silently average every Arab market into one region.

## Sources, and the rule applied to ourselves

[`docs/SOURCES.md`](docs/SOURCES.md) registers all 25 cited facts with dates and
provenance, and states plainly that **no figure this platform reports derives from
any of them** — they establish the shape of the ecosystem, not a number in a
report. Third-party visit figures come from contested rights-holder filings and
are labelled scale context.

The rule that nothing is a number without a source and a timestamp applies to this
repository's own summaries: the refusal count in the verification banner is
computed at runtime, not typed.

## Legal posture

Findings are **evidence of availability, not legal determinations**. Collection is
passive and public; robots.txt is respected on every monitored surface. Saudi PDPL
and the UAE framework differ materially on privacy and on evidence admissibility —
a written local opinion is a **precondition** of operating in those markets, not a
parallel task. Attribution confidence is not proof: `OPERATOR` means "cannot be
explained by shared vendor relationships", and a court may want the C3/C4
escalation path (independent observer, then notary), which is a service to buy,
not an algorithm to write.

## Deployment

Static site on Cloudflare Pages, collector on GitHub Actions cron, no paid
infrastructure in phase one. Hostnames divide the product:

| Host | Job |
|---|---|
| `www` | `index.html` — this page |
| `method` | formulas, sources, limitations, public error log |
| `radar` | live meters and counters |
| `index` | quarterly methodology-transparent report |
| `verify` | owner portal and evidence vault, behind Cloudflare Access |

`validate_manifest()` is the private onboarding gate. It requires provenance
for rights and verified channels, warns when candidate channels are excluded,
checks observation references, and rejects viewer identifiers anywhere in the
payload before publication.

`DetectorRegistry` counts independence groups, not query variants. Two search
queries against one index remain one detector; a genuinely different surface
can add one independent group only when it is explicitly configured and live.
`declared_fleet()` materializes all 17 declared surfaces as `PLANNED`, giving
the operator a procurement checklist without claiming any of them is live.

`assess()` reports launch blockers explicitly: ten-market scope, measured
markets, independent live detectors, healthy sources, valid onboarding, and
explicit deployment authorization.

The operator-facing command is:

```bash
python tools/readiness.py private/radar-manifest.json --health health.json
```

It exits `1` until every launch condition is satisfied.

Run it before building radar:

```bash
python tools/validate_manifest.py private/radar-manifest.json
```

Exit code `0` means the manifest is structurally ready; exit code `1` means it
must not be published yet.

---

*WIPE Enforcement · [wipenforcement.org](https://wipenforcement.org)*
