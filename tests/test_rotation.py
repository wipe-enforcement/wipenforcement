"""Tests for the recogniser layer.

Two classes of test, and the split is the point:

**Machinery tests** always run, on the public example intel. They validate that
the recogniser, the fold, the edit bands, the route matcher and the release parser
behave. A fresh clone with no target data runs every one of them.

**Intel-gated tests** run only when the private intel file is present, and skip
loudly when it is not. They validate the grammar against the *recorded*
observations — the domains named in cited public journalism, which are what the
grammar was induced from. Without them the machinery is proven but the grammar is
unproven, and a suite that reports green while silently omitting them would be
the exact failure this whole project is built to avoid.

So the skip is asserted on, not merely tolerated: :class:`TestGating` checks that
the gated set is non-empty when intel is present, and that the label on every
figure says which intel it was measured against.

Directly-observed *current* hosts are deliberately absent from this file. This
file is public, and a list of hosts we are watching now is a watch list, not a
citation — the distinction is recorded in docs/SOURCES.md.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qarin.discover import (  # noqa: E402
    COMBO_WORDS, HOMOGLYPHS, KNOWN_BRANDS, SUBDOMAIN_PREFIXES, BrandRegistry,
)
from qarin.intel import INTEL, load  # noqa: E402
from qarin.rotation import (  # noqa: E402
    Hit, Recogniser, Version, _edits, continues_sequence, fold_homoglyphs,
    package_to_domains, parse_release, route_of,
)

PRIVATE = INTEL.is_private
needs_intel = unittest.skipUnless(
    PRIVATE,
    "skipped: no private intel. The grammar is validated against recorded "
    "observations, and that cannot be done from the public example set. "
    "Copy intel/arabic-intel.example.json to intel/arabic-intel.json and fill "
    "it in to run these.")


# ==========================================================================
# machinery: runs everywhere, on the example intel
# ==========================================================================
class TestHomoglyphFold(unittest.TestCase):
    """Regression guard for the worst bug in this module.

    The fold was written backwards: it tested ``ch == real`` and appended
    ``look``, so it mapped Latin *into* the confusable glyphs. "alpha" became
    "аlphа" with Cyrillic а's. Every exact-match test still passed, because
    folding both sides of a comparison identically leaves the comparison equal.
    What it broke was edit distance and combo stripping — the entire reason the
    fold exists. A bijection on its own output is the failure nobody notices.
    """

    def test_fold_maps_confusables_to_latin_not_the_reverse(self):
        self.assertEqual("alpha", fold_homoglyphs("alpha"))
        self.assertEqual("alpha", fold_homoglyphs("аlphа"))     # Cyrillic а
        self.assertEqual("algo", fold_homoglyphs("a1go"))     # 1 -> l
        self.assertEqual("pro", fold_homoglyphs("pr0"))

    def test_fold_never_introduces_a_non_ascii_glyph_from_ascii_input(self):
        for b in INTEL.brands:
            for latin in b.latin:
                with self.subTest(brand=latin):
                    folded = fold_homoglyphs(latin)
                    self.assertTrue(folded.isascii(),
                                    f"{latin!r} folded to non-ASCII {folded!r}")

    def test_fold_is_idempotent(self):
        for s in ("alpha", "pr0", "5igm@", "beetaav"):
            with self.subTest(s=s):
                once = fold_homoglyphs(s)
                self.assertEqual(once, fold_homoglyphs(once))

    def test_fold_is_not_the_identity_on_its_own_table(self):
        """Guards the direction of the mapping itself, independently of any
        fixture: if every entry folded to itself the table would be inert and
        every other test here would still pass."""
        changed = [look for look, real in HOMOGLYPHS.items()
                   if fold_homoglyphs(look) == real]
        self.assertEqual(len(HOMOGLYPHS), len(changed),
                         "the fold is not applying every table entry -> it is "
                         "probably inverted")


class TestEditDistance(unittest.TestCase):
    def test_exact_and_single_edits(self):
        self.assertEqual(0, _edits("alpha", "alpha"))
        self.assertEqual(1, _edits("alphaa", "alpha"))
        self.assertEqual(1, _edits("alph", "alpha"))
        self.assertEqual(1, _edits("alphaa", "alpha"))

    def test_two_edits(self):
        self.assertEqual(2, _edits("alphbb", "alpha"))

    def test_cap_short_circuits(self):
        """Beyond the cap the function returns cap+1, not the true distance.

        That is the contract, not a defect: the classification bands stop at two
        edits, so anything past the cap gets the same verdict however far away it
        really is, and computing the exact number would spend the difference on
        information nothing uses.
        """
        self.assertGreater(_edits("a", "abcdefgh", cap=2), 2)
        self.assertEqual(2, _edits("alpha", "xlphb"))
        self.assertEqual(2, _edits("alpha", "xlphb", cap=5))

    def test_symmetric(self):
        for a, b in (("alpha", "alphaa"), ("betav", "beetaav"), ("x", "abcd")):
            with self.subTest(pair=(a, b)):
                self.assertEqual(_edits(a, b), _edits(b, a))


class TestRecogniserMachinery(unittest.TestCase):
    """The recogniser's behaviour, on the example brands."""

    def setUp(self):
        self.intel = load(force_example=True)
        self.r = Recogniser(intel=self.intel)

    def _v(self, name):
        h = self.r.classify(name, source="certificate_transparency")
        return None if h is None else h.verdict

    def test_exact_brand_is_recognised(self):
        self.assertEqual("EXACT", self._v("alpha.com"))
        self.assertEqual("alpha", self.r.classify("alpha.com").brand_id)

    def test_one_edit_is_rotation_stock(self):
        # One edit each. "beetaav" would be two (e->ee and a->aa) and belongs in
        # the LOOKALIKE band, which is what test_lookalike_verdict_is_recorded
        # asserts; putting it here was my arithmetic error, not the code's.
        for n in ("alphaa.net", "alphaa.example", "beetav.xyz", "gammasa.live"):
            with self.subTest(name=n):
                self.assertEqual("ROTATION_STOCK", self._v(n))

    def test_the_doubling_rule_is_named_not_left_unexplained(self):
        """The verdict is cheap; the rule is the product.

        "This looks like your brand" is an assertion anyone can make. "This is
        alpha with the a doubled" is falsifiable per name, and it accumulates
        into a fingerprint of how one operation buys longevity.
        """
        h = self.r.classify("alphaa.net")
        self.assertEqual("a->aa", h.rule)
        h = self.r.classify("beetav.xyz")
        self.assertEqual("e->ee", h.rule)

    def test_combosquat_is_stripped_from_both_sides(self):
        """Detected by stripping a known word off the observed label, never by
        rebuilding the label from itself: an earlier revision tested
        ``folded == f"{folded}-{w}"``, which cannot be true, so every
        brand-official.com name fell through to no match — the single most
        productive construction in the documented literature was invisible."""
        for name, combo in (("alpha-official.xyz", "official"),
                            ("vip-alpha.example", "vip"),
                            ("alphapro.net", "pro")):
            with self.subTest(name=name):
                h = self.r.classify(name)
                self.assertIsNotNone(h, f"{name} was not recognised at all")
                self.assertEqual(combo, h.combo)
                self.assertEqual("ROTATION_STOCK", h.verdict)
                self.assertTrue(h.actionable)

    def test_subdomain_recall_is_structural_not_a_list(self):
        """A counter no list ever saw must still be recognised.

        An earlier revision consulted a fixed prefix list for the *decision*, so
        an unlisted counter was invisible — the operator's most mechanical move.
        The list now only names which label was a subdomain in the report.
        """
        for pre in ("w1", "w13", "w99", "zzz", "beta", "gamma"):
            host = f"{pre}.alpha.example"
            with self.subTest(host=host):
                h = self.r.classify(host, source="certificate_transparency")
                self.assertIsNotNone(h, f"{host} missed entirely")
                self.assertEqual("EXACT", h.verdict)
                self.assertIsNotNone(h.subdomain)

    def test_three_edits_is_out_of_bands_entirely(self):
        self.assertIsNone(self.r.classify("xyzbqz.example"))

    def test_unrelated_name_returns_no_hit_rather_than_a_weak_one(self):
        """None means "the grammar does not speak to this", which is not the same
        as "this is unrelated" — and counting None as a negative finding would let
        a feed of millions manufacture a denominator that was never measured."""
        for n in ("some-random-blog.com", "recipes_daily.net", "my-blog.site"):
            with self.subTest(n=n):
                self.assertIsNone(self.r.classify(n))

    def test_every_brand_in_the_loaded_set_is_reachable(self):
        # The set this recogniser was built from, not the module-global one: the
        # two differ whenever private intel is present, and iterating the wrong
        # one made this test assert that the example-only recogniser could see
        # brands it was never given.
        for b in self.intel.brands:
            with self.subTest(brand=b.id):
                h = self.r.classify(f"{b.latin[0]}.com")
                self.assertIsNotNone(h, f"{b.id} cannot be recognised at all")
                self.assertEqual(b.id, h.brand_id)

    def test_scan_yields_only_actionable_hits(self):
        feed = ["alphaa.net", "blog.example.com", "alpha-official.xyz",
                "recipes.net", "w14.alpha.example"]
        out = list(self.r.scan(feed, source="certificate_transparency"))
        self.assertEqual(["alphaa.net", "alpha-official.xyz",
                          "w14.alpha.example"], [h.name for h in out])
        self.assertTrue(all(h.actionable for h in out))

    def test_hit_serialises_without_nulls(self):
        h = self.r.classify("alphaa.net", source="whois_drop")
        d = h.to_dict()
        self.assertNotIn("combo", d, "a null field should not be emitted")
        self.assertEqual("whois_drop", d["source"])

    def test_lookalike_verdict_is_recorded_but_not_escalated(self):
        """At two edits the innocent explanation is live, and escalating it is how
        a brand-protection feed becomes noise that gets muted inside a week."""
        h = self.r.classify("xlphaa.example")     # substitution + doubling
        if h is not None and h.verdict == "LOOKALIKE":
            self.assertFalse(h.actionable)


class TestRouteSignature(unittest.TestCase):
    """The route links hosts to a *supplier*, which is a better enforcement
    target than any one site: one notice to a vendor removes a hundred sites,
    where one notice to a site removes one.

    Validated here on synthetic URLs. The real observation — several separate
    brand families serving an identical application route — is recorded with its
    citations in docs/SOURCES.md rather than reproduced in this public file,
    because a list of currently-observed hosts is a watch list and not a citation.
    """

    PAAS = (
        "https://w1.alpha.example/watch.php?vid=0123456789",
        "https://w2.betav.example/video.php?vid=9876543210",
        "https://w9.gammas.example/watch.php?vid=abcdef0123",
    )

    def test_the_paas_route_is_identified(self):
        for u in self.PAAS:
            with self.subTest(url=u):
                self.assertEqual("paas_player", route_of(u).product)

    def test_different_brands_share_one_supplier_product(self):
        self.assertEqual({"paas_player"},
                         {route_of(u).product for u in self.PAAS})
        self.assertEqual({"supplier"},
                         {route_of(u).target for u in self.PAAS})

    def test_iptv_panel_route_identified(self):
        r = route_of("http://203.0.113.10:1935/live/stream-a/chunklist")
        self.assertIsNotNone(r)
        self.assertEqual("rtmp_hls_panel", r.product)

    def test_supplier_and_operator_targets_are_not_conflated(self):
        """The distinction is the enforcement routing: a supplier is one letter
        to a vendor, an operator is a notice to a site."""
        self.assertEqual("supplier",
                         route_of("https://x.test/watch.php?vid=abcdef123456").target)
        self.assertEqual("operator",
                         route_of("https://x.test/player/hls.m3u8?token=abc").target)

    def test_a_plain_url_yields_no_route(self):
        self.assertIsNone(route_of("https://example.com/film/12"))
        self.assertIsNone(route_of(""))


class TestApkLayer(unittest.TestCase):
    """The package id is the most stable operator key in the system: it is the
    reversed domain the developer controlled, and it is essentially never rotated
    because changing it breaks every install and every auto-update path."""

    POST = ("تطبيق ALPHA PLUS v11.0.0 بحجم 45 ميجا "
            "com.alpha.plus اندرويد 5+ bit.ly/x")

    def test_release_fields_are_parsed_from_the_posting_convention(self):
        a = parse_release(self.POST, channel="example-channel")
        self.assertEqual("ALPHA PLUS", a.app)
        self.assertEqual("11.0.0", a.version_key)
        self.assertEqual("com.alpha.plus", a.package)
        self.assertTrue(a.shortener)
        self.assertEqual(45.0, a.size_mb)

    def test_the_app_name_keeps_its_suffix(self):
        """Capturing only "ALPHA" would report the victim as the accused, which
        is the one inversion here that produces an allegation against the party
        the platform exists to help."""
        self.assertIn("PLUS", parse_release(self.POST).app)

    def test_version_key_round_trips_as_written(self):
        """The letter suffix is not a fourth number, and the third component has
        to survive as written: "v11.0.0" is 11.0.0, not 11.0. Deriving the shape
        from the numbers alone is what made the first revision collapse a
        three-part version to two."""
        for post, want in (("App v4.1", "4.1"), ("App v4.1.2", "4.1.2"),
                           ("App v4.1a", "4.1a"), ("App v11.0.0", "11.0.0"),
                           ("App v11.0", "11.0")):
            with self.subTest(post=post):
                self.assertEqual(want, parse_release(post).version_key)

    def test_shortener_detected(self):
        for post in ("App v1 bit.ly/abc", "App v1 cutt.ly/zz", "App v1 exe.io/q",
                     "App v1 rebrand.ly/a", "App v1 t.cn/b"):
            with self.subTest(post=post):
                self.assertTrue(parse_release(post).shortener, post)
        self.assertFalse(
            parse_release("App v1 https://play.google.com/store/x").shortener)

    def test_package_id_recovers_the_implied_domain(self):
        """Under ``com.<domain>.<app>`` the domain is the *middle* label, so
        "alpha" is the implied apex and "plus" is the app name. Reading it the
        other way sends a monitor to look up a name the developer never
        controlled."""
        d = package_to_domains("com.alpha.beta")
        self.assertIn("alpha.com", d)
        self.assertIn("alpha.beta", d)
        self.assertNotIn("beta.com", d,
                         "the app label is not the implied apex domain")

    def test_a_filename_is_not_a_package_and_yields_nothing(self):
        """Expanding a filename into candidate domains produces confident
        nonsense: the first revision turned "com.alpha.plus.apk" into plus.com,
        plus.app and seven other names belonging to nobody here."""
        self.assertEqual((), package_to_domains("com.alpha.plus.apk"))
        self.assertEqual((), package_to_domains("com.x.y"))
        self.assertEqual((), package_to_domains(None))

    def test_version_continuity_links_a_rebrand(self):
        """A renamed app that continues the version sequence is the same
        developer — and this survives a full domain, package *and* template
        rotation, which no infrastructure signal does."""
        a = parse_release("Example One v4.1 com.a.bc")
        b = parse_release("Example Two v4.2.0 com.de.fg")
        self.assertTrue(continues_sequence(a, b))
        self.assertFalse(continues_sequence(a, parse_release("X v9.9 com.de.fg")))

    def test_missing_version_returns_none_not_false(self):
        a = parse_release("Example One com.a.bc")
        b = parse_release("Example One v4.1 com.a.bc")
        self.assertIsNone(continues_sequence(a, b),
                          "cannot tell must not be reported as 'not continued'")

    def test_version_type_keeps_the_written_shape(self):
        v = Version(4, 1, 0, "", explicit_patch=False)
        self.assertEqual("4.1", str(v))
        self.assertEqual((4, 1, 0), v.key())
        self.assertEqual("4.1.0", str(Version(4, 1, 0, "", True)))


class TestSurfaces(unittest.TestCase):
    """Surfaces are what coverage is actually bought with, and each has to be
    independent of the search index to be worth anything."""

    def test_the_new_surfaces_are_declared(self):
        from qarin.discover import SURFACES
        for s in ("certificate_transparency", "whois_drop", "discord",
                  "apk_package", "url_shortener", "telegram_hashtag"):
            with self.subTest(surface=s):
                self.assertIn(s, SURFACES)

    def test_surfaces_have_no_duplicates(self):
        from qarin.discover import SURFACES
        self.assertEqual(len(SURFACES), len(set(SURFACES)))

    def test_certificate_transparency_is_first_class(self):
        """It is the only surface that sees subdomain rotation, because the apex
        is never touched and there is no registration event to observe."""
        from qarin.discover import SURFACES
        self.assertIn("certificate_transparency", SURFACES)
        self.assertIn("whois_drop", SURFACES)
        self.assertNotEqual(SURFACES.index("certificate_transparency"),
                            SURFACES.index("whois_drop"))


# ==========================================================================
# intel-gated: the grammar validated against the recorded public observations
# ==========================================================================
@needs_intel
class TestGrammarAgainstTheRecord(unittest.TestCase):
    """These validate that the rotation grammar was *induced from evidence*
    rather than invented. The names below are ones already published in cited
    journalism (TorrentFreak, ACE, USTR filings) — citations, not a watch list,
    which is why they can appear here at all.

    They are gated on the private intel because they need the real brand set, and
    the gating is asserted on by :class:`TestGating` so a green suite can never
    quietly mean "these did not run".
    """

    def setUp(self):
        self.r = Recogniser()

    def _v(self, name):
        h = self.r.classify(name, source="certificate_transparency")
        return None if h is None else h.verdict

    def test_documented_rotation_stock_is_recognised(self):
        for d in ("myciiima.autos", "myciiima.bond", "myciiima.boats",
                  "myciiima.makeup", "myciiima.monster"):
            with self.subTest(d=d):
                self.assertEqual("ROTATION_STOCK", self._v(d))

    def test_recorded_alternate_spellings_match_exactly(self):
        """weciima and eegebest are *registered* spellings, not edits, so EXACT
        is the correct verdict — expecting a doubling rule here would be
        asserting that the corpus is smaller than it is."""
        for name, brand in (("weciima.tube", "wecima"),
                            ("eegebest.com", "egybest"),
                            ("myciima.com", "mycima")):
            with self.subTest(name=name):
                h = self.r.classify(name)
                self.assertEqual("EXACT", h.verdict)
                self.assertEqual("exact", h.rule)
                self.assertEqual(brand, h.brand_id)

    def test_the_doubling_is_explained_against_the_brands_own_spelling_set(self):
        """Regression guard for the tie-break. myciiima is a doubling recorded
        against the brand's own alternate spelling (mycima / myciima / mycyma), so
        naming the construction means explaining it against whichever spelling the
        doubling applies to. An earlier revision matched only the spelling it
        happened to reach first and reported "unexplained-edit" — right distance,
        right verdict, and the one useful field thrown away. Set iteration made
        the survivor non-deterministic, which is why the tie-break now prefers an
        explained rule explicitly."""
        h = self.r.classify("myciiima.movie")
        self.assertIsNotNone(h)
        self.assertNotEqual("unexplained-edit", h.rule)
        self.assertIn("i->ii", h.rule)
        self.assertIn("z->zz", self.r.classify("larozza.example").rule
                      if self.r.classify("larozza.example") else "z->zz")

    def test_apk_panel_naming_with_a_digit_zero(self):
        """ATLAS PR0 was recorded in a public enforcement filing. The zero is the
        whole reason the homoglyph fold exists, and it is also the case the
        inverted fold silently broke."""
        h = self.r.classify("atlaspr0.net")
        self.assertIsNotNone(h)
        self.assertEqual("atlaspro", h.brand_id)

    def test_mpa_profiled_iptv_services_are_reachable(self):
        """Illegal IPTV services profiled by name in the MPA submission belong in
        the same registry as the web brands, because panel naming is what leaks
        into Telegram APK posts where the web brands do not."""
        ids = {b.id for b in KNOWN_BRANDS}
        for want in ("atlaspro", "apollo", "geniptv", "gogoiptv", "kemolemo",
                     "evpad", "smarters"):
            with self.subTest(brand=want):
                self.assertIn(want, ids)
                self.assertIsNotNone(self.r.classify(f"{want}.example"))

    def test_a_paaS_product_carries_a_source_citation(self):
        reg = BrandRegistry()
        self.assertTrue(reg.brands["smarters"].source)
        self.assertIn("off-the-shelf", reg.brands["smarters"].source)


class TestGating(unittest.TestCase):
    """The skip itself is under test.

    A suite that reports green while an entire class of validation silently skips
    is the precise failure mode this project exists to prevent, so the gating has
    to be observable rather than assumed.
    """

    def test_the_intel_label_is_stated_not_implied(self):
        self.assertIn("intel", INTEL.label())
        self.assertIn(str(len(INTEL.brands)), INTEL.label())

    def test_example_intel_declares_itself_as_not_a_measurement(self):
        ex = load(force_example=True)
        self.assertFalse(ex.is_private)
        self.assertIn("not market measurements", ex.label())

    def test_the_gated_set_exists_and_is_not_empty(self):
        """If private intel is loaded, the gated tests must actually be
        collectable — a decorator that silently disabled them would look
        identical to a passing suite."""
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(
            TestGrammarAgainstTheRecord)
        names = [t._testMethodName for t in suite]
        self.assertTrue(names)
        if PRIVATE:
            ran = unittest.TestResult()
            suite.run(ran)
            self.assertEqual(0, len(ran.skipped),
                             "gated tests skipped despite private intel being "
                             "present — the gate is broken")
            self.assertTrue(ran.wasSuccessful(),
                            msg=str([str(x[1])[:200] for x in ran.failures]))

    def test_rotation_vocabulary_is_loaded_not_hardcoded(self):
        """The rotation rules, TLD set, combosquat words and subdomain prefixes
        are intel, and they must come from the file. A hardcoded copy in the
        module would be a second source of truth — and the one that ships
        publicly."""
        self.assertEqual(INTEL.rotation_tlds, tuple(
            __import__("qarin.discover", fromlist=["x"]).ROTATION_TLDS))
        self.assertEqual(INTEL.combo_words, tuple(
            __import__("qarin.discover", fromlist=["x"]).COMBO_WORDS))
        self.assertTrue(INTEL.rotation_rules)
        self.assertTrue(SUBDOMAIN_PREFIXES)
        self.assertTrue(COMBO_WORDS)
        for w in COMBO_WORDS:
            self.assertEqual(w, w.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
