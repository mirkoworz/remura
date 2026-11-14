#!/usr/bin/env python3
# REMURA v0.8.56 LAB — 14/11/2026 CET; synthetic / mocked.
import sqlite3,sys,types,unittest,json
from unittest.mock import patch
from datetime import datetime,timezone
from research_dossier_preview_v1 import dossier,B_SCHEMA,relation
from research_dashboard_preview_v1 import render,notification_preview
from test_fx_asof_handoff_v1 import good
from test_telemetry_v1 import T0
from test_volume_features_v1 import fixture, changed
from volume_features_v1 import M5

def stamp(t):
    return datetime.fromtimestamp(t/1000,tz=timezone.utc).isoformat().replace("+00:00","Z")

def pair(observed=T0+6000):
    return ("EURUSD","2026-11-10",stamp(T0),stamp(observed),"a"*64,1)

def mock_audit(pairs):
    def run(db,*,as_of,days,_verified_pairs):
        _verified_pairs.extend(pairs)
        return {"schema":B_SCHEMA,"status":"LOCAL_PAIR_MOCK","locallyJoinedCausalPairs":len(pairs)}
    return run

class DossierTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("PRAGMA query_only=ON")
    def tearDown(self):
        self.db.close()
    def run_dossier(self,rows,pairs=None):
        packages=types.ModuleType("scripts")
        packages.shark_causal_pair_audit=types.SimpleNamespace(audit=mock_audit([pair()] if pairs is None else pairs))
        with patch.dict(sys.modules,{"scripts":packages}):
            return dossier(self.db,rows,as_of_utc=stamp(T0+8000),origin="SYNTHETIC")

    def test_candidate_and_unknown_sources(self):
        r=self.run_dossier([good()])
        self.assertEqual(r["pair_counts"],{"DESCRIPTIVE_CANDIDATE_ONLY":1})
        self.assertEqual(r["relations"]["cot_vs_intrabar_delta"],{"ALIGNED":1})
        self.assertEqual(r["cvd_status"],"UNKNOWN_NOT_JOINED")
        self.assertEqual(r["sentiment_status"],"UNKNOWN_NOT_JOINED")
        self.assertFalse(r["predictive_admission"])
        self.assertFalse(r["orders_enabled"])
        self.assertFalse(r["track_b_live_connected"])

    def test_late_and_missing(self):
        for rows in ([dict(good(),received_at_ms=T0+7000)],[]):
            r=self.run_dossier(rows)
            self.assertEqual(r["pair_counts"],{"NO_CURRENT_ASOF_OBSERVATION":1})
            self.assertEqual(r["relations"]["cot_vs_intrabar_delta"],{})

    def test_bad_decision_and_duplicates(self):
        r=self.run_dossier([], [("EURUSD","w",stamp(T0-M5),stamp(T0+6000),"a"*64,1)])
        self.assertEqual(r["pair_counts"],{"B_DECISION_CLOCK_OUTSIDE_HANDOFF":1})
        with self.assertRaises(ValueError):
            self.run_dossier([good()],[pair(),pair()])

    def test_mismatched_config_not_paired(self):
        r=self.run_dossier([changed(good(),lambda p:p["quality"].update(lower_tf="2"))])
        self.assertEqual(r["pair_counts"],{"BLOCKED_CONFIG_METADATA_MISMATCH":1})
        self.assertEqual(r["relations"]["cot_vs_intrabar_delta"],{})

    def test_outcomes_exclude_older_than_window(self):
        r=self.run_dossier([good(),fixture(T0-2*86400000)])
        self.assertEqual(r["outcomes"]["selected_rows"],1)

    def test_snapshots_readonly(self):
        self.db.execute("PRAGMA query_only=OFF")
        with self.assertRaises(ValueError):
            self.run_dossier([good()])

    def test_relations_unknown_neutral_opposed(self):
        self.assertEqual(relation(1,None),"UNKNOWN")
        self.assertEqual(relation(1,0),"NEUTRAL")
        self.assertEqual(relation(1,-1),"OPPOSED")

    def test_dashboard_and_preview_no_send(self):
        r=self.run_dossier([good()])
        page=render(r)
        self.assertIn("DATI SINTETICI",page)
        self.assertIn("Nessun segnale operativo",page)
        self.assertNotIn("1.111",page)
        self.assertNotIn("<script",page)
        a,b=notification_preview(r),notification_preview(r)
        self.assertEqual(a["notice_id"],b["notice_id"])
        self.assertFalse(a["would_send"])
        self.assertFalse(a["sent"])
        self.assertEqual(a["candidate_count"],1)

    def test_dashboard_rejects_operational_data(self):
        r=self.run_dossier([good()])
        r["orders_enabled"]=True
        with self.assertRaises(ValueError):
            render(r)

if __name__=="__main__":
    unittest.main()
