/* REMURA Squalo: explainable observations, not a claim of institutional real-time trades. */
(function(root,factory){
  "use strict";
  const api=factory();
  if(typeof module==="object"&&module.exports)module.exports=api;
  if(root)root.REMURA_SQUALO=api;
})(typeof window!=="undefined"?window:null,function(){
  "use strict";
  const fmt=n=>Number.isFinite(n)?new Intl.NumberFormat("it-IT",{maximumFractionDigits:2,signDisplay:"exceptZero"}).format(n):"N/D";
  const pct=n=>Number.isFinite(n)?new Intl.NumberFormat("it-IT",{maximumFractionDigits:1}).format(n)+"%":"N/D";
  const sideName=d=>d>0?"LONG":d<0?"SHORT":"N/D";
  function observed(row,now=Date.now()){
    const l=Number(row?.lPct),s=Number(row?.sPct),t=Date.parse(row?.t||"");
    return row&&row.lPct!==null&&row.lPct!==undefined&&
      row.sPct!==null&&row.sPct!==undefined&&
      Number.isFinite(l)&&Number.isFinite(s)&&l>=0&&s>=0&&
      Math.abs(l+s-100)<=1&&Number.isFinite(t)&&t<=now+300000&&t>=now-10800000;
  }
  function evaluate(input,now=Date.now()){
    const symbol=String(input?.symbol||"").toUpperCase();
    const cot=input?.cot||null,price=input?.price||null;
    const retail=input?.retail||null,capital=input?.capital||null;
    const qualified=cot&&!cot.stale&&!["stale","missing"].includes(cot.state)&&
      [1,-1].includes(cot.bias)&&Number.isFinite(cot.weekly);
    const dir=qualified?cot.bias:0;
    const risks=[],checks=[],evidence=[];
    const add=(name,status,detail)=>checks.push({name,status,detail});
    if(!qualified){
      add("1 · COT istituzionale","missing",cot?.stale?"Report troppo vecchio":"Manca una spinta netta verificata");
      risks.push("Senza COT recente e direzionale non possiamo attribuire un contesto ai grandi operatori.");
    }else{
      const movement=cot.currentNet*dir<0?"posizione netta ancora dal lato opposto":"posizione netta coerente";
      const detail=(cot.specLabel||"Speculatori")+" · netto "+fmt(cot.currentNet)+"% OI; variazione "+
        fmt(cot.weekly)+" pp; 4 settimane "+fmt(cot.fourWeeks)+" pp. ("+movement+")";
      add("1 · COT istituzionale",cot.conflict?"mixed":"support",detail);
      evidence.push((cot.sustained?"Spinta su più report":"Variazione settimanale")+" "+sideName(dir)+" nel COT.");
      if(cot.conflict)risks.push("Categorie COT discordanti: non presumere un unico comportamento istituzionale.");
    }
    const checkRetail=(name,source)=>{
      const sample=source?.row||source,valid=source?.fresh===true&&observed(sample,now);
      if(!valid){add(name,"missing","Rilevazione non recente, non disponibile o non verificata.");return 0;}
      const long=Number(sample.lPct),short=Number(sample.sPct);
      const skew=long>=60?1:short>=60?-1:0;
      const detail=pct(long)+" long, "+pct(short)+" short; campione retail, non istituzionale.";
      const supporting=dir!==0&&skew===-dir;
      add(name,skew===0?"neutral":supporting?"support":"mixed",detail);
      if(supporting)evidence.push(name+" prevalentemente "+sideName(-dir)+", contro il contesto COT.");
      return supporting?10:0;
    };
    const retailPts=checkRetail("2 · Myfxbook (lotti)",retail);
    const capitalPts=checkRetail("3 · Capital.com (posizioni)",capital);
    // Lot history explains whether long/short volume actually grows or shrinks.
    // This is supporting context, never extra institutional evidence or score.
    const hist=Array.isArray(input?.retailHistory)?input.retailHistory:[];
    const lotSamples=hist.filter(p=>p&&Number.isFinite(Date.parse(p.t))&&
      Number.isFinite(Number(p.lLots))&&Number.isFinite(Number(p.sLots))&&
      Number(p.lLots)>=0&&Number(p.sLots)>=0)
      .sort((a,b)=>Date.parse(a.t)-Date.parse(b.t));
    if(lotSamples.length>=2){
      const old=lotSamples[lotSamples.length-2],newest=lotSamples[lotSamples.length-1];
      const gap=Date.parse(newest.t)-Date.parse(old.t);
      if(gap>0&&gap<=4*3600000&&Date.parse(newest.t)>=now-6*3600000){
        const longChange=Number(newest.lLots)-Number(old.lLots);
        const shortChange=Number(newest.sLots)-Number(old.sLots);
        evidence.push("Myfxbook, ultime due rilevazioni: lotti long "+
          (longChange>0?"in aumento":longChange<0?"in diminuzione":"stabili")+
          " ("+fmt(longChange)+"); lotti short "+
          (shortChange>0?"in aumento":shortChange<0?"in diminuzione":"stabili")+
          " ("+fmt(shortChange)+"). La differenza non identifica gli ordini dei fondi.");
      }
    }
    const h4=price?.metrics?.H4,h1=price?.metrics?.H1,m15=price?.metrics?.M15;
    const verified=price&&price.state!=="unavailable"&&
      [h4,h1,m15].every(m=>m?.state==="ok");
    let aligned=false,fast=false;
    if(!verified){
      add("4 · Prezzo H4/H1","missing","Candele chiuse non disponibili o non recenti.");
      add("5 · Prezzo M15","missing","Attendere dati validi.");
      risks.push("Il prezzo non è verificato: nessun movimento può essere considerato confermato.");
    }else{
      aligned=dir!==0&&h4.trend===dir&&h1.trend===dir;
      fast=aligned&&m15.trend===dir;
      const desc=t=>t>0?"rialzista":t<0?"ribassista":"neutro";
      add("4 · Prezzo H4/H1",aligned?"support":"mixed","H4 "+desc(h4.trend)+", H1 "+desc(h1.trend)+".");
      add("5 · Prezzo M15",fast?"support":"mixed","M15 "+desc(m15.trend)+
          (price.state==="confirmed"?" · rottura tecnica verificata.":"."));
      if(aligned)evidence.push("H4 e H1 seguono la stessa direzione del COT.");
      if(fast)evidence.push("Anche M15 è allineato.");
      else risks.push("M15 non fornisce ancora una conferma completa.");
    }
    if(!qualified){
      return {symbol,side:0,score:null,stage:"non-valutabile",
        title:"Squalo non identificabile con i dati attuali",
        summary:"Mancano report COT recenti e direzionali. Il retail da solo non rivela la posizione dei fondi.",
        checks,risks,evidence,coverage:checks.filter(c=>c.status!=="missing").length,
        updatedAt:cot?.asof||null};
    }
    let score=25+(cot.sustained?15:0)+retailPts+capitalPts+
      (aligned?20:0)+(fast?10:0)+(fast&&price.state==="confirmed"?10:0);
    if(cot.conflict)score=Math.min(39,score);
    // A reduction of net LONG futures is NOT the same as funds being net SHORT.
    // Do not call a current-price move "institutionally confirmed" in that case.
    if(cot.currentNet*dir<0){
      score=Math.min(74,score);
      risks.push("Il netto dei fondi è ancora "+sideName(-dir)+
        ": sta diminuendo, ma non dimostra un posizionamento netto "+sideName(dir)+".");
    }
    score=Math.min(100,Math.max(0,score));
    const coverage=checks.filter(c=>c.status!=="missing").length;
    let stage="osservazione",title="Tracce "+sideName(dir)+" da monitorare";
    if(!cot.conflict&&cot.sustained&&aligned&&coverage>=3&&score>=60){
      stage="preparazione";
      title="Indizi di preparazione "+sideName(dir);
    }
    if(stage==="preparazione"&&fast&&price.state==="confirmed"&&score>=80&&coverage>=4){
      stage="coerente";
      title="Movimento "+sideName(dir)+" coerente con il COT";
    }
    if(cot.conflict){
      title="Fondi discordanti: ipotesi "+sideName(dir)+" debole";
      stage="discordante";
    }
    const summary=(cot.sustained?"L'esposizione speculativa varia in modo persistente. ":"Il COT indica una variazione recente, non ancora persistente. ")+
      (aligned?"H4 e H1 sono coerenti. ":"La struttura prezzo H4/H1 non è ancora coerente o verificabile. ")+
      (retailPts||capitalPts?"Almeno un campione retail è prevalentemente sul lato opposto. ":"Il retail non aggiunge una conferma contrarian valida. ")+
      "Non prova ordini istituzionali in corso.";
    return {symbol,side:dir,score,stage,title,summary,checks,risks,evidence,coverage,
      updatedAt:cot.asof,weekly:cot.weekly,currentNet:cot.currentNet,priceConfirmed:!!(fast&&price.state==="confirmed")};
  }
  return {evaluate,observed};
});
