/* REMURA v1.0 — deterministic, offline OHLC interpreter.
   It never fetches prices or API keys. Input comes from a local file chooser.
   All timestamps are UTC candle OPEN times and all buckets are already closed.
*/
(function (root, factory) {
  "use strict";
  const core=factory();
  if (typeof module === "object" && module.exports) module.exports=core;
  if (root) root.REMURA_PRICE_CORE=core;
})(typeof window !== "undefined" ? window : null, function () {
  "use strict";
  const DURATION={M15:900000,H1:3600000,H4:14400000};
  const format=n=>Number.isFinite(n)?new Intl.NumberFormat("it-IT",{maximumFractionDigits:5}).format(n):"N/D";
  const finite = n => typeof n === "number" && Number.isFinite(n);
  function load(bundle,symbol,{now=Date.now()}={}){
    if (!bundle||bundle.schema!=="remura-price-v1"||!bundle.markets||typeof bundle.markets!=="object")
      throw Error("Formato file non riconosciuto (richiesto remura-price-v1).");
    if (!Number.isFinite(Date.parse(bundle.generatedAt || "")) || Date.parse(bundle.generatedAt)>now+300000)
      throw Error("Data di esportazione assente o nel futuro.");
    const data=bundle.markets[symbol];
    if(!data||data.symbol!==symbol||!data.timeframes)throw Error("Il file non contiene un dataset valido per "+symbol+".");
    const frames={};
    for(const tf of Object.keys(DURATION)){
      const raw=data.timeframes[tf];
      if(!Array.isArray(raw))throw Error("Intervallo "+tf+" mancante.");
      let last=-Infinity;
      frames[tf]=raw.map(row=>{
        const t=Date.parse(row.t);
        if(!Number.isFinite(t)||t%DURATION[tf]!==0||t<=last||t+DURATION[tf]>now+300000)
          throw Error("Timestamps non validi, duplicati o candele ancora in formazione: "+tf);
        const vals=[row.o,row.h,row.l,row.c];
        if(!vals.every(x=>finite(x)&&x>0)||row.h<Math.max(row.o,row.c)||row.l>Math.min(row.o,row.c)||row.h<row.l)
          throw Error("OHLC non valido in "+tf);
        last=t;
        return {t, o:row.o,h:row.h,l:row.l,c:row.c};
      });
    }
    const provider=String(data.provider||"sconosciuto");
    if(!["twelve","oanda","mt5","ctrader","csv"].includes(provider))throw Error("Fonte dati non riconosciuta.");
    return {symbol,provider,providerSymbol:String(data.providerSymbol||symbol),generatedAt:bundle.generatedAt,frames};
  }
  function ema(values,length){
    if(values.length<length)return null;
    let v=values.slice(0,length).reduce((a,b)=>a+b,0)/length;
    const alpha=2/(length+1);
    for(let i=length;i<values.length;i++)v=alpha*values[i]+(1-alpha)*v;
    return v;
  }
  function atr(rows,period=14){
    if(rows.length<period+1)return null;
    const end=rows.slice(-(period+1));
    let sum=0;
    for(let i=1;i<end.length;i++){
      const x=end[i],p=end[i-1];
      sum+=Math.max(x.h-x.l,Math.abs(x.h-p.c),Math.abs(x.l-p.c));
    }
    return sum/period;
  }
  function timeframe(rows,tf,now){
    const n=Array.isArray(rows)?rows.length:0;
    if(n<55)return {state:"insufficient",tf,count:n,text:"Servono almeno 55 candele H4/H1/M15 complete."};
    const last=rows[n-1],close=last.c,duration=DURATION[tf];
    const timeLag=now-(last.t+duration);
    const day=new Date(now).getUTCDay();
    const weekend=(day===0||day===6||(day===1&&new Date(now).getUTCHours()<6));
    const maxLag=(weekend?72:18)*3600000;
    const stale=timeLag>maxLag || timeLag< -300000;
    const atr14=atr(rows),e20=ema(rows.map(x=>x.c),20),e50=ema(rows.map(x=>x.c),50);
    const prior20=rows.slice(-22,-2);
    const resistance=Math.max(...prior20.map(x=>x.h)),support=Math.min(...prior20.map(x=>x.l));
    const margin=atr14*.1;
    const one=rows[n-2],two=rows[n-1];
    const twoUp=one.c>resistance+margin && two.c>resistance+margin;
    const twoDown=one.c<support-margin && two.c<support-margin;
    const trend=close>e20&&e20>e50?1:close<e20&&e20<e50?-1:0;
    const breakout=twoUp?1:twoDown?-1:0;
    const gapCount=rows.reduce((acc,row,i)=>i&&row.t-rows[i-1].t>duration*1.01?acc+1:acc,0);
    const recent=rows.slice(-55);
    const recentGaps=recent.reduce((acc,row,i)=>i&&row.t-recent[i-1].t>duration*1.01?acc+1:acc,0);
    const recentExpectedSpan=recent[recent.length-1].t-recent[0].t;
    const spanHours=Math.round(recentExpectedSpan/3600000);
    return {state:stale?"stale":"ok",tf,count:n,close,latest:new Date(last.t+duration).toISOString(),ageHours:timeLag/3600000,
      ema20:e20,ema50:e50,atr14,trend,breakout,resistance,support,gapCount,recentGaps,spanHours,
      // Weekend and market closures are discontinuities, not fabricated candles.
      text:(trend===1?"EMA20 sopra EMA50 e close sopra EMA20":trend===-1?"EMA20 sotto EMA50 e close sotto EMA20":"EMA e prezzo senza direzione concorde")+
        "; "+(breakout===1?"due chiusure oltre la resistenza precedente":breakout===-1?"due chiusure sotto il supporto precedente":"nessuna rottura confermata da due chiusure")+
        "; "+recentGaps+" interruzioni nelle ultime 55 candele."
    };
  }
  function analyze(market,{now=Date.now()}={}){
    const metrics={};
    for(const tf of Object.keys(DURATION))metrics[tf]=timeframe(market.frames[tf],tf,now);
    const fail=Object.values(metrics).filter(m=>m.state!=="ok");
    if(fail.length)return {state:"unavailable",side:0,title:"Analisi prezzo non verificabile",metrics,
      explanation:"Intervalli incompleti o dati troppo vecchi: "+fail.map(x=>x.tf+" ("+x.state+")").join(", ")+". Non attribuiamo nessuna conferma al prezzo.",
      caveats:["Solo candele chiuse; nessun dato simulato.","Dati del provider "+market.provider+" su "+market.providerSymbol+"; prezzi e orari possono differire da TradingView o dal future CFTC."]};
    const h4=metrics.H4,h1=metrics.H1,m15=metrics.M15;
    const aligned=h4.trend!==0&&h4.trend===h1.trend;
    const breakout=(h4.breakout===h4.trend||h1.breakout===h1.trend) && aligned;
    const agreement=aligned&&m15.trend===h4.trend;
    // Two M15 closes are needed to call entry-timing confirmation; no order is generated.
    const confirmed=agreement&&breakout && m15.breakout===h4.trend;
    const tentative=agreement&&breakout;
    let state="neutral",side=0,title="Prezzo senza conferma multi-timeframe";
    if(confirmed){state="confirmed";side=h4.trend;title="Struttura prezzo "+(side>0?"rialzista":"ribassista")+" coerente su H4, H1 e M15";}
    else if(tentative){state="partial";side=h4.trend;title="H4 e H1 coerenti, manca rottura M15";}
    else if(aligned){state="watch";side=h4.trend;title="Tendenza H4 e H1 coerente, rotture non complete";}
    else if(h4.trend!==0&&h1.trend!==0&&h4.trend!==h1.trend){state="conflict";title="H4 e H1 discordanti";}
    return {state,side,title,metrics,confirmed,tentative,
      explanation:"H4: "+h4.text+" H1: "+h1.text+" M15: "+m15.text,
      caveats:["Le soglie EMA20/EMA50 e 20 candele sono regole iniziali, non parametri ottimizzati né un backtest.",
        "Rotture valutate rispetto a 20 candele precedenti e margine 0,1 ATR; sono necessarie due chiusure consecutive.",
        "M15, H1 e H4 sono ricostruiti su orari UTC e potrebbero non avere lo stesso allineamento di altri broker."]};
  }
  function cross(price,cot,retail){
    if(!price||price.state==="unavailable")return {state:"unavailable",text:"Prezzo non verificato. Non è possibile stabilire una conferma del COT."};
    if(!cot||cot.state==="missing"||cot.stale||cot.state==="stale"||!cot.bias)
      return {state:"monitor",text:"Prezzo analizzato, ma manca una spinta COT direzionale recente e verificabile. Non viene generato alcun segnale."};
    if(price.side===0)return {state:"monitor",text:"Il COT suggerisce un contesto, ma la struttura del prezzo non è coerente fra gli intervalli."};
    if(price.side!==cot.bias)return {state:"conflict",text:"Divergenza: il COT e la struttura recente del prezzo indicano direzioni opposte. Evitare di interpretarla come conferma."};
    if(price.state!=="confirmed")return {state:"watch",text:"Contesto COT e tendenza H4/H1 coerenti, ma la conferma tecnica completa manca. Monitorare, non entrare automaticamente."};
    const contrarian=retail && retail.valid && retail.skew===-cot.bias;
    return {state:"context",text:"COT e struttura del prezzo risultano coerenti sul campione disponibile."+
      (contrarian?" Il retail mostra anche una distribuzione contrarian 70/30, che resta soltanto un dato del campione Myfxbook.":"")+
      " Non è una probabilità di successo né un ordine di ingresso."};
  }
  return {load,analyze,timeframe,cross,ema,atr,DURATION,format};
});