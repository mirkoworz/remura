/* REMURA v1.29: menu responsive ad albero + configurazione condivisa dei mercati. */
(() => {
  "use strict";
  const FX_CODES={EUR:"099741",GBP:"096742",JPY:"097741",AUD:"232741",CAD:"090741",CHF:"092741",NZD:"112741"};
  const FX_PAIRS=["EURUSD","GBPUSD","AUDUSD","NZDUSD","USDJPY","USDCAD","USDCHF","EURGBP","EURJPY","EURCHF","EURCAD","EURAUD","EURNZD","GBPJPY","GBPCHF","GBPCAD","GBPAUD","GBPNZD","AUDJPY","AUDCAD","AUDCHF","AUDNZD","NZDJPY","NZDCAD","NZDCHF","CADJPY","CADCHF","CHFJPY"];
  const OTHER={
    XAUUSD:{group:"metals",name:"Gold · Oro COMEX",code:"088691",dataset:"disagg"},
    XAGUSD:{group:"metals",name:"Silver · Argento COMEX",code:"084691",dataset:"disagg"},
    US500:{group:"indices",name:"S&P 500 · E-mini",code:"13874A",dataset:"tff"},
    NAS100:{group:"indices",name:"Nasdaq 100 · E-mini",code:"209742",dataset:"tff"},
    US30:{group:"indices",name:"Dow Jones · E-mini",code:"124603",dataset:"tff"},
    VIX:{group:"macro",name:"VIX · volatilità USA (contratto broker)",code:null,dataset:null},
    DXY:{group:"macro",name:"DXY · USDX (contratto broker)",code:"098662",dataset:"tff"},
    GER30:{group:"indices",name:"DAX 40 · GER30 (broker)",code:null,dataset:null},
    USOIL:{group:"energy",name:"WTI · petrolio USOil",code:"067651",dataset:"disagg"},
    UKOIL:{group:"energy",name:"Brent · petrolio UKOil",code:null,dataset:null}
  };
  const groups=[
    {id:"forex",label:"Forex",icon:"↔",name:"28 coppie principali",items:FX_PAIRS.map(s=>({s,n:s}))},
    {id:"metals",label:"Metalli",icon:"◇",name:"Oro e argento",items:[{s:"XAUUSD",n:"Gold · Oro"},{s:"XAGUSD",n:"Silver · Argento"}]},
    {id:"indices",label:"Indici azionari",icon:"▥",name:"DAX 40, S&P 500, Nasdaq e Dow",items:[
      {s:"GER30",n:"DAX 40 · indice tedesco"},{s:"US500",n:"S&P 500"},{s:"NAS100",n:"Nasdaq 100"},
      {s:"US30",n:"Dow Jones"}]},
    {id:"macro",label:"Indicatori macro",icon:"◈",name:"DXY e VIX · Contesto globale",items:[
      {s:"DXY",n:"DXY · forza del dollaro (USDX)"},{s:"VIX",n:"VIX · volatilità attesa USA"}]},
    {id:"energy",label:"Energia",icon:"◉",name:"Petrolio WTI e Brent",items:[
      {s:"USOIL",n:"WTI · USOil (COT + prezzi)"},{s:"UKOIL",n:"Brent · UKOil (prezzi)"}]}
  ];
  const detailUrl=s=>"./asset.html?symbol="+encodeURIComponent(s)+"&v=8";
  const categoryUrl=id=>"./catalogo.html?categoria="+encodeURIComponent(id)+"&v=8";
  window.REMURA_MARKETS={fxCodes:FX_CODES,fxPairs:FX_PAIRS,other:OTHER,groups,symbols:[...FX_PAIRS,...Object.keys(OTHER)],detailUrl,categoryUrl};
  function init(){
    if(document.getElementById("rm-menu-trigger"))return;
    // Visible on every REMURA page, including the installed iPhone web app.
    const release=document.createElement("div");
    release.id="rm-release";
    release.textContent="REMURA · Aggiornamento v1.29 · 24/10/2026 17:55 (Italia)";
    document.body.prepend(release);

    const page=location.pathname.split("/").pop()||"index.html";
    const q=new URLSearchParams(location.search);
    const activeSymbol=(q.get("symbol")||"").toUpperCase();
    let activeGroup=q.get("categoria")||"";
    if(page==="asset.html"&&activeSymbol){
      activeGroup=OTHER[activeSymbol]?.group||"forex";
    }else if(page==="forex.html")activeGroup="forex";
    const trigger=document.createElement("button");
    trigger.id="rm-menu-trigger";trigger.type="button";trigger.setAttribute("aria-label","Apri menu Remura");
    trigger.setAttribute("aria-controls","rm-menu");trigger.setAttribute("aria-expanded","false");
    trigger.innerHTML='<svg viewBox="0 0 24 24" width="23" height="23" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor" stroke-linecap="round" stroke-width="2" fill="none"/></svg>';
    const shade=document.createElement("div");shade.id="rm-menu-shade";shade.hidden=true;
    const drawer=document.createElement("aside");drawer.id="rm-menu";
    drawer.setAttribute("aria-label","Navigazione principale Remura");drawer.setAttribute("aria-hidden","true");drawer.inert=true;
    drawer.innerHTML='<div class="rm-header"><a href="./index.html" class="rm-brand">REMURA<span>Segui le tracce istituzionali</span></a><button id="rm-close" type="button" aria-label="Chiudi menu">×</button></div><nav aria-label="Menu Remura" class="rm-nav"><div class="rm-shortcuts"><a href="./index.html" data-main="home">⌂ <span>Home</span></a><a href="./mercati.html#institutional-scanner" data-main="scanner">🦈 <span>Radar Squali · Squalincome</span></a><a href="./fonti.html?v=8" data-main="fonti">◈ <span>Fonti sentiment</span></a><a href="./stato-prezzi.html" data-main="prices">▤ <span>Stato prezzi · 38 mercati</span></a><a href="./stato-prezzi.html#macro" data-main="macro">◈ <span>Radar Macro · DXY + VIX</span></a><a href="./impostazioni.html" data-main="settings">⚙ <span>Impostazioni · Capital Google</span></a></div><label class="rm-search-label" for="rm-search">Cerca tra 38 strumenti</label><input id="rm-search" type="search" autocomplete="off" placeholder="Gold, CADJPY, Nasdaq..." aria-label="Filtra strumenti e sottomenu"><div id="rm-menu-tree" class="rm-menu-tree"></div><div class="rm-menu-bottom"><a href="./forex.html?v=8">⌁ Radar Forex classico →</a></div></nav><div class="rm-footer">COT: posizioni istituzionali settimanali. Myfxbook e Capital.com: sentiment retail separato.</div>';
    document.body.append(shade,drawer,trigger);
    document.body.classList.add("rm-has-nav");
    const tree=drawer.querySelector("#rm-menu-tree");
    const search=drawer.querySelector("#rm-search");
    const isHome=page==="index.html",isScanner=page==="mercati.html",isSources=page==="fonti.html",isSettings=page==="impostazioni.html",isPrices=page==="stato-prezzi.html";
    const highlight=drawer.querySelector(isHome?'[data-main="home"]':isScanner?'[data-main="scanner"]':isSources?'[data-main="fonti"]':isSettings?'[data-main="settings"]':isPrices?'[data-main="prices"]':'[data-main="home"]');
    if(highlight&&(isHome||isScanner||isSources||isSettings||isPrices))highlight.classList.add("rm-active");
    function render(){
      const v=search.value.trim().toUpperCase();
      tree.replaceChildren();
      let count=0;
      for(const group of groups){
        const matches=group.items.filter(it=>it.s.includes(v)||it.n.toUpperCase().includes(v));
        if(v&&!matches.length&&!group.label.toUpperCase().includes(v))continue;
        count+=matches.length;
        const section=document.createElement("details");section.className="rm-submenu";
        section.open=v.length>0||group.id===activeGroup;
        const summary=document.createElement("summary");summary.className="rm-parent";
        const icon=document.createElement("span");icon.className="rm-category-icon";icon.textContent=group.icon;
        const label=document.createElement("span");label.className="rm-parent-name";
        const name=document.createElement("strong");name.textContent=group.label;
        const subtitle=document.createElement("small");subtitle.textContent=group.name;label.append(name,subtitle);
        const caret=document.createElement("span");caret.className="rm-caret";caret.textContent="⌄";
        summary.append(icon,label,caret);section.append(summary);
        const inner=document.createElement("div");inner.className="rm-children";
        const overview=document.createElement("a");overview.href=categoryUrl(group.id);
        overview.textContent="Panoramica "+group.label+" →";overview.className="rm-overview";
        if(page==="catalogo.html"&&activeGroup===group.id){overview.classList.add("rm-active");overview.setAttribute("aria-current","page");}
        inner.append(overview);
        for(const item of matches){
          const anchor=document.createElement("a");anchor.href=detailUrl(item.s);anchor.className="rm-leaf";
          if(page==="asset.html"&&activeSymbol===item.s){anchor.classList.add("rm-active");anchor.setAttribute("aria-current","page");}
          const code=document.createElement("b");code.textContent=item.s;
          const title=document.createElement("small");title.textContent=item.n===item.s?"Scheda COT":item.n;
          anchor.append(code,title);inner.append(anchor);
        }
        section.append(inner);tree.append(section);
      }
      if(!tree.children.length){
        const empty=document.createElement("p");empty.className="rm-no-match";empty.textContent="Nessuno strumento trovato.";tree.append(empty);
      }
    }
    let priorFocus=null;
    function toggle(on){
      if(on)priorFocus=document.activeElement;
      drawer.classList.toggle("visible",on);
      shade.hidden=!on;drawer.inert=!on;
      drawer.setAttribute("aria-hidden",on?"false":"true");
      trigger.setAttribute("aria-expanded",on?"true":"false");
      document.body.classList.toggle("rm-menu-open",on);
      if(on){render();drawer.querySelector("#rm-close").focus();}
      else if(priorFocus?.isConnected)priorFocus.focus();
    }
    // iPhone: keep the hamburger off market cards while scrolling down,
    // and bring it back when scrolling up. Preserve keyboard access.
    if(["stato-prezzi.html","mercati.html","asset.html"].includes(page)){
      let lastY=window.scrollY;
      const setTriggerVisible=on=>{
        trigger.classList.toggle("rm-scrolled-away",!on);
        trigger.tabIndex=on?0:-1;
      };
      window.addEventListener("scroll",()=>{
        const nextY=window.scrollY;
        const diff=nextY-lastY;
        lastY=nextY;
        if(nextY<90||drawer.classList.contains("visible")){
          setTriggerVisible(true);
        }else if(diff>5&&document.activeElement!==trigger){
          setTriggerVisible(false);
        }else if(diff< -5){
          setTriggerVisible(true);
        }
      },{passive:true});
      trigger.addEventListener("focus",()=>setTriggerVisible(true));
    }
    trigger.addEventListener("click",()=>toggle(true));
    shade.addEventListener("click",()=>toggle(false));
    drawer.querySelector("#rm-close").addEventListener("click",()=>toggle(false));
    search.addEventListener("input",render);
    document.addEventListener("keydown",e=>{
      if(!drawer.classList.contains("visible"))return;
      if(e.key==="Escape"){e.preventDefault();toggle(false);return;}
      if(e.key==="Tab"){
        const all=[...drawer.querySelectorAll('button:not([disabled]),input:not([disabled]),a[href],summary')].filter(x=>x.getClientRects().length);
        const first=all[0],last=all[all.length-1];
        if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
        else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
      }
    });
    render();
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init,{once:true});else init();
})();