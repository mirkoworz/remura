# REMURA Contributors v0.87 LAB — only new iPhone pilot-preview contract tests.
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent
PREVIEW = ROOT / "contributors_pilot_preview_v087_lab.html"

class Inspect(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.start=[]
        self.ids=set()
        self.links=[]
        self.text=[]
        self.csp=None
        self.version_text=[]
        self._version=False
    def handle_starttag(self,tag,attrs):
        attr=dict(attrs);self.start.append((tag,attr))
        if "id" in attr:
            if attr["id"] in self.ids: raise ValueError("duplicate_id")
            self.ids.add(attr["id"])
        if tag=="a": self.links.append(attr.get("href"))
        if tag=="meta" and attr.get("http-equiv")=="Content-Security-Policy": self.csp=attr.get("content")
        if attr.get("id")=="version":self._version=True
    def handle_endtag(self,tag):
        if tag=="div" and self._version:self._version=False
    def handle_data(self,data):
        self.text.append(data)
        if self._version:self.version_text.append(data)

class PilotPreviewNewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=PREVIEW.read_text(encoding="utf-8")
        cls.parser=Inspect();cls.parser.feed(cls.source)
    def test_01_document_single_file(self):
        self.assertLess(len(self.source.encode()),23000)
    def test_02_version_top(self):
        self.assertIn("Contributors v0.87 LAB",''.join(self.parser.version_text))
        self.assertIn("21/11/2026 18:26 CET",''.join(self.parser.version_text))
        self.assertLess(self.source.index('id="version"'),self.source.index("<main"))
    def test_03_no_javascript(self):
        self.assertNotIn("<script",self.source.lower())
        self.assertNotIn("javascript:",self.source.lower())
    def test_04_no_forms_or_credentials(self):
        tags={k for k,a in self.parser.start}
        self.assertFalse(tags.intersection({"form","input","textarea","select"}))
    def test_05_no_fetch_or_api_calls(self):
        self.assertNotIn("fetch(",self.source)
        self.assertNotIn("XMLHttpRequest",self.source)
        self.assertNotIn("localStorage",self.source)
    def test_06_all_links_local(self):
        self.assertTrue(self.parser.links)
        self.assertTrue(all(isinstance(x,str) and x.startswith("#") and x[1:] in self.parser.ids for x in self.parser.links))
    def test_07_two_roles_visible(self):
        self.assertIn('id="collaboratore"',self.source)
        self.assertIn('id="proprietario"',self.source)
    def test_08_copy_owner_not_contributor_approval(self):
        self.assertIn("approvazione manuale",self.source)
        self.assertIn("OWNER",self.source)
        self.assertIn("propri livelli",self.source)
    def test_09_read_all_write_own(self):
        self.assertIn("consultare REMURA",self.source)
        self.assertIn("esclusivamente i propri livelli",self.source)
    def test_10_d1_unknown_not_zero(self):
        self.assertIn("SCONOSCIUTO",self.source)
        self.assertIn("Non è zero",self.source)
    def test_11_access_unknown(self):
        self.assertIn("DA VERIFICARE",self.source)
    def test_12_no_auto_reserved(self):
        self.assertIn("RESERVED",self.source)
        self.assertIn("nessuno sblocco automatico",self.source)
    def test_13_amendment_separate(self):
        self.assertIn("Registro di amendment separato",self.source)
    def test_14_owner_audit_preserved(self):
        self.assertIn("Audit e stati sospesi",self.source)
    def test_15_csp_network_denied(self):
        self.assertIn("connect-src 'none'",self.parser.csp)
        self.assertIn("script-src 'none'",self.parser.csp)
        self.assertIn("form-action 'none'",self.parser.csp)
    def test_16_responsive(self):
        self.assertIn("viewport-fit=cover",self.source)
        self.assertIn("@media(max-width:420px)",self.source)
    def test_17_accessible_anchors(self):
        self.assertIn('aria-label="Sezioni dell',self.source)
        self.assertIn('aria-labelledby="title-contributor"',self.source)
    def test_18_explicit_no_go(self):
        self.assertIn("STAGING REALE NO-GO",self.source)
        self.assertIn("ANTEPRIMA NON PUBBLICATA",self.source)
    def test_19_meta_noindex(self):
        self.assertIn('content="noindex,nofollow,noarchive"',self.source)
    def test_20_private_pages_not_changed(self):
        self.assertIn("quattro pagine v0.78",self.source)
    def test_21_no_external_resources(self):
        self.assertNotIn("<link ",self.source.lower())
        self.assertNotIn("<img ",self.source.lower())
        self.assertNotIn("<iframe",self.source.lower())
    def test_22_different_owner_and_contributor_titles(self):
        self.assertIn("La tua area",self.source)
        self.assertIn("Pannello proprietario",self.source)
if __name__=="__main__":unittest.main()
