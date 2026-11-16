# REMURA Level Confluence v0.11 LAB — 14/11/2026 23:47 CET
"""Owner-only in-process diagnostic dashboard, synthetic data, no HTTP/export.
Automatic inputs and explicit comparison rules are trusted LAB fixtures.
No actual price feed, no prediction, no operational or scientific admission.
"""
from html import escape
from integrated_lab_v1 import IntegratedLab
from level_confluence_v1 import compare
from ledger_v1 import _time

MAX_AUTO=20
LABELS={
    "NEAR":"Vicino — confluenza candidata",
    "DISTANT":"Distante",
    "COMPARED_NO_NEAR":"Confrontato, nessuna vicinanza",
    "NO_COMPARABLE_MANUAL":"N/D — nessun manuale confrontabile",
    "NO_COMPARABLE_AUTOMATIC":"N/D — nessun automatico confrontabile",
    "NOT_COMPARABLE_NO_RULE":"N/D — regola di confronto assente",
}
STYLE=":root{color-scheme:dark;--bg:#07121a;--panel:#101f2a;--ink:#e8f4f3;--muted:#8ba7ae;--aqua:#69edca}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui}main{max-width:760px;margin:auto;padding:18px}.release{background:#102c35;color:#b9f8df;padding:6px;text-align:center;font-size:11px}article,section{border:1px solid #203642;border-radius:19px;background:linear-gradient(#10222e,#101e29);padding:16px;margin:14px 0;overflow-wrap:anywhere}h1,h2{letter-spacing:-.035em}h2{font-size:20px}small{color:var(--muted)}strong{color:var(--aqua)}.price{font-size:25px;font-weight:800;color:var(--aqua)}li{margin:8px 0}.near{border-left:3px solid var(--aqua)}.missing{color:var(--muted)}"

def _e(x):return escape(str(x),quote=True)

def _render(result,manual,auto):
    # Only display rows admitted into this comparison, never later manual/auto data.
    m={row["id"]:row["data"] for row in manual}
    a={row["id"]:row for row in auto}
    parts=['<!doctype html><html lang="it"><head><meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; form-action \'none\'; base-uri \'none\'">',
           '<title>REMURA Level Confluence v0.11 LAB</title><style>'+STYLE+'</style></head><body>',
           '<div class="release">REMURA · Level Confluence v0.11 LAB · 14/11/2026 23:47 CET</div><main>',
           '<small>REMURA / VOLUMETRICA / LEVEL CONFLUENCE</small><h1>Confluenze volumetriche</h1>',
           '<p>SOLO DATI SINTETICI · Report proprietario in sola lettura. Nessun segnale operativo o prova di attività istituzionale.</p>',
           '<p>Cutoff UTC: '+_e(result["asof_utc"])+'</p>',
           '<section><strong>Livelli automatici disponibili: '+str(len(result["automatic"]))+'</strong>',
           '<p>Manuali approvati al cutoff: '+str(len(result["manual"]))+'<br>Manuali esclusi: '+str(result["excluded_manual"])+'<br>Automatici esclusi: '+str(result["excluded_automatic"])+'</p>',
           '<small>Gruppi fonte dichiarati: non attestano indipendenza. Soglie e tick sperimentali, non validati.</small></section>']
    for item in result["automatic"]:
        p=a[item["automatic_id"]]
        parts.extend(['<article'+(' class="near"' if item["status"]=="NEAR" else '')+'>',
                      '<small>Automatico '+_e(item["automatic_id"])+'</small>',
                      '<h2>'+_e(p["market"])+' · '+_e(p["period"])+'</h2>',
                      '<p>'+_e(p["provider"])+':'+_e(p["ticker"])+' · '+_e(p["product"])+' '+_e(p["contract"])+'</p>',
                      '<small>'+_e(p["kind"])+' · Anchor UTC '+_e(p["anchor_utc"])+'</small>',
                      '<div class="price">'+_e(p["price"])+'</div><strong>'+_e(LABELS[item["status"]])+'</strong>',
                      '<p>Manuali vicini: '+str(item["near_count"])+' · Gruppi dichiarati vicini: '+str(item["declared_source_groups"])+'</p><ul>'])
        for pair in item["pairs"]:
            q=m[pair["manual_id"]]
            parts.append('<li>Manuale #'+_e(pair["manual_id"])+' · '+_e(q["price"])+
                         ' · '+_e(pair["distance_ticks"] if pair["distance_ticks"] is not None else "N/D")+
                         ' tick · '+_e(LABELS[pair["status"]])+'</li>')
        parts.append('</ul></article>')
    if not result["automatic"]:parts.append('<p>N/D — nessun automatico disponibile al cutoff.</p>')
    parts.append('<section><h2>Riepilogo manuali approvati</h2><ul>')
    for item in result["manual"]:
        p=m[item["manual_id"]]
        parts.append('<li>#'+_e(item["manual_id"])+' · '+_e(p["market"])+' · '+_e(p["provider"])+
                     ':'+_e(p["ticker"])+' · '+_e(p["period"])+' · '+_e(p["price"])+' · '+
                     _e(LABELS[item["status"]])+'</li>')
    parts.append('</ul></section></main></body></html>')
    return "".join(parts)

def owner_report(lab,token,automatic,rules,*,asof_utc=None,synthetic=False):
    if synthetic is not True or type(lab) is not IntegratedLab:
        raise ValueError("synthetic_integrated_lab_only")
    # Same timestamp for session check and cutoff ceiling, serial lab thread.
    now=lab._now()
    actor=lab._access.principal(token,now=now)
    manual=lab._archive.queue(actor)  # owner role enforced before examining fixtures
    current=lab._stamp(now)
    cutoff=current if asof_utc is None else asof_utc
    if _time(cutoff)>_time(current):raise ValueError("future_cutoff")
    if type(automatic) is not list or len(automatic)>MAX_AUTO:
        raise ValueError("dashboard_capacity")
    result=compare(manual,automatic,rules,asof_utc=cutoff,synthetic=True)
    return {"result":result,"html":_render(result,manual,automatic)}

# v0.37: independent synthetic aggregate view, no archive/session/HTTP exposure.
def wire_report(manual,envelopes,*,asof_utc,synthetic=False):
    """Render the exact wire handoff result, with no private rows in HTML."""
    from explicit_pine_wire_lab_v1 import handoff
    result=handoff(manual,envelopes,asof_utc=asof_utc,synthetic=synthetic)
    counts=result["automatic_status_counts"]
    parts=['<!doctype html><html lang="it"><head><meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; form-action \'none\'; base-uri \'none\'">',
           '<title>REMURA Level Confluence v0.37 LAB</title><style>'+STYLE+'</style></head><body>',
           '<div class="release">REMURA · Level Confluence v0.37 LAB · 16/11/2026 16:33 CET</div><main>',
           '<small>REMURA / VOLUMETRICA / LEVEL CONFLUENCE</small><h1>Confluenze volumetriche</h1>',
           '<p>SOLO DATI SINTETICI — LABFX fittizio. Nessuna confluenza confermata, nessun segnale operativo.</p>',
           '<p>Cutoff UTC: '+_e(result["asof_utc"])+'</p>',
           '<section><h2>Disponibilità delle fonti</h2>',
           '<p>Automatici disponibili: '+str(result["automatic_eligible"])+'<br>Manuali approvati e compatibili: '+str(result["manual_eligible"])+'</p>',
           '<p>Automatici tardivi: '+str(result["automatic_late"])+'<br>Manuali esclusi dalla revisione: '+str(result["manual_review_excluded"])+'</p>',
           '<p>Automatici con metadati incompatibili: '+str(result["automatic_metadata_blocked"])+'<br>Manuali con metadati non ammessi: '+str(result["manual_metadata_blocked"])+'</p></section>',
           '<section><h2>Confronti causali</h2>',
           '<p>Automatici confrontati: '+str(result["automatic_compared"])+'<br>Coppie vicine candidate: '+str(result["near_pair_count"])+'</p>']
    for key,value in sorted(counts.items()):
        parts.append('<p>'+_e(LABELS[key])+': '+str(value)+'</p>')
    if not result["price_comparison_performed"]:
        parts.append('<p class="missing">N/D — confronto di prezzo non eseguito. Assenza di evidenza non significa disaccordo.</p>')
    parts.extend(['</section><section><h2>Attendibilità</h2>',
                  '<p>Identità della configurazione: '+_e(result["config_id"])+'</p>',
                  '<p>Configurazione, orologio di ricezione, equivalenza feed e indipendenza fonti non attestati. Soglie esclusivamente sintetiche.</p>',
                  '<p>Ammissione scientifica: NO · Ordini: NO · Notifiche: NO</p>',
                  '</section></main></body></html>'])
    return {"result":result,"html":"".join(parts)}
