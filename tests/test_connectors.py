from __future__ import annotations

import json
import unittest

from qarin.connectors import FeedError, fetch_ct_rows, fetch_rss_rows


class Response:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return self.payload


class TestConnectors(unittest.TestCase):
    def opener(self, response):
        return lambda request, timeout: response

    def test_normalises_multiline_ct_names(self):
        payload = json.dumps([
            {"name_value": "Alpha.com\n*.Alpha.com\n"},
            {"name_value": ""},
            {"other": "ignored"},
        ]).encode()
        rows = fetch_ct_rows("https://feed.invalid", observed_at="2026-11-05T02:00:00Z",
                             opener=self.opener(Response(payload)))
        self.assertEqual(("alpha.com", "*.alpha.com"), tuple(row.name for row in rows))

    def test_rejects_non_array_response(self):
        with self.assertRaises(FeedError):
            fetch_ct_rows("https://feed.invalid", observed_at="2026-11-05T02:00:00Z",
                          opener=self.opener(Response(b"{}")))

    def test_transport_error_is_explicit(self):
        def broken(request, timeout):
            raise TimeoutError("slow")
        with self.assertRaisesRegex(FeedError, "public feed request failed"):
            fetch_ct_rows("https://feed.invalid", observed_at="2026-11-05T02:00:00Z",
                          opener=broken)

    def test_rss_connector_keeps_only_public_link_hosts(self):
        payload = b'''<rss><channel><item><link>https://Alpha.example/path?q=1</link></item>
        <item><link href="https://Beta.example/watch" /></item></channel></rss>'''
        rows = fetch_rss_rows("https://feed.invalid", observed_at="2026-11-05T02:00:00Z",
                              opener=self.opener(Response(payload)))
        self.assertEqual(("alpha.example", "beta.example"),
                         tuple(row.name for row in rows))
        self.assertTrue(all(row.source == "public_feed" for row in rows))

    def test_rss_connector_rejects_invalid_xml(self):
        with self.assertRaisesRegex(FeedError, "invalid XML"):
            fetch_rss_rows("https://feed.invalid", observed_at="2026-11-05T02:00:00Z",
                           opener=self.opener(Response(b"<broken>")))
