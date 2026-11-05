# Go-live checklist

The local instrument is validated. Production remains intentionally gated until
the following inputs exist outside the public repository.

## Required inputs

1. **Rights manifest** — verified works, owners, territories, windows, legal
   channels, sponsorships, affiliates, and provenance references.
2. **Audience exports** — aggregate legal-platform records only; no viewer IDs,
   emails, phone numbers, IP addresses, or raw event logs.
3. **Detector configuration** — at least two independent live groups per market
   before any coverage estimate is published. Search wording variants do not
   count as independent groups.
4. **Public source access** — approved CT, RSS/Atom, and other lawful metadata
   endpoints with rate limits, terms review, and a named operator.
5. **Deployment authorization** — approved destination, retention policy,
   access control, incident contact, and permission to schedule collection.

## Acceptance gate

Run the following locally before deployment:

```bash
python tools/validate_manifest.py private/radar-manifest.json
python tools/readiness.py private/radar-manifest.json --health health.json
python tools/qarin_selfcheck.py
```

The readiness command must report `ready: true`. Until then, the radar must
continue to display `UNMEASURED` and must not publish a 95% claim.

## First production slice

Start with one approved public metadata source and one rightsholder pilot. Run
`tools/run_once.py` manually, inspect the health payload and receipts, then add
an operator-approved scheduler. Expand markets and detector groups only after
the previous slice has a measured overlap corpus and a reviewed evidence pack.

## Non-negotiable boundaries

- No media downloads or storage.
- No individual viewer identification.
- No private watch list in public artifacts.
- No legal conclusion from one signal.
- No audience estimate derived from pirate counters.
- No unattended external publication without explicit authorization.
