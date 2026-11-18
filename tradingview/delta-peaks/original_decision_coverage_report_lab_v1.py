"""REMURA v0.8.172 LAB — 18/11/2026, sessione successiva alle 17:48 CET.
Standalone offline aggregate-only mobile report; no real exports or outcome access.
"""
from html import escape
from itertools import product

SCHEMA="remura.tv.original.decision.coverage.lab.v1"
MATRIX={"FXCM_"+a+"|FX_"+b for a,b in product(("PRESENT","PARTIAL","UNKNOWN"),("PRESENT","UNKNOWN"))}
OUTSIDE={"OTHER_B_MARKET","B_CLOCK_OUTSIDE_HANDOFF"}
LEGACY={
"DESCRIPTIVE_CANDIDATE_ONLY":"Disponibile","PARTIAL_DESCRIPTIVE_ONLY":"Parziale",
"NO_EXACT_CLOSE":"Barra non presente nella finestra","NOT_KNOWN_AT_DECISION":"Ricevuto dopo la decisione",
"BLOCKED_INVALID_OR_CONFLICT":"Invalido o conflitto","BLOCKED_NOT_PROSPECTIVELY_TIMELY":"Ricezione non tempestiva",
"BLOCKED_DIAGNOSTIC_REVIEW":"Controllo qualità non superato",
"BLOCKED_CONFIG_METADATA_MISMATCH":"Configurazione incompatibile"}
CVD={
"DESCRIPTIVE_MATCH":"Disponibile","NO_EXACT_CLOSE":"Barra non presente nella finestra",
"NOT_KNOWN_AT_DECISION":"Ricevuto dopo la decisione","BEFORE_CVD_DEPLOYMENT":"Prima della raccolta CVD",
"BLOCKED_CONFLICT":"Conflitto","BLOCKED_INVALID":"Invalido",
"BLOCKED_DIAGNOSTIC_REVIEW":"Controllo qualità non superato","BLOCKED_AMBIGUOUS":"Ambiguo",
"CVD_NOT_ELIGIBLE":"CVD non ammissibile"}

def need(ok):
    if not ok:raise ValueError("COVERAGE_REPORT_GATE")
def counts(value,allowed):
    need(type(value) is dict and all(k in allowed and type(v) is int and 0<=v<=5000 for k,v in value.items()))
    return sum(value.values())
def render(r,*,synthetic=False):
    need(synthetic is True and type(r) is dict and r.get("schema")==SCHEMA)
    need(all(r.get(k) is False for k in ("source_price_equivalence","source_independence_verified",
         "outcomes_evaluated","scientific_admission","orders_enabled","notifications_enabled")))
    n,e=r["population"],r["eligible_clock_population"]
    need(type(n) is int and type(e) is int and 0<=e<=n<=5000)
    c,l,f=r["counts"],r["legacy_reason_counts"],r["cvd_reason_counts"]
    need(counts(c,MATRIX|OUTSIDE)==n and counts(l,LEGACY)==counts(f,CVD)==e)
    need(sum(c.get(k,0) for k in MATRIX)==e)
    for state,reason in (("PRESENT","DESCRIPTIVE_CANDIDATE_ONLY"),("PARTIAL","PARTIAL_DESCRIPTIVE_ONLY")):
        need(sum(c.get("FXCM_"+state+"|FX_"+b,0) for b in ("PRESENT","UNKNOWN"))==l.get(reason,0))
    need(sum(c.get("FXCM_"+a+"|FX_PRESENT",0) for a in ("PRESENT","PARTIAL","UNKNOWN"))==f.get("DESCRIPTIVE_MATCH",0))
    both=c.get("FXCM_PRESENT|FX_PRESENT",0)
    need(type(r["both_descriptive_present"]) is int and r["both_descriptive_present"]==both)
    def table(d,labels):
        return "".join("<tr><td>"+escape(labels[k])+"</td><td>"+str(v)+"</td></tr>"
                       for k,v in sorted(d.items())) or "<tr><td>N/D</td><td>—</td></tr>"
    return ('<!doctype html><html lang="it"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'">'
        '<title>REMURA SQUALINCOME v0.8.172 LAB</title><style>'
        'body{background:#07121a;color:#e8f4f3;font:16px system-ui;margin:0}main{max-width:720px;margin:auto;padding:18px}'
        'section{background:#10222e;border:1px solid #203642;border-radius:16px;padding:16px;margin:12px 0}'
        'small{color:#8ba7ae}strong{color:#69edca}table{width:100%;border-collapse:collapse}td{padding:8px 0;border-bottom:1px solid #203642}td:last-child{text-align:right}</style></head><body><main>'
        '<small>REMURA v0.8.172 LAB · 18/11/2026, dopo le 17:48 CET</small>'
        '<h1>SQUALINCOME — Copertura fonti</h1><p>SOLO DATI SINTETICI. Nessun segnale operativo.</p>'
        '<section><strong>Entrambe disponibili: '+(str(both)+" / "+str(e) if e else "N/D")+'</strong>'
        '<p>Decisioni totali: '+str(n)+' · Compatibili per orario: '+str(e)+'</p></section>'
        '<section><h2>FXCM:EURUSD</h2><table>'+table(l,LEGACY)+'</table></section>'
        '<section><h2>FX:EURUSD CVD</h2><table>'+table(f,CVD)+'</table></section>'
        '<p>Fonti separate; nessuna equivalenza o indipendenza attestata. N/D non significa opposizione.'
        ' Le ricezioni tardive sono diagnostiche retrospettive, non informazioni disponibili alla decisione.</p></main></body></html>')
