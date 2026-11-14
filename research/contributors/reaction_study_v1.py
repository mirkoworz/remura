# REMURA Level Confluence v0.12 LAB — 14/11/2026 23:48 CET
"""Synthetic M5 reaction measurement; fixed windows, no trades or live inputs.
A frozen level and exact feed identity must come from a trusted study manifest.
OHLC cannot determine intrabar sequence: exclude touch-bar excursions.
"""
from datetime import timedelta
from decimal import Decimal, localcontext
from ledger_v1 import _time
from level_confluence_v1 import _positive

BAR=timedelta(minutes=5)
SEARCH=12
FOLLOW=12
TOTAL=SEARCH+FOLLOW
MAX_BARS=TOTAL

def _unknown(reason):
    return {"status":"N_D","reason":reason,"scientific_admission":False,
            "operational_signal":False,"synthetic":True}

def reaction(*,level,cutoff_utc,evaluated_utc,previous_close,bars,synthetic=False):
    if synthetic is not True:raise ValueError("synthetic_only")
    target=_positive(level)
    cutoff=_time(cutoff_utc); evaluated=_time(evaluated_utc)
    if cutoff.minute%5 or cutoff.second:raise ValueError("cutoff_alignment")
    if evaluated<cutoff+TOTAL*BAR:
        return _unknown("WINDOW_NOT_MATURE")
    if type(previous_close) is not dict or set(previous_close)!={"close_utc","available_utc","close"}:
        raise ValueError("previous_close")
    if _time(previous_close["close_utc"])!=cutoff or _time(previous_close["available_utc"])>cutoff:
        return _unknown("PREVIOUS_CLOSE_NOT_AVAILABLE")
    prior=_positive(previous_close["close"])
    if type(bars) is not list or len(bars)>MAX_BARS:raise ValueError("capacity")
    if len(bars)!=TOTAL:return _unknown("INCOMPLETE_WINDOW")
    sequence=[]
    for i,b in enumerate(bars):
        if type(b) is not dict or set(b)!={"close_utc","available_utc","open","high","low","close"}:
            raise ValueError("bar_fields")
        close_at=_time(b["close_utc"]); available=_time(b["available_utc"])
        if close_at!=cutoff+(i+1)*BAR:return _unknown("MISSING_OR_UNORDERED_BAR")
        if available<close_at:raise ValueError("bar_chronology")
        if available>evaluated:return _unknown("BAR_NOT_AVAILABLE")
        o,h,l,c=(_positive(b[x]) for x in ("open","high","low","close"))
        if not l<=min(o,c)<=max(o,c)<=h:raise ValueError("ohlc")
        sequence.append((o,h,l,c))
    if prior==target:return _unknown("ALREADY_AT_LEVEL")
    side=1 if prior>target else -1
    base={"synthetic":True,"scientific_admission":False,"operational_signal":False,
          "cutoff_utc":cutoff_utc,"search_minutes":60,"follow_minutes":60,
          "direction":"FROM_ABOVE" if side==1 else "FROM_BELOW"}
    for i,(o,h,l,c) in enumerate(sequence[:SEARCH]):
        # A discontinuity across level cannot establish an actual contact.
        if (prior-target)*(o-target)<0:
            return dict(base,status="N_D",reason="GAP_ACROSS_BEFORE_TOUCH")
        if l<=target<=h:
            following=sequence[i+1:i+1+FOLLOW]
            with localcontext() as ctx:
                ctx.prec=40
                away=max([Decimal(0)]+[(x[1]-target if side==1 else target-x[2]) for x in following])
                through=max([Decimal(0)]+[(target-x[2] if side==1 else x[1]-target) for x in following])
            # Touch bar close is known, but not the intrabar order of its extrema.
            crossed=(c-target)*side<0 or any((x[3]-target)*side<0 for x in following)
            return dict(base,status="TOUCHED",touch_close_utc=bars[i]["close_utc"],
                        closed_across=crossed,away_excursion=format(away,"f"),
                        through_excursion=format(through,"f"),
                        excursion_scope="NEXT_12_COMPLETE_BARS_EXCLUDES_TOUCH_BAR")
        prior=c
    return dict(base,status="NO_TOUCH")
