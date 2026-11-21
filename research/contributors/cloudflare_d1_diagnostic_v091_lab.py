# REMURA Contributors v0.91 LAB — 21/11/2026 Europe/Rome
# Manual-only D1 GraphQL diagnostic. NO automatic provider calls or secrets in CI.
"""Two calls maximum, with no retry, no raw body logs, and NO staging admission."""
from __future__ import annotations
from datetime import date,datetime,timedelta,timezone
import http.client
import json
import os
import re
import ssl
import sys
from readonly_probe_plan_v086_lab import pinned_query,ProbeError

ACK="AUTORIZZO_DIAGNOSI_D1_MAX_2_POST_SOLO_LETTURA"
ACTIVATION="USER_APPROVED_READ_ONLY_ONCE"
HOST="api.cloudflare.com"
PATH="/client/v4/graphql"
MAX_POSTS=2
MAX_RESPONSE_BYTES=100_000
MAX_BODY=6_000
TIMEOUT=15

class DiagnosticError(ValueError):pass

def counter(x):
    if type(x) not in (int,float) or x<0 or x>10**12 or (type(x) is float and not x.is_integer()):
        raise DiagnosticError("counter_invalid")
    return int(x)

def parse_daily(data,day):
    if type(day) is not date or not isinstance(data,dict) or data.get("errors"):
        raise DiagnosticError("invalid_provider_payload")
    root=data.get("data")
    if not isinstance(root,dict) or not isinstance(root.get("viewer"),dict):
        raise DiagnosticError("viewer_missing")
    accounts=root["viewer"].get("accounts")
    if not isinstance(accounts,list) or len(accounts)!=1 or not isinstance(accounts[0],dict):
        raise DiagnosticError("account_count_invalid")
    groups=accounts[0].get("d1AnalyticsAdaptiveGroups")
    if not isinstance(groups,list) or len(groups)>10:
        raise DiagnosticError("groups_invalid")
    if not groups:return None
    seen=set();reads=writes=0
    for g in groups:
        if not isinstance(g,dict) or not isinstance(g.get("dimensions"),dict) or not isinstance(g.get("sum"),dict):
            raise DiagnosticError("group_invalid")
        dims,nums=g["dimensions"],g["sum"]
        ident=dims.get("databaseId")
        if dims.get("date")!=day.isoformat() or not isinstance(ident,str) or not 1<=len(ident)<=80 or ident in seen:
            raise DiagnosticError("group_identity_or_day_invalid")
        seen.add(ident)
        reads+=counter(nums.get("rowsRead"))
        writes+=counter(nums.get("rowsWritten"))
    return reads,writes

def band(value,limit):
    pct=value*100
    if pct>=100*limit:return "AT_OR_ABOVE_NOMINAL_LIMIT"
    if pct>=90*limit:return "90_TO_100_PERCENT"
    if pct>=70*limit:return "70_TO_90_PERCENT"
    if pct>=50*limit:return "50_TO_70_PERCENT"
    if pct>=25*limit:return "25_TO_50_PERCENT"
    return "BELOW_25_PERCENT"

def report(day,status,calls=0,today=None,prior=None):
    return dict(schema="remura.contributors.d1.diagnostic.v091.lab",version="0.91",
       utc_day_checked=day.isoformat(),status=status,provider_post_count=calls,provider_post_max=MAX_POSTS,
       daily_read_band=None if today is None else band(today[0],5_000_000),
       daily_write_band=None if today is None else band(today[1],100_000),
       prior_utc_day_has_groups=prior,raw_body_logged=False,db_identifiers_logged=False,
       secrets_logged=False,adaptive_metrics_not_exact_billing=True,
       free_plan_verified=False,access_seats_verified=False,staging_allowed=False,
       automatic_retry=False,deploy_allowed=False,d1_sql_calls=0,decision="NO_GO")

def offline_plan(day):
    if type(day) is not date:raise DiagnosticError("day_invalid")
    pinned_query()
    return report(day,"OFFLINE_NOT_AUTHORIZED")

def diagnostic(day,transport):
    if type(day) is not date or not callable(transport):raise DiagnosticError("input_invalid")
    try:q,_=pinned_query()
    except (ProbeError,ValueError,OSError):
        return report(day,"PINNED_QUERY_DRIFT")
    calls=0
    try:
        calls+=1
        today=parse_daily(transport(q,day.isoformat()),day)
        if today is not None:return report(day,"TODAY_ADAPTIVE_ESTIMATE_PRESENT",calls,today)
        prior=day-timedelta(days=1)
        calls+=1
        yesterday=parse_daily(transport(q,prior.isoformat()),prior)
        if yesterday is None:return report(day,"BOTH_DAYS_EMPTY_NOT_ZERO",calls,prior=False)
        return report(day,"TODAY_EMPTY_PREVIOUS_PRESENT",calls,prior=True)
    except Exception:
        # Never report raw errors: provider exceptions may contain URLs/credentials.
        return report(day,"ERROR_UNATTESTED",calls)

def private_transport(account,token):
    def send(q,day):
        body=json.dumps({"query":q,"variables":{"accountTag":account,"day":day}},
                        separators=(",",":"),ensure_ascii=True).encode("ascii")
        if len(body)>MAX_BODY:raise DiagnosticError("request_too_large")
        # Explicit TLS peer + fixed host/path: no cross-host redirects or retries.
        c=http.client.HTTPSConnection(HOST,timeout=TIMEOUT,context=ssl.create_default_context())
        try:
            c.request("POST",PATH,body=body,headers={"Authorization":"Bearer "+token,
                "Content-Type":"application/json","Accept":"application/json"})
            r=c.getresponse()
            if r.status!=200:raise DiagnosticError("provider_non_200")
            data=r.read(MAX_RESPONSE_BYTES+1)
            if len(data)>MAX_RESPONSE_BYTES:raise DiagnosticError("response_too_large")
            return json.loads(data.decode("utf-8"))
        finally:c.close()
    return send

def main(argv):
    day=datetime.now(timezone.utc).date()
    if argv==["--offline-plan"]:
        try:r=offline_plan(day)
        except (ProbeError,DiagnosticError,OSError,ValueError):r=report(day,"PINNED_QUERY_DRIFT")
        print(json.dumps(r,sort_keys=True,separators=(",",":")))
        return 0 if r["status"]=="OFFLINE_NOT_AUTHORIZED" else 2
    if argv!=["--execute-one-time"]:
        print("REMURA_V091_DIAGNOSTIC=INVALID_MODE_NO_NETWORK")
        return 2
    if os.environ.get("REMURA_CF_PROBE_ACK")!=ACK or os.environ.get("REMURA_V091_ACTIVATE")!=ACTIVATION:
        print("REMURA_V091_DIAGNOSTIC=NOT_AUTHORIZED_NO_NETWORK")
        return 3
    account=os.environ.get("REMURA_CF_ACCOUNT_ID","")
    token=os.environ.get("REMURA_CF_ANALYTICS_READ_TOKEN","")
    if not re.fullmatch(r"[a-fA-F0-9]{32}",account) or not re.fullmatch(r"[A-Za-z0-9_.-]{20,512}",token):
        print("REMURA_V091_DIAGNOSTIC=MISSING_OR_INVALID_READ_CREDENTIALS")
        return 4
    r=diagnostic(day,private_transport(account,token))
    print(json.dumps(r,sort_keys=True,separators=(",",":")))
    return 0 if r["status"]=="TODAY_ADAPTIVE_ESTIMATE_PRESENT" else 1

if __name__=="__main__":sys.exit(main(sys.argv[1:]))
