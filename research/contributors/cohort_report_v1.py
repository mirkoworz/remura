# REMURA Level Confluence v0.14 LAB — 14/11/2026 23:53 CET
"""Owner-only synthetic descriptive report, computed from frozen LAB inputs.
No trading returns, rankings, inference, live access, HTTP or persistence.
Caller is trusted to hold the original digest before observing outcomes.
"""
from collections import defaultdict,Counter
from decimal import Decimal,localcontext
from html import escape
from cohort_study_v1 import evaluate,COHORTS
from integrated_lab_v1 import IntegratedLab
from ledger_v1 import _time

LABELS={"A_NEAR":"A — Confluenze candidate","B_DISTANT":"B — Manuali distanti",
        "C_NO_MANUAL":"C — Nessun manuale confrontabile","D_MANUAL_ISOLATED":"D — Manuali isolati",
        "N_D_RULE":"N/D — Regola assente"}

def _stats(values):
    if not values:return None
    a=sorted(values);n=len(a)
    with localcontext() as ctx:
        ctx.prec=40
        median=a[n//2] if n%2 else (a[n//2-1]+a[n//2])/2
        return {"min":format(a[0],"f"),"median":format(median,"f"),"max":format(a[-1],"f")}

def _rate(n,d):
    with localcontext() as ctx:
        ctx.prec=40
        return format(Decimal(n)*100/d,".2f") if d else None

def _summarize(rows):
    c=Counter(r["status"] for r in rows)
    touched=[r for r in rows if r["status"]=="TOUCHED"]
    valid=c["TOUCHED"]+c["NO_TOUCH"]
    crossing=sum(r["closed_across"] for r in touched)
    return dict(total=len(rows),valid=valid,touched=c["TOUCHED"],no_touch=c["NO_TOUCH"],
                n_d=c["N_D"],closed_across=crossing,contact_percent=_rate(len(touched),valid),
                crossing_percent=_rate(crossing,len(touched)),
                reasons=dict(sorted(Counter(r["reason"] for r in rows if r["status"]=="N_D").items())),
                away=_stats([Decimal(r["away_excursion"]) for r in touched]),
                through=_stats([Decimal(r["through_excursion"]) for r in touched]))

def _render(report):
    def e(v):return escape(str(v),quote=True)
    def pct(v):return "N/D" if v is None else e(v)+"%"
    def excursion(v):return "N/D" if v is None else e(v["median"])+" (min "+e(v["min"])+", max "+e(v["max"])+")"
    parts=['<!doctype html><html lang="it"><head><meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width,initial-scale=1">',
           '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; form-action \'none\'; base-uri \'none\'">',
           '<title>REMURA Level Statistics v0.14 LAB</title><style>:root{color-scheme:dark}body{margin:0;background:#07121a;color:#e8f4f3;font:16px/1.5 system-ui}main{max-width:720px;margin:auto;padding:18px}.release{background:#102c35;color:#b9f8df;text-align:center;font-size:11px;padding:6px}article{background:#101f2a;border:1px solid #203642;border-radius:18px;margin:12px 0;padding:15px;overflow-wrap:anywhere}strong{color:#69edca}small{color:#8ba7ae}dt{color:#8ba7ae}dd{margin:0 0 8px}</style></head><body>',
           '<div class="release">REMURA · Level Statistics v0.14 LAB · 14/11/2026 23:53 CET</div><main>',
           '<h1>Statistiche comparative</h1><p>SOLO DATI SINTETICI · Owner · Nessuna inferenza, ranking o segnale operativo.</p>',
           '<small>Cutoff UTC '+e(report["cutoff_utc"])+' · Valutato UTC '+e(report["evaluated_utc"])+'</small>',
           '<p>Campione fissato: '+str(report["total_units"])+' unità. Distanze in unità di prezzo della fonte; nessuna media fra strumenti diversi.</p>']
    for group in report["groups"]:
        key=group["key"];s=group["stats"]
        parts.extend(['<article><small>'+e(key[1])+':'+e(key[2])+' · '+e(key[3])+' '+e(key[4])+'</small>',
                      '<h2>'+e(key[0])+' · '+e(key[5])+'</h2><p>'+e(key[7])+' · Anchor '+e(key[6])+'</p>',
                      '<strong>'+e(LABELS[group["cohort"]])+'</strong><dl>',
                      '<dt>Unità / valide / N/D</dt><dd>'+e(s["total"])+' / '+e(s["valid"])+' / '+e(s["n_d"])+'</dd>',
                      '<dt>Contatti / valide</dt><dd>'+e(s["touched"])+' / '+e(s["valid"])+' · '+pct(s["contact_percent"])+'</dd>',
                      '<dt>Attraversamenti / contatti</dt><dd>'+e(s["closed_across"])+' / '+e(s["touched"])+' · '+pct(s["crossing_percent"])+'</dd>',
                      '<dt>Escursione dal livello verso origine</dt><dd>'+excursion(s["away"])+'</dd>',
                      '<dt>Escursione verso lato opposto</dt><dd>'+excursion(s["through"])+'</dd></dl>'])
        for reason,count in s["reasons"].items():parts.append('<small>'+e(reason)+': '+e(count)+'</small> ')
        parts.append('</article>')
    if not report["groups"]:parts.append('<p>N/D — nessuna unità nel campione.</p>')
    return "".join(parts)+"<p>Confronti descrittivi, dipendenze e dimensione campionaria non validate. Non sono MFE/MAE di trade.</p></main></body></html>"

def owner_statistics(lab,token,manifest,digest,windows,*,evaluated_utc,synthetic=False):
    if synthetic is not True or type(lab) is not IntegratedLab:raise ValueError("synthetic_only")
    now=lab._now()
    actor=lab._access.principal(token,now=now)
    if actor.role!="OWNER":raise PermissionError("owner_required")
    if _time(evaluated_utc)>_time(lab._stamp(now)):raise ValueError("future_evaluation")
    result=evaluate(manifest,digest,windows,evaluated_utc=evaluated_utc,synthetic=True)
    units={u["unit_id"]:u for u in manifest["units"]}
    grouped=defaultdict(list)
    for row in result["results"]:
        u=units[row["unit_id"]]
        grouped[(tuple(u["key"]),row["cohort"])].append(row["result"])
    report=dict(cutoff_utc=manifest["cutoff_utc"],evaluated_utc=evaluated_utc,total_units=len(units),
                groups=[dict(key=list(key),cohort=cohort,stats=_summarize(rows))
                        for (key,cohort),rows in sorted(grouped.items())],
                cohort_counts={k:{n:v for n,v in s.items() if n in ("total","valid","touched","no_touch","n_d","closed_across")}
                               for k,s in result["metrics"].items()},
                manifest_digest=digest,synthetic=True,scientific_admission=False,operational_signal=False,
                independent_observations_verified=False)
    return {"report":report,"html":_render(report)}
