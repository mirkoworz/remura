/* REMURA Shark Evidence v1.69 LAB — 23/11/2026 13:30 CET (Europe/Rome).
 * Pure presentation metadata from already loaded CFTC cards and public Myfxbook snapshot.
 * NO network, trading, price validation, lookahead claims or CVD calculation.
 */
(function(root,factory){
  const api=factory();
  if(typeof module==="object"&&module.exports)module.exports=api;
  if(root)root.REMURA_SHARK_EVIDENCE=api;
})(typeof window!=="undefined"?window:null,function(){
  "use strict";
  const DEFINITIONS={
    tff:{title:"CFTC · TFF",description:"Asset Manager e Leveraged Funds · futures finanziari"},
    disagg:{title:"CFTC · Disaggregated",description:"Managed Money e Producer/Merchant · metalli ed energia"}
  };
  function latestDate(items){
    const dates=items.map(x=>x.reportDate).filter(x=>typeof x==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(x));
    return dates.length?dates.sort().at(-1):null;
  }
  function cftc(kind,cards,loaded){
    const list=cards.filter(x=>x.dataset===kind);
    const total=list.length,dated=list.filter(x=>!!x.reportDate).length;
    const recent=list.filter(x=>x.status==="CURRENT_REPORT_DATE"||x.status==="UNKNOWN_WEEKLY_COMPARISON").length;
    const comparable=list.filter(x=>x.status==="CURRENT_REPORT_DATE"&&x.deltas!==null).length;
    const conflicts=list.filter(x=>x.status==="QUARANTINE_CONFLICT").length;
    const stale=list.filter(x=>x.status==="STALE_REPORT").length;
    let state="NON_DISPONIBILE",headline="Fonte non caricata";
    if(loaded){
      if(conflicts){state="DA_VERIFICARE";headline=conflicts+" contratti con righe discordanti";}
      else if(recent===total&&total){state="RECENTE";headline=recent+" / "+total+" report recenti";}
      else if(recent){state="PARZIALE";headline=recent+" / "+total+" report recenti";}
      else if(stale){state="OBSOLETO";headline=stale+" / "+total+" report datati";}
      else{state="NON_CONFRONTABILE";headline="Nessun report recente utilizzabile";}
    }
    return {id:kind,title:DEFINITIONS[kind].title,state,headline,
      detail:loaded?(dated+" / "+total+" contratti con data · "+comparable+" variazioni WoW confrontabili"):
        "Nessuna posizione mostrata senza risposta CFTC.",
      reference:latestDate(list),
      note:DEFINITIONS[kind].description+". Data martedì CFTC, non ora di pubblicazione o trade."};
  }
  function retail(rows){
    const recent=rows.filter(x=>x.status==="RECENT_RETAIL").length;
    const archived=rows.filter(x=>x.status==="ARCHIVED_RETAIL").length;
    const total=rows.length;
    const latest=rows.map(x=>x.observedAt).filter(x=>typeof x==="string").sort().at(-1)||null;
    const state=!total?"NON_DISPONIBILE":recent===total?"RECENTE":recent?"PARZIALE":archived?"ARCHIVIO":"NON_CONFRONTABILE";
    return {id:"retail",title:"Retail · Myfxbook",state,
      headline:!total?"Snapshot pubblico non disponibile":recent+" / "+total+" campioni recenti",
      detail:total?archived+" archiviati · recente solo entro 3 ore":"Nessun dato retail ricostruito.",
      reference:latest,note:"Snapshot di lotti retail; non rappresenta posizioni istituzionali CFTC."};
  }
  function summarize({cards=[],loaded={},retail:rows=[],readAt=null}={}){
    const safeCards=Array.isArray(cards)?cards:[];
    const safeRetail=Array.isArray(rows)?rows:[];
    const time=Number.isFinite(readAt)&&readAt>0?new Date(readAt).toISOString():null;
    return {readAt:time,publicationTimeVerified:false,independentFirstSeen:false,
      sources:[cftc("tff",safeCards,loaded.tff===true),
        cftc("disagg",safeCards,loaded.disagg===true),
        retail(safeRetail),
        {id:"cvd",title:"CVD · Delta stimato",state:"NON_COLLEGATO",
         headline:"N/D · non disponibile nel Cockpit",
         detail:"Nessun dato CVD o flusso ordini collegato a questa vista.",
         reference:null,
         note:"Il CVD proxy cTrader è CLV × tick-volume M15, non aggressioni di ordini istituzionali. Ricerca Filone A separata."}]};
  }
  return Object.freeze({summarize});
});