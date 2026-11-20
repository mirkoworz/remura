# REMURA Experience v0.22 LAB — 20/11/2026 CET
# Chromium against a dedicated fixture; not the original cinematic HTML.
import json, subprocess, unittest
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f=json.loads(subprocess.check_output(['python3',str(ROOT/'fixture_reply_v021.py')]))
        html=(ROOT/'home_v022_fixture.html').read_text()
        cls.markup,script=html.split('<script type="module">',1)
        script=script.split('</script>',1)[0]
        cls.js='\n'.join((ROOT/n).read_text().replace('export function ','function ') for n in ('validate_shared_fixture_v011.mjs','consumer_v021.mjs','home_v022.mjs'))
        cls.js='\n'.join(line for line in (cls.js+'\n'+script).splitlines() if not line.startswith('import '))
        # Independent in-memory fixture, not URL navigation or production packaging.
        cls.p=sync_playwright().start();cls.browser=cls.p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    @classmethod
    def tearDownClass(cls):cls.browser.close();cls.p.stop();
    def setUp(self):
        self.ctx=self.browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
        self.external=[];self.errors=[]
        def route(r):
            self.external.append(r.request.url);r.abort()
        self.ctx.route('**/*',route);self.page=self.ctx.new_page();self.page.on('pageerror',lambda e:self.errors.append(str(e)))
        self.page.set_content(self.markup+'</body></html>');self.page.add_script_tag(content=self.js);self.page.wait_for_function('window.fixture !== undefined')
        self.assertEqual(self.page.evaluate('f=>fixture.start(f)',self.f),'READY')
    def tearDown(self):self.ctx.close();self.assertEqual(self.external,[]);self.assertEqual(self.errors,[])
    def text(self,selector='#panel'):return self.page.locator(selector).inner_text()
    def time(self,t):self.page.evaluate('t=>fixture.time(t)',t)
    def test_price(self):self.assertIn('1.25',self.text())
    def test_cot(self):self.page.click('#cot');self.assertIn('28 coppie',self.text())
    def test_expiry_timer(self):
        self.time(self.f['now']+1);self.page.wait_for_function("document.querySelector('#panel').innerText.includes('N/D')");self.assertNotIn('1.25',self.text())
    def test_focus_expiry(self):
        self.time(self.f['now']+900001);self.page.evaluate("dispatchEvent(new Event('focus'))");self.assertEqual(self.text('#status'),'N/D');self.assertNotIn('1.25',self.text())
    def test_visibility_expiry(self):
        self.time(self.f['now']+900001);self.page.evaluate("document.dispatchEvent(new Event('visibilitychange'))");self.assertEqual(self.text('#status'),'N/D')
    def test_draft_survives_timer(self):
        self.page.click('#draft');self.page.fill('#level','1.23456');self.time(self.f['now']+1);self.page.wait_for_timeout(30);self.assertEqual(self.page.input_value('#level'),'1.23456')
    def test_draft_survives_refresh(self):
        self.page.click('#draft');self.page.fill('#level','1.23456');self.page.click('#refresh');self.page.wait_for_function("!document.querySelector('#refresh').disabled");self.assertEqual(self.page.input_value('#level'),'1.23456')
    def test_logout_clears_dom(self):self.page.click('#logout');self.assertEqual(self.text(),'');self.assertEqual(self.text('#status'),'Sessione chiusa')
    def test_logout_during_refresh(self):
        self.page.evaluate('fixture.delay(80)');self.page.click('#refresh');self.page.click('#logout');self.page.wait_for_timeout(120);self.assertEqual(self.text(),'');self.assertEqual(self.text('#status'),'Sessione chiusa')
    def test_denied_clears_draft(self):
        self.page.click('#draft');self.page.fill('#level','123');self.page.evaluate('fixture.reply({status:403})');self.page.click('#refresh');self.page.wait_for_function("document.querySelector('#status').innerText==='Sessione chiusa'");self.assertEqual(self.page.locator('#level').count(),0)
    def test_no_polling(self):
        self.time(self.f['now']+1);self.page.wait_for_timeout(40);self.page.evaluate("dispatchEvent(new Event('focus'))");self.assertEqual(self.page.evaluate('fixture.requests()'),1)
    def test_manual_refresh(self):self.page.click('#refresh');self.page.wait_for_function('fixture.requests()===2');self.assertEqual(self.page.evaluate('fixture.requests()'),2)
    def test_bad_response_hides_old(self):
        self.page.evaluate('fixture.reply({status:503})');self.page.click('#refresh');self.page.wait_for_function("document.querySelector('#status').innerText==='N/D'");self.assertNotIn('1.25',self.text())
    def test_role_loss(self):
        self.page.evaluate("fixture.role('OWNER');fixture.sync()");self.assertEqual(self.text(),'');self.assertEqual(self.text('#status'),'Sessione chiusa')
    def test_pagehide(self):self.page.evaluate("dispatchEvent(new Event('pagehide'))");self.assertEqual(self.text(),'');self.assertEqual(self.text('#status'),'Sessione chiusa')
if __name__=='__main__':unittest.main()
