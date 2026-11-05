from __future__ import annotations

import unittest

from qarin.source_catalog import PublicSource, coverage_sources, public_sources


class TestSourceCatalog(unittest.TestCase):
    def test_inventory_separates_context_from_coverage(self):
        sources = public_sources()
        self.assertEqual({source.source_id for source in sources},
                         {"bbc-arabic-rss", "certificate-transparency"})
        self.assertEqual([source.source_id for source in coverage_sources()],
                         ["certificate-transparency"])

    def test_ct_query_is_explicitly_private(self):
        source = coverage_sources()[0]
        self.assertTrue(source.requires_private_query)
        self.assertIn("{private_query}", source.endpoint)

    def test_credentials_are_rejected_from_source_endpoints(self):
        with self.assertRaisesRegex(ValueError, "credentials"):
            PublicSource("bad", "rss", "https://example.test/?token=secret",
                         30, "test", False)

    def test_cadence_and_kind_are_validated(self):
        with self.assertRaisesRegex(ValueError, "cadence"):
            PublicSource("bad", "rss", "https://example.test/feed", 0,
                         "test", False)
        with self.assertRaisesRegex(ValueError, "unsupported"):
            PublicSource("bad", "api", "https://example.test/feed", 30,
                         "test", False)
