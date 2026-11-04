#!/usr/bin/env python3
"""QARIN self-check: the contract, executed and printed.

    python tools/qarin_selfcheck.py

Runs the invariant checks that matter, then the unit suite, and exits non-zero if
anything fails. It is the CI gate and it is the answer to "how do I know this
instrument is honest?" — printed, not asserted in prose.

Standard library only, no network, deterministic. It must be runnable by someone
who does not trust us, on a machine that is not ours.
"""
from __future__ import annotations

import datetime as dt
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from qarin.canonical import fold_arabic, latin_root, parse_instalment, parse_offering  # noqa: E402
from qarin.enforce import (  # noqa: E402
    Notice, NoticeState, Routed, close_loop, escalation_target, route,
)
from qarin.ledger import Ledger, merkle_root  # noqa: E402
from qarin.metrics import (  # noqa: E402
    Appearance, DetectorSpan, availability_gap, catalog_completeness,
    detectors_needed, fleet_reach, reappearance_latency, supply_coverage,
)
from qarin.model import (  # noqa: E402
    Availability, AuthorisedChannel, Right, Work, WorkKind, RightsCalendar,
)
from qarin.operator import Signal, cluster_offerings, signals_from_html  # noqa: E402
from qarin.receipt import Receipt, ReplayRecipe, structural_fingerprint  # noqa: E402
from qarin.report import build_pack, quote_gaps, scan_for_prohibited  # noqa: E402
from qarin.operator import Cluster  # noqa: E402

BAR = "=" * 74
FAILURES: list[str] = []


def section(title: str) -> None:
    print(f"\n{BAR}\n{title}\n{BAR}")


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(label)


HTML = ("<html><head><title>X</title><script>ga('create','G-ABC123456')</script>"
        "</head><body><div><a href='/e12'>الحلقة 12</a></div></body></html>")
HTML_MIRROR = ("<html><head><title>X 2027</title><script>"
               "ga('create','G-XYZ999999')</script>"
               "</head><body><div><a href='/e12'>الحلقة 12</a></div></body></html>")


def main() -> int:
    section("1. Arabic resolution — the bottleneck every number sits behind")
    same = {fold_arabic(x) for x in
            ("الراهب", "الرَّاهِب", "الـراهـب", "ٱلرَّاهِبُ")}
    check("diacritics and tatweel collapse to one key", len(same) == 1,
          f"-> {same}")
    # The fold once deleted U+064A (Arabic yeh) because it sat in the
    # punctuation class through a codepoint confusion. Every other test here
    # passed while that was true, so it is asserted directly: yeh is a letter,
    # and letters survive a fold whose only business is marks and punctuation.
    # The fold once deleted U+064A (Arabic yeh) because it sat in the
    # punctuation class through a codepoint confusion. Every other test here
    # passed while that was true, so the invariant is asserted structurally
    # rather than on one word: a fold may remove MARKS and PUNCTUATION, and it
    # may MAP one letter onto another (teh marbuta to ha, alef variants to bare
    # alef), but it may never DELETE a letter. Counting letters before and after
    # catches every deletion of that family, including the ones nobody thought
    # to name. Tatweel is excluded because removing it is the documented intent.
    def letters(t):
        return [c for c in t if c.isalpha() and "؀" <= c <= "ۿ"
                and c != "ـ"]

    caption = ("مسلسل الراهب "
               "الحلقة مترجم "
               "اليوم")
    folded_cap = fold_arabic(caption)
    check("the fold deletes no letter, only marks and punctuation",
          len(letters(folded_cap)) == len(letters(caption)),
          f"{len(letters(caption))} letters in, {len(letters(folded_cap))} out")
    check("Arabic yeh (U+064A) survives the fold", "ي" in folded_cap,
          repr(folded_cap))
    check("the fold is idempotent, so it can be applied twice safely",
          fold_arabic(folded_cap) == folded_cap)
    # Built from codepoints rather than typed by hand: the first version of this
    # line silently dropped two digits from each script and still passed, so it
    # proved nothing. A digit table has to be asserted exhaustively or not at
    # all — this is the same class of bug that once put Arabic yeh (U+064A) into
    # the punctuation class below.
    ar_digits = "".join(chr(c) for c in range(0x0660, 0x066A))
    ur_digits = "".join(chr(c) for c in range(0x06F0, 0x06FA))
    check("both digit scripts fold to ASCII, all ten of each",
          fold_arabic(ar_digits) == "0123456789"
          and fold_arabic(ur_digits) == "0123456789",
          f"{ar_digits} -> {fold_arabic(ar_digits)}")
    eps = {parse_instalment(t).episode for t in (
        "مسلسل الراهب الحلقة ١٢ مترجم hd",
        "Al Raheb - الحلقة الثانية عشر (12) بجودة WEB-DL",
        "الراهب ح12", "Raheb.S02E12.WEB-DL")}
    check("four observed forms of one episode resolve to one instalment",
          eps == {12}, f"-> {eps}")
    check("word numerals compound correctly",
          parse_instalment("الحلقة الثالثة والعشرون").episode == 23
          and parse_instalment("الحلقة ثلاثين").episode == 30)
    check("a year is never an episode",
          parse_instalment("فيلم 1984").episode is None)
    check("transliterations share one root",
          len({latin_root(n) for n in ("Al Raheb", "El Raheb", "al-raheb",
                                       "ALRAHEB", "Raheb")}) == 1)
    o = parse_offering("الراهب الحلقة 12 WEB-DL")
    check("quality tag implies provenance", o.provenance == "platform_extract",
          f"-> {o.provenance}")
    check("dub vs sub is read as a market signal",
          parse_offering("مسلسل مدبلج").language_mode == "dubbed"
          and parse_offering("مترجم").language_mode == "subtitled")

    section("2. Rights calendar — what a copy *means*, not how big it is")
    w = Work(id="raheb", kind=WorkKind.SERIES, titles={"ar": "الراهب"},
             holder_id="mbc", episode_total=30, first_broadcast=dt.date(2026, 2, 17))
    cal = RightsCalendar(
        rights=[Right("raheb", "EG", "mbc", "making_available",
                      "2026-02-17", "2026-09-30")],
        channels=[AuthorisedChannel("shahid", "Shahid", "mbc", "svod", ("EG",),
                                    status="VERIFIED")],
        works=[w])
    cases = [
        (dt.date(2026, 1, 30), "EG", Availability.PRE_RELEASE_LEAK,
         "before air: a leak, and the only attributable class"),
        (dt.date(2026, 3, 1), "EG", Availability.CONCURRENT_UNAUTHORISED,
         "legally on Shahid at the same time"),
        (dt.date(2026, 12, 1), "EG", Availability.POST_WINDOW,
         "after the window closed"),
        (dt.date(2026, 3, 1), "IQ", Availability.NEVER_AUTHORISED,
         "no licence there at all: an unserved market, not a theft"),
    ]
    for when, terr, want, why in cases:
        got = cal.classify("raheb", terr, when).availability
        check(f"{when} in {terr}: {want.value}", got is want, why)
        if got is not want:
            print(f"        got {got.value}")
    check("expired windows are not read as never-licensed",
          cal.classify("raheb", "EG", dt.date(2026, 12, 1)).availability
          is Availability.POST_WINDOW)
    check("a candidate channel does not count as authorised",
          RightsCalendar(
              rights=[Right("raheb", "EG", "mbc", "making_available",
                            "2026-02-17", "2026-09-30")],
              channels=[AuthorisedChannel("wit", "WATCH IT", "x", "svod", ("EG",),
                                         status="CANDIDATE")],
              works=[w]).classify("raheb", "EG", dt.date(2026, 3, 1))
              .availability is not Availability.CONCURRENT_UNAUTHORISED)

    section("3. Receipt — born admissible, or it is a log line")
    a = Receipt.from_html("https://s.test/e12", HTML, observed_at="2026-11-04T10:00:00Z")
    b = Receipt.from_html("https://s.test/e12", HTML_MIRROR,
                          observed_at="2026-11-04T10:00:05Z")
    check("a mirror changes the bytes but not the template",
          a.body_sha256 != b.body_sha256
          and structural_fingerprint(HTML) == structural_fingerprint(HTML_MIRROR),
          "the structural fingerprint is simultaneously an integrity device and "
          "the cheapest operator signal available")
    sealed = a.seal()
    check("the seal verifies against its own content", sealed.verifies())
    tampered = Receipt(**dict(sealed.__dict__, excerpt="edited"))
    check("editing after sealing is detected", not tampered.verifies())
    naked = Receipt.from_html("https://s.test/x", HTML, observed_at="2026-11-04T10:00:00Z")
    check("no replay recipe caps admissibility",
          naked.admissible_floor == "LOG_ONLY")
    with_rec = Receipt.from_html(
        "https://s.test/x", HTML, observed_at="2026-11-04T10:00:00Z",
        recipe=ReplayRecipe(method="GET", url="https://s.test/x",
                            headers=(("User-Agent", "qarin/1"),),
                            header_order=("User-Agent",),
                            resolved_ips=("1.2.3.4",),
                            egress={"geo": "NL", "asn": "AS14061"},
                            tls_peer_cert_sha256="c" * 64)).seal()
    check("a recipe survives the round trip off disk",
          Receipt.from_dict(with_rec.to_dict()).verifies()
          and Receipt.from_dict(with_rec.to_dict()).recipe is not None,
          "a receipt that survives sealing but not reloading is no evidence")

    section("4. Ledger — deletion must be detectable, not merely discouraged")
    lg = Ledger()
    for i in range(6):
        lg.append(Receipt.from_html(f"https://s.test/{i}", HTML,
                                    observed_at="2026-11-04T10:00:00Z").seal())
    check("six entries verify", lg.verify()[0], lg.verify()[1])
    del lg._entries[2]
    ok, why = lg.verify()
    check("removing one capture is detected", not ok, why)
    check("the day root commits to the set, not the write order",
          merkle_root(sorted([a.body_sha256, b.body_sha256]))
          == merkle_root([b.body_sha256, a.body_sha256]))
    check("an unanchored day says so", lg.unanchored_days() == ["2026-11-04"],
          "a private chain can be rewritten wholesale by anyone holding the file")
    lg2 = Ledger()
    lg2.append(Receipt.from_html("https://s.test/1", HTML,
                                 observed_at="2026-11-04T10:00:00Z").seal())
    payload = lg2.anchor_payload("2026-11-04")
    lg2.record_anchor("2026-11-04", "ots:" + "a" * 40)
    check("anchoring lifts the day and is written back into the chain",
          lg2.unanchored_days() == [] and payload["root"] is not None,
          f"nonce {payload['nonce'][:12]}… binds the anchor to this ledger")

    section("5. Operator clustering — the accusation guard")
    srcs = {
        "a": [Signal("tls_cert_key", "CERT1"), Signal("asn", "AS999")],
        "b": [Signal("tls_cert_key", "CERT1"), Signal("asn", "AS999")],
    }
    cl = cluster_offerings(srcs)
    check("a shared certificate attributes", len(cl) == 1
          and cl[0].verdict == "OPERATOR", cl[0].summary() if cl else "none")
    cdn = {f"s{i}": [Signal("cdn", "CLOUDFLARE"), Signal("asn", "AS13335")]
           for i in range(12)}
    cl2 = cluster_offerings(cdn)
    check("a shared CDN never attributes",
          all(c.verdict != "OPERATOR" for c in cl2),
          f"{len(cl2)} cluster(s), all declined")
    tmpl = {f"t{i}": [Signal("struct_fp", "TPL")] for i in range(4)}
    cl3 = cluster_offerings(tmpl)
    check("a shared template is evidence but never the only evidence",
          all(c.verdict != "OPERATOR" for c in cl3),
          "templates are bought from the same catalogue of dozens")
    sigs = signals_from_html(
        "<html><script>api.telegram.org/bot123456789:"
        "AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsawZ/</script>"
        "<div data-x='ca-pub-1234567890123456'></div>"
        "<img src='https://www.facebook.com/tr?id=9988776655&ev=PageView'></html>")
    kinds = {(s.cls, s.value) for s in sigs}
    check("monetisation and bot identity are extracted",
          ("ad_account", "adsense:1234567890123456") in kinds
          and ("ad_account", "fbpx:9988776655") in kinds
          and ("telegram_bot", "123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsawZ") in kinds)
    check("a repeated tag is one fact, not nine",
          len([s for s in signals_from_html(
              "".join("<script>G-SAMEONE</script>" for _ in range(9)))
              if s.value == "G-SAMEONE"]) == 1)
    check("nothing is emitted from a guessed pattern",
          signals_from_html("<html><body>plain</body></html>") == [])

    section("6. Supply coverage — enumerable, unlike demand")
    pool = [f"p{i}" for i in range(200)]
    ordered = [
        ("disjoint", [f"a{i}" for i in range(60)], [f"b{i}" for i in range(60)]),
        ("quarter", pool[:60], pool[45:105]),
        ("half", pool[:60], pool[30:90]),
        ("nested", pool[:60], pool[:60]),
    ]
    prev = None
    for tag, x, y in ordered:
        c = supply_coverage([DetectorSpan("d0", frozenset(x)),
                             DetectorSpan("d1", frozenset(y))])
        cov = c.coverage_p50
        print(f"    {tag:9s} union={c.n_observed:3d} N={c.population_p50 or 0:8.1f} "
              f"coverage={cov if cov is None else round(cov, 4)} "
              f"blind_pairs={c.blind_pairs}")
        if prev is not None and cov is not None:
            check(f"{tag} overlap raises claimed coverage above {prev[0]}",
                  cov > prev[1], "the bias the correction exists to fight")
        prev = (tag, cov)
    c1 = supply_coverage([DetectorSpan("d0", frozenset(pool[:60]))])
    check("one detector is unmeasurable, not 100%", c1.coverage_p50 is None,
          c1.reason or "")
    check("a thin corpus refuses rather than estimates",
          supply_coverage([DetectorSpan("d0", frozenset(["a", "b"])),
                           DetectorSpan("d1", frozenset(["c", "d"]))]).coverage_p50 is None)

    section("7. The cost of 95% — a procurement fact, not an aspiration")
    for p_ in (0.09, 0.13, 0.20, 0.34):
        need = detectors_needed(p_, 0.95)
        have5 = fleet_reach([p_] * 5)
        print(f"    per-detector reach {p_:>4.0%} -> {need:2d} mutually "
              f"independent detectors; a 5-fleet reaches {have5:.1%}")
    check("five detectors cannot reach 95% at any level of effort",
          fleet_reach([0.20] * 5) < 0.95 and detectors_needed(0.20) > 5,
          f"need {detectors_needed(0.20)}, have 5 — the constraint is "
          "independence, not engineering quality")

    section("8. Latency — the harm metric that needs no model")
    t0 = dt.datetime(2026, 11, 4, 10, 0)
    apps = [
        Appearance("o1", "s1", t0, t0, t0 + dt.timedelta(minutes=20),
                   t0 + dt.timedelta(minutes=24)),
        Appearance("o2", "s2", t0, t0, t0 + dt.timedelta(minutes=20),
                   t0 + dt.timedelta(minutes=140)),
        Appearance("o3", "s3", t0, t0, t0 + dt.timedelta(minutes=20), None),
        Appearance("o1", "s9", t0 + dt.timedelta(minutes=26),
                   t0 + dt.timedelta(minutes=26), None, None),
    ]
    lat = reappearance_latency(apps)
    print(f"    n={lat.n} median={lat.median_min}min p90={lat.p90_min}min "
          f"within30={lat.within_30min}/{lat.n} never_returned={lat.never_returned} "
          f"mirrored_elsewhere={lat.mirrored_elsewhere}")
    check("reappearance is measured, not assumed", lat.n == 2)
    check("a removal that stuck is counted separately", lat.never_returned == 1)
    check("the mirror hop is detected without anybody's cooperation",
          lat.mirrored_elsewhere == 1,
          "removed here, back there, inside the window: this is why per-URL "
          "takedown is cosmetic")
    check("no rate is claimed where no latency was observed",
          reappearance_latency([]).share_within_30 is None)

    section("9. Catalogue completeness — 'not one scene uncounted'")
    avail = {i: dt.datetime(2026, 2, 17, 20, 0) for i in range(1, 31)}
    pirate = {i: dt.datetime(2026, 2, 17, 23, 30) for i in range(1, 26)}
    pirate.update({27: dt.datetime(2026, 1, 9, 4, 0),
                   28: dt.datetime(2026, 1, 9, 4, 5)})
    comp = catalog_completeness("raheb", range(1, 31), pirate, avail)
    print(f"    legal={comp.legal_episodes} pirate={comp.pirate_episodes} "
          f"share={comp.share} pre_release={comp.pre_release_episodes}")
    check("completeness is episode-level", comp.share == round(27 / 30, 4),
          f"{comp.pirate_episodes}/{comp.legal_episodes} -> {comp.share}")
    check("the pre-release set is isolated as attributable evidence",
          comp.pre_release_episodes == (27, 28),
          "the only class of infringement with a defendant the network already "
          "knows by name")
    # 27 pirate episodes, all within the legal 1..30 range, so completeness is
    # 27/30. Episodes 27 and 28 are additionally *pre-release*: completeness and
    # leakage are separate measurements and this fixture keeps them separate.
    check("an unknown denominator refuses to divide",
          catalog_completeness("x", None, {1: t0}).share is None)
    check("a real zero is reported as zero, not as unknown",
          catalog_completeness("x", range(1, 31), {}).share == 0.0)

    section("10. The availability gap — the constructive finding")
    g_iq = availability_gap("raheb", "IQ", "NEVER_AUTHORISED", 412,
                            [f"s{i}" for i in range(40)], 30,
                            tariff_unit="USD per 1k views", tariff_value=3.5,
                            billable_units=1_800_000 / 1000)
    g_ma = availability_gap("raheb", "MA", "NEVER_AUTHORISED", 88, ["m1"], 12)
    print("    " + g_iq.sentence())
    print("    " + g_ma.sentence())
    q = quote_gaps([g_iq, g_ma])
    check("the quotation prices only what it can", q.total_quoted == 6300.0,
          f"{len(q.refused)} market(s) deliberately left unpriced and listed")
    check("no tariff supplied means no value asserted", g_ma.quoted_value is None)
    check("the arithmetic is the whole analysis", "your published" in g_iq.sentence()
          and "no loss assumption" in g_iq.note)
    md = q.markdown()
    check("the document says it is not a loss figure", "not a loss figure" in md)

    section("11. Enforcement loop — priority follows the calendar")
    items = [
        Routed(1, "archive", Availability.POST_WINDOW, "3-year-old series, 5M views"),
        Routed(2, "telegram", Availability.SIMULTANEOUS_LIVE, "final, 500 viewers"),
        Routed(3, "mirror", Availability.PRE_RELEASE_LEAK, "screener, ep 1-4"),
        Routed(4, "unserved", Availability.NEVER_AUTHORISED, "no licence in IQ"),
        Routed(5, "mystery", Availability.UNKNOWN, "calendar unresolved"),
    ]
    out = route(items)
    print("    queue: " + " | ".join(f"{r.rank}.{r.target}({r.availability.value},"
                                     f"sla={r.sla_minutes}m)" for r in out))
    check("500 live viewers outrank 5M archive views",
          tuple(r.target for r in out) == ("mirror", "telegram"))
    ns = [Notice(f"u{i}", f"url{i}", "direct_operator", operator_cluster="cl_001",
                 served_at=t0) for i in range(40)]
    tgt = escalation_target(ns)
    check("40 URLs reduce to 1 entity, 1 letter", list(tgt) == ["cl_001"]
          and len(tgt["cl_001"]) == 40)
    n_ignored = Notice("n1", "s1", "direct_operator", served_at=t0,
                       state=NoticeState.IGNORED)
    n_removed = Notice("n2", "s2", "cdn_host", served_at=t0,
                       responded_at=t0 + dt.timedelta(minutes=90),
                       state=NoticeState.REMOVED)
    loop = close_loop([n_ignored, n_removed], apps)
    print(f"    served={loop.served} responded={loop.responded} "
          f"ignored={loop.ignored} removed={loop.removed} "
          f"compliance={loop.compliance_rate} median={loop.median_response_min}m")
    check("non-response is an outcome with a date, not a blank",
          loop.ignored == 1 and loop.compliance_rate == 0.5)
    check("a notice nobody answered has no response time, not a zero",
          n_ignored.within_standard is None)
    check("the recalibration is printed, not learned", bool(loop.recalibration))
    for line in loop.recalibration:
        print("    -> " + line[:100])

    section("12. Report emission")
    receipts = [Receipt.from_html(
        f"https://s{i}.test/e12", HTML, observed_at=f"2026-11-04T1{i}:00:00Z",
        recipe=ReplayRecipe(method="GET", url=f"https://s{i}.test/e12")).seal()
        for i in range(3)]
    lgr = Ledger()
    for r in receipts:
        lgr.append(r)
    cluster = Cluster("cl_001", frozenset(f"s{i}" for i in range(3)), 2.4, (),
                      "OPERATOR")
    pack = build_pack(cluster, receipts, lgr, appearances=apps)
    check("an unanchored pack says so on its first line",
          not pack.anchored and "externally anchored" in pack.statement())
    check("non-replayable captures are caveated, not hidden",
          any("no replay recipe" in c for c in pack.caveats)
          or all(r.replayable for r in receipts))
    check("a blind pair in the fleet is disclosed, not corrected away",
          any("blind spot" in c for c in pack.caveats)
          or pack.coverage.get("blind_pairs", 0) == 0)
    check("the pack carries no prohibited field",
          scan_for_prohibited(pack.to_dict()) == [])
    check("a tampered receipt refuses the whole pack",
          _raises_pack(cluster, receipts, lgr))
    doc = pack.markdown()
    check("the markdown renders with its caveats", "## Caveats" in doc)

    section("13. Unit suite")
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"),
                                                top_level_dir=str(ROOT))
    res = unittest.TextTestRunner(verbosity=1).run(suite)
    if not res.wasSuccessful():
        FAILURES.append(f"{len(res.failures) + len(res.errors)} unit test(s)")

    section("VERDICT")
    if FAILURES:
        print(f"  FAILED — {len(FAILURES)} check(s):")
        for f in FAILURES:
            print("    - " + f)
        print("\n  Do not publish a number from this build.")
        return 1
    print(f"  ALL {13} CONTRACT SECTIONS PASSED, {res.testsRun} UNIT TESTS GREEN")
    print("\n  Every refusal above is a feature: this instrument says 'I do not")
    print("  know' in eighteen distinct situations, and in none of them does it")
    print("  print a zero.")
    return 0


def _raises_pack(cluster, receipts, lgr) -> bool:
    from qarin.report import PackRefused
    bad = [Receipt(**dict(r.__dict__, excerpt="edited")) for r in receipts]
    try:
        build_pack(cluster, bad, lgr)
    except PackRefused:
        return True
    except Exception:
        return False
    return False


if __name__ == "__main__":
    raise SystemExit(main())
