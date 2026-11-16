# REMURA v0.8.107 LAB — 16/11/2026 16:38 CET
import unittest,json,re
from pathlib import Path
from level_local_probe_v1 import parse,ORDER
HERE=Path(__file__).resolve().parent
OLD=(HERE/"REMURA-ALL-IN-ONE-Premium-v0.9.1-CVD-TELEMETRY-PREVIEW.pine").read_text()
NEW=(HERE/"REMURA-ALL-IN-ONE-Premium-v0.9.2-LEVEL-CONTRACT-PREVIEW.pine").read_text()
T=1794859200000
def fixture():
    config=dict(lower_tf="1",lookback=30,multiplier=3.5,max_efficiency=0.07,min_peak_gap=6,
        daily_min_effort=1.5,daily_anchor="HL2",fp_ticks=10,fp_imbalance_pct=300,
        fp_value_area_pct=70,atr_length=14,delta_library="TradingView/ta/14",price_decimal_places_max=10)
    rows=[]
    for period,rank in ORDER:
        prev=period=="PREVIOUS_OBSERVED_MONTH"
        rows.append(dict(period=period,rank=rank,price="1.085301" if rank==1 else None,
            peak_origin_close_ms=(T-900000 if prev else T) if rank==1 else None,
            period_start_ms=T-(1200000 if prev else 600000),period_end_ms=T-(600000 if prev else -600000),
            boundary_observed=True,method="DAY_TOP3_ABS_DELTA_HL2" if period=="DAY" else "PERIOD_MAX_ABS_DELTA_HL2"))
    return dict(schema="remura.tv.level.local.probe.v1",version="0.9.2-level-lab",
        mode="HISTORICAL_RECONSTRUCTION",symbol="FX:EURUSD",feed="FX",ticker="EURUSD",
        chart_type="forex",timezone="Etc/UTC",session="regular",timeframe="5",
        calendar="TRADINGVIEW_CHART_PERIOD_V1",product_status="UNATTESTED",contract=None,
        snapshot_open_ms=T-300000,snapshot_close_ms=T,sender_clock_ms=T+1000,
        receive_clock_ms=None,history_complete=False,method_er="SIGNED_BODY_ATR_OVER_RELATIVE_ABS_DELTA_V1",
        configuration=config,levels=rows)
def check(p):return parse(json.dumps(p))
class ProbeTests(unittest.TestCase):
    def test_calculation_body_preserved(self):
        a=OLD.split("// MASSIMI ASSOLUTI DEL DELTA NEI PERIODI DISPONIBILI",1)[1].split("// Experimental sender",1)[0]
        b=NEW.split("// MASSIMI ASSOLUTI DEL DELTA NEI PERIODI DISPONIBILI",1)[1].split("tvNum(float x)",1)[0]
        self.assertEqual(a.replace("CVD LAB v0.9.1","CVD LAB v0.9.2").strip(),b.strip())
        a=OLD.split("// DELTA STIMATO DA TIMEFRAME INFERIORE",1)[1].split("// MASSIMI ASSOLUTI",1)[0]
        b=NEW.split("// DELTA STIMATO DA TIMEFRAME INFERIORE",1)[1].split("// LEVEL CONTRACT:",1)[0]
        self.assertEqual(a.strip(),b.strip())
    def test_no_alert_one_footprint_and_log_mode(self):
        self.assertNotRegex(NEW,r"\balert(?:condition)?\s*\(")
        self.assertEqual(len(re.findall(r"=\s*request\.footprint\(",NEW)),1)
        self.assertIn('log.info("{0}", message)',NEW)
        self.assertIn('time("1M")[1]',NEW)
        self.assertIn('barstate.islastconfirmedhistory and not barstate.isrealtime',NEW)
    def test_positive_no_admission(self):
        r=check(fixture())
        self.assertEqual(r["present_levels"],4)
        self.assertFalse(r["comparison_admitted"])
        self.assertFalse(r["receipt_authenticated"])
        self.assertNotIn("1.085301",str(r))
    def test_wrong_feed_or_receipt(self):
        for k,v in (("symbol","FXCM:EURUSD"),("receive_clock_ms",T),("history_complete",True),
                    ("schema","remura.tv.level.explicit.synthetic.v1"),("contract","SPOT")):
            p=fixture();p[k]=v
            with self.assertRaises(ValueError):check(p)
    def test_wrong_anchor_origin_and_method(self):
        for k,v in (("period_start_ms",T+1000),("peak_origin_close_ms",T+1000),("method","OTHER"),("price",1.085)):
            p=fixture();p["levels"][0][k]=v
            with self.assertRaises(ValueError):check(p)
    def test_previous_month_is_observed_not_inferred(self):
        p=fixture()
        p["levels"][-1].update(price=None,peak_origin_close_ms=None,period_start_ms=None,
                                period_end_ms=None,boundary_observed=False)
        self.assertEqual(check(p)["present_levels"],3)
        p["levels"][-1]["period"]="PREVIOUS_MONTH"
        with self.assertRaises(ValueError):check(p)
    def test_config_digest_and_duplicate(self):
        p=fixture();first=check(p);p["configuration"]["daily_min_effort"]=2.0
        self.assertNotEqual(first["configuration_digest"],check(p)["configuration_digest"])
        with self.assertRaises(ValueError):parse(json.dumps(p)[:-1]+',"symbol":"FX:EURUSD"}')
if __name__=="__main__":unittest.main()
