"""REMURA Filone B: CFTC public audit offline mock tests — ZERO real HTTP calls."""
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs,urlsplit

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("cot_public_official_audit",ROOT/"scripts"/"cot_public_official_audit.py")
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
NOW=dt.datetime(2026,11,23,15,30,tzinfo=dt.timezone.utc)

def sample(kind,date="2026-11-17"):
 cfg=audit.CONFIG[kind]
 return [{
  "report_date_as_yyyy_mm_dd":date+"T00:00:00",
  "cftc_contract_market_code":code,"open_interest_all":"2000",
  **{name:"300" for name in cfg["cols"]}
 } for code in cfg["codes"]]

class TestOfficialCftcAudit(unittest.TestCase):
 def test_queries_exact_two_allowlisted_datasets_and_fields(self):
  for kind in ("tff","disagg"):
   p=urlsplit(audit.query(kind,NOW))
   self.assertEqual(p.hostname,"publicreporting.cftc.gov")
   self.assertEqual(p.path,"/resource/"+audit.CONFIG[kind]["id"]+".json")
   q=parse_qs(p.query)
   self.assertIn("cftc_contract_market_code IN",q["$where"][0])
   self.assertEqual(q["$limit"],["1500"])
   self.assertIn(audit.CONFIG[kind]["cols"][0],q["$select"][0])
  with self.assertRaises(ValueError):audit.query("legacy",NOW)
  with self.assertRaises(ValueError):audit.query("tff",NOW,200)
 def test_mock_only_two_reads_14_reports_no_fake_publication_clock(self):
  called=[]
  def fake(kind,now):
   called.append(kind)
   return audit.extract(kind,sample(kind),now)
  s=audit.build_snapshot(NOW,fake)
  self.assertEqual(called,["tff","disagg"])
  self.assertEqual(s["rowCount"],14)
  self.assertEqual(s["readAtUtc"],"2026-11-23T15:30:00Z")
  self.assertEqual(s["source"],"official_public_cftc_socrata")
  self.assertTrue(all(x["first_seen_at"] is None for x in s["rows"]))
  self.assertEqual(len(s["dataSha256"]),64)
  self.assertFalse(s["truncated"])
 def test_invalid_inputs_and_conflicting_duplicates_rejected(self):
  for mutation in (
   {"open_interest_all":"0"},
   {"open_interest_all":"NaN"},
   {"report_date_as_yyyy_mm_dd":"2030-11-17T00:00:00"},
   {"cftc_contract_market_code":"999999"},
   {"asset_mgr_positions_long":"-3"}
  ):
   data=sample("tff")
   data[0].update(mutation)
   with self.assertRaises(ValueError):
    audit.extract("tff",data,NOW)
  data=sample("tff")
  data.append({**data[0],"asset_mgr_positions_long":"999"})
  with self.assertRaisesRegex(ValueError,"CONFLICTING_PUBLIC_CFTC_DUPLICATE"):
   audit.extract("tff",data,NOW)
 def test_no_truncation_or_empty_are_accepted(self):
  with self.assertRaisesRegex(ValueError,"PUBLIC_CFTC_EMPTY_OR_TRUNCATED"):
   audit.extract("tff",[],NOW)
  with self.assertRaises(ValueError):
   audit.extract("tff",[{}]*audit.MAX_ROWS,NOW)
 def test_runner_does_not_accept_wrong_current_timezone(self):
  with self.assertRaises(ValueError):
   audit.build_snapshot(dt.datetime(2026,11,23,10,0))
  with self.assertRaises(ValueError):
   audit.query("tff",dt.datetime(2026,11,23,10,0,tzinfo=dt.timezone(dt.timedelta(hours=1))))

if __name__=="__main__":unittest.main()
