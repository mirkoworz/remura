# REMURA v0.80 LAB — 20 NEW offline HTML safety/accessibility checks.
from __future__ import annotations
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

PAGE = Path(__file__).with_name("contributors_readiness_v080_lab.html")
HTML = PAGE.read_text(encoding="utf-8")


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags=[]
        self.links=[]
        self.attrs=[]
    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attrs.append((tag,dict(attrs)))
        if tag=="a":
            self.links.append(dict(attrs).get("href",""))


class ReadinessPageTests(unittest.TestCase):
    def test_01_html5_doctype(self):
        self.assertTrue(HTML.lstrip().lower().startswith("<!doctype html>"))

    def test_02_italian_language(self):
        self.assertIn('<html lang="it">',HTML)

    def test_03_version_at_very_top_before_main(self):
        self.assertLess(HTML.index('<header id="version">'),HTML.index("<main>"))

    def test_04_version_v080_lab_is_explicit(self):
        self.assertIn("STAGING READINESS v0.80 LAB",HTML)

    def test_05_italian_date_time_on_banner(self):
        self.assertIn("21/11/2026 17:24 CET (Europe/Rome)",HTML)

    def test_06_static_snapshot_is_not_live(self):
        self.assertIn("SNAPSHOT NON LIVE",HTML)

    def test_07_status_is_no_go(self):
        self.assertIn("STAGING REALE · NO-GO",HTML)

    def test_08_d1_missing_is_not_zero(self):
        self.assertIn("GraphQL senza dati del giorno. Non equivale a zero.",HTML)

    def test_09_access_seats_are_not_claimed_attested(self):
        self.assertIn("Cloudflare Access · posti",HTML)
        self.assertIn("Da verificare",HTML)

    def test_10_new_ci_60_tests_not_historical(self):
        self.assertIn("60 nuovi test sintetici PASS",HTML)

    def test_11_source_lock_14_files_reported(self):
        self.assertIn("14 file fondamentali",HTML)

    def test_12_no_script_tags_or_inline_js(self):
        self.assertNotIn("<script",HTML.lower())
        self.assertNotIn("javascript:",HTML.lower())

    def test_13_no_forms_or_uploads(self):
        self.assertNotIn("<form",HTML.lower())
        self.assertNotIn('type="file"',HTML.lower())

    def test_14_no_iframe_embeds(self):
        self.assertNotIn("<iframe",HTML.lower())
        self.assertNotIn("<object",HTML.lower())

    def test_15_no_external_css_images_or_api_fetch(self):
        self.assertNotIn('<link rel="stylesheet"',HTML)
        self.assertNotIn("<img",HTML.lower())
        self.assertNotIn("fetch(",HTML)

    def test_16_responsive_mobile_viewport(self):
        self.assertIn('name="viewport"',HTML)
        self.assertIn("@media(max-width:410px)",HTML)

    def test_17_no_secrets_or_personal_data(self):
        for needle in ("Bearer ","API_KEY=","CF_ACCOUNT_ID=","@gmail.","PRIVATE_KEY","HMAC_SECRET"):
            self.assertNotIn(needle,HTML)

    def test_18_only_public_github_urls(self):
        parser=Tags();parser.feed(HTML)
        self.assertEqual(len(parser.links),3)
        for url in parser.links:
            self.assertTrue(url.startswith("https://github.com/mirkoworz/remura/"))

    def test_19_headings_have_accessible_labels(self):
        self.assertIn('aria-labelledby="readiness"',HTML)
        self.assertIn('aria-labelledby="boundary"',HTML)

    def test_20_no_fake_release_or_account_activation(self):
        self.assertIn("non può attivare nulla",HTML)
        self.assertIn("non autorizza il deploy",HTML)


if __name__=="__main__":
    unittest.main()
