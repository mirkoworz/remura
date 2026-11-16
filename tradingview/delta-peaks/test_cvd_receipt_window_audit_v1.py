# REMURA v0.8.89 LAB — 16/11/2026 10:29 CET
import sys,unittest,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
from cvd_receipt_window_audit_v1 import aggregate_receipts,AuditError
from cvd_oos_protocol_preview_v2 import digest
from cvd_pilot_analytic_reader_v1 import SYMBOL,VERSION,M5,utc_ms
T=utc_ms("2026-11-16T09:05Z")
def record(run,start,end,got=4,v=1):
    count=(end-start)//M5+1
    now=end+180000
    r={"schema":"remura.tv.cvd.first.receipt.preview.v"+str(v),"symbol":SYMBOL,"sender_version":VERSION,"protocol_sha256":digest(),"scope":"REQUESTED_SLOTS_NOT_MARKET_CALENDAR","requested_slots":count,"valid_unique_bars":got,"missing_requested_slots":count-got,"duplicate_rows":0,"max_lag_ms":7092 if got else None,"status":"NO_MATCHING_ROWS" if got==0 else "COMPLETE_REQUESTED_WINDOW" if got==count else "PARTIAL_REQUESTED_WINDOW","collection":{"target":"EU_D1_TEST_ONLY","query_meta_scope":"THIS_COLLECTION_ONLY_NOT_ACCOUNT_USAGE","account_quota_utilization":None,"raw_logged":False,"raw_persisted":False,"inventory_requests":1,"select_requests":1,"query_rows_read":9,"query_rows_written":0}}
    for k in ("scientific_admission","orders_enabled","notifications_enabled","outcomes_computed","conflict_ledger_available","independent_provenance"):r[k]=False
    if v==2:r["window"]={"start_close_ms":start,"end_close_ms":end,"as_of_ms":now}
    return dict(run_id=run,start_ms=start,end_ms=end,observed_ms=now,report=r)
class ReceiptWindows(unittest.TestCase):
    def test_disjoint_partial(self):
        a=record(1,T,T+3*M5);b=record(2,T+4*M5,T+7*M5,got=3,v=2)
        o=aggregate_receipts([a,b])
        self.assertEqual((o["requested_slots"],o["valid_unique_bars"],o["missing_requested_slots"],o["collection_rows_read"]),(8,7,1,18))
        self.assertFalse(o["scientific_admission"])
    def test_overlap_or_duplicate(self):
        a=record(1,T,T+3*M5)
        for b in (record(2,T+3*M5,T+6*M5),record(1,T+4*M5,T+7*M5)):
            with self.assertRaises(AuditError):aggregate_receipts([a,b])
    def test_wrong_range_or_flags(self):
        a=record(1,T,T+3*M5,v=2)
        for k,x in (("window",{"start_close_ms":T+M5,"end_close_ms":T+3*M5,"as_of_ms":T+3*M5+180000}),("scientific_admission",True),("missing_requested_slots",1),("protocol_sha256","a"*64),("requested_slots",12),("status","PARTIAL_REQUESTED_WINDOW")):
            b=copy.deepcopy(a);b["report"][k]=x
            with self.assertRaises(AuditError):aggregate_receipts([b])
        b=copy.deepcopy(a);b["report"]["collection"]["query_rows_written"]=1
        with self.assertRaises(AuditError):aggregate_receipts([b])
    def test_immature(self):
        a=record(1,T,T+3*M5);a["observed_ms"]=T+3*M5+119999
        with self.assertRaises(AuditError):aggregate_receipts([a])
