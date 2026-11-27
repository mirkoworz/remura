/* REMURA Shark Focus UI v1.71 LAB — 23/11/2026 20:20 CET.
 * Touch-first view of existing CFTC favorites; DOM-only, no network.
 */
(function(){
  "use strict";
  const core=window.REMURA_SHARK_FOCUS;
  const container=document.getElementById("my-sharks-list");
  const status=document.getElementById("my-sharks-status");
  if(!core||!container||!status)return;
  const number=new Intl.NumberFormat("it-IT",{maximumFractionDigits:2,minimumFractionDigits:1});
  const itDate=new Intl.DateTimeFormat("it-IT",{day:"2-digit",month:"short",year:"numeric",timeZone:"UTC"});
  const make=(tag,cls,value)=>{
    const el=document.createElement(tag);
    if(cls)el.className=cls;
    if(value!==undefined)el.textContent=value;
    return el;
  };
  const date=s=>typeof s==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(s)?
    itDate.format(new Date(s+"T12:00:00Z")):"N/D";
  const pp=x=>Number.isFinite(x)?(x>0?"+":"")+number.format(x)+" pp":"N/D";
  const label=status=>({
    CONFRONTABILE:"COT confrontabile",SOLO_REPORT:"Solo report, WoW N/D",
    DATATO:"Report datato",CONFLITTO:"Righe in conflitto",
    NON_DISPONIBILE:"Dati N/D"
  })[status]||"N/D";
  function render(cards,favorites,{onOpen,onToggle}={}){
    const data=core.build(cards,favorites);
    container.replaceChildren();
    const counter=data.count+" futures seguiti · "+data.comparable+
      " confrontabili · "+data.onlyReport+" senza settimana confrontabile · "+
      data.unavailable+" datati, discordanti o assenti.";
    status.textContent=counter+(data.differentReportWeeks?
      " Le variazioni disponibili provengono da martedì diversi: non confrontarle come un unico periodo.":"");
    if(!data.count){
      const empty=make("div","focus-empty");
      empty.append(make("strong","","Non stai seguendo ancora nessun future."),
        make("p","","Scorri alle schede e tocca ☆ per creare la tua vista personale. Nessun account o servizio aggiuntivo."));
      const link=make("a","focus-start","Scegli i contratti ↓");
      link.href="#contracts";empty.append(link);
      container.append(empty);
      return;
    }
    const fragment=document.createDocumentFragment();
    for(const item of data.items){
      const card=make("article","focus-card");
      card.dataset.quality=item.quality;
      const top=make("div","focus-card-top");
      const identification=make("div","focus-identification");
      identification.append(make("div","focus-family",(item.family||"Future")+" · CFTC "+(item.dataset==="tff"?"TFF":item.dataset==="disagg"?"Disaggregated":"N/D")),
        make("h3","",item.name));
      const del=make("button","focus-unstar","★");
      del.type="button";
      del.setAttribute("aria-label","Rimuovi "+item.name+" dai preferiti");
      del.title="Non seguire più questo future";
      if(typeof onToggle==="function")del.addEventListener("click",()=>onToggle(item.code));
      else del.disabled=true;
      top.append(identification,del);
      card.append(top);
      const quality=make("p","focus-quality",label(item.quality));
      card.append(quality);
      card.append(make("p","focus-report","Report CFTC: "+date(item.reportDate)+
        (Number.isFinite(item.ageDays)?" · "+item.ageDays+" giorni dal martedì":"")));
      if(item.deltas){
        const grid=make("div","focus-changes");
        for(let i=0;i<2;i++){
          const change=make("div","focus-change");
          const key=i===0?"first":"second";
          change.append(make("span","",item.labels[i]||"Categoria "+(i+1)),
            make("strong",item.deltas[key]>0?"focus-plus":item.deltas[key]<0?"focus-minus":"",
              pp(item.deltas[key])));
          grid.append(change);
        }
        card.append(grid);
        if(item.comparison==="DIVERGENT")card.append(make("p","focus-divergence",
          "Variazioni tra categorie in direzioni opposte · non un segnale"));
      }else{
        card.append(make("p","focus-unavailable",
          "Δ WoW: N/D. Non ricostruiamo le settimane mancanti o i report discordanti."));
      }
      const open=make("button","focus-open","Apri radiografia e storico");
      open.type="button";
      if(typeof onOpen==="function")open.addEventListener("click",()=>onOpen(item.code));
      else open.disabled=true;
      card.append(open);
      fragment.append(card);
    }
    container.append(fragment);
  }
  window.REMURA_SHARK_FOCUS_UI=Object.freeze({render});
})();