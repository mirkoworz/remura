/* REMURA Shark Evidence UI v1.69 LAB — 23/11/2026 13:30 CET.
 * DOM-only view. No fetch, storage, credentials or new service.
 */
(function(){
  "use strict";
  const core=window.REMURA_SHARK_EVIDENCE;
  const list=document.getElementById("evidence-list");
  const note=document.getElementById("evidence-read-at");
  if(!core||!list)return;
  const dt=new Intl.DateTimeFormat("it-IT",{
    day:"2-digit",month:"2-digit",year:"numeric",hour:"2-digit",minute:"2-digit",
    timeZone:"Europe/Rome",timeZoneName:"short"
  });
  const day=new Intl.DateTimeFormat("it-IT",{
    day:"2-digit",month:"2-digit",year:"numeric",timeZone:"UTC"
  });
  function element(tag,cls,value){
    const node=document.createElement(tag);
    if(cls)node.className=cls;
    if(value!==undefined)node.textContent=value;
    return node;
  }
  function prettyDate(value,id){
    if(!value)return "Data fonte: N/D";
    const date=new Date(id==="retail"?value:value+"T12:00:00Z");
    if(!Number.isFinite(date.getTime()))return "Data fonte: N/D";
    return id==="retail"?"Ultimo snapshot: "+dt.format(date):
      "Ultimo martedì disponibile: "+day.format(date);
  }
  function render(input){
    const evidence=core.summarize(input);
    const fragment=document.createDocumentFragment();
    for(const source of evidence.sources){
      const card=element("article","evidence-card");
      card.dataset.state=source.state;
      card.setAttribute("aria-label",source.title+" · "+source.state.replaceAll("_"," "));
      const head=element("div","evidence-head");
      head.append(element("span","evidence-name",source.title),
        element("span","evidence-grade",source.state.replaceAll("_"," ")));
      card.append(head,element("strong","evidence-main",source.headline),
        element("p","evidence-detail",source.detail),
        element("p","evidence-date",prettyDate(source.reference,source.id)),
        element("p","evidence-small",source.note));
      fragment.append(card);
    }
    list.replaceChildren(fragment);
    if(note){
      note.textContent=evidence.readAt?
        "Lettura del browser: "+dt.format(new Date(evidence.readAt))+
        " · NON è l'ora di pubblicazione CFTC. Nessun primo avvistamento indipendente attestato.":
        "Nessuna lettura ancora completata. I dati e i timestamp restano N/D.";
    }
  }
  window.REMURA_SHARK_EVIDENCE_UI=Object.freeze({render});
})();