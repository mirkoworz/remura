# REMURA Contributors v0.4 LAB — 14/11/2026 23:32 CET
"""Local owner-only synthetic review preview; no HTTP, forms or actions."""
from collections import Counter
from html import escape
from ledger_v1 import _time

LABELS={"UNREVIEWED":"In attesa","APPROVED":"Approvato","REJECTED":"Rifiutato","REVOKED":"Revocato"}
def render_owner(archive, principal, *, generated_utc):
    # queue performs owner allowlist check before exposing data.
    data=archive.queue(principal)
    _time(generated_utc)
    counts=Counter(row["status"] for row in data)
    def e(v):return escape(str(v),quote=True)
    parts=['<!doctype html><html lang="it"><head><meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; form-action \'none\'; base-uri \'none\'">',
           '<title>REMURA Contributors v0.4 LAB — Revisione</title>',
           '<style>:root{color-scheme:dark;--bg:#07121a;--panel:#101f2a;--outline:#203642;--ink:#e8f4f3;--muted:#8ba7ae;--aqua:#69edca}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui}main{max-width:680px;margin:auto;padding:18px}.release{background:#102c35;color:#b9f8df;padding:6px;text-align:center;font-size:11px}small{color:var(--muted)}article,section{border:1px solid var(--outline);background:linear-gradient(180deg,#10222e,#101e29);padding:16px;border-radius:19px;margin:12px 0;overflow-wrap:anywhere}h1,h2,h3{letter-spacing:-.025em}h2{font-size:20px}strong{color:var(--aqua)}.counts{display:grid;grid-template-columns:1fr 1fr;gap:8px}.counts div{padding:10px;border:1px solid var(--outline);border-radius:12px}ol{padding-left:24px}</style></head><body>',
           '<div class="release">REMURA · Contributors v0.4 LAB · 14/11/2026 23:32 CET</div><main>',
           '<small>REMURA / VOLUMETRICA / CONTRIBUTORS</small><h1>Revisione contributi</h1>',
           '<p>SOLO DATI SINTETICI · Anteprima owner in sola lettura · Nessuna ammissione scientifica.</p>',
           '<small>Generato UTC: '+e(generated_utc)+'</small><section class="counts">']
    for status,label in LABELS.items():
        parts.append('<div>'+e(label)+'<br><strong>'+str(counts[status])+'</strong></div>')
    parts.append('</section>')
    for row in data:
        p=row["data"]
        parts.extend(['<article><small>Contributo #'+e(row["id"])+' · '+e(row["subject"])+'</small>',
                      '<h2>'+e(p["market"])+' · '+e(p["price"])+'</h2>',
                      '<p>'+e(p["provider"])+':'+e(p["ticker"])+' · '+e(p["product"])+' '+e(p["contract"])+'</p>',
                      '<p>'+e(p["period"])+' · '+e(p["kind"])+'<br>Fonte gruppo: '+e(p["source_group"])+'</p>',
                      '<small>Anchor: '+e(p["anchor_utc"])+'<br>Osservato: '+e(p["observed_utc"])+'<br>Ricevuto: '+e(row["received_utc"])+'</small>',
                      '<p>Nota: '+e(p["note"])+'</p><strong>'+e(LABELS[row["status"]])+'</strong><ol>'])
        for h in row["history"]:
            parts.append('<li>'+e(h["at_utc"])+' · '+e(LABELS[h["action"]])+' · '+e(h["owner"])+': '+e(h["reason"])+'</li>')
        parts.append('</ol></article>')
    if not data:parts.append('<p>Nessun contributo sintetico.</p>')
    parts.append('</main></body></html>')
    return "".join(parts)
