"""V31.0 LAB — provider-neutral CME ingestion contract.
No SDKs, network, credentials, subscription or orders.
An explicit approval and license review are mandatory before any real ingestion.
"""
from dataclasses import dataclass
from decimal import Decimal
from datetime import date
import re
PROVIDERS=("RITHMIC","TRADOVATE")
ROOTS={"6E":("EURUSD",1),"6B":("GBPUSD",1),"6A":("AUDUSD",1),"6N":("NZDUSD",1),"6J":("USDJPY",-1),"6C":("USDCAD",-1),"6S":("USDCHF",-1),"GC":("XAUUSD",1),"NQ":("NASDAQ100",1),"ES":("SP500",1)}
@dataclass(frozen=True)
class Contract:
    provider:str
    venue:str
    root:str
    instrument_id:str
    expiration:date
    currency:str
    tick_size:Decimal
def validate(c):
    if not isinstance(c,Contract) or c.provider not in PROVIDERS or c.root not in ROOTS:raise ValueError("provider_root")
    venue="COMEX" if c.root=="GC" else "CME"
    if c.venue!=venue or c.currency!="USD" or type(c.expiration) is not date or not re.fullmatch(r"[A-Za-z0-9._:/-]{1,80}",c.instrument_id):raise ValueError("contract")
    if type(c.tick_size) is not Decimal or not c.tick_size.is_finite() or c.tick_size<=0:raise ValueError("tick_size")
    spot,direction=ROOTS[c.root]
    return {"spot_reference":spot,"expected_direction":direction,"direct_spot":False}
def normalize_trade(c,event,*,approved=False,license_ref=None):
    if approved is not True or not isinstance(license_ref,str) or not license_ref.strip():raise PermissionError("disabled")
    validate(c)
    if event.get("instrument_id")!=c.instrument_id or event.get("venue")!=c.venue:raise ValueError("identity")
    t,r=event["exchange_ms"],event["received_ms"]
    if any(type(x) is not int for x in (t,r)) or not 0<t<=r:raise ValueError("clock")
    seq=event.get("trade_id")
    if type(seq) is not str or not seq or len(seq)>100:raise ValueError("trade_id")
    p=Decimal(str(event["price"]));q=event["quantity"]
    if not p.is_finite() or p<=0 or p%c.tick_size or type(q) is not int or q<=0:raise ValueError("trade")
    side=event.get("aggressor")
    if side not in ("BUY","SELL","UNKNOWN"):raise ValueError("side")
    method=event.get("side_provenance")
    if method not in ("EXCHANGE_REPORTED","VENDOR_CLASSIFIED","UNKNOWN"):raise ValueError("provenance")
    if side=="UNKNOWN" or method=="UNKNOWN":side="UNKNOWN";method="UNKNOWN"
    return {"provider":c.provider,"venue":c.venue,"root":c.root,"instrument_id":c.instrument_id,"expiration":c.expiration.isoformat(),"exchange_ms":t,"received_ms":r,"trade_id":seq,"price":str(p),"quantity":q,"aggressor":side,"side_provenance":method,"signed_quantity":q if side=="BUY" else -q if side=="SELL" else None,"prospective_admitted":False}
