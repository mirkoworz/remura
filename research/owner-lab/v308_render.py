"""LAB only. The caller must authenticate OWNER server-side.
Never mount this handler on a public or contributor route.
No network, no browser authentication, no raw source data.
"""
from pathlib import Path
LABELS={"DESCRIPTIVE_ONLY":"Disponibile per osservazione","PUBLIC_DESCRIPTIVE_ONLY":"Contesto pubblico disponibile","RETAIL_DESCRIPTIVE_ONLY":"Snapshot retail disponibile","STALE":"Non aggiornato","STALE_BAR":"Barra non aggiornata","NO_VALID_FEATURE":"Nessun segmento valido","NO_CLOSED_BAR":"Nessuna barra chiusa","NOT_AVAILABLE_ASOF":"Non disponibile al momento","UNAVAILABLE":"Non disponibile","MISSING_SYMBOL":"Simbolo assente","NOT_JOINED":"Non collegato"}
def render(summary,*,authenticated_owner=False):
    if authenticated_owner is not True:raise PermissionError("owner_required")
    if summary.get("status")!="DESCRIPTIVE_ONLY" or summary.get("prospective_admitted") is not False:
        raise ValueError("summary")
    def count(k,maximum):
        n=summary.get(k)
        if type(n) is not int or not 0<=n<=maximum:raise ValueError("count")
        return n
    def label(k):
        return LABELS.get(summary.get(k),"Stato non disponibile")
    fields=[label("footprint_status")+" · "+str(count("footprint_segment_bars",288))+" barre",
            str(count("available_level_count",7))+" livelli",
            label("price_status"),label("cot_status"),label("sentiment_status")]
    html=Path(__file__).with_name("intelligence-v308.template.html").read_text()
    html=html.replace("@@HEADER@@","Osservazione descrittiva · nessun segnale operativo")
    for i,v in enumerate(fields,1):html=html.replace("@@SOURCE"+str(i)+"@@",v)
    for key,token in (("local_observations","LOCAL"),("outcome_rows","OUTCOMES"),("certified_observations","CERTIFIED"),("price_snapshots","SNAPSHOTS"),("historical_m15","M15"),("conflicted_bars","CONFLICTS"),("terminal_missing_horizons","MISSING")):
        value=summary.get(key)
        if value is None:label_value="Non disponibile"
        elif type(value) is int and 0<=value<=1000000:label_value=str(value)
        else:raise ValueError("science_count")
        if key=="certified_observations" and value not in (0,None):raise ValueError("not_admitted")
        html=html.replace("@@"+token+"@@",label_value)
    return html
