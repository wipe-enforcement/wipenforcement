"""Tests for the discovery layer.

The load-bearing assertions here are about *accounting*, not about cleverness:
a probe set must report itself as one detector when it is one detector, and the
rotation grammar must reproduce domains that were actually observed rather than
plausible-sounding ones. A discovery module that inflates its own independence
is the fastest route to a false 95% coverage claim.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qarin.discover import (  # noqa: E402
    CO_OCCURRENCE_MIN, KNOWN_BRANDS, LEXICON, ROTATION_TLDS, SURFACES,
    Brand, BrandRegistry, arabic_technical_terms, brand_signal,
    build_probes, co_occurrence_verdict, enumerate_rotation_candidates, plan,
)


class TestTransliteratedVocabulary(unittest.TestCase):
    """The ecosystem writes technical English in Arabic script. A parser that
    looks for the Arabic *translation* of these words finds nothing."""

    def test_hd_bluray_and_box_office_are_transliterated_not_translated(self):
        got = arabic_technical_terms("جودة اتش دي بلوراي بوكس اوفيس")
        self.assertIn("HD", got)
        self.assertIn("BluRay", got)
        self.assertIn("box office", got)

    def test_brand_names_written_in_arabic_map_to_their_latin_form(self):
        got = arabic_technical_terms("ماي سيما وي سيما ايجي بست")
        self.assertTrue({"mycima", "wecima", "egybest"} <= got, msg=str(got))

    def test_ordinary_arabic_prose_produces_no_false_term(self):
        self.assertEqual(set(), arabic_technical_terms("مسلسل جميل جداً"))

    def test_every_lexicon_slot_is_non_empty_and_lowercase_stable(self):
        for slot, words in LEXICON.items():
            with self.subTest(slot=slot):
                self.assertTrue(words)
                self.assertTrue(all(isinstance(w, str) and w for w in words))


class TestRotationGrammar(unittest.TestCase):
    """The grammar is induced from observed pairs, so it must reproduce them."""

    #: Documented in the TorrentFreak / ACE record of the MyCima shutdown: these
    #: near-identical domains were in circulation as rotation stock.
    OBSERVED_MYCIMA = ("myciiima.autos", "myciiima.bond", "myciiima.boats",
                       "myciiima.makeup", "myciiima.monster")

    def test_reproduces_the_documented_mycima_stock(self):
        cands = set(enumerate_rotation_candidates("mycima"))
        hit = [d for d in self.OBSERVED_MYCIMA if d in cands]
        self.assertGreaterEqual(len(hit), 4,
                                f"grammar reproduced only {hit}")

    def test_reproduces_the_documented_wecima_stock(self):
        cands = set(enumerate_rotation_candidates("wecima"))
        self.assertTrue(any(d.startswith("weciima.") for d in cands),
                        "weciima.* was observed pre-registered before the rebrand")

    def test_reproduces_the_eegebest_lookalike(self):
        """eegebest.com was found carrying keyword metadata for the whole brand
        family, so the vowel-doubling rule is evidenced, not invented."""
        cands = set(enumerate_rotation_candidates("egybest"))
        self.assertIn("eegebest.com", cands)

    def test_only_rotation_tlds_are_used(self):
        cands = enumerate_rotation_candidates("mycima")
        allowed = set(KNOWN_BRANDS[0].observed_tlds) | set(ROTATION_TLDS)
        for d in cands:
            self.assertIn(d.rsplit(".", 1)[1], allowed, msg=d)

    def test_unknown_brand_returns_empty_not_a_guess(self):
        self.assertEqual([], enumerate_rotation_candidates("no-such-brand"))

    def test_max_tlds_bounds_the_output(self):
        """The bound is structural, not a number to keep re-tuning.

        An earlier version asserted ``<= 4 * 12``, which encoded a stem count that
        moved the moment the rotation rules were widened — and a test that fails
        when the grammar gets *better* is measuring the fixture, not the code.
        What actually matters is that ``max_tlds`` caps the TLD axis, so the
        output is an exact multiple of the stem count and grows linearly in
        ``max_tlds``.
        """
        from qarin.discover import _stems, BrandRegistry as _BR
        stems = len(_stems(_BR().brands["mycima"]))
        n4 = len(enumerate_rotation_candidates("mycima", max_tlds=4))
        n8 = len(enumerate_rotation_candidates("mycima", max_tlds=8))
        self.assertEqual(4 * stems, n4, f"expected {stems} stems")
        self.assertEqual(8 * stems, n8)
        self.assertGreater(n8, n4)

    def test_rotation_tld_set_contains_the_observed_ones(self):
        for tld in ("autos", "bond", "boats", "makeup", "monster", "tube", "codes"):
            self.assertIn(tld, ROTATION_TLDS, msg=tld)


class TestBrandRegistry(unittest.TestCase):
    def test_documented_scale_figures_are_attached_with_sources(self):
        """These are third-party estimates from rights-holder filings. They are
        kept as scale context and are never a measurement of this platform's own,
        which is why every one of them carries a citation."""
        reg = BrandRegistry()
        for bid, visits in (("mycima", 50_000_000), ("shahid4u", 155_000_000),
                            ("faselhd", 30_000_000), ("laroza", 7_000_000),
                            ("wecima", 18_000_000)):
            b = reg.brands[bid]
            with self.subTest(brand=bid):
                self.assertEqual(visits, b.peak_monthly_visits)
                self.assertTrue(b.source, "a scale figure with no citation is rumour")

    def test_lineage_is_recorded_as_an_edge_not_a_replacement(self):
        reg = BrandRegistry()
        self.assertIn("mycima", reg.brands["wecima"].successor_of)
        self.assertEqual(("wecima",), reg.successors_of("mycima"))
        self.assertEqual(("mycima", "egybest"), reg.brands["wecima"].successor_of)

    def test_tolerates_both_arabic_and_latin_mentions(self):
        reg = BrandRegistry()
        toks = reg.tokens()
        self.assertEqual("mycima", toks["mycima"])
        self.assertIn("ماي سيما", [n for b in reg.brands.values() for n in b.names])

    def test_every_brand_has_at_least_one_latin_spelling(self):
        for b in KNOWN_BRANDS:
            with self.subTest(brand=b.id):
                self.assertTrue(b.latin)
                self.assertTrue(b.names)


class TestProbes(unittest.TestCase):
    def test_reproduces_the_documented_title_pattern(self):
        """The observed pattern is: name + year + dubbed/translated + quality +
        brand names. A probe set that does not contain that shape is not
        reproducing the method it claims to encode."""
        p = build_probes("الراهب", "Al Raheb", year="2026")
        qs = [x.query for x in p]
        self.assertTrue(any("مدبلج" in q and "2026" in q for q in qs),
                        msg="no dubbed+year probe")
        self.assertTrue(any("HD" in q for q in qs), msg="no quality probe")
        self.assertTrue(any(x.brand_tokens for x in p), msg="no brand probe")

    def test_mixes_scripts_in_one_string(self):
        """Observed real page titles are bidirectional — Arabic text carrying
        'Sherlock Holmes: A Game of Shadows hd' inline. A monolingual generator
        misses them, so mixed-script probes must exist and be labelled."""
        p = build_probes("الراهب", "Al Raheb")
        mixed = [x for x in p if x.script == "mixed"]
        self.assertTrue(mixed)
        self.assertTrue(any("1080p" in x.query for x in mixed))

    def test_brand_probes_record_which_brands_so_a_hit_is_attributable(self):
        """Adding a competitor brand is what makes the method work, and it is
        also what pollutes precision. A hit must be attributable to the brand
        term or to the title, so a false positive on 'mycima' alone is never
        logged as an infringement of the work."""
        p = build_probes("الراهب", "Al Raheb")
        for x in p:
            if x.brand_tokens:
                self.assertTrue(all(t in {b.id for b in KNOWN_BRANDS}
                                    for t in x.brand_tokens), msg=str(x.brand_tokens))
        self.assertTrue(any(len(x.brand_tokens) > 1 for x in p))

    def test_include_brand_can_be_turned_off(self):
        p = build_probes("الراهب", "Al Raheb", include_brand=False)
        self.assertEqual([], [x for x in p if x.brand_tokens])
        self.assertTrue(p, "turning brands off must not empty the probe set")

    def test_no_duplicate_queries(self):
        p = build_probes("الراهب", "Al Raheb", year="2026")
        keys = [x.query for x in p]
        self.assertEqual(len(keys), len(set(keys)), "duplicate probes inflate yield")

    def test_missing_title_yields_nothing(self):
        # Only a missing *title* empties the set. An empty unit is a valid
        # choice — it omits the word "film"/"series" and still searches — so it
        # must keep producing probes rather than silently returning nothing.
        self.assertEqual([], build_probes(None, None))
        bare = build_probes("الراهب", None, unit="")
        self.assertTrue(bare)
        self.assertFalse(any("  " in b.query for b in bare))

    def test_episodic_instalment_probes_exist(self):
        p = build_probes("الراهب", None)
        self.assertTrue(any("الحلقة" in x.query for x in p))


class TestIndependenceAccounting(unittest.TestCase):
    """The refinement. Keyword variety buys recall inside a surface; it buys
    nothing in fleet coverage. A plan must say so about itself."""

    def test_a_thousand_probes_on_one_surface_is_one_detector(self):
        p = build_probes("الراهب", "Al Raheb", year="2026")
        pl = plan(p)
        self.assertEqual(1, pl.n_surfaces)
        self.assertGreater(len(pl.probes), 50)
        self.assertIn("ONE detector", pl.independence_note())

    def test_surface_count_is_what_independence_charges(self):
        from qarin.discover import Probe
        ps = [Probe("a", "search_index", "t", "ar"),
              Probe("b", "search_index", "t", "ar"),
              Probe("c", "telegram", "t", "ar"),
              Probe("d", "iptv_manifest", "t", "latn")]
        pl = plan(ps)
        self.assertEqual(3, pl.n_surfaces)
        self.assertEqual(4, len(pl.probes))
        self.assertIn("3 surfaces", pl.independence_note())

    def test_surfaces_are_distinct_in_kind_not_in_wording(self):
        self.assertGreaterEqual(len(SURFACES), 8)
        self.assertEqual(len(SURFACES), len(set(SURFACES)))
        for s in ("search_index", "telegram", "iptv_manifest", "torrent_swarm",
                  "app_store", "ugc", "new_domain_feed"):
            self.assertIn(s, SURFACES, msg=s)

    def test_every_probe_lands_on_a_declared_surface(self):
        p = build_probes("الراهب", "Al Raheb")
        for x in p:
            self.assertIn(x.surface, SURFACES, msg=x.surface)

    def test_probes_are_marked_non_independent_by_default(self):
        """No two search-index probes may claim independence, because they share
        one index. The field exists so the claim has to be made explicitly
        rather than assumed."""
        p = build_probes("الراهب", "Al Raheb")
        self.assertTrue(all(not x.independent for x in p))


class TestBrandCoOccurrence(unittest.TestCase):
    """The pirates bid on each other's names, so co-occurrence is the signal.
    One mention is not, and the tiers exist so a weak signal is recorded without
    being asserted."""

    def test_single_mention_is_not_evidence(self):
        got = brand_signal("شاهد فيلم الراهب على ماي سيما")
        self.assertEqual(("mycima",), got)
        self.assertEqual("MENTION_ONLY", co_occurrence_verdict(got))

    def test_family_stack_is_rotation_stock(self):
        """eegebest.com carried the whole family in one meta block. No innocent
        party bids on six competitors."""
        text = ("egybest mycima wecima cima4u arabseed akwam faselhd "
                "افلام مترجمة")
        got = brand_signal(text)
        self.assertGreaterEqual(len(got), CO_OCCURRENCE_MIN, msg=str(got))
        self.assertEqual("ROTATION_STOCK", co_occurrence_verdict(got))

    def test_arabic_script_brands_are_matched_too(self):
        got = brand_signal("ماي سيما وي سيما ايجي بست شاهد فور يو")
        self.assertGreaterEqual(len(got), 4, msg=str(got))
        self.assertEqual("ROTATION_STOCK", co_occurrence_verdict(got))

    def test_two_brands_is_corroborating_not_conclusive(self):
        got = brand_signal("mycima wecima افلام")
        self.assertEqual(2, len(got), msg=str(got))
        self.assertEqual("CORROBORATING", co_occurrence_verdict(got))

    def test_no_brands_returns_empty_not_a_default(self):
        self.assertEqual((), brand_signal("مسلسل عربي جميل"))
        self.assertEqual("NONE", co_occurrence_verdict(()))

    def test_succession_is_detectable_from_a_document(self):
        """The strongest operator finding available without anybody's
        cooperation, because the successor advertises itself as the heir
        (بديل ماي سيما)."""
        got = brand_signal("وي سيما الجديد 2023 بديل ماي سيما mycima wecima")
        self.assertTrue({"mycima", "wecima"} <= set(got), msg=str(got))
        from qarin.discover import lineage_edge
        self.assertTrue(lineage_edge("wecima", "mycima", got))
        self.assertFalse(lineage_edge("laroza", "mycima", got),
                         "unrelated brands must not fabricate a lineage edge")


class TestPolicy(unittest.TestCase):
    """Discovery is for observation. Nothing here may become a distribution
    channel or a harassment tool."""

    def test_no_probe_contains_a_media_or_stream_reference(self):
        banned = ("m3u8", ".mp4", "magnet:", "playlist.m3u", "chunklist")
        p = build_probes("الراهب", "Al Raheb", year="2026")
        for x in p:
            with self.subTest(query=x.query):
                for b in banned:
                    self.assertNotIn(b, x.query.lower())

    def test_rotation_candidates_are_names_not_urls(self):
        cands = enumerate_rotation_candidates("mycima")
        for d in cands:
            self.assertNotIn("/", d)
            self.assertNotIn("http", d)
            self.assertGreaterEqual(d.count("."), 1)

    def test_surface_hints_name_surfaces_not_works(self):
        from qarin.discover import SURFACE_HINTS
        self.assertTrue(set(SURFACE_HINTS.values()) <= set(SURFACES) | {"whatsapp", "torrent"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
