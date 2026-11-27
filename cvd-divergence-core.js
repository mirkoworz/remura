/* REMURA v1.60 CANDIDATO — divergenze prezzo / CVD proxy, SOLO OFFLINE.
 * Nessuna API, ordine, notifica, archivio o modifica alla VPS.
 * Usa ESATTAMENTE price-core.flow() (CLV × tick volume cTrader M15).
 * I pivot sono riconosciuti solo dopo la chiusura delle barre a destra.
 */
(function(root,factory){
  "use strict";
  const price=(typeof module==="object"&&module.exports)
    ?require("./price-core.js"):root&&root.REMURA_PRICE_CORE;
  const detector=factory(price);
  if(typeof module==="object"&&module.exports)module.exports=detector;
  if(root)root.REMURA_CVD_DIVERGENCES=detector;
})(typeof window!=="undefined"?window:null,function(priceCore){
  "use strict";
  const STEP=15*60*1000,VERSION="cvd-divergence-proxy-m15-v1";
  const PILOT=new Set(["EURUSD","XAUUSD"]);
  const DEFAULTS=Object.freeze({
    left:2,right:2,minSeparation:3,maxSeparation:36,
    atrPeriod:14,minPriceAtr:0.1,minCvdFraction:0.04
  });
  const finite=n=>typeof n==="number"&&Number.isFinite(n);
  const iso=t=>new Date(t).toISOString();
  function unavailable(status,reason,now,extra={}){
    return {status,reason,asOf:finite(now)?iso(now):null,
      method:"CLV × tick volume cTrader (proxy, non volume eseguito)",
      algorithm:VERSION,events:[],...extra};
  }
  function parameters(input){
    const p={...DEFAULTS,...(input||{})};
    for(const k of ["left","right","minSeparation","maxSeparation","atrPeriod"])
      if(!Number.isSafeInteger(p[k])||p[k]<1||p[k]>100)
        throw Error("Parametro non valido: "+k);
    if(p.minSeparation>p.maxSeparation||p.left>12||p.right>12)
      throw Error("Finestre pivot non valide.");
    for(const k of ["minPriceAtr","minCvdFraction"])
      if(!finite(p[k])||p[k]<0||p[k]>=1)
        throw Error("Tolleranza non valida: "+k);
    return p;
  }
  function atrAt(rows,knownIndex,period){
    if(knownIndex<period)return null;
    let total=0;
    for(let j=knownIndex-period+1;j<=knownIndex;j++){
      const bar=rows[j],previous=rows[j-1];
      total+=Math.max(bar.h-bar.l,Math.abs(bar.h-previous.c),Math.abs(bar.l-previous.c));
    }
    return total/period;
  }
  function isPivot(rows,index,side,left,right){
    const value=rows[index][side==="high"?"h":"l"];
    // Equality is *not* a confirmed pivot: prevent plateau/double counting.
    for(let i=index-left;i<=index+right;i++){
      if(i===index)continue;
      const neighbor=rows[i][side==="high"?"h":"l"];
      if(side==="high" ? value<=neighbor : value>=neighbor)return false;
    }
    return true;
  }
  function analyze(market,{now=Date.now(),settings={}}={}){
    const p=parameters(settings);
    if(!finite(now)||now<0)return unavailable("invalid","Ora di scansione non valida.",now);
    if(!market||!PILOT.has(market.symbol))
      return unavailable("unsupported","Pilota limitato a EURUSD e XAUUSD.",now);
    if(market.provider!=="ctrader"||typeof market.providerSymbol!=="string"||
       !market.providerSymbol.trim())
      return unavailable("missing","Fonte/broker cTrader non verificato.",now);

    const all=market.frames?.M15;
    if(!Array.isArray(all)||!all.length)
      return unavailable("missing","Non esistono M15 chiuse.",now);
    let prev=-Infinity;
    for(const r of all){
      if(!r||!finite(r.t)||r.t%STEP!==0||r.t<=prev||r.t+STEP>now||
         ![r.o,r.h,r.l,r.c].every(v=>finite(v)&&v>0)||
         r.h<Math.max(r.o,r.c)||r.l>Math.min(r.o,r.c)||r.h<r.l)
        return unavailable("invalid","Orari o OHLC non confermati.",now);
      if(!Number.isSafeInteger(r.v)||r.v<0)
        return unavailable("missing","Tick volume non disponibile o invalido.",now);
      prev=r.t;
    }
    // This is the sole source of proxy values. No second formula or fake CVD.
    const flow=priceCore&&priceCore.flow?priceCore.flow(market,{now}):null;
    if(!flow||flow.status!=="ok")
      return unavailable(flow?.status||"missing",
        flow?.reason||"Motore CVD proxy non disponibile.",now);

    const rows=all.filter(r=>iso(r.t).slice(0,10)===flow.day);
    const pts=flow.points;
    if(!pts||rows.length!==pts.length||rows.some((r,i)=>r.t!==pts[i].t))
      return unavailable("invalid","Allineamento candele/CVD incoerente.",now);
    if(rows.length<Math.max(p.atrPeriod+1,p.left+p.right+2,8))
      return unavailable("insufficient","Sessione troppo breve per pivot e ATR.",now);
    const highs=[],lows=[],events=[];
    for(let i=p.left;i+ p.right<rows.length;i++){
      if(isPivot(rows,i,"high",p.left,p.right))highs.push(i);
      if(isPivot(rows,i,"low",p.left,p.right))lows.push(i);
    }
    for(const [kind,pivots] of [["bearish_regular",highs],["bullish_regular",lows]]){
      for(let k=1;k<pivots.length;k++){
        const a=pivots[k-1],b=pivots[k],knownAt=b+p.right;
        if(b-a<p.minSeparation||b-a>p.maxSeparation)continue;
        const currentAtr=atrAt(rows,knownAt,p.atrPeriod);
        if(!finite(currentAtr)||currentAtr<=0)continue;
        // CVD tolerance based only on candles up to confirmation.
        let ticks=0;
        for(let j=a+1;j<=knownAt;j++)ticks+=rows[j].v;
        if(ticks<=0)continue;
        const priceA=kind==="bearish_regular"?rows[a].h:rows[a].l;
        const priceB=kind==="bearish_regular"?rows[b].h:rows[b].l;
        const cvdA=pts[a].cvd,cvdB=pts[b].cvd;
        const minPriceMove=currentAtr*p.minPriceAtr;
        const minCvdMove=ticks*p.minCvdFraction;
        const agrees=kind==="bearish_regular"
          ?priceB>priceA+minPriceMove && cvdB<cvdA-minCvdMove
          :priceB<priceA-minPriceMove && cvdB>cvdA+minCvdMove;
        if(!agrees)continue;
        const confirmedAt=rows[knownAt].t+STEP;
        // An event must not claim a timestamp before the confirming M15 closes.
        if(confirmedAt>now)continue;
        const broker=market.providerSymbol.trim();
        const eventId=[VERSION,"ctrader",broker,market.symbol,"M15",flow.day,
          kind,rows[a].t,rows[b].t].join("|");
        events.push({
          id:eventId,algorithm:VERSION,symbol:market.symbol,provider:"ctrader",
          providerSymbol:broker,timeframe:"M15",sessionUtc:flow.day,
          type:kind,side:kind==="bearish_regular"?"bearish":"bullish",
          state:"confirmed_technical_not_trade_signal",
          first:{pivotAt:iso(rows[a].t),price:priceA,cvdProxy:cvdA},
          second:{pivotAt:iso(rows[b].t),price:priceB,cvdProxy:cvdB},
          confirmedAt:iso(confirmedAt),
          threshold:{atr14OrConfigured:currentAtr,price:minPriceMove,
            tickVolumeBetweenAndConfirmation:ticks,cvdProxy:minCvdMove},
          note:"Divergenza tecnica fra prezzo e proxy CLV×tick volume; non prova pressione buy/sell reale.",
        });
      }
    }
    events.sort((a,b)=>a.confirmedAt.localeCompare(b.confirmedAt)||a.id.localeCompare(b.id));
    return {
      status:"ok",reason:events.length?"Divergenze tecniche confermate sui dati chiusi.":
        "Nessuna divergenza confermata nel campione disponibile.",
      asOf:iso(now),method:"CLV × tick volume cTrader (proxy, non volume eseguito)",
      algorithm:VERSION,sessionUtc:flow.day,candles:rows.length,events,
      notificationEnabled:false,persistenceEnabled:false,
      caveat:"Il proxy dipende anche dal prezzo: valore predittivo e latenza degli avvisi non ancora validati.",
    };
  }
  return {analyze,parameters,DEFAULTS,VERSION};
});
