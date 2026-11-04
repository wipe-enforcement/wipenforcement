# QARIN — thesis

## 1. The thing the industry has been getting wrong for twenty years

Every piracy measurement system ever built tries to answer one question: **how
many people watched illegally?** It is the question rightsholders ask, so it is
the question vendors answer. It is also unanswerable, and the twenty-year track
record of billions-of-dollars-lost figures — none of which have ever survived a
serious audit — is the proof.

The reason is structural, not a matter of better data. To count a hidden audience
you must model it, and every model of it rests on a counterfactual you cannot
observe: *would this person have paid?* Industry convention sets that answer
somewhere between 1:1 and 4:1 by fiat, and the entire spread of published "loss"
figures is explained by where each vendor happens to sit on that dial. That is not
measurement. It is an opinion with a unit of currency attached, and it is why
finance departments ignore anti-piracy reports and why courts treat them as
advocacy.

There is a second, quieter problem. A system built to estimate audience must
estimate *its own blindness* in order to extrapolate, and every such system sets
that factor by assumption. Nobody has ever published a coverage figure for their
own crawl, because nobody has ever measured one.

## 2. The inversion: supply is enumerable, demand is not

QARIN refuses the unanswerable question and answers a different one.

> **Count the copies. Cluster them into the businesses that run them. Measure
> those businesses from the figures they publish about themselves. Price the
> result at the rightsholder's own tariff.**

The asymmetry that makes this work is that **every pirate offering must be
public somewhere in order to earn anything.** A hidden audience stays hidden
forever; a paywall, an ad slot, a reseller catalogue, a Telegram premium channel
and an IPTV panel are all advertisements. The pirate's economics are
self-disclosing in a way the viewer's behaviour never is.

This is not a softer version of the same ambition. It is a strictly harder claim,
because it is falsifiable:

| Claim | Falsifiable by |
|---|---|
| "2.4 million people watched this illegally" | nobody, ever |
| "these 340 domains are one business" | any one of them turning out to be an unrelated customer of the same vendor |
| "this copy appeared 11 minutes before broadcast" | the broadcast schedule |
| "this operator was up for 90 minutes after removal" | the receipts |

A claim that can be broken is one you can win. That is the whole product.

## 3. Four objects, and why each exists

### 3.1 The rights calendar — a copy is not one kind of thing

The single most consequential idea in this design: **severity comes from the
relationship between a copy and the rights calendar, never from its size.**

A live final with 500 simultaneous viewers is a substitution event at a rate near
one, inside a window that closes in minutes. A three-year-old series with 5
million views in a territory where it was never licensed is not stealing anything,
because there is no sale it prevents. Both appear identically in every dashboard
that counts "infringing items" — and they are worth wildly different amounts to
the person who owns the work.

So the calendar classifies every observation:

```
PRE_RELEASE_LEAK        before air, anywhere        ← attributable: a named defendant
SIMULTANEOUS_LIVE       inside the event window     ← damage is a function of minutes up
CONCURRENT_UNAUTHORISED available legally elsewhere ← real but partial substitution
POST_WINDOW             licence expired             ← weak, and reported as weak
NEVER_AUTHORISED        no licence in territory     ← NOT THEFT. An unserved market.
UNKNOWN                 calendar does not cover it  ← never defaulted
```

`PRE_RELEASE_LEAK` deserves emphasis, because it is the only class in the whole
taxonomy that produces a **defendant the network already knows by name**. A copy
circulating three weeks before broadcast came from a screener, a satellite feed,
or a post-production drive. It is traceable to a partner without anybody's
cooperation, and it is the one finding that gets a rightsholder a settlement
rather than a statistic. A platform that ranks by volume buries it under archive
copies.

And `NEVER_AUTHORISED` is the one the industry cannot bring itself to say,
because saying it turns an accusation into a distribution question. It is also
the finding a programming director can act on Monday.

### 3.2 The receipt — born admissible, or it is a log line

Every system collects first and thinks about proof later. The order is wrong, and
it is wrong in a specific way: the facts that make a capture re-verifiable two
years from now — which resolver answered, which TLS certificate was presented,
what the exact request bytes were — **cannot be reconstructed later.** The page
will have moved, the certificate will have rotated, the host will have been
repointed.

So a receipt records a *replay recipe* alongside the hash, and its admissibility
floor is derived from what it actually carries rather than from what its author
intended:

```
no replay recipe      -> LOG_ONLY          evidences our collector's report
single observer       -> SINGLE_OBSERVER   evidences the page, unreproduced
two observers, same bytes -> C3
notarised chain       -> C4
```

Two hashes are kept, because they answer different questions. `body_sha256` pins
the bytes. `structural_fingerprint` — the SHA-256 of the document's *tag
skeleton*, with text, attributes, scripts and comments discarded — is stable
across the one-copyright-year-and-an-analytics-ID difference between a mirror and
its original. So the same number that detects cosmetic tampering also identifies
template clones, which is the cheapest and strongest operator signal in the whole
system, and it is free because you were going to hash the page anyway.

### 3.3 The operator graph — titles don't go to court

A rightsholder's problem is never "there are 4,000 infringing URLs". It is "there
are four businesses, and each runs a thousand URLs". Enforcement against a URL is
whack-a-mole by definition, and two decades have demonstrated that.

The entity is discoverable from passive public data, because **infrastructure has
to be shared to be cheap.** So sources are clustered on shared certificates,
monetisation accounts, payment endpoints, bot tokens, favicons, template
fingerprints, release-group tags, IP blocks — weighted by inverse document
frequency, so that a value carried by half the corpus contributes nothing:

```
w(signal) = class_weight × log(1 + N / n_carriers)
```

The IDF term is not a heuristic borrowed for its sound. It is the correct measure
of how much an observation reduces uncertainty about *common ownership*, and it
makes the CDN problem quantitative instead of a matter of tuning: a Cloudflare IP
scores approximately zero automatically, with no blocklist for the next provider
to evade by being new.

**And this is where the accusation risk lives, so it gets two hard floors rather
than a threshold on a weighted sum.** A weighted sum can always be coaxed over a
line by accumulating enough near-nothings. So:

1. **Decisive class.** A signal may carry an attribution alone only if sharing it
   is close to impossible without common control — a certificate key, a
   monetisation account, a payment endpoint, a bot token. A favicon and a
   template are things you can **buy from the same catalogue of dozens**, so they
   are corroborating evidence, never the only evidence.
2. **Vendor prevalence.** A value on more than 30% of sources is infrastructure,
   and it is *zeroed*, not discounted. Discounting a shared IP still lets it
   contribute, and accumulation of small contributions is precisely how false
   clusters get built.

Below the floors the output is `CO_HOSTED` — these things share plumbing — never
`OPERATOR`. **The distance between those two words is the distance between a lead
and a libel.** A platform that cannot decline to accuse is not an evidence
platform, and this one is built so that declining is the default state.

### 3.4 The ledger — deletion, not modification, is the threat

A hash chain proves one thing did not change. It does not prove something was not
*omitted* — and omission is the attack that matters, because a compromised runner
or a future maintainer pruning an inconvenient week can delete whole captures and
leave every remaining seal perfectly valid.

So: entries commit to their predecessor (deletion breaks the walk), each day's
captures fold into a Merkle root, and the root is what gets anchored to an
external time authority. **An unanchored day is reported as unanchored on the
first line of any pack built from it**, because a private chain can be rewritten
wholesale by anyone holding the file, and a system that implies a protection it
does not have is worse than one that admits the gap.

The day root sorts its leaves before folding, which is a deliberate departure from
the textbook indexed Merkle tree. The anchor has to prove *which captures existed
on a day* — not the order in which the collector happened to write them down. An
anchor that moves when the export is regenerated proves nothing durable.

## 4. What is measured, and what is therefore refused

| Instrument | What it observes | Assumption about viewers |
|---|---|---|
| `supply_coverage` | detection histories of offerings across independent detectors | none |
| `reappearance_latency` | removal → re-detection, in minutes | none |
| `catalog_completeness` | which instalments exist where | none |
| `availability_gap` | authorised channels in territory × measured supply | none |
| `operator clustering` | shared infrastructure | none |

Not one of these requires a assumption about human behaviour. That is the
achievement, and it is why they can be put in front of a regulator.

**Coverage is estimated on offerings, never on audiences** — and this is worth
being explicit about, because it is the same mathematics applied twice, once
honestly and once not. Capture-recapture assumes detectors are independent. An
audience's detection history is determined by the very popularity that makes it
valuable, so independence fails *structurally and always in the direction that
inflates reach*. An offering's detection history is a property of the fleet's
coverage of infrastructure — different crawlers, different discovery paths,
different schedules — which is independent by construction.

And coverage is **measured, not promised**. The brief asks for 95% and no system
can promise that; any system claiming it is guessing. But the gap is countable,
and the arithmetic of closing it is a procurement fact:

```
coverage = 1 − (1 − p)^k        →        k ≥ log(1 − target) / log(1 − p)
```

| per-detector reach | independent detectors for 95% | what 5 achieve |
|---|---|---|
| 9 % | 32 | 37.6 % |
| 13 % | 22 | 50.2 % |
| 20 % | 14 | 67.2 % |
| 34 % | 8 | 87.5 % |

Five sources cannot reach 95% at any level of engineering effort, because the
binding constraint is **independence, not quality**. So the question is never
"more crawlers" — it is "which crawler is least correlated with the ones I have",
which is why an IPTV panel harvester and a torrent-swarm listener outrank a sixth
website scraper. `greedy` ordering on marginal reach is the whole fleet-planning
problem, and it now has an integer answer.

Two further refusals are load-bearing:

- **Extrapolation without coverage is blocked.** If coverage is unknown,
  `pirate_views` is unknown. A missing coverage figure must never silently become
  a divisor of 1.0, which is the same as claiming perfect visibility.
- **No value is quoted without a tariff and a measured unit.** Both must come
  from outside this system. Absent either, the gap is reported as a count and
  stops — and the unpriced markets are *listed next to the total*, because a sum
  that silently omits four markets will be quoted as though it covered eight.

## 5. The tariff, not the loss

The money output is a **quotation**, and the distinction is the entire commercial
strategy:

> *"412 unauthorised offerings across 40 sources in Iraq, 1.8M measured views, at
> your published rate of $3.50 per thousand → $6,300."*

Their rate. Our count. The multiplication is the whole of the analysis, and both
factors are independently checkable. There is no assumption about whether anyone
would have paid, because there is no claim that anyone lost it.

Compare the defensibility:

| | "You lost $40M to piracy" | "At your tariff, measured unserved supply in IQ is $6,300" |
|---|---|---|
| Contested assumption | would-have-paid (unknowable) | none |
| Who can verify | nobody | their own finance team and our receipts |
| What it invites | an argument about methodology | a decision |

And the framing matters as much as the arithmetic. **Loss framing gets ignored;
opportunity framing gets budget.** "Here is demand you are not selling into" is
the only sentence in this domain that a network acts on, because it is the only
one that does not require them to admit a failure to their own board. The
constructive finding and the defensible finding turn out to be the same finding —
which is the reason this design is commercially viable where the audience-estimation
model is a compliance cost.

## 6. Latency is the harm metric

`reappearance_latency` is the most valuable single number here, and it needs no
model at all: a duration between two observed events, reproducible by any third
party from the receipts alone.

- It maps directly onto how the harm actually works. For live sport and
  simultaneous Ramadan releases, value is destroyed per minute, so "came back in
  4 minutes" is a statement about the futility of the response, not about the size
  of the audience.
- It measures the **operator**, not the page. A takedown that is undone in four
  minutes is not a takedown, and the industry's own compliance statistics say so.
- Absence is *observed*, not taken from a reply. An offering is absent when a
  detector that previously found it fails to find it. Waiting for a notice to be
  acknowledged is waiting for an adversary to answer, and most of the time they
  will not — so non-response becomes a dated outcome (`IGNORED`) rather than a
  blank cell, and the blank cell is exactly what destroys the evidence that
  non-compliance is systematic.
- The mirror hop is detectable without anybody's cooperation: removed here, back
  there, inside the window. That one measurement is the empirical refutation of
  per-URL enforcement, and it is the argument that gets an enforcement budget
  redirected at entities.

Priority therefore follows the calendar and the cluster, never the view count:
`route()` orders by severity class, then by how many sources share the operator.
Audience magnitude never enters the ordering, because it is the one input that
would have to be modelled.

## 7. Arabic-specificity, and why it is the bottleneck

Every number in this system is conditional on one upstream fact: that four
observations of the same episode were recognised as one episode. That is not
string matching. It is morphology, and it is where generic tooling fails quietly.

What the fold has to handle, all of it observed in real captions:

- **Diacrits, tatweel, superscript alef** — decoration, not phonology
- **Alef family** (أ إ آ ٱ) collapsing to bare alef; **teh marbuta** ة → ه;
  **yeh/alef maqsūra** ى → ي; hamza carriers ؤ ئ
- **Two digit systems** — Arabic-Indic ٠-٩ *and* Extended Arabic-Indic ۰-۹, the
  latter arriving with Iranian-dubbed serials, a real and growing slice of the
  catalogue
- **Arabic punctuation** (، ؛ ؟) as separate codepoints from the Latin ones, so a
  Latin-only punctuation class leaves the text untokenised
- **Word numerals and ordinals**, which dominate in written captions: the twelfth
  episode is normally announced as "الحلقة الثانية عشر", and the twenty-third as
  "الحلقة الثالثة والعشرون". Missing these does not degrade accuracy gradually —
  it splits the corpus into a digit-parsed half and an unparseable half. Getting
  the compounding wrong is worse than missing it: reading "twenty-third" as
  "third" files episode 23 under episode 3, a *silent mis-attribution to a real
  instalment*
- **Transliteration** — al/el/∅ × Raheb/Raheba, plus glued articles
- **The instalment grammar itself** — `الحلقة ١٢`, `ح12`, `EP12`, `S02E12`, a bare
  `(12)`, the number in the URL path, and the ordinal spelled out
- **The pirate's own release vocabulary** — `WEB-DL`, `TS`, `SCREENER`, `مدبلج`,
  `مترجم`, and the release-group tag

Two of those vocabulary families are not noise and are treated as first-class
signals, which is the Arabic-specific insight most systems miss entirely:

- **Quality implies provenance.** `WEB-DL` means an extract from a legal platform
  — a supply-chain fact about a *licensee*. `TS`/`CAM` means a camera in a
  physical cinema. `SCREENER` means a review copy. These are different crimes with
  different defendants, and the pirate prints which one it was, in the filename,
  to advertise quality to its own customers.
- **Dubbed versus subtitled is a demographic read on supply.** Dubbing is
  expensive and targets Gulf and Egyptian audiences; subtitling is cheap and
  targets the Levant and Maghreb. Which one an operator invests in tells you where
  they think the money is — and that is a market signal obtained without asking a
  single viewer, which is the only demographic data this design trusts.

Resolution therefore works by **candidate generation against a registry**, not by
building a perfect normaliser, and the normaliser is deliberately lossy in exactly
one direction: it may merge two different works (which the registry then has to
separate, visibly) and may never split one work into two (which would silently
under-count and be invisible forever). Keys are weighted by inverse document
frequency over the catalogue, so a name three serials share cannot support a
confident attribution — and ambiguous matches produce a **review queue, never a
coin flip**, because assigning an ambiguous name to the more popular of two works
is the fastest way to manufacture a false allegation against the less popular one.

## 8. Deliberate constraints

**Standard library only.** No PyMC, no ClickHouse, no Neo4j, no Kafka — whatever
the enterprise architecture says. Not from thrift, and this point should not be
softened: *an estimator nobody can re-run on their own machine is not evidence,
it is a receipt from a vendor.* Empirical-Bayes pooling by method of moments
replaces hierarchical MCMC and is re-derivable by hand from one printed formula.
Deterministic, milliseconds, free runner.

**No learned collection policy.** What the enforcement loop adapts is *where to
look*, printed as a sentence. Never *what to believe*. A self-modifying policy
cannot be described to a regulator, and explicable-ness is the whole asset.

**No media stored.** Metadata, structural fingerprints, hashes and text
extraction only. Holding a copy of the infringed work converts an evidence
instrument into a distribution network, and hands the operator's lawyer the only
genuinely good argument they have. Emission checks for `stream_url`/`media`/
`viewer_identity` on the way out, not on the way in, because the realistic failure
is a well-meaning later edit pasting a stream link into an evidence field "to make
it clearer for the lawyer".

**No identities of individual viewers.** Ever. Small operators yes, as far as
infrastructure attributes them; audiences no.

## 9. What this design does not solve

Stated plainly, because a method page that hides its own failure modes is not a
method page.

1. **Private distribution is invisible.** A closed WhatsApp group, a paid
   Telegram private channel, a resold IPTV panel with no public manifest. No
   passive method reaches these. The honest position: they are a *flow* problem
   addressed by cutting the payment and the hosting, not a *measurement* problem.
2. **Coverage is a model-based figure**, interval from an entity-level bootstrap
   over the estimator pipeline. That prices in sampling noise and estimator
   instability. It does not price in model misspecification.
3. **Dependence is modelled pairwise, not three-way and up.** With five detectors
   this is the largest unquantified approximation in the system, and it is
   reducible only by buying genuinely orthogonal sources — which is §4's
   procurement argument in another form.
4. **A two-detector fleet admits no dependence correction at all.** Two lists
   with one nested inside the other are perfectly consistent with a population
   equal to the union. This is a real identifiability limit, and the code returns
   the estimate with the caveat rather than pretending the correction fired.
5. **Registry completeness bounds everything.** An unregistered work is
   unattributable, and its supply lands in the unresolved bucket. That bucket is
   kept and surfaced — a name recurring there across channels is an unregistered
   viral title, which is a discovery the registry needs — but it is not a
   measurement.
6. **Legal-posture variance.** Saudi PDPL and the UAE framework differ materially
   on privacy and on evidence admissibility. A written opinion for KSA and UAE is
   a **precondition** of operating in those markets, not a parallel workstream.
7. **Attribution confidence is not proof.** `OPERATOR` means "cannot be explained
   by shared vendor relationships". A court may want more, and the correct answer
   to that is the C3/C4 escalation path (independent observer, then notary), which
   is a service to be purchased, not an algorithm to be written.

## 10. Why this is a durable position

Three properties that compound and cannot be copied by adding a feature to an
audience-estimation product:

1. **Falsifiability as moat.** Competitors sell a number. QARIN sells a count, a
   provenance chain, a disclosed blind spot and a quotation built on the client's
   own tariff. Every one of those is checkable, which is precisely what lets it be
   relied upon. A number that cannot be disproved is not valuable — it is
   *worthless and untestable*, which is the current state of the entire industry,
   and the reason nobody believes it.
2. **The data network effect runs through ground truth, not through volume.**
   Every rightsholder who shares first-party availability data sharpens the rights
   calendar, which improves the severity classification for *every* other
   rightsholder in the same territory. This is why `CANDIDATE` channels are
   excluded from the legal denominator: it makes honest registration the only route
   to a favourable number, so the incentive points at contributing data rather than
   at contesting ours.
3. **The operator graph compounds in the other direction.** Each cycle of
   enforcement teaches which clusters respond, which channels are load-bearing and
   which vendors are worth writing to. That learning is proprietary, accumulates
   across engagements, and is unavailable to a competitor who starts from a cold
   corpus — because it is bought with *dated observations of the same entities over
   time*, and time cannot be backfilled.

And underneath all three, the property that is hardest to replicate: **the
instrument declines.** It refuses to accuse on a template. It refuses to quote a
loss. It refuses to extrapolate without a measured coverage figure. It refuses to
publish a capture with no replay recipe, and it refuses to issue a pack built from
a tampered receipt. Eighteen distinct situations in which it prints an em dash
instead of a number, each with a stated reason.

An organisation that has been selling certainty cannot copy that, because the
refusals are the product.
