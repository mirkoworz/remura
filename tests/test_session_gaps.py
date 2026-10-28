"""Pure/offline regression tests for session-gap diagnostics; zero credentials."""
import datetime as dt
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from session_gaps import inspect_market, session_gap_overview
from price_store import connect

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 10, 28, 16, 0, tzinfo=UTC)


def mock_doc(utc_hour=21, skipped=None, provider="CTRADER-SECRET-BROKER"):
    """Fake M15 timestamps only; values never used as real prices."""
    skipped = skipped or set()
    begin = dt.datetime(2026, 10, 20, 0, 0, tzinfo=UTC)
    samples = []
    for i in range(int((NOW - begin).total_seconds() / 900)):
        t = begin + dt.timedelta(minutes=15*i)
        if t.weekday() >= 5:
            continue
        if t.hour == utc_hour or t in skipped:
            continue
        samples.append({"t": t.isoformat()})
    return {"provider": "ctrader", "providerSymbol": provider,
            "timeframes": {"M15": samples}}


class SessionGapTests(unittest.TestCase):
    def test_recurrence_is_utc_constant_across_rome_dst_change(self):
        doc = mock_doc()
        found = inspect_market(doc, NOW)
        self.assertEqual(found["status"], "observed")
        self.assertTrue(found["recurringCandidate"])
        self.assertEqual(found["patterns"][0]["startUtc"], "21:00")
        self.assertEqual(found["patterns"][0]["missingM15"], 4)
        self.assertGreaterEqual(found["patterns"][0]["observedDays"], 4)

    def test_ctrader_session_wallclock_matches_same_utc_gap_across_dst(self):
        from zoneinfo import ZoneInfo
        rome = ZoneInfo("Europe/Rome")
        # Platform displayed CET 22:00–23:00 on 27 October, while the
        # same 21:00–22:00 UTC interval read 23:00–00:00 in CEST.
        for day, local_hour in ((dt.date(2026,10,22),23),
                                (dt.date(2026,10,27),22)):
            utc_start = dt.datetime.combine(day,dt.time(21),tzinfo=UTC)
            local_start = utc_start.astimezone(rome)
            self.assertEqual(local_start.hour,local_hour)
            self.assertEqual((utc_start+dt.timedelta(hours=1)).astimezone(rome).hour,
                             (local_hour+1)%24)

    def test_one_off_missing_bars_not_called_session(self):
        only = dt.datetime(2026, 10, 27, 13, 0, tzinfo=UTC)
        doc = mock_doc(utc_hour=99, skipped={only})
        result = inspect_market(doc, NOW)
        self.assertFalse(result["recurringCandidate"])
        self.assertEqual(result["patterns"][0]["missingM15"], 1)

    def test_weekend_not_classified_as_daily_hour_break(self):
        doc = mock_doc(utc_hour=99)
        result = inspect_market(doc, NOW)
        self.assertEqual(result["shortGapCount"], 0)
        self.assertFalse(result["recurringCandidate"])

    def test_future_bars_are_not_evidence(self):
        doc = mock_doc()
        cutoff = dt.datetime(2026, 10, 21, 20, 0, tzinfo=UTC)
        result = inspect_market(doc, cutoff)
        self.assertFalse(result["recurringCandidate"])

    def test_duplicate_and_unordered_candle_timestamps_rejected(self):
        doc = mock_doc()
        doc["timeframes"]["M15"][1]["t"] = doc["timeframes"]["M15"][0]["t"]
        self.assertEqual(inspect_market(doc, NOW)["status"], "invalid_timestamps")

    def test_no_database_mutation_and_private_broker_name_redacted(self):
        with tempfile.TemporaryDirectory() as temp:
            dbpath = Path(temp) / "private" / "remura-prices.sqlite3"
            db = connect(dbpath)
            for symbol in ("XAUUSD", "XAGUSD"):
                doc = mock_doc(provider="SECRET-FP-ACCOUNT")
                db.execute(
                    "INSERT INTO prices(symbol,source,broker_symbol,updated_at,payload)"
                    " VALUES(?,?,?,?,?)",
                    (symbol, "ctrader", "SECRET-FP-ACCOUNT", NOW.isoformat(),
                     json.dumps(doc)))
            db.commit()
            before = db.total_changes
            report = session_gap_overview(dbpath, NOW)
            self.assertEqual(db.total_changes, before)
            self.assertEqual(report["schema"], "remura-session-gap-diagnostics-v1")
            self.assertTrue(report["bothMetalsSamePattern"])
            self.assertFalse(report["brokerHoursConfirmed"])
            self.assertEqual(len(report["markets"]), 2)
            self.assertNotIn("SECRET-FP-ACCOUNT", json.dumps(report))
            self.assertNotIn('"o":', json.dumps(report))
            db.close()

    def test_missing_private_db_does_not_create_database(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"no-database.sqlite3"
            result = session_gap_overview(path, NOW)
            self.assertEqual(result["markets"], [])
            self.assertFalse(path.exists())


    def test_private_http_route_is_no_store_and_redacted(self):
        import threading
        from http.server import ThreadingHTTPServer
        from urllib.request import urlopen
        import private_server
        with tempfile.TemporaryDirectory() as temp:
            dbpath = Path(temp) / "private" / "remura-prices.sqlite3"
            db = connect(dbpath)
            with db:
                for symbol in ("XAUUSD", "XAGUSD"):
                    db.execute(
                        "INSERT INTO prices(symbol,source,broker_symbol,updated_at,payload)"
                        " VALUES(?,?,?,?,?)",
                        (symbol, "ctrader", "SENSITIVE-BROKER-KEY", NOW.isoformat(),
                         json.dumps(mock_doc(provider="SENSITIVE-BROKER-KEY"))))
            db.close()
            server = ThreadingHTTPServer(("127.0.0.1", 0),
                                         private_server.http_handler(dbpath))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = ("http://127.0.0.1:" + str(server.server_port)
                       + "/private-api/signals/session-gaps")
                with urlopen(url, timeout=5) as response:
                    self.assertEqual(response.headers["Cache-Control"],
                                     "no-store, max-age=0")
                    body = json.load(response)
                self.assertEqual(body["mode"], "diagnostic_only")
                self.assertTrue(body["bothMetalsSamePattern"])
                self.assertNotIn("SENSITIVE-BROKER-KEY", json.dumps(body))
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
