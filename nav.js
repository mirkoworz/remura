/* REMURA navigation, shared across radar and single-market pages. No external dependencies. */
(() => {
  "use strict";
  const FX_CODES = {EUR:"099741",GBP:"096742",JPY:"097741",AUD:"232741",CAD:"090741",CHF:"092741",NZD:"112741"};
  const FX_PAIRS = ["EURUSD","GBPUSD","AUDUSD","NZDUSD","USDJPY","USDCAD","USDCHF","EURGBP","EURJPY","EURCHF","EURCAD","EURAUD","EURNZD","GBPJPY","GBPCHF","GBPCAD","GBPAUD","GBPNZD","AUDJPY","AUDCAD","AUDCHF","AUDNZD","NZDJPY","NZDCAD","NZDCHF","CADJPY","CADCHF","CHFJPY"];
  const OTHER = {
    XAUUSD:{group:"metals",name:"Gold · Oro COMEX",code:"088691",dataset:"disagg"},
    XAGUSD:{group:"metals",name:"Silver · Argento COMEX",code:"084691",dataset:"disagg"},
    US500:{group:"indices",name:"S&P 500 · E-mini",code:"13874A",dataset:"tff"},
    NAS100:{group:"indices",name:"Nasdaq 100 · E-mini",code:"209742",dataset:"tff"},
    US30:{group:"indices",name:"Dow Jones · E-mini",code:"124603",dataset:"tff"},
    US2000:{group:"indices",name:"Russell 2000 · E-mini",code:"239742",dataset:"tff"},
    DXY:{group:"indices",name:"Dollar Index · ICE",code:"098662",dataset:"tff"}
  };
  const config={fxCodes:FX_CODES,fxPairs:FX_PAIRS,other:OTHER,
    symbols:[...FX_PAIRS,...Object.keys(OTHER)],
    detailUrl:sym=>"./asset.html?symbol="+encodeURIComponent(sym)+"&v=4"};
  window.REMURA_MARKETS=config;
  function start(){
    if(document.getElementById("rm-menu-trigger"))return;
    const active=new URLSearchParams(location.search).get("symbol")||"";
    const open=document.createElement("button");open.type="button";open.id="rm-menu-trigger";
    open.setAttribute("aria-label","Apri menu dei mercati");open.setAttribute("aria-expanded","false");open.setAttribute("aria-controls","rm-menu");
    open.innerHTML='<svg viewBox="0 0 24 24" width="23" height="23" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" stroke-linecap="round" stroke-width="2" fill="none"/></svg>';
    const shade=document.createElement("div");shade.id="rm-menu-shade";shade.hidden=true;
    const drawer=document.createElement("aside");drawer.id="rm-menu";drawer.setAttribute("aria-label","Menu laterale REMURA");drawer.setAttribute("aria-hidden","true");drawer.inert=true;
    drawer.innerHTML='<div class="rm-header"><div class="rm-wordmark">REMURA<span>Esplora i mercati</span></div><button id="rm-close" type="button" aria-label="Chiudi menu">×</button></div><div class="rm-links"><a href="./index.html">⌂ Dashboard Forex</a><a href="./mercati.html?v=4">◎ Scanner tutti i mercati</a><a href="./asset.html?symbol=XAUUSD&v=4">◇ GOLD · XAUUSD</a></div><label for="rm-search" class="rm-search-label">CERCA UNO STRUMENTO</label><input id="rm-search" type="search" autocomplete="off" placeholder="Gold, EURUSD, Nasdaq…" aria-label="Cerca mercato nel menu"><div class="rm-menu-list" id="rm-menu-list"></div><div class="rm-footer">I dati COT sono settimanali. Sentiment retail ancora da collegare.</div>';
    document.body.append(shade,drawer,open);document.body.classList.add("rm-has-nav");
    const list=drawer.querySelector("#rm-menu-list"),search=drawer.querySelector("#rm-search");
    function build(){
      const val=search.value.toUpperCase().trim();list.replaceChildren();
      const groups=[["Forex",FX_PAIRS.map(s=>({s,n:s}))],["Metalli",[["XAUUSD","Oro · Gold"],["XAGUSD","Argento · Silver"]].map(([s,n])=>({s,n}))],["Indici USA",[["US500","S&P 500"],["NAS100","Nasdaq 100"],["US30","Dow Jones"],["US2000","Russell 2000"],["DXY","Dollar Index"]].map(([s,n])=>({s,n}))]];
      for(const [title,items] of groups){
        const match=items.filter(it=>it.s.includes(val)||it.n.toUpperCase().includes(val));if(!match.length)continue;
        const group=document.createElement("section");group.className="rm-group";
        const heading=document.createElement("h3");heading.textContent=title;group.append(heading);
        for(const it of match){
          const link=document.createElement("a");link.href=config.detailUrl(it.s);
          if(it.s===active){link.className="selected";link.setAttribute("aria-current","page");}
          const label=document.createElement("span");label.textContent=it.s;
          const name=document.createElement("small");name.textContent=it.n===it.s?"Apri scheda":it.n;
          link.append(label,name);group.append(link);
        }list.append(group);
      }
      if(!list.childElementCount){const p=document.createElement("p");p.className="rm-no-match";p.textContent="Nessun mercato trovato.";list.append(p);}
    }
    let savedFocus=null;
    function toggle(state){
      const showing=!!state;
      if(showing)savedFocus=document.activeElement;
      drawer.classList.toggle("visible",showing);shade.hidden=!showing;
      drawer.setAttribute("aria-hidden",showing?"false":"true");drawer.inert=!showing;open.setAttribute("aria-expanded",showing?"true":"false");
      document.body.classList.toggle("rm-menu-open",showing);
      if(showing){build();drawer.querySelector("#rm-close").focus();}
      else if(savedFocus&&savedFocus.isConnected){savedFocus.focus();}
    }
    open.addEventListener("click",()=>toggle(true));shade.addEventListener("click",()=>toggle(false));
    drawer.querySelector("#rm-close").addEventListener("click",()=>toggle(false));search.addEventListener("input",build);
    document.addEventListener("keydown",e=>{
      if(!drawer.classList.contains("visible"))return;
      if(e.key==="Escape"){e.preventDefault();toggle(false);}
      if(e.key==="Tab"){
        const focusable=[...drawer.querySelectorAll('button:not([disabled]),a[href],input:not([disabled])')].filter(el=>el.getClientRects().length);
        if(!focusable.length)return;
        const first=focusable[0],last=focusable[focusable.length-1];
        if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
        else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
      }
    });
    build();
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",start,{once:true});else start();
})();