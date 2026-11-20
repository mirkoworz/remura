"""REMURA v0.8.170 LAB — 18/11/2026, sessione successiva alle 16:54 CET.
Availability-only report on explicit private CVD receipt windows.
Never evaluate outcomes, candidate selection, directional agreement or returns.
No network, new export, writes or proof of full market coverage.
"""
from cvd_archive_preview_v1 import validate_windows

def availability(windows,*,as_of_ms):
    valid,stats=validate_windows(windows,as_of_ms=as_of_ms)
    counts=dict(receipt_clock_usable=0,receipt_clock_unknown=0,cvd_complete=0,
                cvd_continuous=0,cvd_eligible_declared=0,delta_available=0,
                footprint_available=0,prior_level_available=0,
                cvd_delta_footprint_prior_level_joint=0)
    for row,e,v in valid:
        t=row["bar_close_ms"]
        if not 0<=row["received_at_ms"]-t<=120000:
            counts["receipt_clock_unknown"]+=1
            continue
        counts["receipt_clock_usable"]+=1
        c,p=e["cvd"],e["snapshot"]
        counts["cvd_complete"]+=int(c["complete"])
        counts["cvd_continuous"]+=int(c["continuous"] is True)
        counts["cvd_eligible_declared"]+=int(c["eligible"])
        counts["delta_available"]+=int(p["delta_intrabar"] is not None)
        counts["footprint_available"]+=int(p["footprint"]["available"])
        prior=any(price is not None and p["level_origin_ms"][name]<=p["bar_open_ms"]
                  for name,price in p["levels"].items())
        counts["prior_level_available"]+=int(prior)
        counts["cvd_delta_footprint_prior_level_joint"]+=int(
            c["eligible"] and p["delta_intrabar"] is not None
            and p["footprint"]["available"] and prior)
    return {"schema":"remura.tv.cvd.source.availability.lab.v1",
            "status":"SCOPED_RECEIPT_AVAILABILITY_ONLY" if valid else "NO_OBSERVATIONS",
            "scope":"EXPLICIT_WINDOWS_NOT_MARKET_CALENDAR","receipt_counts":stats,
            "availability_counts":counts,"availability_denominator":"RECEIPT_CLOCK_USABLE",
            "provenance_attested":False,"conflict_ledger_available":False,
            "outcomes_evaluated":False,"scientific_admission":False,
            "orders_enabled":False,"notifications_enabled":False}
