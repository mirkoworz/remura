/* Two retail sentiments first. Reuse existing widgets without re-fetching providers. */
(() => {
  "use strict";
  const layout=document.querySelector(".layout");
  const retail=document.getElementById("retail-module");
  const capital=document.getElementById("remura-capital");
  const price=document.getElementById("remura-price-engine");
  const insights=document.getElementById("rm-insights");
  if(!layout||!retail||!capital||!price||!insights)return;
  if(document.body.classList.contains("remura-simple"))return;
  document.body.classList.add("remura-simple");

  const cotOverview=layout.querySelector(".panel.overview:not(#retail-module):not(#remura-capital)");
  if(!cotOverview)return;
  cotOverview.id="remura-cot-summary";
  const extra=[...layout.children].filter(el=>el!==cotOverview&&el!==retail&&el!==capital&&el!==price&&el!==insights);

  const intro=document.createElement("div");
  intro.className="rm-simple-intro";
  intro.innerHTML='<span class="eyebrow">REMURA · SENTIMENT RETAIL</span>'+
    '<h2>Chi è long e chi è short?</h2>'+
    '<p>Due community differenti, lette separatamente. Verde = long, rosa = short. L’indicazione contrarian non dimostra posizioni istituzionali.</p>';
  layout.prepend(intro);
  intro.after(retail);
  retail.after(capital);
  capital.after(price);
  price.after(cotOverview);
  cotOverview.after(insights);

  const label=retail.querySelector(".rt-head .eyebrow");
  if(label)label.textContent="01 · SENTIMENT · FONTE 1 DI 2";
  const heading=retail.querySelector(".rt-head h2");
  if(heading)heading.textContent="Myfxbook · posizioni retail";
  const sub=retail.querySelector(".rt-sub");
  if(sub)sub.textContent="Percentuali basate sui lotti della community Myfxbook. Non rappresentano tutto il mercato.";
  const graphTitle=retail.querySelector("#r-chart")?.closest(".rt-section")?.querySelector("h3");
  if(graphTitle)graphTitle.textContent="Bande e storico Myfxbook";

  const readout=retail.querySelector(".rt-summary");
  const allStats=[...readout.querySelectorAll(".rt-stat")];
  const sections=[...retail.querySelectorAll(":scope > .rt-section")];
  const details=document.createElement("details");
  details.className="rm-more";
  details.innerHTML="<summary>Grafico TradingView, numero posizioni e dettagli Myfxbook</summary>";
  const additional=document.createElement("div");
  additional.className="rm-more-body";
  for(const item of allStats.slice(2))additional.append(item);
  for(const item of sections.filter(item=>!item.querySelector("#r-chart")))additional.append(item);
  details.append(additional);
  retail.append(details);

  // Keep the three price directions visible; reveal technical prose only on request.
  for(const card of price.querySelectorAll(".rp-grid .rp-box")){
    const explanation=card.querySelector("p");
    const levels=card.querySelector("small");
    if(!explanation&&!levels)continue;
    const expanded=document.createElement("details");
    expanded.className="rm-timeframe-more";
    expanded.innerHTML="<summary>Indicatori e livelli</summary>";
    if(explanation)expanded.append(explanation);
    if(levels)expanded.append(levels);
    card.append(expanded);
  }
  const technical=document.createElement("details");
  technical.className="rm-more rm-price-extra";
  technical.innerHTML="<summary>Spiegazione tecnica e importazione file</summary>";
  for(const el of [price.querySelector(".rp-upload"),price.querySelector("#rp-narrative"),
                   price.querySelector(":scope > details")]){
    if(el)technical.append(el);
  }
  price.append(technical);

  const alert=document.getElementById("alert");
  if(alert)cotOverview.append(alert);
  const cotHeader=cotOverview.querySelector("h2");
  if(cotHeader)cotHeader.textContent="COT · cosa fanno i grandi operatori";
  const advanced=document.createElement("details");
  advanced.className="rm-more rm-extra-cot";
  advanced.innerHTML="<summary>Approfondimenti COT: grafici, contratti e storico settimanale</summary>";
  const advancedBody=document.createElement("div");
  advancedBody.className="rm-advanced-body";
  for(const el of extra)advancedBody.append(el);
  advanced.append(advancedBody);
  insights.after(advanced);

  const note=insights.querySelector("#rm-interpretation");
  if(note){
    const cotDetail=document.createElement("details");
    cotDetail.className="rm-more rm-insight-more";
    cotDetail.innerHTML="<summary>Leggi spiegazioni, limiti e grafici dettagliati</summary>";
    const inner=document.createElement("div");
    inner.className="rm-more-body";
    while(note.nextSibling)inner.append(note.nextSibling);
    const openGraph=inner.querySelector(".rm-charts");
    if(openGraph)openGraph.removeAttribute("open");
    cotDetail.append(inner);
    insights.append(cotDetail);
  }

  function makeDonut(container,label){
    const wrapper=document.createElement("div");
    wrapper.className="rm-donut";
    wrapper.dataset.ready="false";
    wrapper.setAttribute("role","img");
    wrapper.setAttribute("aria-label",label+" senza dati");
    wrapper.innerHTML='<div class="rm-donut-hole"><strong>N/D</strong><small>long</small></div>';
    container.insertAdjacentElement("beforebegin",wrapper);
    return wrapper;
  }
  const retailDonut=makeDonut(retail.querySelector(".rt-summary"),"Myfxbook");
  const capitalDonut=makeDonut(capital.querySelector(".ms-readings"),"Capital.com");
  const parsePct=text=>{
    const match=String(text||"").trim().match(/^(\d+(?:[.,]\d+)?)%$/);
    const n=match?Number(match[1].replace(",",".")):NaN;
    return Number.isFinite(n)&&n>=0&&n<=100?n:null;
  };
  function paintDonut(donut,lp,sp,source){
    const l=parsePct(lp),s=parsePct(sp);
    const valid=l!==null&&s!==null&&Math.abs(l+s-100)<=1;
    donut.dataset.ready=String(valid);
    donut.style.setProperty("--rm-long",valid?l+"%":"0%");
    const center=donut.querySelector("strong");
    center.textContent=valid?lp:"N/D";
    donut.setAttribute("aria-label",valid?source+": "+lp+" long, "+sp+" short":source+": dato non disponibile");
  }
  function update(){
    paintDonut(retailDonut,document.getElementById("r-lp")?.textContent,document.getElementById("r-sp")?.textContent,"Myfxbook");
    const amounts=[...capital.querySelectorAll(".ms-reading strong")];
    paintDonut(capitalDonut,amounts[0]?.textContent,amounts[1]?.textContent,"Capital.com");
  }
  for(const name of ["remura:retail","remura:capital"]){
    window.addEventListener(name,evt=>{
      if(!evt.detail || evt.detail.symbol!==(new URLSearchParams(location.search).get("symbol")||"XAUUSD").toUpperCase())return;
      window.setTimeout(update,0);
    });
  }
  update();
})();
