"""Synthetic-only future CVD event ledger tests; not imported by LIVE."""
from datetime import datetime, timedelta, timezone
import json
import sqlite3
import unittest
from unittest.mock import patch

from scripts import cvd_divergence as detector
from scripts import shark_cvd_ledger as ledger

UTC = timezone.utc
START = datetime(2026, 11, 2, 0, 0, tzinfo=UTC)
SECRET = b"test-only-stable-key-not-for-live-use"
COLLECTED = "2026-11-02T06:20:00.000Z"
NOW = datetime(2026, 11, 2, 6, 25, tzinfo=UTC)
QUALITY = {"dataQualityVerified": True, "closedM15": True,
           "contiguousSession": True, "tickVolumeComplete": True,
           "h1Ready": True}


def event():
    rows = []
    for i in range(25):
        low = 10.0 if i == 10 else (9.7 if i == 22 else 10.4)
        rows.append({
            "t": int((START+timedelta(minutes=i*15)).timestamp()*1000),
            "o": 10.8, "h": 11.2, "l": low, "c": 11.0, "v": 100
        })
    market = {"symbol": "EURUSD", "provider": "ctrader",
              "providerSymbol": "PRIVATE_BROKER_CODE_NOT_FOR_PUBLIC",
              "frames": {"M15": rows, "H1": [], "H4": []}}
    report = detector.analyze(market, now=rows[-1]["t"]+900000+60000)
    assert report["status"] == "ok" and len(report["events"]) == 1
    return report["events"][0]


def save(db, ev=None, q=None, **kwargs):
    return ledger.append(
        db, event() if ev is None else ev, QUALITY if q is None else q,
        source_collected_at=kwargs.pop("source_collected_at", COLLECTED),
        hmac_secret=kwargs.pop("hmac_secret", SECRET),
        now=kwargs.pop("now", NOW), **kwargs)


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        ledger.ensure_schema(self.db)

    def tearDown(self):
        self.db.close()

    def test_actual_detector_event_is_recorded_without_identifiers_or_prices(self):
        ev = event()
        self.assertEqual(save(self.db)["state"], "RECORDED")
        report = ledger.aggregate(self.db)
        self.assertEqual(report["events"], 1)
        self.assertFalse(report["isLiveActive"])
        self.assertFalse(report["alertsEnabled"])
        self.assertEqual(report["newBrokerCalls"], 0)
        dump = "\n".join(self.db.iterdump())
        self.assertNotIn(ev["id"], dump)
        self.assertNotIn(ev["providerSymbol"], dump)
        self.assertNotIn("10.8", dump)
        self.assertNotIn("tickVolumeBetweenAndConfirmation", dump)
        self.assertNotIn(ev["id"], json.dumps(report))

    def test_duplicate_event_is_not_recorded_twice(self):
        self.assertEqual(save(self.db)["state"], "RECORDED")
        self.assertEqual(save(self.db, now=NOW+timedelta(minutes=2))["state"],
                         "DUPLICATE")
        self.assertEqual(ledger.aggregate(self.db)["events"], 1)

    def test_prohibit_update_delete_of_future_evidence(self):
        save(self.db)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE research_cvd_observations SET side='bearish'")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("DELETE FROM research_cvd_observations")
        self.assertEqual(ledger.aggregate(self.db)["events"], 1)

    def test_reject_stale_event_or_future_collection(self):
        with self.assertRaises(ValueError):
            save(self.db, now=NOW+timedelta(hours=2))
        with self.assertRaises(ValueError):
            save(self.db,source_collected_at="2026-11-02T06:30:00.000Z")
        self.assertEqual(ledger.aggregate(self.db)["events"], 0)

    def test_incomplete_quality_blocks_appending_technical_event(self):
        for name in QUALITY:
            q = dict(QUALITY)
            q[name] = False
            with self.assertRaises(ValueError):
                save(self.db, q=q)
        self.assertEqual(ledger.aggregate(self.db)["events"], 0)

    def test_no_backdated_event_or_forged_pivot_id(self):
        ev = event()
        ev["id"] += "misleading"
        with self.assertRaises(ValueError):
            save(self.db,ev=ev)
        ev = event()
        ev["confirmedAt"] = "2026-11-02T06:00:00.000Z"
        with self.assertRaises(ValueError):
            save(self.db,ev=ev)
        self.assertEqual(ledger.aggregate(self.db)["events"], 0)

    def test_invalid_secret_and_unsupported_symbols_rejected(self):
        with self.assertRaises(ValueError):
            save(self.db,hmac_secret=b"short")
        ev = event()
        ev["symbol"] = "NAS100"
        with self.assertRaises(ValueError):
            save(self.db,ev=ev)

    def test_capacity_is_bounded_and_rejects_new_identifiers(self):
        with patch.object(ledger, "MAX_EVENTS", 1):
            self.assertEqual(save(self.db)["state"],"RECORDED")
            ev = event()
            ev["providerSymbol"] = "SECOND_PRIVATE_BROKER_CODE"
            ev["id"] = ev["id"].replace(
                "PRIVATE_BROKER_CODE_NOT_FOR_PUBLIC",
                "SECOND_PRIVATE_BROKER_CODE")
            with self.assertRaises(ValueError):
                save(self.db,ev=ev)
            self.assertEqual(ledger.aggregate(self.db)["events"],1)

    def test_naive_clock_and_uninitialized_connection_fail_closed(self):
        with self.assertRaises(ValueError):
            save(self.db,now=NOW.replace(tzinfo=None))
        with sqlite3.connect(":memory:") as db:
            with self.assertRaises(sqlite3.OperationalError):
                save(db)

if __name__ == "__main__":
    unittest.main()
