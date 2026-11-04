# QARIN — the shadow catalogue

**قرين** (*qarīn*): the double. Every work has one in the pirate ecosystem, and
unlike its audience it can be counted.

> Enumerate the copy. Attribute the profit. Quote the tariff. Never estimate the
> grief.

This is a from-scratch design for measuring unauthorised distribution of Arabic
audiovisual works and turning that measurement into something a rightsholder can
act on. It is not derived from any prior specification. The reasoning for why it
takes this shape — and specifically why it refuses to produce the number the
industry has been quoting for twenty years — is in [`THESIS.md`](docs/THESIS.md).

## The one-line version

Demand is uncountable. **Supply is enumerable.** So don't model the viewer:
count the copies, cluster them into the businesses that run them, measure those
businesses from the numbers they publish about themselves, and price the gap at
the rightsholder's own tariff — their number, our arithmetic.

## Layout

| Module | Job |
|---|---|
| `qarin.model` | Works, rights, territories, authorised channels, the rights calendar |
| `qarin.canonical` | Arabic/Latin entity resolution incl. episode & season grammar |
| `qarin.receipt` | A capture that is born admissible, and replayable years later |
| `qarin.ledger` | Append-only Merkle chain; anchorable to RFC 3161 / OpenTimestamps |
| `qarin.operator` | IDF-weighted infrastructure clustering → operator attribution |
| `qarin.metrics` | Supply coverage, reappearance latency, catalog completeness, availability gap |
| `qarin.enforce` | Notice → outcome → latency loop; the 30-minute standard as a measured quantity |
| `qarin.report` | Evidence packs and the tariff quotation |

Standard library only, deterministic, no network at test time. Not from thrift:
an instrument whose output nobody can re-run on their own machine is not
evidence, it is a receipt from a vendor.

## Run it

```
python tools/qarin_selfcheck.py
python -m unittest discover -s tests
```

## What it refuses to do

1. **It does not output "revenue lost."** There is no counterfactual that could
   support it, and a figure with no possible disproof is not a measurement. It
   outputs a *quotation* instead: a measured quantity of unauthorised supply,
   priced at a tariff the rightsholder supplies and can verify. See
   `metrics.availability_gap`.
2. **It does not accuse an operator on one signal.** `operator.attribute`
   returns a confidence and a floor; below the floor the output is "co-hosted",
   not "owned". Prevalent infrastructure (a CDN, a mail provider, a payment
   processor) is discounted by inverse document frequency, because the
   information in a shared Cloudflare IP is approximately zero.
3. **It does not print a number without a receipt.** Every observation carries
   the hash of the bytes it was taken from, the resolver that answered, the TLS
   chain, and a replay recipe. If the recipe cannot be re-run to the same body
   hash, the observation is downgraded, not deleted — but it is *labelled*.
4. **It does not store the work.** Metadata, structural fingerprints and hashes
   only. Holding a copy of the infringed media converts an evidence system into
   a distribution system.
