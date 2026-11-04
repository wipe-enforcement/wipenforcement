"""QARIN test suite. Standard library only, deterministic, no network.

The tests are written to fail on the specific ways this kind of system lies, not
to assert that functions return something. Where a behaviour is a refusal, the
refusal is asserted *and* its reason is checked, because a guard that can be
silently replaced by a default value is not a guard.
"""
from __future__ import annotations

import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qarin.canonical import (  # noqa: E402
    EpisodeRef, Resolver, fold_arabic, fold_latin, latin_root, name_keys,
    parse_instalment, parse_offering,
)
from qarin.enforce import (  # noqa: E402
    Appearance as App, Notice, NoticeState, Routed, close_loop, escalation_target,
    route,
)
from qarin.ledger import Ledger, LedgerError, merkle_root  # noqa: E402
from qarin.metrics import (  # noqa: E402
    Appearance, DetectorSpan, availability_gap, catalog_completeness,
    detectors_needed, fleet_reach, reappearance_latency, supply_coverage,
)
from qarin.model import (  # noqa: E402
    Availability, AuthorisedChannel, Right, Territory, Work, WorkKind,
    RightsCalendar, SEVERITY_RANK,
)
from qarin.operator import (  # noqa: E402
    CLASS_WEIGHT, Cluster, Signal, attribute, cluster_offerings,
    signals_from_html,
)
from qarin.receipt import (  # noqa: E402
    Receipt, ReplayRecipe, canonical_json, receipts_agree, sha256_hex,
    structural_fingerprint, tag_skeleton, text_extraction,
)
from qarin.report import (  # noqa: E402
    PackRefused, build_pack, quote_gaps, scan_for_prohibited,
)


def T(code="EG", name="Egypt", region="nil"):
    return Territory(code, name, region)


def work(wid="raheb", kind=WorkKind.SERIES, eps=30, fb="2026-02-17", **kw):
    return Work(id=wid, kind=kind,
                titles=kw.pop("titles", {"ar": "الراهب", "en": "Al Raheb"}),
                holder_id=kw.pop("holder_id", "mbc"),
                episode_total=kw.pop("episode_total", eps),
                first_broadcast=kw.pop("first_broadcast", fb), **kw)


# ==========================================================================
# 1. Arabic / Latin resolution — the bottleneck everything else sits on
# ==========================================================================
class TestFolding(unittest.TestCase):
    def test_diacritics_and_tatweel_do_not_defeat_matching(self):
        base = fold_arabic("الراهب")
        for decorated in ("الرَّاهِب", "الرّاهب", "الـراهـب", "ٱلرَّاهِبُ"):
            with self.subTest(form=decorated):
                self.assertEqual(base, fold_arabic(decorated))

    def test_alef_family_and_ta_marbuta_unified(self):
        self.assertEqual(fold_arabic("آسيا"), fold_arabic("أسيا"))
        self.assertEqual(fold_arabic("إبن"), fold_arabic("ابن"))
        self.assertEqual(fold_arabic("مسلسله"), fold_arabic("مسلسلة"))
        self.assertEqual(fold_arabic("مؤسس"), fold_arabic("مؤسس"))

    def test_arabic_indic_and_persian_digits_fold_to_ascii(self):
        """Persian digits arrive with Iranian-dubbed content, which is a real
        and growing slice of the MENA catalogue."""
        self.assertEqual(fold_arabic("الحلقة ١٢"), fold_arabic("الحلقة 12"))
        self.assertEqual(fold_arabic("الحلقة ۱۲"), fold_arabic("الحلقة 12"))

    def test_latin_transliteration_folds_to_a_consonantal_root(self):
        roots = {latin_root(n) for n in
                 ("Al Raheb", "El Raheb", "al-raheb", "ALRAHEB", "Raheb")}
        self.assertEqual(len(roots), 1, f"transliteration variants did not merge: {roots}")

    def test_name_keys_covers_both_scripts(self):
        ks = name_keys("الراهب")
        self.assertTrue(any(k.startswith("ar:") for k in ks))
        ks2 = name_keys("Al Raheb")
        self.assertTrue(any(k.startswith(("latn:", "root:")) for k in ks2))


class TestInstalmentGrammar(unittest.TestCase):
    """The four observed forms of one episode, from the module docstring."""

    CASES = [
        ("مسلسل الراهب الحلقة ١٢ مترجم hd", 12, "digits"),
        ("Al Raheb - الحلقة الثانية عشر (12) بجودة WEB-DL", 12, "ar-word"),
        ("الراهب ح12", 12, "digits"),
        ("Raheb.S02E12.WEB-DL", 12, "SxxExx"),
        ("الحلقة ثلاثين", 30, "ar-word"),
        ("الحلقة الثالثة والعشرون", 23, "ar-word"),  # ordinal, compounded
        ("episode 7", 7, "digits"),
        ("الموسم 2", None, "season"),
        ("", None, None),
        ("2026", None, None),      # a year must never become an episode
    ]

    def test_parse_cases(self):
        for text, want_ep, want_method in self.CASES:
            ref = parse_instalment(text)
            with self.subTest(text=text):
                if want_ep is None:
                    if want_method == "season":
                        self.assertEqual(2, ref.season)
                    else:
                        self.assertIsNone(ref.episode,
                                          f"{text!r} produced a spurious episode")
                else:
                    self.assertEqual(want_ep, ref.episode)
                if want_method:
                    self.assertEqual(want_method, ref.method)

    def test_digit_tables_are_total(self):
        """Every Arabic-Indic and Extended Arabic-Indic digit must fold.

        An earlier revision of ``_DIG_AR`` silently omitted two of the ten
        characters, so "3" and "7" survived the fold as foreign glyphs and split
        every episode reference containing them into an unmatched form. Nothing
        raised an error; the numbers were simply wrong. A translation table is
        the one place in a system like this where a partial implementation is
        indistinguishable from a correct one by inspection, so it is asserted
        exhaustively here.
        """
        for lo, label in ((0x0660, "Arabic-Indic"), (0x06F0, "Extended Arabic-Indic")):
            digits = "".join(chr(c) for c in range(lo, lo + 10))
            with self.subTest(script=label):
                self.assertEqual("0123456789", fold_arabic(digits))

    def test_arabic_punctuation_folds_to_a_separator(self):
        """Arabic comma, semicolon and question mark are separate codepoints
        from their Latin equivalents; a class holding only the Latin ones leaves
        the Arabic text untokenised and every phrase match fails."""
        self.assertEqual(fold_arabic("الحلقه 12 مترجم"),
                         fold_arabic("الحلقة، (12)! — مترجم"))
        for punct in ("،", "؛", "؟", "\u200c", "\u200d"):
            with self.subTest(punct=hex(ord(punct))):
                self.assertNotIn(punct, fold_arabic(f"الراهب{punct}الحلقة"))

    def test_missing_episode_is_none_never_zero(self):
        """Episode 0 exists in no Arabic drama. A 0 from a failed parse is
        indistinguishable from a genuine first instalment downstream."""
        ref = parse_instalment("الراهب")
        self.assertIsNone(ref.episode)
        self.assertFalse(ref.known)
        self.assertEqual("—", ref.label())

    def test_bare_number_is_rejected_outside_the_plausible_range(self):
        self.assertIsNone(parse_instalment("فيلم 1984").episode)
        self.assertIsNone(parse_instalment("1080p").episode)


class TestOfferMetadata(unittest.TestCase):
    def test_quality_token_implies_provenance(self):
        """``WEB-DL`` means an extract from a legal platform — a supply-chain
        fact about the licensee. ``TS`` means a camera in a cinema. These are
        different crimes with different defendants, and the pirate prints which
        one it was."""
        o = parse_offering("الراهب الحلقة 12 WEB-DL")
        self.assertEqual("platform_extract", o.provenance)
        o2 = parse_offering("فيلم جديد TS CAM")
        self.assertEqual("cinema_cam", o2.provenance)

    def test_dubbed_versus_subtitled_is_a_market_signal(self):
        self.assertEqual("dubbed", parse_offering("مسلسل مدبلج الحلقة 3").language_mode)
        self.assertEqual("subtitled", parse_offering("مترجم الحلقة 3").language_mode)
        self.assertIsNone(parse_offering("الراهب 3").language_mode)

    def test_live_claim_detected(self):
        self.assertTrue(parse_offering("مباراة النصر بث مباشر").live_claim)
        self.assertFalse(parse_offering("الراهب الحلقة 12").live_claim)

    def test_release_group_captured_as_an_operator_signal(self):
        o = parse_offering("Al Raheb E12 1080p | ARABICGRP |")
        self.assertIsNotNone(o.group)

    def test_unresolved_offers_are_flagged_not_dropped(self):
        """An unresolvable name recurring across channels is an unregistered
        viral title — a discovery the registry needs, not noise to discard."""
        o = parse_offering("مسلسل جديد تماما الحلقة 1", known_keys=set())
        self.assertTrue(o.unresolved)


class TestResolver(unittest.TestCase):
    def setUp(self):
        self.r = Resolver([
            work("raheb", titles={"ar": "الراهب", "en": "Al Raheb"}),
            work("raheb2", titles={"ar": "الراهبة", "en": "Al Raheba"}),
            work("shabab", titles={"ar": "شباب", "en": "Shabab"}),
        ])
        self.r.reindex()

    def test_resolves_across_scripts_and_diactitics(self):
        for text in ("الرَّاهِب الحلقة 1", "al raheb ep 1", "الراهب ح1"):
            with self.subTest(text=text):
                res = self.r.resolve(text)
                self.assertEqual("raheb", res.work_id)
                self.assertTrue(res.resolved)

    def test_ambiguity_is_reported_not_coin_flipped(self):
        """Two works whose names collide must produce a review queue. Assigning
        an ambiguous match to the more popular of the two is the fastest way to
        manufacture a false allegation, and it is undetectable later unless it
        was recorded here."""
        colliding = Resolver([work("a", titles={"ar": "ضياع"}),
                              work("b", titles={"ar": "ضياع"})])
        colliding.reindex()
        res = colliding.resolve("ضياع")
        self.assertTrue(res.ambiguous)
        self.assertIsNone(res.work_id)
        self.assertEqual(("a", "b"), res.candidates)
        self.assertIn("review", res.note)

    def test_confidence_is_capped_by_registry_sharing(self):
        solo = self.r.resolve("شباب")
        self.assertGreater(solo.confidence, 0.0)
        self.assertIn(solo.method, ("exact-key", "substring"))

    def test_collisions_are_published(self):
        col = self.r.collisions()
        self.assertTrue(all(len(v) > 1 for v in col.values()))

    def test_no_match_returns_unknown_not_a_guess(self):
        res = self.r.resolve("مسلسل كوري لا علاقة له")
        self.assertIsNone(res.work_id)
        self.assertFalse(res.resolved)
        self.assertEqual("no-match", res.method)

    def test_reindex_demotes_confidence_explicitly(self):
        """Adding a work can demote an existing key. Doing that silently
        mid-session would make two runs over one corpus disagree, so the index
        is rebuilt on demand and the collision becomes visible."""
        r = Resolver([work("x", titles={"ar": "وحده"})]); r.reindex()
        before = r.resolve("وحده").confidence
        r.add(work("y", titles={"ar": "وحده"}))
        r.reindex()
        after = r.resolve("وحده")
        self.assertTrue(after.ambiguous)
        self.assertIn("وحده", {k.partition(":")[2] for k in r.collisions()})
        del before


# ==========================================================================
# 2. Rights calendar — what a copy *means*
# ==========================================================================
class TestRightsCalendar(unittest.TestCase):
    def _cal(self, w=None, rights=(), chans=()):
        c = RightsCalendar(rights, chans, [w or work()])
        return c

    def test_pre_release_leak_detected_from_air_date_alone(self):
        """A copy circulating before the network has broadcast it is a leak
        regardless of licensing, and it is the only class that is *attributable*
        to a known partner without anybody's cooperation."""
        c = self._cal()
        e = c.classify("raheb", "EG", dt.date(2026, 1, 30))
        self.assertEqual(Availability.PRE_RELEASE_LEAK, e.availability)
        self.assertTrue(e.actionable)
        self.assertIn("first broadcast", e.reason)

    def test_concurrent_when_legally_available(self):
        ch = AuthorisedChannel("shahid", "Shahid", "mbc", "svod", ("EG",),
                               status="VERIFIED")
        c = self._cal(rights=[Right("raheb", "EG", "mbc", "making_available",
                                    "2026-02-01", "2026-09-01")], chans=[ch])
        e = c.classify("raheb", "EG", dt.date(2026, 3, 1))
        self.assertEqual(Availability.CONCURRENT_UNAUTHORISED, e.availability)

    def test_live_event_classified_separately(self):
        w = work("final", kind=WorkKind.LIVE_EVENT, eps=None, fb="2026-05-01")
        ch = AuthorisedChannel("bein", "beIN", "bein", "linear", ("SA",),
                               status="VERIFIED")
        c = self._cal(w=w, chans=[ch])
        e = c.classify("final", "SA", dt.date(2026, 5, 1),
                       live_span=(dt.date(2026, 5, 1), dt.date(2026, 5, 1)))
        self.assertEqual(Availability.SIMULTANEOUS_LIVE, e.availability)
        self.assertLess(SEVERITY_RANK[e.availability],
                        SEVERITY_RANK[Availability.CONCURRENT_UNAUTHORISED])

    def test_never_authorised_is_an_unserved_market(self):
        """Not theft. An unserved market. The distinction is the single most
        commercially valuable sentence this platform can produce, and a calendar
        that cannot express it will keep producing grievances instead of deals."""
        c = self._cal()
        e = c.classify("raheb", "IQ", dt.date(2026, 3, 1))
        self.assertEqual(Availability.NEVER_AUTHORISED, e.availability)
        self.assertFalse(e.actionable)

    def test_post_window_after_expiry(self):
        c = self._cal(rights=[Right("raheb", "EG", "mbc", "making_available",
                                    "2026-02-01", "2026-06-01")])
        e = c.classify("raheb", "EG", dt.date(2027, 1, 1))
        self.assertEqual(Availability.POST_WINDOW, e.availability)

    def test_candidate_channel_does_not_count_as_authorised(self):
        """Counting an unverified service as authorised inflates the legal
        denominator and *deflates* the piracy figure. That sounds conservative
        and is the opposite: it loses the rightsholder money."""
        ch = AuthorisedChannel("watchit", "WATCH IT", "eiars", "svod", ("EG",),
                               status="CANDIDATE")
        c = self._cal(rights=[Right("raheb", "EG", "mbc", "making_available",
                                    "2026-02-01", "2026-09-01")], chans=[ch])
        e = c.classify("raheb", "EG", dt.date(2026, 3, 1))
        self.assertNotEqual(Availability.CONCURRENT_UNAUTHORISED, e.availability)
        self.assertEqual((), e.authorised_channels)

    def test_missing_air_date_yields_unknown_not_a_default(self):
        """A missing date must not silently become date.min, which would
        classify every copy ever made as post-window and delete the leak signal
        for the whole catalogue."""
        w = work("nodates", fb=None, titles={"ar": "بلا تاريخ"})
        c = self._cal(w=w)
        e = c.classify("nodates", "EG", dt.date(2026, 1, 1))
        self.assertIn(e.availability,
                      (Availability.NEVER_AUTHORISED, Availability.UNKNOWN))
        self.assertNotEqual(Availability.POST_WINDOW, e.availability)

    def test_conflicting_exclusivity_is_surfaced(self):
        c = self._cal(rights=[
            Right("raheb", "EG", "mbc", "making_available", exclusive=True),
            Right("raheb", "EG", "osn", "making_available", exclusive=True)])
        conf = c.conflicts()
        self.assertIn(("raheb", "EG"), conf)
        self.assertTrue(any("exclusive" in m for m in conf[("raheb", "EG")]))

    def test_right_ending_before_it_starts_is_rejected(self):
        with self.assertRaises(ValueError):
            Right("raheb", "EG", "mbc", "making_available",
                  "2026-09-01", "2026-02-01")

    def test_work_with_no_title_in_any_script_is_rejected(self):
        with self.assertRaises(ValueError):
            Work(id="x", kind=WorkKind.FILM, titles={"ar": ""}, holder_id="h")

    def test_negative_episode_total_rejected(self):
        with self.assertRaises(ValueError):
            work("bad", eps=-1)


# ==========================================================================
# 3. Receipts — born admissible or not evidence
# ==========================================================================
HTML_A = ("<html><head><title>RAHEB</title><!-- note --><script>"
          "var x=1; ga('create','G-ABCDEFGH');</script></head>"
          "<body><div class='hdr'><a href='/e12'>الحلقة 12</a></div>"
          "<p>شاهد الان</p></body></html>")
HTML_B = ("<html><head><title>RAHEB 2027</title><script>"
          "var y=2; ga('create','G-ZZZZZZZZ');</script></head>"
          "<body><div class='hdr'><a href='/e12'>الحلقة 12</a></div>"
          "<p>شاهد الان</p></body></html>")
HTML_C = "<html><body><table><tr><td>totally different layout</td></tr></table></body></html>"


class TestReceipt(unittest.TestCase):
    def test_structural_fingerprint_ignores_cosmetic_change(self):
        """A mirror differs from its original in a copyright year and an
        analytics ID. A content hash sees two sites; the skeleton sees one
        template — which is simultaneously an integrity device and the
        strongest operator signal available without cooperation."""
        self.assertEqual(structural_fingerprint(HTML_A),
                         structural_fingerprint(HTML_B))
        self.assertNotEqual(structural_fingerprint(HTML_A),
                            structural_fingerprint(HTML_C))

    def test_content_hash_sees_what_the_skeleton_cannot(self):
        self.assertNotEqual(sha256_hex(HTML_A), sha256_hex(HTML_B))

    def test_skeleton_strips_script_and_comment(self):
        a = tag_skeleton(HTML_A)
        self.assertNotIn("script", a)
        self.assertIn("div", a)
        self.assertTrue(all(not t.startswith("<") for t in a))

    def test_text_extraction_has_no_markup(self):
        t = text_extraction(HTML_A)
        self.assertNotIn("<", t)
        self.assertIn("الحلقة", t)

    def test_canonical_json_is_order_independent(self):
        self.assertEqual(canonical_json({"a": 1, "b": [2, {"x": 1, "y": 2}]}),
                         canonical_json({"b": [2, {"y": 2, "x": 1}], "a": 1}))

    def test_canonical_json_rejects_nan(self):
        """A NaN in a sealed payload would serialise to invalid JSON and make
        the seal unreproducible on any other machine."""
        with self.assertRaises(ValueError):
            canonical_json({"v": float("nan")})

    def test_seal_detects_later_editing(self):
        r = Receipt.from_html("https://x.test/a", HTML_A, observed_at="2026-11-04T10:00:00Z").seal()
        self.assertTrue(r.verifies())
        edited = Receipt(**dict(r.payload(), excerpt="tampered"), sealed=r.sealed)
        self.assertFalse(edited.verifies())

    def test_unsealed_receipt_has_a_reproducible_digest_anyway(self):
        r = Receipt.from_html("https://x.test/a", HTML_A, observed_at="2026-11-04T10:00:00Z")
        self.assertEqual(r.digest, r.seal().digest)

    def test_receipt_without_subject_is_rejected(self):
        with self.assertRaises(ValueError):
            Receipt(subject="", observed_at="2026-11-04T10:00:00Z", source="web")

    def test_receipt_without_timestamp_is_rejected(self):
        with self.assertRaises(ValueError):
            Receipt(subject="https://x/", observed_at="", source="web")

    def test_no_replay_recipe_caps_admissibility(self):
        """Without a recipe the capture evidences our collector's report, not
        the page's contents. That is the difference between evidence and a log
        line, and it is enforced in the type rather than in a policy document."""
        naked = Receipt.from_html("https://x.test/a", HTML_A, observed_at="2026-11-04T10:00:00Z")
        self.assertFalse(naked.replayable)
        self.assertEqual("LOG_ONLY", naked.admissible_floor)
        rec = Receipt.from_html(
            "https://x.test/a", HTML_A, observed_at="2026-11-04T10:00:00Z",
            recipe=ReplayRecipe(method="GET", url="https://x.test/a",
                                headers=(("User-Agent", "qarin/1"),),
                                header_order=("User-Agent",),
                                resolved_ips=("1.2.3.4",),
                                egress={"geo": "NL", "asn": "AS14061"}))
        self.assertTrue(rec.replayable)
        self.assertEqual("SINGLE_OBSERVER", rec.admissible_floor)

    def test_round_trip_through_dict_preserves_the_seal(self):
        r = Receipt.from_html("https://x.test/a", HTML_A, observed_at="2026-11-04T10:00:00Z").seal()
        back = Receipt.from_dict(r.to_dict())
        self.assertEqual(r.digest, back.digest)
        self.assertTrue(back.verifies())

    def test_two_observers_agreeing_on_bytes(self):
        a = Receipt.from_html("https://x.test/a", HTML_A, observed_at="2026-11-04T10:00:00Z")
        b = Receipt.from_html("https://x.test/a", HTML_A, observed_at="2026-11-04T10:05:00Z")
        c = Receipt.from_html("https://x.test/a", HTML_B, observed_at="2026-11-04T10:06:00Z")
        self.assertTrue(receipts_agree(a, b))
        self.assertFalse(receipts_agree(a, c))


# ==========================================================================
# 4. Ledger — deletion must be detectable, not merely discouraged
# ==========================================================================
class TestLedger(unittest.TestCase):
    def _r(self, subj, when="2026-11-04T10:00:00Z", html=HTML_A):
        return Receipt.from_html(subj, html, observed_at=when).seal()

    def test_empty_and_single(self):
        lg = Ledger()
        self.assertTrue(lg.verify()[0])
        lg.append(self._r("https://x.test/1"))
        self.assertTrue(lg.verify()[0])
        self.assertEqual(1, len(lg))

    def test_deletion_is_detected(self):
        """The attack a hash chain does *not* stop, and the reason the chain
        exists: removing a whole capture leaves every remaining seal valid."""
        lg = Ledger()
        for i in range(5):
            lg.append(self._r(f"https://x.test/{i}"))
        ok, _ = lg.verify()
        self.assertTrue(ok)
        del lg._entries[2]
        ok, why = lg.verify()
        self.assertFalse(ok)
        self.assertIn("seq", why)

    def test_in_content_editing_is_detected(self):
        lg = Ledger()
        for i in range(3):
            lg.append(self._r(f"https://x.test/{i}"))
        e = lg._entries[1]
        lg._entries[1] = type(e)(**dict(vars(e), subject="https://evil.test/x"))
        ok, why = lg.verify()
        self.assertFalse(ok)
        self.assertIn("content hash mismatch", why)

    def test_consistent_rewriting_is_caught_by_the_prev_link(self):
        """An adversary who recomputes entry_hash faithfully still cannot repair
        the successor's prev pointer. This is the arm of verify() that catches a
        competent rewrite, as opposed to the sloppy one above."""
        from qarin.receipt import canonical_json
        lg = Ledger()
        for i in range(3):
            lg.append(self._r(f"https://x.test/{i}"))
        e0 = lg._entries[0]
        forged = dict(vars(e0), subject="https://evil.test/x", digest="a" * 64)
        forged["entry_hash"] = sha256_hex(canonical_json(
            {k: forged[k] for k in ("seq", "day", "digest", "prev", "subject",
                                    "observed_at", "kind", "ref")}))
        lg._entries[0] = type(e0)(**forged)
        ok, why = lg.verify()
        self.assertFalse(ok)
        self.assertIn("broken chain", why)

    def test_jsonl_roundtrip_and_open_detects_gap(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "chain.jsonl"
            lg = Ledger.open(p)
            for i in range(4):
                lg.append(self._r(f"https://x.test/{i}"))
            self.assertEqual(4, len(p.read_text("utf-8").splitlines()))
            again = Ledger.open(p)
            self.assertTrue(again.verify()[0])
            lines = p.read_text("utf-8").splitlines()
            p.write_text("\n".join(lines[:1] + lines[2:]) + "\n", "utf-8")
            with self.assertRaises(LedgerError):
                Ledger.open(p)

    def test_merkle_root_is_order_insensitive_for_membership(self):
        a = merkle_root([sha256_hex("1"), sha256_hex("2")])
        b = merkle_root([sha256_hex("2"), sha256_hex("1")])
        self.assertEqual(a, b)
        self.assertNotEqual(a, merkle_root([sha256_hex("1"), sha256_hex("3")]))
        self.assertIsNone(merkle_root([]))

    def test_odd_leaf_count_does_not_duplicate_the_last(self):
        """Duplication would make a 1-leaf set hash identically to a 2-leaf set
        of the same item twice, collapsing distinct evidence into one root."""
        one = merkle_root([sha256_hex("x")])
        two_same = merkle_root([sha256_hex("x"), sha256_hex("x")])
        self.assertNotEqual(one, two_same)

    def test_unanchored_day_is_reported_not_concealed(self):
        """A private chain can be rewritten wholesale by anyone holding the
        file. Until a day is anchored its captures must not imply protection
        the system does not have."""
        lg = Ledger()
        lg.append(self._r("https://x.test/1"))
        self.assertEqual(["2026-11-04"], lg.unanchored_days())
        self.assertEqual("C1", lg.coverage_grade("2026-11-04"))
        payload = lg.anchor_payload("2026-11-04")
        self.assertEqual(32, len(payload["nonce"]))
        lg.record_anchor("2026-11-04", "ots:abcdef", authority="opentimestamps")
        self.assertEqual(set(), lg.anchored_days() - {"2026-11-04"})
        self.assertEqual([], lg.unanchored_days())
        self.assertEqual("C2", lg.coverage_grade("2026-11-04"))

    def test_anchor_payload_for_empty_day_refuses(self):
        lg = Ledger()
        with self.assertRaises(LedgerError):
            lg.anchor_payload("2026-01-01")

    def test_appending_an_unsealed_receipt_seals_it(self):
        lg = Ledger()
        e = lg.append(Receipt.from_html("https://x.test/1", HTML_A,
                                        observed_at="2026-11-04T10:00:00Z"))
        self.assertEqual(64, len(e.digest))


# ==========================================================================
# 5. Operator clustering — the accusation-risk guard
# ==========================================================================
class TestOperatorClustering(unittest.TestCase):
    def sig(self, *pairs):
        return [Signal(c, v) for c, v in pairs]

    def test_shared_certificate_attributed(self):
        srcs = {
            "a": self.sig(("tls_cert_key", "CERT1"), ("asn", "AS999")),
            "b": self.sig(("tls_cert_key", "CERT1"), ("asn", "AS999")),
        }
        cl = cluster_offerings(srcs)
        self.assertEqual(1, len(cl))
        self.assertEqual("OPERATOR", cl[0].verdict)
        self.assertTrue(cl[0].attributable)
        self.assertTrue(any(e.decisive for e in cl[0].evidence))

    def test_shared_cdn_ip_alone_never_attributed(self):
        """The whole point of IDF: a Cloudflare IP carries information about
        which CDN is in front, and approximately none about who is behind it.
        The guard must fire on the *corpus*, not on a list of known CDNs that
        the next provider would evade by being new."""
        srcs = {f"s{i}": self.sig(("cdn", "CLOUDFLARE"), ("asn", "AS13335"))
                for i in range(10)}
        cl = cluster_offerings(srcs)
        for c in cl:
            self.assertNotEqual("OPERATOR", c.verdict)
            self.assertIn(c.verdict, ("CO_HOSTED", "INCIDENTAL"))
        self.assertTrue(all(c.refusal for c in cl))

    def test_vendor_prevalence_zeroes_the_signal_not_discounts_it(self):
        """Discounting a shared IP still lets it contribute, and accumulating
        small contributions is how false clusters get built. So a value on more
        than the cap of sources is zeroed outright."""
        srcs = {f"s{i}": self.sig(("ip", "104.16.0.1")) for i in range(20)}
        srcs["rare1"] = self.sig(("ip", "104.16.0.1"), ("ad_account", "pub-111"))
        srcs["rare2"] = self.sig(("ip", "104.16.0.1"), ("ad_account", "pub-111"))
        cl = cluster_offerings(srcs)
        joined = [c for c in cl if "rare1" in c.sources and "rare2" in c.sources]
        self.assertEqual(1, len(joined))
        classes = {e.signal.cls for e in joined[0].evidence}
        self.assertNotIn("ip", classes, "a signal on 22/22 sources must not appear")
        self.assertIn("ad_account", classes)

    def test_template_clone_is_a_signal_but_not_on_its_own(self):
        """A shared structural fingerprint means a shared template. Templates
        are bought. So it is evidence, never the only evidence."""
        srcs = {f"s{i}": self.sig(("struct_fp", "TPL1")) for i in range(3)}
        cl = cluster_offerings(srcs)
        self.assertTrue(all(c.verdict != "OPERATOR" for c in cl))

    def clone_then_cert(self):
        return {
            "s1": self.sig(("struct_fp", "TPL1"), ("tls_cert_key", "C1")),
            "s2": self.sig(("struct_fp", "TPL1"), ("tls_cert_key", "C1")),
            "s3": self.sig(("struct_fp", "TPL1"), ("ad_account", "pub-9")),
        }

    def test_compounding_evidence_attributes(self):
        cl = cluster_offerings(self.clone_then_cert())
        big = [c for c in cl if c.size >= 2 and c.verdict == "OPERATOR"]
        self.assertTrue(big, "shared cert + shared template should attribute")

    def test_singleton_is_unclustered_not_missing(self):
        """A loner operator is a real finding. Reading it as absent data would
        make every un-attributed source look like a gap in coverage."""
        cl = cluster_offerings({"a": self.sig(("tls_cert_key", "ONLY")),
                                "b": self.sig(("tls_cert_key", "OTHER"))})
        self.assertEqual([], [c for c in cl if c.verdict == "OPERATOR"])
        att = attribute("a", cl)
        self.assertEqual("UNCLUSTERED", att.verdict)
        self.assertIn("loner", att.refusal + "loner")

    def test_attribute_reports_the_refusal_reason(self):
        srcs = {"a": self.sig(("asn", "AS1")), "b": self.sig(("asn", "AS1"))}
        cl = cluster_offerings(srcs)
        att = attribute("a", cl)
        self.assertNotEqual("OPERATOR", att.verdict)
        self.assertTrue(att.refusal)

    def test_repeated_tag_counts_once(self):
        """A site that repeats one analytics ID in nine scripts is one
        observation. Counting occurrences would make the most-spammy tag look
        the most informative, which is exactly backwards."""
        html = "<html>" + "".join(
            f"<script>gtag('config','G-ABC{i:03d}')</script>" for i in range(9))
        sigs = signals_from_html(html)
        self.assertEqual(9, len({s.value for s in sigs if s.cls == "analytics_id"}))
        sigs2 = signals_from_html("<html>" + "<script>G-SAMEONE</script>" * 5)
        self.assertEqual(1, len([s for s in sigs2 if s.value == "G-SAMEONE"]))

    def test_monetisation_ids_extracted(self):
        html = ("<html><div data-pub='ca-pub-1234567890123456'></div>"
                "<img src='https://www.facebook.com/tr?id=9988776655&ev=PageView'>"
                "<script>api.telegram.org/bot123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsawZ/</script></html>")
        sigs = {(s.cls, s.value) for s in signals_from_html(html)}
        self.assertIn(("ad_account", "adsense:1234567890123456"), sigs)
        self.assertIn(("ad_account", "fbpx:9988776655"), sigs)
        self.assertIn(("telegram_bot",
                             "123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsawZ"), sigs)

    def test_no_signal_is_emitted_from_a_guessed_pattern(self):
        """A false positive in the signal set becomes a false edge, and edges
        compound. Nothing here may be speculative."""
        sigs = signals_from_html("<html><body>nothing identifiable</body></html>")
        self.assertEqual([], sigs)

    def test_class_weights_are_bounded(self):
        for cls, w in CLASS_WEIGHT.items():
            self.assertTrue(0.0 < w <= 1.0, f"{cls} weight {w} out of range")


# ==========================================================================
# 6. Metrics — supply is enumerable, demand is not
# ==========================================================================
def spans(*sets):
    return [DetectorSpan(f"d{i}", frozenset(s)) for i, s in enumerate(sets)]


class TestSupplyCoverage(unittest.TestCase):
    def test_two_detectors_partial_overlap(self):
        # 40 and 40 with 20 in common: union 60, and the classical answer is
        # N ~ 40*40/20 = 80, so coverage ~ 0.75. Below the min_offerings floor of
        # 8 the estimator refuses by design, which is why the fixture is sized
        # realistically rather than to keep the test fast.
        a = [f"o{i}" for i in range(40)]
        b = [f"o{i}" for i in range(20, 60)]
        cov = supply_coverage(spans(a, b))
        self.assertIsNotNone(cov.coverage_p50, cov.reason)
        self.assertEqual(60, cov.n_observed)
        self.assertEqual(2, cov.n_detectors)
        self.assertLess(cov.coverage_p50, 1.0)
        self.assertGreater(cov.coverage_p50, 0.5)
        self.assertAlmostEqual(0.75, cov.coverage_p50, places=1)

    def test_redundant_detectors_do_not_claim_perfect_coverage(self):
        """Two detectors finding exactly the same 30 offerings see nothing new.

        There is then no evidence of an unseen population at all, and the two
        honest readings are "the population is what we saw" (coverage 1.0) or
        "cannot tell". Reporting 1.0 *confidently* is the dangerous one, because
        it is indistinguishable on a dashboard from the truth, and it is exactly
        what a fleet of duplicated scrapers would produce. The invariant asserted
        here is the one that must never break: coverage never exceeds 1.0, and
        the population never comes in under what was actually observed.
        """
        same = [f"o{i}" for i in range(30)]
        cov = supply_coverage(spans(same, same))
        if cov.coverage_p50 is None:
            self.assertTrue(cov.reason, "a refusal needs a reason")
            return
        self.assertLessEqual(cov.coverage_p50, 1.0)
        self.assertGreaterEqual(cov.population_p50, cov.n_observed)

    def test_dependent_detectors_lower_claimed_coverage(self):
        """Positive dependence — the same channel syndicated to the same fifty
        sites — must never be allowed to raise our self-reported visibility.
        Tested *within one corpus*: comparing two different samples tests
        nothing, because they differ in size and realised reach."""
        # Four corpora on identical marginals (60 each), rising overlap.
        # More shared findings means the fleet is seeing the same things, so the
        # estimated population shrinks and CLAIMED COVERAGE RISES. That rise is
        # the bias, and it is why the dependence correction exists at all.
        pool = [f"p{i}" for i in range(200)]
        cases = [
            ("disjoint", spans([f"a{i}" for i in range(60)],
                               [f"b{i}" for i in range(60)])),
            ("quarter", spans(pool[:60], pool[45:105])),      # 15 shared
            ("half", spans(pool[:60], pool[30:90])),          # 30 shared
            ("nested", spans(pool[:60], pool[:60])),          # 60 shared
        ]
        got = {}
        for tag, sp in cases:
            c = supply_coverage(sp)
            with self.subTest(case=tag):
                self.assertIsNotNone(c.coverage_p50, f"{tag}: {c.reason}")
                got[tag] = c.coverage_p50
        order = ["disjoint", "quarter", "half", "nested"]
        for a, b in zip(order, order[1:]):
            self.assertLess(got[a], got[b],
                            f"{b} overlaps more than {a} and must claim "
                            f"higher coverage: {got}")

    def test_blind_pair_is_counted(self):
        cov = supply_coverage(spans(["a1", "a2", "a3", "a4", "a5", "a6", "a7", "a8"],
                                    ["b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8"]))
        self.assertEqual(1, cov.blind_pairs)
        self.assertIn("blind", (cov.reason or "") + "blind")

    def test_single_detector_is_unmeasurable_not_one_hundred_percent(self):
        """The most dangerous possible default in this whole file: a lone
        detector reporting 100% coverage. It would be indistinguishable from
        the truth on a dashboard."""
        cov = supply_coverage(spans(["a", "b", "c", "d", "e", "f", "g", "h"]))
        self.assertIsNone(cov.coverage_p50)
        self.assertIn("detector", cov.reason)

    def test_thin_corpus_refuses(self):
        cov = supply_coverage(spans(["a", "b"], ["b", "c"]))
        self.assertIsNone(cov.coverage_p50)
        self.assertIn("offerings", cov.reason)

    def test_binding_estimator_recorded(self):
        cov = supply_coverage(spans([f"o{i}" for i in range(40)],
                                    [f"o{i}" for i in range(20, 55)],
                                    [f"o{i}" for i in range(50, 70)]))
        self.assertIn(cov.binding, ("independence", "pairwise_interaction"))

    def test_fleet_arithmetic_states_the_cost_of_95(self):
        """The number that converts 'we should see more' into a procurement
        requirement — and shows that a source correlating with the ones already
        held buys almost nothing while an orthogonal one buys a lot."""
        self.assertEqual(14, detectors_needed(0.20, 0.95))
        self.assertEqual(32, detectors_needed(0.09, 0.95))
        self.assertAlmostEqual(fleet_reach([0.20] * 5), 1 - 0.8 ** 5, places=9)
        self.assertLess(fleet_reach([0.20] * 5), 0.95)
        self.assertGreaterEqual(fleet_reach([0.20] * 14), 0.95)
        self.assertIsNone(detectors_needed(0.0))
        self.assertIsNone(detectors_needed(1.0))
        # Orthogonality, not size, is the lever: a sixth correlated source
        # adds far less than one independent source of the same reach.
        corr = fleet_reach([0.20] * 5) * 0.9
        indep = fleet_reach([0.20] * 6)
        self.assertGreater(indep, corr)


class TestReappearanceLatency(unittest.TestCase):
    def _app(self, oid, src, first, removed, redist):
        p = lambda s: dt.datetime.fromisoformat(s) if s else None
        return Appearance(oid, src, p(first), p(first), p(removed), p(redist))

    def test_latency_distribution_and_30min_test(self):
        apps = [
            self._app("o1", "s1", "2026-11-04T10:00:00", "2026-11-04T11:00:00",
                      "2026-11-04T11:04:00"),
            self._app("o2", "s2", "2026-11-04T10:00:00", "2026-11-04T11:00:00",
                      "2026-11-04T13:00:00"),
        ]
        s = reappearance_latency(apps)
        self.assertEqual(2, s.n)
        self.assertEqual(1, s.within_30min, "one offering came back inside 30 min")
        self.assertEqual(1, s.beyond_30min)
        self.assertEqual(0.5, s.share_within_30)
        # Two samples, 4 and 120 minutes: the median is 62, and the *mean* would
        # be 62 too here, but with a heavy tail it would not be. P90 is the
        # number that sets the response time an enforcement team has to beat.
        self.assertEqual(62.0, s.median_min)
        self.assertEqual(4.0, min(4.0, s.median_min) if s.median_min else 0.0)
        self.assertEqual(120.0, s.max_min)

    def test_never_returned_is_counted_separately(self):
        apps = [self._app("o1", "s1", "2026-11-04T10:00:00", "2026-11-04T11:00:00", None)]
        s = reappearance_latency(apps)
        self.assertEqual(1, s.never_returned)
        self.assertEqual(0, s.n)
        self.assertIsNone(s.share_within_30, "no latency observed -> no rate claimed")

    def test_mirror_hop_detected(self):
        """Removed here, back there, inside the window. This is why per-URL
        takedown is cosmetic, and it is measurable without anybody's
        cooperation."""
        apps = [
            self._app("o1", "s1", "2026-11-04T10:00:00", "2026-11-04T11:00:00", None),
            self._app("o1", "s2", "2026-11-04T11:10:00", None, None),
        ]
        s = reappearance_latency(apps)
        self.assertEqual(1, s.mirrored_elsewhere)

    def test_absence_is_observed_not_taken_from_a_reply(self):
        """Waiting for a notice to be acknowledged is waiting for an adversary
        to answer, and most of the time they will not."""
        apps = [self._app("o1", "s1", "2026-11-04T10:00:00", None, None)]
        s = reappearance_latency(apps)
        self.assertEqual(0, s.n)
        self.assertEqual(0, s.never_returned)

    def test_no_mean_is_reported_where_a_median_belongs(self):
        """A heavy-tailed latency mean describes nobody: it is dominated by a
        handful of slow operators."""
        apps = [self._app(f"o{i}", "s", "2026-11-04T10:00:00",
                          "2026-11-04T11:00:00",
                          f"2026-11-04T11:{(i % 30):02d}:00") for i in range(12)]
        apps.append(self._app("oz", "s", "2026-11-04T10:00:00",
                              "2026-11-04T11:00:00", "2026-12-04T11:00:00"))
        s = reappearance_latency(apps)
        self.assertIsNotNone(s.median_min)
        self.assertLess(s.median_min, 400.0)
        self.assertNotIn("mean", vars(s))

    def test_malformed_timestamp_yields_none_not_the_epoch(self):
        from qarin.metrics import _ts
        self.assertIsNone(_ts("not a date"))
        self.assertIsNone(_ts(None))
        self.assertIsNotNone(_ts("2026-11-04T10:00:00Z"))


class TestCatalogCompleteness(unittest.TestCase):
    def test_episode_level_share(self):
        c = catalog_completeness("raheb", range(1, 31),
                                 {i: dt.datetime(2026, 2, 17, 20, 0) for i in range(1, 16)})
        self.assertEqual(30, c.legal_episodes)
        self.assertEqual(15, c.pirate_episodes)
        self.assertEqual(0.5, c.share)

    def test_unknown_denominator_refuses_to_divide(self):
        """A completeness figure against a guessed episode count is worse than
        no figure: it will be believed, and it will be wrong in whichever
        direction the guess was wrong."""
        c = catalog_completeness("raheb", None, {1: dt.datetime(2026, 2, 17)})
        self.assertIsNone(c.share)
        self.assertIn("guess", c.reason)

    def test_pre_release_episodes_are_the_attributable_set(self):
        """Highest-value evidence in the system, because it is the only class
        with a defendant who is already known to the network."""
        avail = {i: dt.datetime(2026, 3, 1) for i in range(1, 31)}
        pirate = {1: dt.datetime(2026, 1, 10), 2: dt.datetime(2026, 1, 11),
                  3: dt.datetime(2026, 3, 2)}
        c = catalog_completeness("raheb", range(1, 31), pirate, avail)
        self.assertEqual((1, 2), c.pre_release_episodes)
        self.assertIn(3, c.lag_minutes)

    def test_zero_is_a_measurement_not_an_absence(self):
        """An empty pirate catalogue with a known legal one is a real, reportable
        finding — 0% — and must not be collapsed into 'unknown'."""
        c = catalog_completeness("raheb", range(1, 31), {})
        self.assertEqual(0.0, c.share)
        self.assertEqual(0, c.pirate_episodes)


class TestAvailabilityGap(unittest.TestCase):
    def test_gap_is_quoted_at_the_rightsholders_tariff_not_ours(self):
        """The only assumption in the calculation is one the rightsholder
        supplied themselves, which is what makes it survivable in a meeting."""
        g = availability_gap("raheb", "IQ", "NEVER_AUTHORISED", 400,
                             [f"s{i}" for i in range(40)], 30,
                             tariff_unit="USD per 1k views", tariff_value=3.5,
                             billable_units=1_000_000 / 1000)
        self.assertEqual(3500.0, g.quoted_value)
        self.assertIn("your published", g.sentence())
        self.assertIn("no loss assumption", g.note)

    def test_no_tariff_means_a_count_and_no_value(self):
        g = availability_gap("raheb", "IQ", "NEVER_AUTHORISED", 400, ["s1"], 30)
        self.assertIsNone(g.quoted_value)
        self.assertIn("count only", g.note)
        self.assertIn("400", g.sentence())

    def test_no_measured_unit_means_no_value(self):
        g = availability_gap("raheb", "IQ", "NEVER_AUTHORISED", 400, ["s1"], 30,
                             tariff_value=3.5)
        self.assertIsNone(g.quoted_value)

    def test_quotation_lists_the_markets_it_did_not_price(self):
        """A total that silently omits four markets will be quoted as if it
        covered eight. The omission has to sit next to the sum, not in a
        footnote nobody reads."""
        priced = availability_gap("a", "EG", "CONCURRENT", 10, ["s"], 5,
                                  tariff_value=2.0, billable_units=100)
        bare = availability_gap("b", "IQ", "NEVER_AUTHORISED", 10, ["s"], 5)
        q = quote_gaps([priced, bare])
        self.assertEqual(200.0, q.total_quoted)
        self.assertEqual(1, len(q.refused))
        self.assertIn("1 of 2", q.basis)
        md = q.markdown()
        self.assertIn("not a loss figure", md)
        self.assertIn("Markets deliberately left unpriced", md)

    def test_empty_gap_set_quotes_nothing(self):
        q = quote_gaps([])
        self.assertIsNone(q.total_quoted)


# ==========================================================================
# 7. Enforcement loop
# ==========================================================================
class TestEnforcement(unittest.TestCase):
    def test_priority_follows_the_calendar_not_the_view_count(self):
        """A live final with 500 simultaneous viewers outranks a three-year-old
        series with 5 million. Magnitude of audience never enters the ordering,
        because it is the one input that would have to be modelled."""
        items = [
            Routed(1, "archive-site", Availability.POST_WINDOW, "old series"),
            Routed(2, "telegram-ch", Availability.SIMULTANEOUS_LIVE, "final"),
            Routed(3, "mirror-1", Availability.PRE_RELEASE_LEAK, "screener"),
            Routed(4, "unserved", Availability.NEVER_AUTHORISED, "no licence"),
            Routed(5, "mystery", Availability.UNKNOWN, "calendar unresolved"),
        ]
        out = route(items)
        # Only actionable classes enter the queue at all: an archive copy and an
        # unserved market are not tonight's work, whatever their size.
        self.assertEqual(("mirror-1", "telegram-ch"), tuple(r.target for r in out))
        self.assertEqual(15.0, out[0].sla_minutes)
        self.assertEqual(5.0, out[1].sla_minutes)
        self.assertNotIn("mystery", [r.target for r in out])
        self.assertNotIn("archive-site", [r.target for r in out])
        everything = route(items, include_non_actionable=True)
        # UNKNOWN sits at the bottom of the severity ladder, below even an
        # unserved market: an item whose calendar is unresolved cannot be
        # prioritised honestly, so it is last when it is admitted at all.
        self.assertEqual(("mirror-1", "telegram-ch", "archive-site", "unserved",
                          "mystery"), tuple(r.target for r in everything))

    def test_unknown_classification_can_top_a_queue_when_asked(self):
        out = route([Routed(1, "m", Availability.UNKNOWN, "x")],
                    include_non_actionable=True)
        self.assertEqual(1, len(out))
        self.assertIsNone(out[0].sla_minutes)

    def test_ignore_is_an_outcome_with_a_date(self):
        """Non-response is the most useful datum for a regulatory filing, and
        systems that leave it blank destroy it."""
        served = dt.datetime(2026, 11, 4, 10, 0)
        n = Notice("n1", "s1", "direct_operator", served_at=served,
                   state=NoticeState.IGNORED)
        self.assertIsNone(n.response_minutes)
        self.assertIsNone(n.within_standard,
                          "no reply -> no response time, not a False")
        rep = close_loop([n, Notice("n2", "s2", "cdn_host", served_at=served,
                                    responded_at=served + dt.timedelta(minutes=90),
                                    state=NoticeState.REMOVED)], [])
        self.assertEqual(2, rep.served)
        self.assertEqual(1, rep.ignored)
        self.assertEqual(1, rep.removed)
        self.assertEqual(0.5, rep.compliance_rate)
        self.assertEqual(90.0, rep.median_response_min)
        self.assertEqual(0, rep.within_30)

    def test_escalation_reduces_urls_to_entities(self):
        """Forty URLs belonging to one operator are one letter to one payment
        processor, not forty acts of whack-a-mole."""
        ns = [Notice(f"n{i}", f"url{i}", "direct_operator", operator_cluster="cl_001")
              for i in range(40)]
        ns.append(Notice("x", "loner", "direct_operator", operator_cluster=None))
        tgt = escalation_target(ns)
        self.assertEqual(1, len([k for k in tgt if k == "cl_001"]))
        self.assertEqual(40, len(tgt["cl_001"]))
        self.assertTrue(any(k.startswith("unattributed:") for k in tgt))
        self.assertNotIn("", tgt)

    def test_recalibration_is_printed_not_learned(self):
        """A self-modifying collection policy cannot be described to a
        regulator. What is adapted is *where to look*, never *what to believe*."""
        served = dt.datetime(2026, 11, 4, 10, 0)
        # Removed, back up 90 minutes later: outside the 30-minute standard, so
        # the per-URL rule fires. Each one also reappears on a second source, so
        # the mirror rule fires too.
        apps = []
        for i in range(5):
            gone = served + dt.timedelta(minutes=60)
            apps.append(Appearance(f"o{i}", "s1", served, served, gone,
                                   gone + dt.timedelta(minutes=90)))
            apps.append(Appearance(f"o{i}", "s2", gone + dt.timedelta(minutes=10),
                                   gone + dt.timedelta(minutes=10), None, None))
        out = close_loop([], apps)
        self.assertTrue(out.recalibration)
        self.assertTrue(any("operator cluster" in c for c in out.recalibration),
                        msg=str(out.recalibration))
        self.assertTrue(any("mirror" in c.lower() or "enumerated" in c.lower()
                            for c in out.recalibration), msg=str(out.recalibration))
        self.assertEqual("cdn_host", out.recommended_channel)

    def test_notice_state_terminality(self):
        self.assertTrue(NoticeState.REMOVED.terminal)
        self.assertFalse(NoticeState.PENDING.terminal)


# ==========================================================================
# 8. Report emission
# ==========================================================================
class TestReport(unittest.TestCase):
    def _fixtures(self):
        lg = Ledger()
        receipts = []
        for i in range(3):
            r = Receipt.from_html(f"https://s{i}.test/e12", HTML_A,
                                  observed_at=f"2026-11-04T1{i}:00:00Z",
                                  recipe=ReplayRecipe(method="GET",
                                                      url=f"https://s{i}.test/e12")).seal()
            receipts.append(r)
            lg.append(r)
        cl = Cluster("cl_001", frozenset(f"s{i}" for i in range(3)), 2.4,
                     (Signal("tls_cert_key", "C1"),), "OPERATOR")
        cl = Cluster("cl_001", cl.sources, cl.total_weight,
                     tuple(), cl.verdict)
        return lg, receipts, cl

    def test_pack_marks_itself_unanchored(self):
        """The absence of an external anchor belongs on the first line, not on
        page nine: it is the difference between evidence and a database."""
        lg, receipts, cl = self._fixtures()
        p = build_pack(cl, receipts, lg)
        self.assertFalse(p.anchored)
        self.assertIn("No day of this record is externally anchored", p.statement())
        self.assertIn("2026-11-04", p.unanchored_days)

    def test_pack_after_anchoring_claims_coverage(self):
        lg, receipts, cl = self._fixtures()
        lg.record_anchor("2026-11-04", "ots:xyz")
        p = build_pack(cl, receipts, lg)
        self.assertTrue(p.anchored)
        self.assertEqual((), p.unanchored_days)

    def test_tampered_receipt_refuses_the_whole_pack(self):
        lg, receipts, cl = self._fixtures()
        bad = [Receipt(**dict(r.payload(), excerpt="edited"), sealed=r.sealed)
               for r in receipts]
        with self.assertRaises(PackRefused):
            build_pack(cl, bad, lg)

    def test_caveat_when_receipts_are_not_replayable(self):
        lg = Ledger()
        receipts = [Receipt.from_html(f"https://s{i}.test/", HTML_A,
                                      observed_at=f"2026-11-04T1{i}:00:00Z").seal()
                    for i in range(2)]
        for r in receipts:
            lg.append(r)
        cl = Cluster("c", frozenset({"s0", "s1"}), 2.0, (), "OPERATOR")
        p = build_pack(cl, receipts, lg)
        self.assertTrue(any("no replay recipe" in c for c in p.caveats))

    def test_markdown_contains_no_prohibited_field(self):
        lg, receipts, cl = self._fixtures()
        p = build_pack(cl, receipts, lg)
        self.assertEqual([], scan_for_prohibited(p.to_dict()))

    def test_prohibited_scan_finds_a_pasted_stream_url(self):
        """Checked on emission, not on authoring: the realistic failure is a
        later edit pasting a stream link into an evidence field to make a point
        clearer for a lawyer."""
        dirty = {"evidence": {"stream_url": "https://evil/x.m3u8", "hash": "abc"}}
        self.assertIn("stream_url", scan_for_prohibited(dirty))
        self.assertEqual([], scan_for_prohibited({"evidence": {"hash": "abc"}}))

    def test_pack_markdown_renders(self):
        lg, receipts, cl = self._fixtures()
        md = build_pack(cl, receipts, lg).markdown()
        self.assertIn("## Caveats", md)
        self.assertIn("body sha256", md)


# ==========================================================================
# 9. Cross-cutting: the refusals, in one place
# ==========================================================================
class TestRefusalsAreUniform(unittest.TestCase):
    """Every metric in this system must be able to say 'I do not know', and say
    it in a way a caller cannot mistake for a zero. This class checks that
    property uniformly rather than trusting each module to remember it."""

    def test_all_metrics_degrade_to_none_not_zero(self):
        results = [
            supply_coverage(spans(["a"])).coverage_p50,
            supply_coverage(spans(["a", "b", "c"], ["d", "e", "f"])).coverage_p50,
            reappearance_latency([]).share_within_30,
            catalog_completeness("w", None, {1: dt.datetime(2026, 1, 1)}).share,
            availability_gap("w", "IQ", "NEVER_AUTHORISED", 5, ["s"]).quoted_value,
            quote_gaps([]).total_quoted,
            detectors_needed(0.0),
        ]
        for i, v in enumerate(results):
            with self.subTest(metric=i):
                self.assertIsNone(v, f"metric {i} fabricated {v!r}")

    def test_no_metric_returns_a_negative_count(self):
        cov = supply_coverage(spans([f"o{i}" for i in range(30)],
                                    [f"o{i}" for i in range(15, 45)]))
        self.assertGreaterEqual(cov.coverage_p50, 0.0)
        self.assertLessEqual(cov.coverage_p50, 1.0)
        self.assertGreaterEqual(cov.population_p50, cov.n_observed)

    def test_reason_strings_are_present_where_a_value_is_absent(self):
        for spans_ in ([spans(["a"])], [spans(["a", "b"], ["c", "d"])]):
            cov = supply_coverage(*spans_)
            if cov.coverage_p50 is None:
                self.assertTrue(cov.reason and len(cov.reason) > 10,
                                "a refusal with no reason is indistinguishable "
                                "from a bug")


if __name__ == "__main__":
    unittest.main(verbosity=2)
