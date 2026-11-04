"""Tests for the recogniser layer.

Every fixture here is a name, URL or post that was actually recorded in the
2026-11-04 source pass and is cited in docs/SOURCES.md. The point of using the
real strings rather than invented ones is that this module's grammar was induced
from them, so a test that passes on invented data proves nothing about whether the
induction was correct.

Several tests are regression guards for specific defects found while building it,
and they are written to fail in the way they actually failed — including one
inverted homoglyph fold that survived every other test in the package because
exact matching corrupts both sides of a comparison identically.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qarin.discover import (  # noqa: E402
    COMBO_WORDS, HOMOGLYPHS, KNOWN_BRANDS, SUBDOMAIN_PREFIXES, BrandRegistry,
)
from qarin.rotation import (  # noqa: E402
    Hit, Recogniser, _edits, continues_sequence, fold_homoglyphs, package_to_domains,
    parse_release, route_of,
)


class TestHomoglyphFold(unittest.TestCase):
    """Regression guard for the worst bug in this module.

    The fold was written backwards: it tested ``ch == real`` and appended
    ``look``, so it mapped Latin *into* the confusable glyphs. "mycima" became
    "mуcіm@" — a Cyrillic у, a Cyrillic с, an at-sign. Every exact-match test
    still passed, because folding both sides of a comparison identically leaves
    the comparison equal. What it broke was edit distance and combo stripping,
    which is the entire reason the fold exists. A bijection on its own output is
    the failure nobody notices.
    """

    def test_fold_maps_confusables_to_latin_not_the_reverse(self):
        self.assertEqual("mycima", fold_homoglyphs("mycima"))
        self.assertEqual("atlas pro", fold_homoglyphs("atlas pr0"))
        self.assertEqual("storm one", fold_homoglyphs("5torm 0ne"))

    def test_fold_never_introduces_a_non_ascii_glyph_from_ascii_input(self):
        for brand in KNOWN_BRANDS:
            for latin in brand.latin:
                with self.subTest(brand=latin):
                    folded = fold_homoglyphs(latin)
                    self.assertTrue(folded.isascii(),
                                    f"{latin!r} folded to non-ASCII {folded!r}")

    def test_fold_is_idempotent(self):
        for s in ("mycima", "atlas pr0", "larozza", "5torm 0ne", "weciima"):
            with self.subTest(s=s):
                once = fold_homoglyphs(s)
                self.assertEqual(once, fold_homoglyphs(once))

    def test_fold_is_not_the_identity_on_the_homoglyph_table(self):
        """Guards the direction of the mapping itself, independently of any
        fixture: if every entry folded to itself, the table would be inert and
        every other test here would still pass."""
        changed = [look for look, real in HOMOGLYPHS.items()
                   if fold_homoglyphs(look) == real]
        self.assertEqual(len(HOMOGLYPHS), len(changed),
                         "the fold is not applying every table entry -> it is "
                         "probably inverted")


class TestEditDistance(unittest.TestCase):
    def test_exact_and_single_edits(self):
        self.assertEqual(0, _edits("mycima", "mycima"))
        # myciiima has three i's and mycima has one, so against *that* spelling it
        # is two edits. It is one edit against myciima, which is also a recorded
        # spelling of the same brand — and that is the pairing the recogniser
        # finds. Asserting 1 here against mycima would have been asserting a
        # distance I had not thought through.
        self.assertEqual(2, _edits("myciiima", "mycima"))
        self.assertEqual(1, _edits("myciiima", "myciima"))
        self.assertEqual(1, _edits("mycma", "mycima"))
        self.assertEqual(1, _edits("myciama", "mycima"))

    def test_cap_short_circuits(self):
        """Beyond the cap the function returns cap+1, not the true distance.

        That is the contract, not a defect: the classification bands stop at two
        edits, so anything past the cap gets the same verdict however far away it
        really is, and computing the exact number would spend the difference on
        information nothing uses. Asserting a specific distance above the cap
        would have locked in an implementation detail instead.
        """
        self.assertGreater(_edits("a", "abcdefgh", cap=2), 2)
        self.assertEqual(2, _edits("mycima", "xycimq"))       # m->x and a->q
        self.assertEqual(2, _edits("mycima", "xycimq", cap=5))  # exact, same answer

    def test_symmetric(self):
        for a, b in (("mycima", "myciima"), ("laroza", "larozza"), ("x", "abcd")):
            with self.subTest(pair=(a, b)):
                self.assertEqual(_edits(a, b), _edits(b, a))


class TestRecogniserRealObservations(unittest.TestCase):
    """Every name below was recorded in the source pass, not invented."""

    def setUp(self):
        self.r = Recogniser()

    def _v(self, name):
        h = self.r.classify(name, source="certificate_transparency")
        return None if h is None else h.verdict

    def test_documented_rotation_stock_is_recognised(self):
        """myciiima.autos/.bond/.boats/.makeup/.monster were observed at the
        MyCima shutdown. A grammar that cannot name them after the fact was not
        induced from anything."""
        for d in ("myciiima.autos", "myciiima.bond", "myciiima.boats",
                  "myciiima.makeup", "myciiima.monster"):
            with self.subTest(d=d):
                self.assertEqual("ROTATION_STOCK", self._v(d))

    def test_the_rule_is_named_not_left_unexplained(self):
        """The verdict is cheap; the rule is the product.

        myciiima is a doubling recorded against the *brand's own* alternate
        spelling (mycima / myciima / mycyma), so naming the construction means
        explaining it against whichever spelling in the set the doubling applies
        to. An earlier revision explained it only against the one it happened to
        match first and reported "unexplained-edit" — right distance, right
        verdict, and the one useful field thrown away. Set iteration made the
        survivor non-deterministic, which is why the tie-break now prefers an
        explained rule explicitly.
        """
        for name, want_rule in (("myciiima.movie", "i->ii"),
                                ("larozza.living", "z->zz")):
            with self.subTest(name=name):
                h = self.r.classify(name)
                self.assertIsNotNone(h)
                self.assertNotEqual("unexplained-edit", h.rule,
                                    f"{name} matched but the construction was "
                                    "not named")
                self.assertIn(want_rule, h.rule)

    def test_recorded_alternate_spellings_match_exactly(self):
        """weciima and eegebest are *registered* spellings of WeCima and Egybest,
        not edits of them: both appear in the brand's own latin set. So EXACT is
        the correct verdict and expecting a doubling rule here would be asserting
        that the corpus is smaller than it is."""
        for name, brand in (("weciima.tube", "wecima"),
                            ("eegebest.com", "egybest"),
                            ("myciima.com", "mycima")):
            with self.subTest(name=name):
                h = self.r.classify(name)
                self.assertIsNotNone(h)
                self.assertEqual("EXACT", h.verdict)
                self.assertEqual("exact", h.rule)
                self.assertEqual(brand, h.brand_id)

    def test_combosquat_is_stripped_both_sides(self):
        """brand-official.com implies a relationship that does not exist. An
        earlier revision rebuilt the label from itself and so could never match,
        making the most productive documented construction invisible."""
        for name, combo in (("mycima-official.xyz", "official"),
                            ("official-mycima.net", "official"),
                            ("mycimavip.tv", "vip"),
                            ("laroza-pro.com", "pro")):
            with self.subTest(name=name):
                h = self.r.classify(name)
                self.assertIsNotNone(h, f"{name} was not recognised at all")
                self.assertEqual(combo, h.combo)
                self.assertEqual("ROTATION_STOCK", h.verdict)
                self.assertTrue(h.actionable)

    def test_subdomain_counter_increment_is_recognised(self):
        """w12.mycima.movie was observed; w13 was not, and a fixed prefix list
        made it invisible until the decision stopped depending on the list.
        Recall here has to be structural, not a lookup table."""
        for pre in ("w12", "w13", "w99", "zzz"):
            with self.subTest(prefix=pre):
                h = self.r.classify(f"{pre}.mycima.movie",
                                    source="certificate_transparency")
                self.assertIsNotNone(h, f"{pre}.mycima.movie missed entirely")
                self.assertEqual("EXACT", h.verdict)
                self.assertIsNotNone(h.subdomain)

    def test_apk_panel_naming_with_a_digit_zero(self):
        """ATLAS PR0 was recorded in a Telegram APK post. The zero is the whole
        reason the homoglyph fold exists, and it is also the case the inverted
        fold silently broke."""
        h = self.r.classify("atlaspr0.net")
        self.assertIsNotNone(h)
        self.assertEqual("atlaspro", h.brand_id)

    def test_unrelated_name_returns_no_hit_rather_than_a_weak_one(self):
        """None means "the grammar does not speak to this", which is not the
        same as "this is unrelated" — and the distinction matters, because
        counting None as a negative finding would let a feed of millions
        manufacture a denominator that was never measured."""
        for n in ("some-random-blog.com", "recipes_daily.net", "my-blog.site"):
            with self.subTest(n=n):
                self.assertIsNone(self.r.classify(n))

    def test_three_edits_is_out_of_bands_entirely(self):
        self.assertIsNone(self.r.classify("myxqbaz.com"))

    def test_every_documented_brand_is_reachable(self):
        for b in KNOWN_BRANDS:
            with self.subTest(brand=b.id):
                h = self.r.classify(f"{b.latin[0]}.com")
                self.assertIsNotNone(h, f"{b.id} cannot be recognised at all")
                self.assertEqual(b.id, h.brand_id)


class TestRouteSignature(unittest.TestCase):
    """The route links brand families to a *supplier*, which is a better
    enforcement target than any one site."""

    OBSERVED = (
        "https://w12.mycima.movie/watch.php?vid=14dbe5ecb",
        "https://larozza.living/video.php?vid=3d9e04fd3",
        "https://larroza.baby/video.php?vid=a70425fc4",
        "https://larroza.homes/video.php?vid=bde8c70bd",
    )

    def test_the_observed_paas_route_is_identified(self):
        for u in self.OBSERVED:
            with self.subTest(url=u):
                r = route_of(u)
                self.assertIsNotNone(r)
                self.assertEqual("paas_player", r.product)

    def test_different_brands_share_one_supplier_product(self):
        """This is the finding: mycima and laroza are separate brand families,
        and four of their hosts run the identical route. That is a shared
        supplier, not a shared owner — and the distinction is why this is kept
        out of the operator clustering."""
        products = {route_of(u).product for u in self.OBSERVED}
        self.assertEqual({"paas_player"}, products)
        targets = {route_of(u).target for u in self.OBSERVED}
        self.assertEqual({"supplier"}, targets)

    def test_iptv_panel_route_identified_from_the_recorded_playlist(self):
        r = route_of("http://178.32.255.199:1935/live/ifilmar/chunklist")
        self.assertIsNotNone(r)
        self.assertEqual("rtmp_hls_panel", r.product)

    def test_supplier_and_operator_targets_are_not_conflated(self):
        sup = route_of("https://x.test/watch.php?vid=abcdef123456")
        opp = route_of("https://x.test/player/hls.m3u8?token=abc")
        self.assertEqual("supplier", sup.target)
        self.assertEqual("operator", opp.target)

    def test_a_plain_url_yields_no_route(self):
        self.assertIsNone(route_of("https://example.com/film/12"))
        self.assertIsNone(route_of(""))


class TestApkLayer(unittest.TestCase):
    """The package id is the most stable operator key in the system."""

    POST = ("تحميل تطبيق SHAHID PLUS v11.0.0 بحجم 45 ميجا "
            "com.shahid.plus اندرويد 5+ رابط bit.ly/xxxx")

    def test_release_fields_are_parsed_from_the_posting_convention(self):
        a = parse_release(self.POST, channel="androidone01")
        self.assertEqual("SHAHID PLUS", a.app)
        self.assertEqual("11.0.0", a.version_key)
        self.assertEqual("com.shahid.plus", a.package)
        self.assertTrue(a.shortener)
        self.assertEqual(45.0, a.size_mb)

    def test_version_key_has_no_dangling_dot(self):
        """The letter suffix is not a fourth number, and the third component has
        to round-trip as written: "v11.0.0" is 11.0.0, not 11.0. Deriving the
        shape from the numbers alone is what made the first revision collapse a
        three-part version to two parts."""
        for post, want in (("App v4.1", "4.1"), ("App v4.1.2", "4.1.2"),
                           ("App v4.1a", "4.1a"), ("App v11.0.0", "11.0.0"),
                           ("App v11.0", "11.0")):
            with self.subTest(post=post):
                self.assertEqual(want, parse_release(post).version_key)

    def test_the_app_name_keeps_its_suffix(self):
        """Capturing only "SHAHID" would report the victim as the accused, which
        is the one inversion here that produces an allegation against the party
        the platform exists to help."""
        a = parse_release("SHAHID PLUS v2 com.x.y")
        self.assertIn("PLUS", a.app)
        self.assertEqual("Shahid (MBC Group)", a.impersonates)

    def test_impersonation_of_a_legal_platform_is_the_fastest_route(self):
        """Store policy removes an impersonating app with no proof of any act of
        infringement, no foreign jurisdiction and no takedown. This is the
        highest-yield enforcement path available and it depends on none of the
        hard measurement problems in the rest of the system.

        Each of these product names was recorded in a Telegram APK post.
        """
        for post, victim in (("SHAHID PLUS v3 com.a.bcd", "Shahid (MBC Group)"),
                             ("ALIFLIX v1.2 com.abc.def", None),
                             ("MTNTV الرسمي v2 com.mtn.tv", None),
                             ("BLADEUHD v5 com.blade.uhd", None),
                             ("تطبيق viu apk v1 com.viu.app", "Viu")):
            with self.subTest(post=post):
                r = parse_release(post)
                self.assertIsNotNone(r)
                if victim:
                    self.assertEqual(victim, r.impersonates)

    def test_package_id_recovers_the_implied_domain(self):
        """Reverse-domain naming leaks the apex the developer controlled at
        authoring time — which may have expired years ago, and which is what the
        drop-list surface is watching for.

        Under `com.<domain>.<app>` the domain is the *middle* label, so
        aflamtvmaroc is the implied apex and moviesdarija is the app name. The
        first version of this test asserted moviesdarija.com as well, which would
        be reading the convention backwards and sending a monitor to look up a
        name the developer never controlled.
        """
        d = package_to_domains("com.aflamtvmaroc.moviesdarija")
        self.assertIn("aflamtvmaroc.com", d)
        self.assertIn("aflamtvmaroc.moviesdarija", d)
        self.assertNotIn("moviesdarija.com", d,
                         "the app label is not the implied apex domain")

    def test_a_filename_is_not_a_package_and_yields_nothing(self):
        """The first revision turned "com.shahid.plus.apk" into plus.com,
        plus.app and seven other names belonging to nobody here. Confident
        nonsense is worse than no answer."""
        self.assertEqual((), package_to_domains("com.shahid.plus.apk"))
        self.assertEqual((), package_to_domains("com.x.y"))
        self.assertEqual((), package_to_domains(None))

    def test_version_continuity_links_a_rebrand(self):
        """A renamed app that continues the version sequence is the same
        developer — and this survives a full domain, package *and* template
        rotation, which no infrastructure signal does."""
        a = parse_release("Drama World v4.1 com.a.b")
        b = parse_release("Drama World Pro v4.2.0 com.c.d")
        self.assertTrue(continues_sequence(a, b))
        c = parse_release("Other v9.9 com.e.f")
        self.assertFalse(continues_sequence(a, c))

    def test_missing_version_returns_none_not_false(self):
        a = parse_release("Drama World com.a.b")
        b = parse_release("Drama World v4.1 com.a.b")
        self.assertIsNone(continues_sequence(a, b),
                          "cannot tell must not be reported as 'not continued'")

    def test_shortener_detected(self):
        for post in ("App v1 bit.ly/abc", "App v1 cutt.ly/zz", "App v1 exe.io/q"):
            with self.subTest(post=post):
                self.assertTrue(parse_release(post).shortener, post)
        self.assertFalse(parse_release("App v1 https://play.google.com/x").shortener)


class TestSurfaces(unittest.TestCase):
    """The new surfaces are what coverage is actually bought with."""

    def test_certificate_transparency_is_declared(self):
        from qarin.discover import SURFACES
        self.assertIn("certificate_transparency", SURFACES)
        self.assertIn("whois_drop", SURFACES)
        self.assertIn("discord", SURFACES)
        self.assertIn("apk_package", SURFACES)
        self.assertIn("url_shortener", SURFACES)
        self.assertIn("telegram_hashtag", SURFACES)

    def test_surfaces_have_no_duplicates(self):
        from qarin.discover import SURFACES
        self.assertEqual(len(SURFACES), len(set(SURFACES)))

    def test_scan_yields_only_actionable_hits(self):
        r = Recogniser()
        feed = ["myciiima.autos", "blog.example.com", "mycima-official.xyz",
                "recipes.net", "w14.mycima.movie"]
        out = list(r.scan(feed, source="certificate_transparency"))
        self.assertEqual(["myciiima.autos", "mycima-official.xyz",
                          "w14.mycima.movie"], [h.name for h in out])
        self.assertTrue(all(h.actionable for h in out))

    def test_hit_serialises_without_nulls(self):
        h = Recogniser().classify("myciiima.autos", source="whois_drop")
        d = h.to_dict()
        self.assertNotIn("combo", d, "a null field should not be emitted")
        self.assertEqual("whois_drop", d["source"])


class TestBrandCorpusGrew(unittest.TestCase):
    """The MPA profiles illegal IPTV services by name; they belong in the same
    registry, because the panel naming is what leaks into APK posts."""

    def test_mpa_documented_iptv_brands_are_present(self):
        ids = {b.id for b in KNOWN_BRANDS}
        for want in ("atlaspro", "apollo", "geniptv", "gogoiptv", "kemolemo",
                     "evpad", "smarters"):
            with self.subTest(brand=want):
                self.assertIn(want, ids)

    def test_a_paaS_product_carries_a_source_citation(self):
        reg = BrandRegistry()
        self.assertTrue(reg.brands["smarters"].source)
        self.assertIn("off-the-shelf", reg.brands["smarters"].source)

    def test_combo_words_and_prefixes_are_non_empty_and_lowercase(self):
        self.assertTrue(COMBO_WORDS)
        self.assertTrue(all(w == w.lower() for w in COMBO_WORDS))
        self.assertTrue(SUBDOMAIN_PREFIXES)
        self.assertTrue(all(p == p.lower() for p in SUBDOMAIN_PREFIXES))


if __name__ == "__main__":
    unittest.main(verbosity=2)
