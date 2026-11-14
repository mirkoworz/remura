#!/usr/bin/env python3
# REMURA v0.8.69 LAB — 14/11/2026 CET
"""Render the aggregate research dossier offline; no external assets or scripts."""
from html import escape
from hashlib import sha256
from datetime import datetime, timezone
import json

SCHEMA="remura.tv.research.dossier.preview.v1"

def _validate(r):
    if (type(r) is not dict or r.get("schema")!=SCHEMA or
        r.get("origin") not in ("SYNTHETIC","LOCAL_SNAPSHOT") or
        any(r.get(k) is not False for k in ("orders_enabled","notifications_enabled",
            "predictive_admission","track_b_live_connected"))):
        raise ValueError("not_research_only_dossier")

def notification_preview(r):
    _validate(r)
    join=r.get("tv_cvd_join")
    if join is not None and (type(join) is not dict or join.get("schema")!="remura.tv.cvd.b.asof.preview.v1" or
        any(join.get(k) is not False for k in ("orders_enabled","notifications_enabled","scientific_admission"))):
        raise ValueError("not_research_only_cvd_join")
    # Repeatable diagnostic notice ID only: does not send or save anything.
    counts=r["pair_counts"]
    paired=sum(counts.get(k,0) for k in ("DESCRIPTIVE_CANDIDATE_ONLY","PARTIAL_DESCRIPTIVE_ONLY"))
    state="DESCRIPTIVE_CANDIDATES_PRESENT" if paired else "NO_DESCRIPTIVE_PAIR"
    cvd_pairs={} if join is None else join["pair_counts"]
    cvd_reasons={} if join is None else join["observed_reason_counts"]
    _counts(cvd_pairs); _counts(cvd_reasons)
    n_cvd=cvd_pairs.get("DESCRIPTIVE_MATCH",0)
    if n_cvd:
        state="CVD_DESCRIPTIVE_MATCHES_PRESENT"
    fingerprint=sha256(json.dumps([r["origin"],r["as_of_ms"],r["days"],counts,cvd_pairs,cvd_reasons],
        sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return {"schema":"remura.tv.diagnostic.notice.preview.v1","notice_id":fingerprint,
            "state":state,"text":"REMURA LAB: verifica descrittiva. Nessun segnale operativo.",
            "candidate_count":paired,"tv_cvd_match_count":n_cvd,
            "tv_cvd_reasons":dict(sorted(cvd_reasons.items())),
            "would_send":False,"sent":False,
            "orders_enabled":False}

def _counts(counts):
    if not isinstance(counts,dict) or any(type(k) is not str or type(v) is not int or v<0 for k,v in counts.items()):
        raise ValueError("invalid_aggregate_counts")
    return "".join("<tr><td>"+escape(k)+"</td><td>"+str(v)+"</td></tr>"
                   for k,v in sorted(counts.items())) or "<tr><td>N/D</td><td>—</td></tr>"

def render(r):
    _validate(r)
    notice=notification_preview(r)
    headings={"cot_vs_intrabar_delta":"COT / delta intrabar",
              "cot_vs_price_body":"COT / corpo candela",
              "cot_vs_footprint_delta":"COT / delta footprint"}
    relations="".join("<section><h2>"+label+"</h2><table>"+_counts(r["relations"][k])+
                      "</table></section>" for k,label in headings.items())
    horizons=""
    for h in ("15","30","60"):
        data=r["outcomes"]["horizons"].get(h,{})
        horizons+="<section><h2>"+h+" minuti</h2><h3>Eventi (ANY_EVENT)</h3><table>"+_counts(
            data.get("event_counts",{}).get("ANY_EVENT",{}))+"</table><h3>Baseline</h3><table>"+_counts(
            data.get("baseline_counts",{}))+"</table></section>"
    join=r.get("tv_cvd_join")
    cvd_panel=("<p>N/D — nessun raccordo CVD TradingView disponibile.</p>" if join is None else
        "<h3>Copertura rispetto alle coppie B (non sommare a FXCM)</h3><table>"+_counts(join["pair_counts"])+
        "</table><h3>Motivi osservati — possono coesistere</h3><table>"+_counts(join["observed_reason_counts"])+
        "</table><h3>COT / direzione candidata selezionata CVD</h3><table>"+_counts(join["cot_vs_cvd_selected"])+"</table>")
    origin="DATI SINTETICI — NON REALI" if r["origin"]=="SYNTHETIC" else "SNAPSHOT LOCALE — PROVENIENZA NON CERTIFICATA"
    pairs="N/D" if r["b_local_pairs"] is None else str(r["b_local_pairs"])
    asof=datetime.fromtimestamp(r["as_of_ms"]/1000,tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return """<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>REMURA LAB — 0.8.69</title><style>
*{box-sizing:border-box}body{margin:0;background:#0b141d;color:#e7eef4;font:16px system-ui,sans-serif}
main{max-width:1040px;margin:auto;padding:22px}header{border-bottom:1px solid #354653;padding-bottom:18px}
small,p{color:#b2c4d1}h1{font-size:1.8rem;margin:10px 0}h2{font-size:1.1rem}h3{font-size:.9rem}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(245px,1fr));gap:12px}
section{background:#14212d;border:1px solid #354653;border-radius:12px;padding:16px;margin:8px 0}
table{border-collapse:collapse;width:100%;font-size:.88rem}td{padding:8px 4px;border-bottom:1px solid #354653;overflow-wrap:anywhere}td:last-child{text-align:right;font-variant-numeric:tabular-nums}
.notice{color:#e9ca81}footer{margin-top:20px;color:#b2c4d1;font-size:.85rem}
</style></head><body><main><header><small>v0.8.69 LAB | 14/11/2026 CET | Anteprima offline</small>
<h1>REMURA — Ricerca volumetrica EURUSD</h1><p class="notice">"""+origin+""" · Nessun segnale operativo</p><p>Cutoff dati: """+escape(asof)+"""</p></header>
<section><h2>Coppie COT/prezzo locali: """+escape(pairs)+"""</h2><table>"""+_counts(r["pair_counts"])+"""</table></section>
<div class="grid">"""+relations+"""</div><section><h2>Fonti mancanti / non attestate</h2>
<p>CVD cTrader: N/D · Sentiment retail: N/D · Parametri effettivi: non attestati. Nessuna prova di edge.</p></section>
<section><h2>TradingView CVD — FX:EURUSD M5, fonte distinta</h2>"""+cvd_panel+"""<p>Associazione temporale descrittiva, non conferma istituzionale. ER non direzionale.</p></section>
<h2>Disponibilità esiti prospettici</h2><div class="grid">"""+horizons+"""</div>
<section><h2>Anteprima notifica diagnostica (non inviata)</h2><p>"""+escape(notice["text"])+"""</p><p>Coppie CVD descrittive: """+str(notice["tv_cvd_match_count"])+"""</p><table>"""+_counts(notice["tv_cvd_reasons"])+"""</table></section>
<footer>Solo ricerca. Nessun collegamento live, ordine, invio, o equivalenza tra feed presunta.</footer></main></body></html>"""
