"""Synthetic-only PRICE as-of provenance, H1 freshness & SQLite privacy tests.

No cTrader requests, no Oracle DB copy, no authentic price data or trade PnL.
"""
from datetime import datetime,timedelta,timezone
import json
import sqlite3
import unittest

from scripts import shark_price_asof_evidence as price

UTC=timezone.utc
END=datetime(2026,11,4,11,0,tzinfo=UTC)
OBS=END+timedelta(minutes=16)
NOW=OBS+timedelta(seconds=2)
SECRET="PRIVATE_FAKE_BROKER_IDENTIFIER_DO_NOT_PUBLISH"


def stamp(t):
    return t.isoformat().replace("+00:00","Z")


def prepare():
    db=sqlite3.connect(":memory:")
    db.executescript("""
      CREATE TABLE prices(
        symbol TEXT PRIMARY KEY,source TEXT,broker_symbol TEXT,
        updated_at TEXT,payload TEXT);
      CREATE TABLE squalincome_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,symbol TEXT,state TEXT,
        cot_side INTEGER,price_side INTEGER,h4_side INTEGER,h1_side INTEGER,
        m15_side INTEGER,price_state TEXT,report_date TEXT,
        price_time TEXT,observed_at TEXT,cot_weekly REAL,origin TEXT,
        UNIQUE(symbol,report_date,price_time));
    """)
    m15=[]
    for i in range(1024):
        start=END-timedelta(minutes=15*(1024-i))
        m15.append({
            "t":stamp(start),"o":1.01,"h":1.02,"l":1.00,"c":1.015,"v":100
        })
    def rollup(seconds):
        groups={}
        for bar in m15:
            opened=datetime.fromisoformat(bar["t"].replace("Z","+00:00"))
            aligned=datetime.fromtimestamp(
                int(opened.timestamp())//seconds*seconds,tz=UTC)
            groups.setdefault(aligned,[]).append(bar)
        n=seconds//900
        bars=[]
        for opened,rows in sorted(groups.items()):
            if len(rows)!=n:
                continue
            bars.append({
                "t":stamp(opened),"o":rows[0]["o"],
                "h":max(x["h"] for x in rows),
                "l":min(x["l"] for x in rows),
                "c":rows[-1]["c"],
                "v":sum(x["v"] for x in rows),
            })
        return bars
    data={"symbol":"EURUSD","provider":"ctrader","providerSymbol":SECRET,
          "sourceTimeframe":"M15","timezone":"UTC",
          "lastComplete":m15[-1]["t"],
          "timeframes":{"M15":m15,"H1":rollup(3600),"H4":rollup(14400)}}
    db.execute("INSERT INTO prices VALUES(?,?,?,?,?)",
               ("EURUSD","ctrader",SECRET,m15[-1]["t"],json.dumps(data)))
    db.commit()
    price.ensure_schema(db)
    return db


def add_observation(db, *,observed=OBS,closed=END,h1=1,h4=1,m15=1,
                    pstate="confirmed"):
    cur=db.execute(
        "INSERT INTO squalincome_history("
        "symbol,state,cot_side,price_side,h4_side,h1_side,m15_side,"
        "price_state,report_date,price_time,observed_at,cot_weekly,origin)"
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("EURUSD","aligned",1,1,h4,h1,m15,pstate,
         "2026-10-27",stamp(closed),stamp(observed),5.,"update"))
    return cur.lastrowid


def mutate(db,func):
    raw=db.execute("SELECT payload FROM prices WHERE symbol='EURUSD'").fetchone()[0]
    doc=json.loads(raw)
    func(doc)
    db.execute("UPDATE prices SET payload=? WHERE symbol='EURUSD'",
               (json.dumps(doc),))
    db.commit()


class PriceEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.db=prepare()

    def tearDown(self):
        self.db.close()

    def record(self,*,clock=NOW,**kwargs):
        source=json.loads(self.db.execute(
            "SELECT payload FROM prices WHERE symbol='EURUSD'").fetchone()[0]
        ) if self.db.execute("SELECT count(*) FROM prices").fetchone()[0] else None
        with self.db:
            hid=add_observation(self.db,**kwargs)
            return price.capture(
                self.db,history_id=hid,observed_document=source,clock=clock)

    def test_valid_three_timeframe_price_context_is_append_only(self):
        result=self.record()
        self.assertEqual(result["status"],"PRICE_ASOF_SOURCE_VERIFIED")
        self.assertTrue(result["m15H1H4FreshAtOriginalObservation"])
        self.assertTrue(result["h1H4RollupsValidatedAgainstM15"])
        self.assertTrue(result["last16TickVolumeComplete"])
        self.assertFalse(result["candleCollectionTimeIndependentlyKnown"])
        self.assertFalse(result["originalPriceDirectionIndependentlyReproduced"])
        self.assertFalse(result["alertsEnabled"])
        self.assertEqual(result["brokerCalls"],0)
        stored=self.db.execute(
            "SELECT source_document_sha256,m15_closed_at,h1_closed_at,h4_closed_at "
            "FROM research_squalincome_price_evidence").fetchone()
        self.assertEqual(len(stored[0]),64)
        self.assertEqual(stored[1],stamp(END).replace("Z",".000000Z"))
        self.assertEqual(stored[2],stamp(END).replace("Z",".000000Z"))
        self.assertEqual(stored[3],
                         stamp(END-timedelta(hours=3)).replace("Z",".000000Z"))
        out=json.dumps(result)+json.dumps(price.aggregate(self.db))
        self.assertNotIn(SECRET,out)
        self.assertNotIn("1.015",out)
        self.assertNotIn("2026-11-04T11:16",out)
        self.assertEqual(price.aggregate(self.db)["recordedEvidence"],1)

    def test_price_document_changed_between_scan_and_evidence_is_rejected(self):
        original=json.loads(self.db.execute(
            "SELECT payload FROM prices WHERE symbol='EURUSD'"
        ).fetchone()[0])
        # Change a distant historical M15 that cannot affect the latest
        # 30 H4 rollups; a correct validator must STILL detect this race.
        def changed(doc):
            doc["timeframes"]["M15"][0]["h"]=1.03
        mutate(self.db,changed)
        with self.assertRaisesRegex(ValueError,"price_document_changed_since_scan"):
            with self.db:
                hid=add_observation(self.db)
                price.capture(self.db,history_id=hid,
                              observed_document=original,clock=NOW)
        self.assertEqual(price.aggregate(self.db)["recordedEvidence"],0)

    def test_stale_H1_is_rejected_even_when_M15_is_current(self):
        mutate(self.db, lambda d:d["timeframes"]["H1"].__delitem__(slice(-2,None)))
        with self.assertRaisesRegex(ValueError,"stale_future_or_unclosed_h1"):
            self.record()
        self.assertEqual(price.aggregate(self.db)["recordedEvidence"],0)
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM squalincome_history").fetchone()[0],0)

    def test_stale_H4_is_rejected_even_when_H1_is_current(self):
        mutate(self.db, lambda d:d["timeframes"]["H4"].pop())
        with self.assertRaisesRegex(ValueError,"stale_future_or_unclosed_h4"):
            self.record()

    def test_price_time_must_identify_actual_latest_closed_M15(self):
        with self.assertRaisesRegex(ValueError,"different_m15_at_original_observation"):
            self.record(closed=END-timedelta(minutes=15))

    def test_unclosed_future_bar_does_not_pass_as_valid_evidence(self):
        def shift(d):
            d["timeframes"]["H1"].append({
                "t":stamp(END),"o":1.01,"h":1.02,"l":1.0,"c":1.015,"v":400
            })
        mutate(self.db,shift)
        with self.assertRaisesRegex(ValueError,"stale_future_or_unclosed_h1"):
            self.record()

    def test_h1_mismatched_rollup_rejected(self):
        def corrupt(d):
            d["timeframes"]["H1"][-1]["h"]=1.1
        mutate(self.db,corrupt)
        with self.assertRaisesRegex(ValueError,"ohlc_rollup_mismatch"):
            self.record()

    def test_missing_one_m15_rollup_input_rejected(self):
        def corrupt(d):
            d["timeframes"]["M15"].pop(-5)
        mutate(self.db,corrupt)
        with self.assertRaisesRegex(ValueError,"missing_m15_rollup_input"):
            self.record()

    def test_provider_mapping_or_candle_open_timestamp_mismatch_is_rejected(self):
        self.db.execute("UPDATE prices SET broker_symbol='CHANGED' WHERE symbol='EURUSD'")
        self.db.commit()
        with self.assertRaisesRegex(ValueError,"source_mapping_mismatch"):
            self.record()
        self.db.execute("UPDATE prices SET broker_symbol=? WHERE symbol='EURUSD'",(SECRET,))
        self.db.execute("UPDATE prices SET updated_at=? WHERE symbol='EURUSD'",
                        (stamp(END),))
        self.db.commit()
        with self.assertRaisesRegex(ValueError,"last_complete_open_mismatch"):
            self.record()

    def test_missing_tick_volume_does_not_become_fake_cvd_measurement(self):
        def remove(d):
            for rows in d["timeframes"].values():
                for r in rows:
                    r.pop("v",None)
        mutate(self.db,remove)
        result=self.record()
        self.assertFalse(result["last16TickVolumeComplete"])
        self.assertFalse(result["realAggressorFlowMeasured"])

    def test_old_history_or_naive_clock_rejected(self):
        with self.assertRaisesRegex(ValueError,"invalid_original_signal_or_time"):
            self.record(clock=NOW+timedelta(minutes=1))
        with self.assertRaises(ValueError):
            self.record(clock=datetime(2026,11,4,11,16))
        self.assertEqual(price.aggregate(self.db)["recordedEvidence"],0)

    def test_optional_missing_price_never_relabels_real_history(self):
        self.db.execute("DELETE FROM prices")
        self.db.commit()
        with self.db:
            hid=add_observation(self.db)
            result=price.capture_optional(
                self.db,history_id=hid,observed_document=None,clock=NOW)
            self.assertEqual(result["status"],"PRICE_PROVENANCE_NOT_VERIFIABLE")
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM squalincome_history").fetchone()[0],1)
        self.assertEqual(price.aggregate(self.db)["recordedEvidence"],0)

    def test_sqlite_failure_not_masked_by_optional_capture(self):
        self.db.execute("DROP TABLE research_squalincome_price_evidence")
        self.db.commit()
        with self.assertRaises(sqlite3.OperationalError):
            with self.db:
                hid=add_observation(self.db)
                price.capture_optional(
                    self.db,history_id=hid,
                    observed_document=json.loads(self.db.execute(
                        "SELECT payload FROM prices WHERE symbol='EURUSD'"
                    ).fetchone()[0]),clock=NOW)
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM squalincome_history").fetchone()[0],0)

    def test_duplicate_and_immutable_storage(self):
        self.record()
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("DELETE FROM research_squalincome_price_evidence")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE research_squalincome_price_evidence SET algorithm='other'")
        self.assertEqual(price.aggregate(self.db)["recordedEvidence"],1)

    def test_capacity_stops_before_writing_rows(self):
        from unittest.mock import patch
        with patch.object(price,"MAX_EVENTS",0):
            with self.assertRaisesRegex(ValueError,"price_evidence_capacity_reached"):
                self.record()
        self.assertEqual(price.aggregate(self.db)["recordedEvidence"],0)

if __name__=="__main__":
    unittest.main()
