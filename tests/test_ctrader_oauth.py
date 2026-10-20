"""Offline tests: official read-only scope, cookie-bound callback and secret-free output."""
import datetime as dt
import http.client
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import ctrader_oauth as oauth
import ctrader_tokens
import private_server as server

REDIRECT="https://remura.example-tailnet.ts.net/private-api/ctrader/callback"
ENV={"CTRADER_OAUTH_ENABLED":"1","CTRADER_CLIENT_ID":"test-id",
     "CTRADER_CLIENT_SECRET":"test-secret","CTRADER_REDIRECT_URI":REDIRECT}


class OAuthUnitTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=Path(self.tmp.name)/"private"/"remura-prices.sqlite3"

    def tearDown(self):
        self.tmp.cleanup()

    def test_accounts_only_authorization_and_tailscale_requirement(self):
        client_id,_,redirect=oauth.settings(ENV)
        url=oauth.authorization_url(client_id,redirect)
        fields=parse_qs(urlsplit(url).query)
        self.assertEqual(fields["scope"],["accounts"])
        self.assertEqual(fields["redirect_uri"],[REDIRECT])
        self.assertNotIn("test-secret",url)
        for bad in ("https://public.example.com"+oauth.CALLBACK_PATH,
                    "http://remura.example-tailnet.ts.net"+oauth.CALLBACK_PATH,
                    REDIRECT+"?unsafe=1",
                    REDIRECT.replace("/callback","/other")):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    oauth.settings({**ENV,"CTRADER_REDIRECT_URI":bad})
        with self.assertRaises(ValueError):
            oauth.settings({**ENV,"CTRADER_OAUTH_ENABLED":"0"})

    def test_code_exchange_saves_tokens_privately_without_echo(self):
        seen=[]
        def fake(req):
            seen.append(req.full_url)
            self.assertEqual(req.get_method(),"GET")
            self.assertEqual(parse_qs(urlsplit(req.full_url).query)["grant_type"],["authorization_code"])
            return {"accessToken":"private-access","refreshToken":"private-refresh",
                    "tokenType":"bearer","expiresIn":2628000,"errorCode":None}
        self.assertTrue(oauth.exchange_code(self.db,"one-time-code","test-id","test-secret",REDIRECT,
                     now=dt.datetime(2026,10,20,tzinfo=dt.timezone.utc),requester=fake))
        self.assertEqual(len(seen),1)
        stored=ctrader_tokens.read_file(ctrader_tokens.path_for(self.db))
        self.assertEqual(stored["refreshToken"],"private-refresh")
        self.assertTrue(server.source_configured({**ENV,"CTRADER_ACCOUNT_ID":"123"},self.db))
        if os.name!="nt":
            self.assertEqual(ctrader_tokens.path_for(self.db).stat().st_mode & 0o777,0o600)

    def test_failed_exchange_never_overwrites_credentials(self):
        ctrader_tokens.safe_write(ctrader_tokens.path_for(self.db),
                                 {"accessToken":"good","refreshToken":"old","expiresAt":"2026-12-01T00:00:00Z"})
        with self.assertRaisesRegex(RuntimeError,"rifiutato"):
            oauth.exchange_code(self.db,"one-time-code","test-id","test-secret",REDIRECT,
                                requester=lambda req: {"errorCode":"invalid","description":"secret"})
        self.assertEqual(ctrader_tokens.read_file(ctrader_tokens.path_for(self.db))["refreshToken"],"old")


class OAuthHttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=Path(self.tmp.name)/"private"/"remura-prices.sqlite3"
        self.env=patch.dict(os.environ,ENV,clear=True)
        self.env.start()
        self.http=server.ThreadingHTTPServer(("127.0.0.1",0),server.http_handler(self.db))
        self.worker=threading.Thread(target=self.http.serve_forever,daemon=True)
        self.worker.start()

    def tearDown(self):
        self.http.shutdown()
        self.http.server_close()
        self.worker.join(5)
        self.env.stop()
        self.tmp.cleanup()
        with server.OAUTH_LOCK:
            server.OAUTH_PENDING.clear()

    def get(self,path,cookie=None):
        conn=http.client.HTTPConnection("127.0.0.1",self.http.server_port,timeout=5)
        headers={"Cookie":cookie} if cookie else {}
        conn.request("GET",path,headers=headers)
        response=conn.getresponse()
        body=response.read().decode()
        status=response.status
        headers=dict(response.getheaders())
        conn.close()
        return status,headers,body

    def test_browser_flow_cookie_binding_and_no_token_in_browser(self):
        status,headers,body=self.get(oauth.START_PATH)
        self.assertEqual(status,302)
        self.assertIn("scope=accounts",headers["Location"])
        self.assertNotIn("test-secret",headers["Location"])
        self.assertEqual(body,"")
        self.assertIn("Secure",headers["Set-Cookie"])
        self.assertIn("HttpOnly",headers["Set-Cookie"])
        cookie=headers["Set-Cookie"].split(";",1)[0]
        called=[]
        with patch.object(server,"exchange_code",side_effect=lambda *a: called.append(a) or True):
            unauthorized,h,_=self.get(oauth.CALLBACK_PATH+"?code=private-code")
            self.assertEqual(unauthorized,303)
            self.assertEqual(h["Location"],"/private-api/ctrader/failed")
            authorized,h,_=self.get(oauth.CALLBACK_PATH+"?code=private-code",cookie=cookie)
            self.assertEqual(authorized,303)
            self.assertEqual(h["Location"],"/private-api/ctrader/connected")
            self.assertNotIn("private-code",str(h))
            replay,h,_=self.get(oauth.CALLBACK_PATH+"?code=private-code",cookie=cookie)
            self.assertEqual(replay,303)
            self.assertEqual(h["Location"],"/private-api/ctrader/failed")
        self.assertEqual(len(called),1)
        self.assertEqual(called[0][1],"private-code")

    def test_no_approval_no_redirect(self):
        with patch.dict(os.environ,{"CTRADER_OAUTH_ENABLED":"0"}):
            status,headers,body=self.get(oauth.START_PATH)
            self.assertEqual(status,503)
            self.assertNotIn("Location",headers)
            self.assertNotIn("test-secret",body)

if __name__=="__main__":
    unittest.main()
