# Production onboarding packet

This packet is the handoff between the validated instrument and an authorized
production run. It is deliberately a checklist, not a request to paste secrets
into the repository.

## 1. Detector access

For each proposed detector group, provide this information to the operator
through the approved secret manager or account connection:

| Field | Required decision |
|---|---|
| `source_id` | Stable name used in health and receipts |
| `surface` | CT, RSS/Atom, public search, public UGC, app metadata, or IPTV metadata |
| `endpoint` | HTTPS endpoint or approved connector account |
| `terms_reviewed_at` | Date and reviewer for terms/robots/rate limits |
| `market_scope` | One or more of the ten baseline markets |
| `cadence_minutes` | Poll interval within provider limits |
| `operator` | Named owner responsible for failures and notices |

At least two independent detector groups are required per market. Multiple
queries against the same index are recall improvements, not independent
coverage.

## 2. Rightsholder pilot

Start with one title and one territory. The owner supplies:

- a stable `holder_id` and verified ownership/provenance reference;
- title, season, episode, language, and canonical identifiers;
- legal platforms, territory, start/end windows, and sponsorship or affiliate
  relationships that affect interpretation;
- an aggregate audience export with period, platform, market, device share,
  demographic buckets, and cohort size;
- the minimum cohort policy, with cohorts below 30 withheld.

The export must not contain names, emails, phone numbers, IP addresses,
advertising IDs, raw event logs, or viewer-level rows.

## 3. Market measurement

The baseline markets are declared in `qarin.scope`. A market becomes measured
only after its rights context, at least two independent detector groups, source
health history, and overlap corpus have been reviewed. Declared scope alone is
never treated as measured reach.

## 4. Source health and operations

The operator configures:

- secret storage and rotation;
- request budgets, backoff, and provider-specific terms;
- freshness thresholds and alert destinations;
- retention and deletion rules for receipts;
- a manual kill switch for collection and publication.

An unavailable or stale feed must become visible as non-live. It must not be
converted into zero findings or silently carried forward.

## 5. Authorization record

Before scheduling, record outside Git:

1. the approving rightsholder or operator;
2. the approved markets, surfaces, cadence, and retention period;
3. the public destination and access policy;
4. the incident contact and escalation path;
5. the date on which authorization expires or is reviewed.

Only after those five items exist may `deployment_authorized` become true.

## First handoff

The smallest useful handoff is therefore: one owner, one title, one market,
one legal audience export, two lawful public detector groups, and one named
production approver. The system can then run a measured pilot without claiming
regional coverage or a loss figure.
