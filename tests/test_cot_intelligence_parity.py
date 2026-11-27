"""REMURA B v21.0 — offline-only public/private CFTC parity mock tests."""
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("parity",ROOT/"scripts"/"cot_intelligence_parity.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
NOW="2026-11-23T19:00:00Z"
DATES=["2026-11-10","2026-11-17"]

def fixtures():
 rows=[]
 for date in DATES:
  for dataset,codes in mod.EXPECTED.items():
   for j,code in enumerate(codes):
    rows.append({"dataset":dataset,"code":code,"report_date":date,
                 "oi":2000.0,"first_long":300.0+j,"first_short":200.0,
                 "second_long":400.0,"second_short":100.0,"first_seen_at":None})
 raw=json.dumps(rows,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
 public={"schema":mod.SCHEMA,"source":mod.PUBLIC_SOURCE,
         "captureClock":mod.CLOCK_PUBLIC,"readAtUtc":"2026-11-23T15:35:17Z",
         "dataSha256":hashlib.sha256(raw).hexdigest(),
         "rowCount":len(rows),"truncated":False,"rows":rows}
 private=json.loads(json.dumps(public))
 private.update({"source":mod.PRIVATE_SOURCE,"captureClock":mod.CLOCK_PRIVATE})
 for row in private["rows"]:
  row["first_seen_at"]=(row["report_date"]+"T20:00:00Z").replace(
    "T20:00:00Z","T20:00:00Z")
  # Acquisition realistically occurs after the Tuesday report date.
  day=dt.date.fromisoformat(row["report_date"])+dt.timedelta(days=3)
  row["first_seen_at"]=day.isoformat()+"T20:00:00+00:00"
 return public,private

def run(pub=None,priv=None):
 if pub is None or priv is None:
  p,q=fixtures();pub=p if pub is None else pub;priv=q if priv is None else priv
 return mod.reconcile(pub,priv,DATES,NOW)

def resign(pub):
 raw=json.dumps(pub["rows"],sort_keys=True,separators=(",",":"),allow_nan=False).encode()
 pub["dataSha256"]=hashlib.sha256(raw).hexdigest()
 pub["rowCount"]=len(pub["rows"])

class TestCotOfflineParity(unittest.TestCase):
 def test_two_weeks_14_exact_contracts_all_match_and_capture_known(self):
  r=run()
  self.assertEqual(r["state"],"value_parity_only")
  self.assertEqual(r["expectedKeys"],28)
  self.assertEqual(r["matchedKeys"],28)
  self.assertTrue(r["publicRowsSha256Verified"])
  self.assertEqual(sum(c["capture_known"] for c in r["coverage"]),28)
  self.assertEqual(sum(c["capture_unknown"] for c in r["coverage"]),0)
  self.assertTrue(any("revisions" in x for x in r["limitations"]))
 def test_first_seen_unknown_is_visible_but_values_can_still_match(self):
  p,q=fixtures();q["rows"][0]["first_seen_at"]=None
  r=run(p,q)
  self.assertEqual(r["state"],"value_parity_only")
  self.assertEqual(r["matchedKeys"],28)
  self.assertEqual(sum(x["capture_unknown"] for x in r["coverage"]),1)
 def test_local_cache_missing_one_code_is_not_masked(self):
  p,q=fixtures();q["rows"].pop(0);q["rowCount"]=len(q["rows"])
  r=run(p,q)
  self.assertEqual(r["state"],"incomplete_or_different")
  self.assertEqual(r["matchedKeys"],27)
  self.assertEqual(sum(x["missing_private"] for x in r["coverage"]),1)
 def test_public_reference_missing_one_code_is_not_called_complete(self):
  p,q=fixtures();p["rows"].pop(0);resign(p)
  r=run(p,q)
  self.assertEqual(r["state"],"incomplete_or_different")
  self.assertEqual(sum(x["missing_public"] for x in r["coverage"]),1)
 def test_mismatch_is_field_scoped_and_no_values_or_secrets_are_printed(self):
  p,q=fixtures();q["rows"][0]["first_long"]+=12.0
  r=run(p,q)
  self.assertEqual(r["state"],"incomplete_or_different")
  self.assertEqual(r["matchedKeys"],27)
  bad=[x for c in r["coverage"] for x in c["mismatchedKeys"]]
  self.assertEqual(bad,[{"code":p["rows"][0]["code"],"fields":["first_long"]}])
 def test_public_checksum_mutation_is_rejected_before_parity(self):
  p,q=fixtures();p["rows"][0]["first_long"]+=1.0
  with self.assertRaisesRegex(ValueError,"PUBLIC_ROWS_CHECKSUM_MISMATCH"):
   run(p,q)
 def test_fake_public_capture_not_accepted_even_with_rehashed_rows(self):
  p,q=fixtures();p["rows"][0]["first_seen_at"]="2026-11-19T00:00:00Z";resign(p)
  with self.assertRaisesRegex(ValueError,"FORGED_PUBLIC_LOCAL_CLOCK"):
   run(p,q)
 def test_clock_in_future_and_pre_report_marked_or_rejected(self):
  p,q=fixtures();q["rows"][0]["first_seen_at"]="2027-01-01T00:00:00Z"
  with self.assertRaisesRegex(ValueError,"FUTURE_PRIVATE_CAPTURE"):
   run(p,q)
  p,q=fixtures();q["rows"][0]["first_seen_at"]="2026-11-09T10:00:00Z"
  r=run(p,q)
  self.assertEqual(r["state"],"incomplete_or_different")
  self.assertEqual(sum(c["capture_before_report"] for c in r["coverage"]),1)
 def test_weeks_must_be_explicit_and_separated_5_to_9_days(self):
  p,q=fixtures()
  with self.assertRaisesRegex(ValueError,"EXACTLY_TWO_REPORT_DATES_REQUIRED"):
   mod.reconcile(p,q,["2026-11-17"],NOW)
  with self.assertRaisesRegex(ValueError,"INVALID_WEEKLY_COMPARISON"):
   mod.reconcile(p,q,["2026-11-10","2026-11-13"],NOW)
 def test_reject_duplicate_conflicts_and_truncated_json(self):
  p,q=fixtures()
  q["rows"].append(q["rows"][0].copy());q["rowCount"]=len(q["rows"])
  with self.assertRaisesRegex(ValueError,"DUPLICATE_CFTC_ROW"):
   run(p,q)
  p,q=fixtures();q["truncated"]=True
  with self.assertRaisesRegex(ValueError,"INVALID_OR_TRUNCATED_SNAPSHOT"):
   run(p,q)
 def test_local_file_reader_does_not_create_modify_or_fetch(self):
  p,q=fixtures()
  with tempfile.TemporaryDirectory() as folder:
   f=Path(folder)/"offline-public.json"
   f.write_text(json.dumps(p),encoding="utf-8")
   original=f.read_bytes()
   self.assertEqual(mod.read_local(f)["rowCount"],28)
   self.assertEqual(original,f.read_bytes())
   with self.assertRaises(FileNotFoundError):mod.read_local(Path(folder)/"missing.json")

if __name__=="__main__":unittest.main()
