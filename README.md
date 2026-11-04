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
site/             the public page (single self-contained HTML file)
docs/             THESIS.md · SOURCES.md · METHOD notes
tests/            141 unit tests
tools/            one-command contract check
```

## Run it

```bash
python tools/qarin_selfcheck.py     # 71 contract checks + the unit suite
python -m unittest discover -s tests
```

No dependencies. No network at test time. Deterministic. Exits non-zero if
anything fails, so it is the CI gate (`.github/workflows/validate.yml`) and the
answer to *"how do I know this instrument is honest?"* — printed, not asserted.

```
ALL 14 CONTRACT SECTIONS PASSED — 71 checks, of which 30 are refusals — 141 UNIT TESTS GREEN
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
  all in fleet coverage; coverage is bought with surfaces, of which 11 are
  declared. This is the most likely single cause of a false 95% claim, so it is
  instrumented rather than warned about.
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
| `www` | this page |
| `method` | formulas, sources, limitations, public error log |
| `radar` | live meters and counters |
| `index` | quarterly methodology-transparent report |
| `verify` | owner portal and evidence vault, behind Cloudflare Access |

---

*WIPE Enforcement · [wipenforcement.org](https://wipenforcement.org)*
