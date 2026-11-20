#!/usr/bin/env python3
# REMURA v0.8.84 LAB — 14/11/2026 20:34 CET
"""Read one atomic private state generation, never query D1 or SQLite.
Caller must authorize viewing separately; this is NOT an HTTP handler.
Trusted producer only; local checksum is integrity, not authentication.
"""
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from html import escape
from cvd_runtime_private_state_v1 import open_state,bucket,DELAY
from cvd_telemetry_preview_v1 import M5
LABELS={
    "NO_SAVED_RESULT":"Nessuna analisi salvata",
    "INCOMPLETE_NO_RESULT":"Tentativo registrato, nessun risultato valido",
    "CURRENT_EMPTY":"Intervallo corrente, nessuna barra ricevuta",
    "CURRENT_PARTIAL":"Intervallo corrente, copertura parziale",
    "CURRENT_REQUESTED_COMPLETE":"Intervallo corrente, slot richiesti completi",
    "OLDER_RESULT":"Risultato precedente — non aggiornato",
    "INCOMPLETE_NEWER_CLAIM":"Risultato precedente — tentativo successivo incompleto",
    "STATE_UNAVAILABLE":"Stato non disponibile o non verificabile",
    "CLOCK_UNVERIFIED":"Orologio incoerente — risultato non mostrato",
}
def _stamp(ms):
    return datetime.fromtimestamp(ms/1000,tz=timezone.utc).astimezone(ZoneInfo("Europe/Rome")).strftime("%d/%m/%Y %H:%M:%S %Z")

def _base(now,origin,status):
    return {"schema":"remura.tv.private.dashboard.read.v1","version":"0.8.84-lab",
            "status":status,"origin":origin,"viewed_ms":now,"claim_ms":None,
            "cutoff_ms":None,"completed_ms":None,"age_ms":None,"coverage":None,
            "latest_claim_incomplete":None,"market_calendar_verified":False,
            "live_authorized":False,"notifications_enabled":False,"orders_enabled":False,
            "html":None}
def _coverage(c,cutoff):
    keys={"requested_slots","valid_unique_bars","missing_requested_slots","first_requested_close_ms","last_requested_close_ms","basis","latest_immature_bars_not_queried","legacy_fxcm_export_supplied","scientific_benchmarks_computed"}
    if type(c) is not dict or set(c)!=keys:
        raise ValueError("dashboard_coverage")
    n,v,m,a,b=(c[k] for k in ("requested_slots","valid_unique_bars","missing_requested_slots","first_requested_close_ms","last_requested_close_ms"))
    if (any(type(x) is not int for x in (n,v,m,a,b)) or not 1<=n<=360 or not 0<=v<=n or
        m!=n-v or a%M5 or b%M5 or b!=cutoff-DELAY or a>b or (b-a)//M5+1!=n or
        c["basis"]!="MATURE_REQUESTED_SLOTS_NOT_MARKET_CALENDAR" or
        c["latest_immature_bars_not_queried"] is not True or
        any(c[k] is not False for k in ("legacy_fxcm_export_supplied","scientific_benchmarks_computed"))):
        raise ValueError("dashboard_coverage_invalid")
    return c
def _banner(r):
    text=escape(LABELS[r["status"]])
    parts=["<section><small>v0.8.84 LAB | Consultazione "+escape(_stamp(r["viewed_ms"]))+"</small>",
           "<h2>"+text+"</h2>","<p>Solo ricerca privata. Nessun segnale operativo.</p>"]
    if r["cutoff_ms"] is not None:
        c=r["coverage"]
        parts.append("<p>Cutoff: "+escape(_stamp(r["cutoff_ms"]))+" · Ultimo salvataggio: "+escape(_stamp(r["completed_ms"]))+"</p>")
        parts.append("<p>Età del cutoff: "+str(r["age_ms"]//60000)+" min · Barre valide: "+str(c["valid_unique_bars"])+"/"+str(c["requested_slots"])+" slot richiesti.</p>")
    if r["latest_claim_incomplete"]:
        parts.append("<p>Tentativo senza completamento: non distingue in corso, errore o arresto.</p>")
    parts.append("<p>Copertura riferita agli slot richiesti, non alle sessioni di mercato. Nessuna prova di disponibilità live o qualità predittiva.</p></section>")
    return "".join(parts)
def _standalone(r):
    origin="DATI SINTETICI — NON REALI" if r["origin"]=="SYNTHETIC" else "SNAPSHOT LOCALE — NON LIVE"
    return '<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'"><title>REMURA LAB — 0.8.84</title></head><body><main><h1>REMURA — '+origin+'</h1>'+_banner(r)+'</main></body></html>'

def read_dashboard(root,*,now,origin="LOCAL_SNAPSHOT",explicit=False):
    if explicit is not True or origin not in ("LOCAL_SNAPSHOT","SYNTHETIC"):
        raise ValueError("explicit_private_dashboard_required")
    current=bucket(now)
    r=_base(now,origin,"STATE_UNAVAILABLE")
    try:
        # Atomic replace makes one descriptor a coherent old or new generation.
        # Do not lock the writer or create anything; no claim liveness assertion.
        with open_state(root,origin=origin,guard=lambda:None,explicit=True) as state:
            s=state.read()
        claim,success=s["claim_ms"],s["last_success"]
        if claim is not None and claim>current or success is not None and success["completed_ms"]>now:
            r["status"]="CLOCK_UNVERIFIED"
        else:
            r["claim_ms"]=claim
            incomplete=claim is not None and (success is None or claim>success["cutoff_ms"])
            r["latest_claim_incomplete"]=incomplete
            if success is None:
                r["status"]="INCOMPLETE_NO_RESULT" if incomplete else "NO_SAVED_RESULT"
            else:
                cutoff=success["cutoff_ms"]; c=_coverage(success["coverage"],cutoff)
                status=("INCOMPLETE_NEWER_CLAIM" if incomplete else "OLDER_RESULT" if cutoff<current else
                    "CURRENT_EMPTY" if c["valid_unique_bars"]==0 else "CURRENT_PARTIAL" if c["missing_requested_slots"] else "CURRENT_REQUESTED_COMPLETE")
                html=success["html"]
                if html.count("<main><header>")!=1 or html.count("<title>REMURA LAB — 0.8.83</title>")!=1:
                    raise ValueError("dashboard_producer_shape")
                r.update(status=status,cutoff_ms=cutoff,completed_ms=success["completed_ms"],
                         age_ms=now-cutoff,coverage=c)
                # Status above the original saved header; original save stamp retained.
                r["html"]=html.replace("<main><header>","<main>"+_banner(r)+"<header>",1).replace(
                    "<title>REMURA LAB — 0.8.83</title>","<title>REMURA LAB — 0.8.84</title>",1)
    except (OSError,ValueError,TypeError,KeyError,OverflowError,RecursionError):
        r=_base(now,origin,"STATE_UNAVAILABLE")
    if r["html"] is None:r["html"]=_standalone(r)
    return r
