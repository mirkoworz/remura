/* REMURA Shark Movers display v1.67 LAB — 22/11/2026 21:41 CET.
 * Pure DOM presentation of current per-contract CFTC weekly changes.
 * This file performs no API calls and creates no trading signals.
 */
(function(){
  "use strict";
  const core=window.REMURA_SHARK_MOVERS;
  const el=(tag,cls,value)=>{
    const node=document.createElement(tag);
    if(cls)node.className=cls;
    if(value!==undefined)node.textContent=value;
    return node;
  };
  const pp=new Intl.NumberFormat("it-IT",{maximumFractionDigits:2,minimumFractionDigits:1});
  const dateFmt=new Intl.DateTimeFormat("it-IT",{day:"2-digit",month:"short",year:"numeric",timeZone:"UTC"});
  function render(cards,{favorites=[],favoritesOnly=false}={}){
    const list=document.getElementById("movers-list");
    const status=document.getElementById("movers-status");
    if(!list||!status||!core)return;
    const result=core.scan(cards,{favorites,favoritesOnly,limit:6});
    list.replaceChildren();
    if(!result.items.length){
      const text=result.status==="WATCHLIST_EMPTY"?
        "Nessun preferito: tocca ☆ su una scheda per iniziare.":
        "Nessuna variazione COT confrontabile. Report mancanti, datati o discordanti restano N/D.";
      list.append(el("p","movers-placeholder",text));
      status.textContent="Movimenti non valutabili con i filtri attuali. Nessun dato ricostruito da prezzi o retail.";
      return;
    }
    const t=new Date(result.reportDate+"T12:00:00Z");
    status.textContent="Report CFTC del "+dateFmt.format(t)+" · "+result.alignedContracts+
      " contratti confrontabili nello stesso martedì"+
      (result.excludedOtherWeeks?" · "+result.excludedOtherWeeks+" esclusi (report di altri martedì)":"")+
      ". Non è flusso ordini live; primo istante di pubblicazione non attestato.";
    for(const item of result.items){
      const button=el("button","mover-card");
      button.type="button";
      const display=(item.netChangePp>0?"+":"")+pp.format(item.netChangePp)+" pp";
      button.setAttribute("aria-label","Apri "+item.name+": variazione "+display);
      button.append(el("span","mover-heading",item.name),
                    el("strong","mover-value "+(item.netChangePp>0?"mover-up":"mover-down"),display),
                    el("span","mover-category",item.category),
                    el("span","mover-sub",item.netChangePp>0?
                      "Netto aumentato · non necessariamente nuovi acquisti":
                      "Netto diminuito · non necessariamente nuove vendite"),
                    el("span","mover-open","Apri il future ↘"));
      button.addEventListener("click",()=>{
        const target=document.getElementById("shark-contract-"+item.code);
        if(!target)return;
        target.scrollIntoView({behavior:"smooth",block:"center"});
        target.focus({preventScroll:true});
      });
      list.append(button);
    }
  }
  window.REMURA_SHARK_MOVERS_UI=Object.freeze({render});
})();
