/* REMURA Shark Cockpit v1.66 LAB — 22/11/2026 18:13 CET.
 * Browser-only CFTC direct reads and already published same-origin Myfxbook.
 * No auto-polling, Cloudflare writes, authentication, trading or alerts.
 */
(() => {
  "use strict";
  const core=window.REMURA_SHARK_CORE;
  const byId=id=>document.getElementById(id);
  if(!core||!byId("cards"))return;
  const nf=new Intl.NumberFormat("it-IT",{maximumFractionDigits:2,minimumFractionDigits:1});
  const whole=new Intl.NumberFormat("it-IT",{maximumFractionDigits:0});
  const stamp=new Intl.DateTimeFormat("it-IT",{day:"2-digit",month:"short",year:"numeric",timeZone:"UTC"});
  const rome=new Intl.DateTimeFormat("it-IT",{day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit",timeZone:"Europe/Rome"});
  const els={cards:byId("cards"),message:byId("message"),refresh:byId("refresh"),
    family:byId("family"),sort:byId("sort"),search:byId("search"),
    retailList:byId("retail-list"),retailStatus:byId("retail-status"),
    favoritesOnly:byId("only-favorites"),watchlistNote:byId("watchlist-note")};
  const create=(tag,cls,text)=>{
    const e=document.createElement(tag);
    if(cls)e.className=cls;
    if(text!==undefined)e.textContent=text;
    return e;
  };
  const fmt=(v,kind="pct")=>Number.isFinite(v)?(v>0?"+":"")+nf.format(v)+(kind==="pp"?" pp":"%"):"N/D";
  const date=v=>v?stamp.format(new Date(v+"T12:00:00Z")):"N/D";
  const sortStatus=s=>s==="CURRENT_REPORT_DATE"?"Report recente":
    s==="STALE_REPORT"?"COT datato":
    s==="QUARANTINE_CONFLICT"?"Date in conflitto":
    s==="UNKNOWN_WEEKLY_COMPARISON"?"Settimane non consecutive":"Report non disponibile";
  const comparisonLabel=c=>c==="DIVERGENT"?"↗ Divergenza tra gruppi":
    c==="CO_MOVING"?"↔ Variazioni concordi":
    c==="FLAT_OR_MIXED"?"· Misto / senza variazione":
    "Divergenza non valutabile";
  let busy=false,cards=core.CONTRACTS.map(c=>core.card(c,null)),loaded={tff:false,disagg:false},
      errors={tff:"",disagg:""},retrievedAt=null;

  const WATCH_KEY="remura:shark:favorite-cftc:v166";
  let favorites=[],storageAvailable=true,expandedCodes=new Set(),
      snapshots={tff:null,disagg:null};
  try{favorites=core.parseFavorites(localStorage.getItem(WATCH_KEY)||"[]");}
  catch{storageAvailable=false;}
  function keepFavorites(){
    if(!storageAvailable)return;
    try{localStorage.setItem(WATCH_KEY,JSON.stringify(favorites));}
    catch{storageAvailable=false;}
  }
  function updateWatchNote(){
    if(!els.watchlistNote)return;
    const count=favorites.length;
    els.watchlistNote.textContent=count+" contratti seguiti · "+
      (storageAvailable?"Preferiti salvati solo su questo iPhone.":"Salvataggio Safari non disponibile: preferiti validi solo finché la pagina resta aperta.")+
      " Nessuna notifica o monitoraggio in background.";
  }
  function historyPanel(item){
    const details=create("details","history-details");
    details.open=expandedCodes.has(item.code);
    details.addEventListener("toggle",()=>{
      if(details.open)expandedCodes.add(item.code);
      else expandedCodes.delete(item.code);
    });
    const title=create("summary","","Storico per categorie · fino a 12 report CFTC");
    details.append(title);
    const h=core.historyFor(core.CONTRACTS.find(c=>c.code===item.code),snapshots[item.dataset]);
    if(h.status==="QUARANTINE_CONFLICT"){
      details.append(create("p","history-warning","Revisione discordante: storico sospeso. Non scegliere arbitrariamente una delle righe."));
      return details;
    }
    if(!h.rows.length){
      details.append(create("p","history-warning","Nessun report disponibile per questo contratto. Non sono stati costruiti esempi."));
      return details;
    }
    const scroll=create("div","history-scroll");
    const table=create("table","history-table"),header=create("thead",""),tr=create("tr","");
    for(const h of ["Martedì CFTC",item.labels[0]+" · netto %OI",item.labels[1]+" · netto %OI","Δ da settimana precedente"]){
      tr.append(create("th","",h));
    }
    header.append(tr);table.append(header);
    const tb=create("tbody","");
    for(const x of h.rows.slice().reverse()){
      const row=create("tr","");
      row.append(create("td","",date(x.date)));
      row.append(create("td","",fmt(x.first)));
      row.append(create("td","",fmt(x.second)));
      row.append(create("td","",x.priorWeekMissing?"Settimana non consecutiva · N/D":
        "A "+fmt(x.firstChange,"pp")+" · L "+fmt(x.secondChange,"pp")));
      tb.append(row);
    }
    table.append(tb);scroll.append(table);details.append(scroll);
    details.append(create("p","history-caption","Fonte CFTC pubblica · posizioni settimanali aggregate · nessun timestamp originario verificato. I vuoti non vengono riempiti."));
    return details;
  }

  function cohort(item,index){
    const key=index===0?"first":"second",v=item[key],delta=item.deltas?.[key]??null;
    const root=create("div","cohort");
    const top=create("div","cohort-top");
    top.append(create("span","cohort-label",item.labels[index]));
    top.append(create("strong","cohort-value "+(v>0?"pos":v<0?"neg":""),fmt(v)));
    root.append(top);
    const strip=create("div","cohort-strip");
    strip.setAttribute("aria-label",item.labels[index]+": netto "+fmt(v));
    if(Number.isFinite(v)){
      const fill=create("span","cohort-fill"+(index===1?" second":""));
      const width=Math.min(50,Math.abs(v)/2);
      fill.style.width=width+"%";
      fill.style.left=v<0?"calc(50% - "+width+"%)":"50%";
      strip.append(fill);
    }
    root.append(strip);
    const bottom=create("div","cohort-bottom");
    bottom.append(create("span","",item.deltas?"Variazione sul report precedente":"Δ settimanale: non verificabile"));
    bottom.append(create("span","cohort-change",fmt(delta,"pp")));
    root.append(bottom);
    return root;
  }
  function contractCard(item){
    const r=create("article","contract-card");
    r.dataset.grade=item.status==="CURRENT_REPORT_DATE"?"ready":
      item.status==="STALE_REPORT"?"stale":"unknown";
    const head=create("div","card-head"),title=create("div","");
    title.append(create("div","card-kicker",item.family+" · "+(item.dataset==="tff"?"TFF":"Disaggregated")));
    title.append(create("h3","",item.name));
    title.append(create("div","card-code","Contratto CFTC "+item.code));
    const grade=create("span","grade "+(item.status==="CURRENT_REPORT_DATE"?"":item.status==="STALE_REPORT"?"warn":"unknown"),sortStatus(item.status));
    const favButton=create("button","favorite-toggle",favorites.includes(item.code)?"★":"☆");
    favButton.type="button";
    favButton.setAttribute("aria-label",favorites.includes(item.code)?
      "Rimuovi "+item.name+" dai preferiti":"Segui "+item.name+" nei preferiti");
    favButton.setAttribute("aria-pressed",String(favorites.includes(item.code)));
    favButton.addEventListener("click",()=>{
      favorites=core.toggleFavorite(favorites,item.code);
      keepFavorites();draw();
    });
    head.append(title,favButton,grade);r.append(head);

    const body=create("div","cohorts");
    body.append(cohort(item,0),cohort(item,1));r.append(body);
    const foot=create("div","card-foot"),top=create("div","foot-top");
    top.append(create("span","","Riferimento: "+date(item.reportDate)+(item.ageDays!==null?" · "+item.ageDays+" giorni":"")));
    top.append(create("strong","foot-status"+(item.comparison==="DIVERGENT"?" divergent":""),comparisonLabel(item.comparison)));
    foot.append(top);
    const end=create("div","card-bottom");
    const link=create("a","","Fonte ufficiale CFTC ↗");
    link.href=item.source;link.target="_blank";link.rel="noopener noreferrer";
    end.append(link,create("small","","OI: "+(Number.isFinite(item.openInterest)?whole.format(item.openInterest):"N/D")+" · "+item.availableWeeks+" settimane in risposta"));
    foot.append(end);
    if(item.fourWeek){
      foot.append(create("div","card-code","Variazione su 4 settimane: "+item.labels[0]+" "+fmt(item.fourWeek.first,"pp")+" · "+item.labels[1]+" "+fmt(item.fourWeek.second,"pp")));
    }
    if(item.status==="UNKNOWN_WEEKLY_COMPARISON"){
      foot.append(create("div","card-code","Settimana precedente mancante o non consecutiva: nessun delta ricostruito."));
    }
    if(item.status==="QUARANTINE_CONFLICT"){
      foot.append(create("div","card-code","Righe CFTC discordanti per la stessa data: confronto sospeso."));
    }
    if(item.family==="Valute")foot.append(create("div","card-code","Future sulla valuta: non indica da solo il verso di una coppia spot USD."));
    r.append(foot);
    r.append(historyPanel(item));
    return r;
  }
  function draw(){
    const sorted=core.filterCards(cards,{family:els.family.value,
      search:els.search.value,mode:els.sort.value,
      favoritesOnly:els.favoritesOnly?.checked===true,favorites});
    els.cards.replaceChildren();
    if(!sorted.length)els.cards.append(create("div","metric","Nessun contratto corrisponde ai filtri."));
    else for(const item of sorted)els.cards.append(contractCard(item));
    byId("total-contracts").textContent=String(core.CONTRACTS.length);
    byId("available-contracts").textContent=String(cards.filter(c=>c.reportDate).length);
    byId("valid-moves").textContent=String(cards.filter(c=>c.status==="CURRENT_REPORT_DATE"&&c.deltas).length);
    byId("divergent-count").textContent=String(cards.filter(c=>c.status==="CURRENT_REPORT_DATE"&&c.comparison==="DIVERGENT").length);
    updateWatchNote();
  }
  async function fetchCftc(dataset){
    const codes=core.CONTRACTS.filter(c=>c.dataset===dataset).map(c=>c.code);
    const start=new Date(Date.now()-120*core.DAY).toISOString().slice(0,10);
    const where="report_date_as_yyyy_mm_dd >= '"+start+"T00:00:00' AND cftc_contract_market_code IN ("+
      codes.map(c=>"'"+c+"'").join(",")+")";
    const hosts=["https://publicreporting.cftc.gov","https://publicreportinghub.cftc.gov"];
    let reason="Fonte CFTC non raggiungibile";
    for(const host of hosts){
      const url=new URL("/resource/"+core.DATASETS[dataset]+".json",host);
      url.searchParams.set("$select",core.FIELDS[dataset].join(","));
      url.searchParams.set("$where",where);
      url.searchParams.set("$order","report_date_as_yyyy_mm_dd DESC");
      url.searchParams.set("$limit","1800");
      const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),16000);
      try{
        const res=await fetch(url.toString(),{mode:"cors",cache:"no-store",
          headers:{Accept:"application/json"},signal:ctrl.signal,credentials:"omit"});
        if(!res.ok)throw Error("HTTP "+res.status);
        const records=await res.json(),parsed=core.parseRows(records,dataset,Date.now());
        if(parsed.valid===0)throw Error("Nessun report compatibile");
        return parsed;
      }catch(err){
        reason=err?.name==="AbortError"?"Timeout CFTC":String(err?.message||err);
      }finally{clearTimeout(timer);}
    }
    throw Error(reason);
  }
  async function readRetail(){
    try{
      const ctrl=new AbortController(),timer=setTimeout(()=>ctrl.abort(),6500);
      let response;
      try{response=await fetch("./data/myfxbook/latest.json",{cache:"no-store",
        credentials:"omit",signal:ctrl.signal,headers:{Accept:"application/json"}});}
      finally{clearTimeout(timer);}
      if(!response.ok)throw Error("MYFXBOOK_HTTP");
      const data=await response.json();
      return core.summarizeRetail(data,Date.now());
    }catch{return [];}
  }
  function drawRetail(rows){
    els.retailList.replaceChildren();
    if(!rows.length){
      els.retailStatus.textContent="Snapshot Myfxbook non disponibile: nessun valore retail inventato.";
      return;
    }
    const recent=rows.filter(r=>r.status==="RECENT_RETAIL").length;
    els.retailStatus.textContent=recent+" / "+rows.length+
      " campioni recenti (entro 3 ore). Gli altri sono archiviati o sconosciuti; non sono segnali.";
    for(const row of rows){
      const box=create("div","retail-item");
      const link=create("a","",row.pair);link.href="./asset.html?symbol="+encodeURIComponent(row.pair)+"&v=8";
      const label=row.status==="RECENT_RETAIL"?"Recente · retail":
        row.status==="ARCHIVED_RETAIL"?"Archivio · retail":"N/D · retail";
      box.append(link);
      box.append(create("span","lot-pct",Number.isFinite(row.longLotsPct)?nf.format(row.longLotsPct)+"% long":"N/D"));
      box.append(create("small","",label));
      box.append(create("small","",row.observedAt?rome.format(new Date(row.observedAt))+" (Italia)":"Data sconosciuta"));
      box.append(create("small","",Number.isFinite(row.samplePositions)?
        whole.format(row.samplePositions)+" posizioni del campione":"Campione insufficiente"));
      els.retailList.append(box);
    }
  }
  async function reload(){
    if(busy)return;
    busy=true;els.refresh.disabled=true;els.message.dataset.status="waiting";
    els.message.textContent="Consulto la fonte CFTC: TFF e Disaggregated. I numeri restano N/D se la fonte non risponde…";
    try{
      const requests=["tff","disagg"].map(async kind=>{
        try{return {kind,data:await fetchCftc(kind)};}
        catch(e){return {kind,error:String(e?.message||e)};}
      });
      const [all,retail]=await Promise.all([Promise.all(requests),readRetail()]);
      const parsed={};
      for(const x of all){
        parsed[x.kind]=x.data||null;
        loaded[x.kind]=!!x.data;
        errors[x.kind]=x.error||"";
      }
      snapshots=parsed;
      cards=core.prepare(parsed.tff,parsed.disagg,Date.now());
      retrievedAt=Date.now();
      draw();drawRetail(retail);
      const success=Object.values(loaded).filter(Boolean).length;
      els.message.dataset.status=success===0?"error":"ready";
      els.message.textContent=success===2?
        "Entrambi i dataset CFTC caricati. Report settimanali · orario della pubblicazione originaria NON attestato. Lettura browser: "+rome.format(new Date(retrievedAt))+".":
        success===1?"CFTC parziale: "+(loaded.tff?"Disaggregated":"TFF")+" indisponibile. Dati mancanti segnalati come N/D. "+Object.values(errors).filter(Boolean).join(" · "):
        "CFTC non raggiungibile: nessuna esposizione stimata o inventata. "+Object.values(errors).filter(Boolean).join(" · ");
    }finally{busy=false;els.refresh.disabled=false;}
  }
  for(const node of [els.family,els.sort,els.search]){
    node.addEventListener(node===els.search?"input":"change",draw);
  }
  els.favoritesOnly?.addEventListener("change",draw);
  els.refresh.addEventListener("click",reload);
  draw();reload();
})();
