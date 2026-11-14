# REMURA Contributors v0.1 LAB — 14/11/2026 23:16 CET
import unittest
from uuid import UUID
from ledger_v1 import OfflineLedger, Principal

class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.db = OfflineLedger({"FX:EURUSD", "FXCM:EURUSD"}, {"lab-friend"})
        self.actor = Principal("lab-friend", "CONTRIBUTOR")
        self.now = "2026-11-14T21:00:00Z"
        self.p = dict(request_id=str(UUID(int=1)), symbol="FX:EURUSD", period="WEEK",
                      kind="DELTA_PEAK", price="1.08540", observed_utc="2026-11-14T20:00:00Z", note="")
    def tearDown(self):
        self.db.close()
    def submit(self, **changes):
        return self.db.submit(self.actor, dict(self.p, **changes), received_utc=self.now)
    def test_unreviewed(self):
        self.assertEqual(self.submit()["status"], "UNREVIEWED")
    def test_repeat(self):
        a = self.submit()
        b = self.submit(price="1.0854")
        self.assertEqual(a["id"], b["id"])
        self.assertTrue(b["duplicate"])
    def test_conflicting_repeat(self):
        self.submit()
        with self.assertRaises(ValueError):
            self.submit(price="1.09")
    def test_wrong_subject_or_role(self):
        for actor in (Principal("outsider", "CONTRIBUTOR"), Principal("lab-friend", "ADMIN")):
            with self.assertRaises(PermissionError):
                self.db.submit(actor, self.p, received_utc=self.now)
    def test_extra_fields(self):
        for field in ("role", "subject", "received_utc", "status"):
            with self.assertRaises(ValueError):
                self.submit(**{field: "fake"})
    def test_feed_identity(self):
        with self.assertRaises(ValueError):
            self.submit(symbol="EURUSD")
        self.submit(symbol="FXCM:EURUSD")
    def test_invalid_price(self):
        for price in ("NaN", "Infinity", "-1", "0", "1e2", "1,08", "1.123456789", 1.1):
            with self.assertRaises(ValueError):
                self.submit(price=price)
    def test_future_observation(self):
        with self.assertRaises(ValueError):
            self.submit(observed_utc="2026-11-14T21:00:01Z")
    def test_bad_input(self):
        for changes in ({"period":"YEAR"}, {"kind":"BUY"}, {"note":"a"*281},
                        {"note":"a\nb"}, {"observed_utc":"2026-11-14T20:00+01:00"},
                        {"request_id":"bad"}):
            with self.assertRaises(ValueError):
                self.submit(**changes)
    def test_daily_capacity(self):
        for i in range(1,21):
            self.submit(request_id=str(UUID(int=i)))
        with self.assertRaises(ValueError):
            self.submit(request_id=str(UUID(int=21)))
        self.assertTrue(self.submit()["duplicate"])
if __name__ == "__main__":
    unittest.main()
