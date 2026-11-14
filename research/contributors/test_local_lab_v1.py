# REMURA Contributors v0.5 LAB — 14/11/2026 23:35 CET
import http.client
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode
from uuid import UUID
from archive_v1 import Archive
from local_lab_v1 import Lab,CATALOG,MAX_BODY

NOW="2026-11-14T22:35:00Z"
class LabTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db=Archive(Path(self.temp.name).resolve(),catalog=CATALOG,contributors=["friend-a","friend-b"],owners=["owner"],synthetic=True)
        self.now=NOW
        self.lab=Lab(self.db,clock=lambda:self.now)
        self.payload=dict(csrf=self.lab.csrf,request_id=str(UUID(int=1)),market="NAS100",provider="PEPPERSTONE",
                          ticker="NAS100",product="CFD",contract="",period="WEEK",kind="DELTA_PEAK",price="21000,50",
                          anchor_utc="2026-11-09T00:00:00Z",observed_utc=NOW,note="<script>synthetic</script>")
    def tearDown(self):
        self.db.close();self.temp.cleanup()
    def post(self,path,data):
        return self.lab.submit(path,urlencode(data).encode())
    def test_end_to_end(self):
        self.assertEqual(self.post("/friend-a",self.payload)["status"],"UNREVIEWED")
        self.assertTrue(self.post("/friend-a",self.payload)["duplicate"])
        self.assertIn("21000.5",self.lab.page("/friend-a"))
        self.assertNotIn("21000.5",self.lab.page("/friend-b"))
        self.assertIn("&lt;script&gt;synthetic",self.lab.page("/owner"))
        self.assertNotIn("<script>",self.lab.page("/owner"))
        p=dict(csrf=self.lab.csrf,entry_id="1",action="APPROVED",reason="synthetic review")
        self.now="2026-11-14T22:35:01Z"
        with self.assertRaises(ValueError):self.post("/friend-a",p)
        self.post("/owner",p)
        self.assertIn("Approvato",self.lab.page("/friend-a"))
        self.assertIn("Revoca approvazione",self.lab.page("/owner"))
        self.now="2026-11-14T22:35:02Z"
        self.post("/owner",dict(p,action="REVOKED"))
        self.assertIn("Revocato",self.lab.page("/friend-a"))
    def test_boundary(self):
        for change in ({"market":"SPX500"},{"product":"SPOT"},{"provider":"OANDA"},{"role":"OWNER"},{"source_group":"forged"}):
            with self.assertRaises(ValueError):self.post("/friend-a",dict(self.payload,**change))
        for token in ("wrong","é",""):
            with self.assertRaises(PermissionError):self.post("/friend-a",dict(self.payload,csrf=token))
        with self.assertRaises(ValueError):self.lab.submit("/friend-a",urlencode(self.payload).encode()+b"&price=1")
        with self.assertRaises(ValueError):self.lab.submit("/friend-a",b"x"*(MAX_BODY+1))
        self.assertNotIn("21000.5",self.lab.page("/owner"))
    def test_render_and_fields(self):
        page=self.lab.page("/friend-a")
        self.assertIn("SOLO DATI FITTIZI",page)
        self.assertLess(page.index("1. Pair"),page.index("2. Broker"))
        for key in self.payload:self.assertIn('name="'+key+'"',page)
        self.assertNotIn("Approva",page)

class LoopbackHTTPTests(unittest.TestCase):
    def test_real_http(self):
        # Child owns its SQLite connection. No external network; ephemeral port.
        script=Path(__file__).with_name("local_lab_v1.py")
        proc=subprocess.Popen([sys.executable,str(script),"--synthetic-lab"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            import select
            ready,_,_=select.select([proc.stdout],[],[],8)
            self.assertTrue(ready,"local child startup")
            line=proc.stdout.readline()
            m=re.search(r"http://127\.0\.0\.1:(\d+)",line)
            self.assertIsNotNone(m,line)
            port=int(m.group(1));origin=f"http://127.0.0.1:{port}"
            def request(method,path,body=None,headers=None):
                conn=http.client.HTTPConnection("127.0.0.1",port,timeout=5)
                try:
                    conn.request(method,path,body,headers or {})
                    res=conn.getresponse();return res.status,res.read().decode(),dict(res.getheaders())
                finally:conn.close()
            status,page,h=request("GET","/friend-a")
            self.assertEqual(status,200);self.assertEqual(h["Cache-Control"],"no-store")
            self.assertIn("form-action 'self'",h["Content-Security-Policy"])
            self.assertEqual(request("GET","/friend-a",headers={"Host":"evil.invalid"})[0],403)
            self.assertEqual(request("GET","/private-api/health")[0],404)
            fields=dict(re.findall(r'<input type="hidden" name="([^"]+)" value="([^"]*)">',page))
            data=dict(fields,market="EURUSD",provider="OANDA",ticker="EURUSD",product="SPOT",period="WEEK",
                      kind="DELTA_PEAK",price="1.0854",anchor_utc=NOW,observed_utc=NOW,note="HTTP synthetic")
            raw=urlencode(data);headers={"Content-Type":"application/x-www-form-urlencoded","Origin":origin}
            self.assertEqual(request("POST","/friend-a",raw,dict(headers,Origin="https://evil.invalid"))[0],403)
            self.assertEqual(request("POST","/friend-a",raw,headers)[0],303)
            self.assertIn("HTTP synthetic",request("GET","/friend-a")[1])
            self.assertNotIn("HTTP synthetic",request("GET","/friend-b")[1])
            owner_page=request("GET","/owner")[1]
            token=re.search(r'name="csrf" value="([^"]+)"',owner_page).group(1)
            review=urlencode(dict(csrf=token,entry_id="1",action="APPROVED",reason="synthetic"))
            self.assertEqual(request("POST","/owner",review,headers)[0],303)
            self.assertIn("Approvato",request("GET","/friend-a")[1])
        finally:
            import signal
            if proc.poll() is None:proc.send_signal(signal.SIGINT)
            try:proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:proc.kill();proc.communicate()

if __name__=="__main__":unittest.main()
