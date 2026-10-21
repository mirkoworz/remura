/* Independent multi-market scanner. Uses official CFTC & private read-only sources.
   No fake prices, no trading, no automatic alerts until Web Push is implemented. */
(()=>{
 "use strict";
 const markets=window.REMURA_MARKETS,cotCore=window.REMURA_INSIGHTS_CORE;
 const priceCore=window.REMURA_PRICE_CORE,core=window.REMURA_SQUALO;
 const status=document.getElementById("sq-scan-status"),list=document.getElementById("sq-market-list");
 if(!markets||!cotCore||!priceCore||!core||!status||!list)return;
 const all=markets.symbols,FX=markets.fxCodes,OTHER=markets.other;
 const HOSTS=["https://publicreporting.cftc.gov","https://publicreportinghub.cftc.gov"];
 const nums=v=>v===null||v===undefined||v===""?NaN:Number(v);
 const NET=(row,name)=>row?.oi>0&&(row?.[name])?
   (row[name].long-row[name].short)/row.oi*100:NaN;
 let busy=false,results=[];
 const filter=document.getElementById("sq-filter");
 const money=n=>Number.isFinite(n)?new Intl.NumberFormat("it-IT",{maximumFractionDigits:1,signDisplay:"exceptZero"}).format(n):"N/D";
 function seriesFor(sym,fx,index){
   const desc=OTHER[sym];
   const convert=m=>[...m.values()].sort((a,b)=>a.date.localeCompare(b.date)).slice(-56).map(row=>({
      date:row.date,a:NET(row,"one"),b:NET(row,"two")
   }));
   if(desc)return convert(index[sym]||new Map());
   const base=sym.slice(0,3),quote=sym.slice(3),a=fx[base],b=fx[quote];
   if(base!=="USD"&&quote!=="USD"){
     if(!a||!b)return [];
     return [...a.keys()].filter(k=>b.has(k)).sort().slice(-56).map(date=>({
       date,a:NET(a.get(date),"one")-NET(b.get(date),"one"),
       b:NET(a.get(date),"two")-NET(b.get(date),"two")
     }));
   }
   const d=base==="USD"?b:a,sign=base==="USD"?-1:1;
   if(!d)return [];
   return convert(d).map(row=>({...row,a:sign*row.a,b:sign*row.b}));
 }
 async function cotDataset(kind){
   const tff=kind==="tff";
   const columns=["report_date_as_yyyy_mm_dd","cftc_contract_market_code","open_interest_all",
     ...(tff?["asset_mgr_positions_long","asset_mgr_positions_short","lev_money_positions_long","lev_money_positions_short"]:
     ["m_money_positions_long_all","m_money_positions_short_all","prod_merc_positions_long","prod_merc_positions_short"])];
   const codes=[...(tff?Object.values(FX):[]),...Object.values(OTHER).filter(x=>x.dataset===kind).map(x=>x.code)];
   const days=new Date();days.setUTCDate(days.getUTCDate()-410);
   const where="report_date_as_yyyy_mm_dd >= '"+days.toISOString().slice(0,10)+"T00:00:00' AND cftc_contract_market_code IN ("+
     codes.map(x=>"'"+x+"'").join(",")+")";
   const errors=[];
   for(const host of HOSTS){
     const url=new URL("/resource/"+(tff?"gpe5-46if":"72hh-3qpy")+".json",host);
     url.searchParams.set("$select",columns.join(","));
     url.searchParams.set("$where",where);
     url.searchParams.set("$order","report_date_as_yyyy_mm_dd DESC");
     url.searchParams.set("$limit","3000");
     const abort=new AbortController(),timer=setTimeout(()=>abort.abort(),17000);
     try{
       const response=await fetch(url.toString(),{mode:"cors",headers:{Accept:"application/json"},signal:abort.signal});
       if(!response.ok)throw Error("HTTP "+response.status);
       const data=await response.json();
       if(!Array.isArray(data)||!data.length)throw Error("Dataset CFTC vuoto");
       const out=Object.create(null);
       for(const item of data){
         const code=String(item.cftc_contract_market_code||"").toUpperCase().padStart(6,"0");
         const date=String(item.report_date_as_yyyy_mm_dd||"").slice(0,10);
         const oi=nums(item.open_interest_all);
         if(!codes.includes(code)||!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(date)||!Number.isFinite(oi)||oi<=0)continue;
         const one=tff?{long:nums(item.asset_mgr_positions_long),short:nums(item.asset_mgr_positions_short)}:
           {long:nums(item.m_money_positions_long_all),short:nums(item.m_money_positions_short_all)};
         const two=tff?{long:nums(item.lev_money_positions_long),short:nums(item.lev_money_positions_short)}:
           {long:nums(item.prod_merc_positions_long),short:nums(item.prod_merc_positions_short)};
         if(![one.long,one.short,two.long,two.short].every(Number.isFinite))continue;
         if(!out[code])out[code]=new Map();
         out[code].set(date,{date,oi,one,two});
       }
       if(!Object.keys(out).length)throw Error("Codici futures assenti");
       return out;
     }catch(e){errors.push(String(e.message||e));}
     finally{clearTimeout(timer);}
   }
   throw Error("CFTC "+kind+": "+errors.join(" / "));
 }
 async function sources(){
   const retail=await fetch("./private-api/retail/latest.json",{cache:"no-store"})
     .then(r=>r.ok?r.json():null).catch(()=>null);
   let capital=null;
   try{
     const r=await fetch("./private-api/capital/latest.json",{cache:"no-store"});
     if(r.ok)capital=await r.json();
   }catch(_){}
   if(!capital&&window.REMURA_CAPITAL_CLOUD?.enabled){
     try{
       if(await window.REMURA_CAPITAL_CLOUD.isSignedIn())capital=await window.REMURA_CAPITAL_CLOUD.latest();
     }catch(_){}
   }
   return {retail,capital};
 }
 async function prices(){
   const available=Object.create(null);
   let index=0;
   const supported=all.filter(sym=>!["NAS100","US2000","US500","DXY"].includes(sym));
   async function worker(){
     while(index<supported.length){
       const symbol=supported[index++];
       try{
         const timeout=new AbortController();
         const timer=setTimeout(()=>timeout.abort(),13000);
         let r;
         try{r=await fetch("./private-api/prices/"+encodeURIComponent(symbol),{
           cache:"no-store",signal:timeout.signal,headers:{Accept:"application/json"}
         });}
         finally{clearTimeout(timer);}
         if(!r.ok)continue;
         const obj=await r.json();
         const m=priceCore.load(obj,symbol);
         available[symbol]=priceCore.analyze(m);
       }catch(_){/* Missing price means missing check: never synthesize. */}
     }
   }
   await Promise.all(Array.from({length:4},()=>worker()));
   return available;
 }
 function refreshList(){
   const visible=results.filter(x=>filter.value==="all"||
     filter.value==="long"&&x.side===1||
     filter.value==="short"&&x.side===-1||
     filter.value==="preparazione"&&["preparazione","coerente"].includes(x.stage));
   const ranked=visible.slice().sort((a,b)=>(b.score??-1)-(a.score??-1)||b.coverage-a.coverage);
   list.replaceChildren();
   if(!ranked.length){
     const p=document.createElement("p");p.className="sq-empty";
     p.textContent="Nessuna situazione verificabile con i filtri attuali. Non viene generata una falsa occasione.";
     list.append(p);
     return;
   }
   for(const r of ranked){
     const link=document.createElement("a");
     link.className="sq-market";link.href=markets.detailUrl(r.symbol)+"#squalo-verdict";
     link.dataset.stage=r.stage;
     const head=document.createElement("div");head.className="sq-market-head";
     const name=document.createElement("strong");name.textContent=r.symbol;
     const value=document.createElement("b");value.textContent=r.score===null?"N/D":r.score+"/100";
     head.append(name,value);
     const title=document.createElement("div");title.className="sq-market-title";title.textContent=r.title;
     const desc=document.createElement("p");desc.textContent=r.summary;
     const meta=document.createElement("small");
     meta.textContent=r.coverage+"/5 verifiche disponibili · COT "+(r.updatedAt||"N/D")+
       " · punteggio descrittivo";
     link.append(head,title,desc,meta);list.append(link);
   }
 }
 async function run(){
   if(busy)return;busy=true;
   document.getElementById("sq-refresh").disabled=true;
   status.textContent="Caricamento COT ufficiale e dati delle due fonti retail...";
   try{
     const [tffResult,metalResult,feed]=await Promise.allSettled([cotDataset("tff"),cotDataset("disagg"),sources()]);
     const tff=tffResult.status==="fulfilled"?tffResult.value:{};
     const metal=metalResult.status==="fulfilled"?metalResult.value:{};
     const fx=Object.create(null),index=Object.create(null);
     for(const [currency,code] of Object.entries(FX))fx[currency]=tff[code]||new Map();
     for(const [symbol,desc] of Object.entries(OTHER))index[symbol]=(desc.dataset==="tff"?tff:metal)[desc.code]||new Map();
     const docs=feed.status==="fulfilled"?feed.value:{};
     results=all.map(symbol=>{
       const desc=OTHER[symbol];
       const series=seriesFor(symbol,fx,index).filter(p=>Number.isFinite(p.a)&&Number.isFinite(p.b));
       const cot=cotCore.analyze(series,{
         symbol,isFX:!desc,isMetal:desc?.group==="metals",
         labels:desc?.group==="metals"?["Managed Money","Producer / Merchant"]:["Asset Manager","Leveraged Funds"]
       });
       const r=docs.retail?.symbols?.[symbol],c=docs.capital?.symbols?.[symbol];
       const now=Date.now();
       const recent=x=>x&&Number.isFinite(Date.parse(x.t))&&now-Date.parse(x.t)>=0&&now-Date.parse(x.t)<3*3600000;
       return {symbol,cot,retail:r?{row:r,fresh:recent(r)}:null,
         capital:c?{row:c,fresh:recent(c)}:null};
     });
     status.textContent="COT elaborato. Verifico le candele cTrader dei mercati supportati...";
     const priceData=await prices();
     results=results.map(row=>core.evaluate({...row,price:priceData[row.symbol]||null}));
     refreshList();
     const complete=results.filter(r=>r.coverage===5).length;
     const good=results.filter(r=>["preparazione","coerente"].includes(r.stage)).length;
     status.textContent=results.length+" strumenti controllati · "+complete+
       " con 5 verifiche disponibili · "+good+" contesti da approfondire. "+
       ((tffResult.status!=="fulfilled"||metalResult.status!=="fulfilled")?
       "Una fonte CFTC non ha risposto: i mercati coinvolti rimangono N/D.":"");
   }catch(e){
     status.textContent="Scanner non disponibile: "+String(e.message||e)+". Nessun punteggio simulato.";
   }finally{busy=false;document.getElementById("sq-refresh").disabled=false;}
 }
 filter.addEventListener("change",refreshList);
 document.getElementById("sq-refresh").addEventListener("click",run);
 run();
})();
