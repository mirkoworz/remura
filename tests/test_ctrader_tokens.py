"""Offline tests for cTrader private refresh tokens: no real API request or credentials."""
import datetime as dt
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import ctrader_tokens as auth

NOW=dt.datetime(2026,10,17,9,0,tzinfo=dt.timezone.utc)
KEYS={"CTRADER_CLIENT_ID":"local-id","CTRADER_CLIENT_SECRET":"local-secret",
      "CTRADER_REFRESH_TOKEN":"old-private-refresh"}
CALLS=[]

def fake_refresh(request):
    CALLS.append(request.full_url)
    assert request.get_method()=="POST"
    assert "grant_type=refresh_token" in request.full_url
    return {"accessToken":"new-private-access","refreshToken":"new-private-refresh",
            "expiresIn":2628000,"errorCode":None}

class TokenTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=Path(self.tmp.name)/"private"/"prices.sqlite3"
        CALLS.clear()
    def tearDown(self):
        self.tmp.cleanup()

    def test_first_consent_token_is_exchanged_and_stored_privately(self):
        received=auth.access_token(self.db,env=KEYS,now=NOW,requester=fake_refresh)
        self.assertEqual(received,"new-private-access")
        file=auth.path_for(self.db)
        self.assertTrue(file.is_file())
        stored=auth.read_file(file)
        self.assertEqual(stored["refreshToken"],"new-private-refresh")
        if os.name!="nt":
            self.assertEqual(file.stat().st_mode & 0o777,0o600)

    def test_reuses_valid_access_token_without_network(self):
        auth.access_token(self.db,env=KEYS,now=NOW,requester=fake_refresh)
        second=auth.access_token(self.db,env=KEYS,now=NOW+dt.timedelta(days=3),
            requester=lambda req: (_ for _ in ()).throw(AssertionError("unnecessary API call")))
        self.assertEqual(second,"new-private-access")
        self.assertEqual(len(CALLS),1)

    def test_refresh_failure_preserves_previous_refresh_token(self):
        auth.access_token(self.db,env=KEYS,now=NOW,requester=fake_refresh)
        old=auth.read_file(auth.path_for(self.db))
        def reject(request):return {"errorCode":"INVALID","description":"do not expose token"}
        with self.assertRaisesRegex(RuntimeError,"rejected"):
            auth.access_token(self.db,env=KEYS,now=NOW+dt.timedelta(days=29),requester=reject)
        self.assertEqual(auth.read_file(auth.path_for(self.db)),old)

    def test_refresh_rotates_at_expiry_threshold(self):
        auth.access_token(self.db,env=KEYS,now=NOW,requester=fake_refresh)
        token=auth.access_token(self.db,env=KEYS,now=NOW+dt.timedelta(days=29),requester=fake_refresh)
        self.assertEqual(token,"new-private-access")
        self.assertEqual(len(CALLS),2)
        self.assertGreater(dt.datetime.fromisoformat(auth.read_file(auth.path_for(self.db))["expiresAt"]), NOW+dt.timedelta(days=29))

    def test_isolated_backup_token_file(self):
        normal=auth.path_for(self.db)
        backup=auth.path_for(self.db,source="backup")
        self.assertNotEqual(normal,backup)
        with self.assertRaises(ValueError):
            auth.path_for(self.db,source="../../private")
        auth.access_token(self.db,env=KEYS,now=NOW,requester=fake_refresh,source="backup")
        self.assertTrue(backup.is_file())
        self.assertFalse(normal.exists())

    def test_missing_token_never_generates_random_credentials(self):
        with self.assertRaisesRegex(RuntimeError,"token missing"):
            auth.access_token(self.db,env={"CTRADER_CLIENT_ID":"x"},now=NOW)

if __name__=="__main__":
    unittest.main()
