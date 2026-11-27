"""V31.3 LAB: explicit session/contract coverage assessment.
Calendar and provider sequence semantics must be separately verified; no connection.
"""
import unittest
M5=300000
def coverage(windows,session,provenance):
    if provenance not in ("EXCHANGE_REPORTED","VENDOR_CLASSIFIED"):raise ValueError("provenance")
    start,end=session["start_ms"],session["end_ms"]
    if type(start) is not int or type(end) is not int or not 0<start<end or start%M5 or end%M5 or end-start>86400000:raise ValueError("session")
    ident=(session["provider"],session["instrument_id"],session["expiry"])
    seen={};known=unknown=delta=0;previous=None;gaps=0
    for w in windows:
        if (w["provider"],w["instrument_id"],w["expiry"])!=ident:raise ValueError("rollover_or_provider")
        t=w["start_ms"]
        if type(t) is not int or t%M5 or not start<=t<end or w["end_ms"]!=t+M5 or t in seen:raise ValueError("window")
        if previous is not None and t<=previous:raise ValueError("ordering")
        previous=t;seen[t]=True
        g=w["by_provenance"][provenance]
        b,s,u=g["buy"],g["sell"],w["unknown_side_volume"]
        total=w["total_trade_volume"]
        if any(type(x) is not int or x<0 for x in (b,s,u,total)) or b+s+u>total or g["delta"]!=b-s:raise ValueError("volume")
        known+=b+s;unknown+=total-b-s;delta+=b-s
        if w.get("transport_continuity_verified") is not True:gaps+=1
    missing=(end-start)//M5-len(seen)
    eligible=missing==0 and gaps==0 and unknown==0 and session.get("calendar_verified") is True
    return {"provider":ident[0],"instrument_id":ident[1],"expiry":ident[2],"missing_windows":missing,"unverified_transport_windows":gaps,
      "known_side_volume":known,"unclassified_or_other_volume":unknown,"observed_delta":delta,
      "candidate_complete_coverage":eligible,"cvd_certified":False,"prospective_admitted":False}
class Tests(unittest.TestCase):
    def test_session(self):
        s=dict(start_ms=M5,end_ms=3*M5,provider="RITHMIC",instrument_id="6EH7",expiry="2027-03-15",calendar_verified=True)
        w=dict(provider="RITHMIC",instrument_id="6EH7",expiry="2027-03-15",start_ms=M5,end_ms=2*M5,unknown_side_volume=0,total_trade_volume=5,transport_continuity_verified=True,by_provenance={"EXCHANGE_REPORTED":dict(buy=4,sell=1,delta=3)})
        self.assertFalse(coverage([w],s,"EXCHANGE_REPORTED")["candidate_complete_coverage"])
        a=coverage([w,dict(w,start_ms=2*M5,end_ms=3*M5)],s,"EXCHANGE_REPORTED")
        self.assertTrue(a["candidate_complete_coverage"]);self.assertFalse(a["cvd_certified"])
        with self.assertRaises(ValueError):coverage([dict(w,provider="TRADOVATE")],s,"EXCHANGE_REPORTED")
if __name__=="__main__":unittest.main()
