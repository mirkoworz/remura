/* REMURA v1.24 — pure evidence synthesis. Descriptive, not a trading signal. */
(function(root,factory){
 "use strict";
 const api=factory();
 if(typeof module==="object"&&module.exports)module.exports=api;
 if(root)root.REMURA_SQUALO_VERDICT_CORE=api;
})(typeof window==="undefined"?null:window,function(){
 "use strict";
 const HOUR=3600000;
 const sideName=n=>n>0?"rialzista":n<0?"ribassista":"senza direzione";
 function cotEvidence(cot){
  if(!cot||cot.state==="missing")return {status:"missing",side:0,title:"COT non disponibile",detail:"Nessuna posizione istituzionale dedotta da altri strumenti."};
  if(cot.stale||cot.state==="stale")return {status:"stale",side:0,title:"COT datato",detail:"L'ultima fotografia settimanale è troppo vecchia per una conclusione."};
  if(cot.conflict||cot.state==="conflict")return {status:"mixed",side:0,title:"Gruppi COT non concordi",detail:"Il gruppo speculativo e quello secondario indicano variazioni contrapposte."};
  if((cot.bias!==1&&cot.bias!==-1)||!["watch","trend"].includes(cot.state))
   return {status:"neutral",side:0,title:"COT senza spinta netta",detail:"Non emerge una variazione settimanale robusta nel netto dei futures."};
  return {status:"valid",side:cot.bias,title:"Spinta COT "+sideName(cot.bias),detail:
   (cot.sustained?"Variazioni persistenti su più rilevazioni. ":"Variazione settimanale ancora da confermare. ")+
   "Si riferisce ai futures CFTC, non agli ordini del broker."};
 }
 function priceEvidence(price,now=Date.now()){
  if(!price||price.state==="unavailable")return {status:"missing",side:0,title:"Prezzo non verificato",detail:"Mancano candele H4/H1/M15 idonee o recenti."};
  const latest=Date.parse(price.metrics?.M15?.latest||"");
  const weekend=[0,6].includes(new Date(now).getUTCDay());
  const maxAge=(weekend?72:3)*HOUR;
  if(!Number.isFinite(latest)||latest>now+300000||now-latest>maxAge)
   return {status:"stale",side:0,title:"Prezzo non aggiornato",detail:"Le candele non sono sufficientemente recenti per questo verdetto."};
  if(price.state==="conflict")return {status:"mixed",side:0,title:"H4 e H1 discordanti",detail:"La struttura dei timeframe non sostiene una direzione univoca."};
  if((price.side!==1&&price.side!==-1)||!["watch","partial","confirmed"].includes(price.state))
   return {status:"neutral",side:0,title:"Prezzo senza direzione comune",detail:"H4 e H1 non forniscono una lettura concorde utilizzabile."};
  return {status:"valid",side:price.side,title:"Struttura prezzo "+sideName(price.side),
   detail:price.state==="confirmed"?"Conferma tecnica H4/H1/M15 completa sul campione chiuso.":
    price.state==="partial"?"H4 e H1 coerenti, ma manca conferma M15 completa.":
     "Tendenza H4/H1 coerente; rotture ancora incomplete."};
 }
 function retailEvidence(feed,source,now=Date.now()){
  const current=feed?.current,stamp=Date.parse(current?.t||"");
  const age=now-stamp;
  if(!current)return {status:"missing",side:0,title:source+" N/D",detail:"Campione non disponibile."};
  if(feed.fresh!==true||!Number.isFinite(age)||age< -300000||age>3*HOUR)
   return {status:"stale",side:0,title:source+" datato",detail:"Rilevazione retail conservata, ma non valida come lettura corrente."};
  const lots=source==="Myfxbook";
  if(lots){
   const count=Number(current.lPos)+Number(current.sPos);
   const l=Number(current.lLots),s=Number(current.sLots);
   if(!Number.isFinite(count)||count<30||!Number.isFinite(l)||!Number.isFinite(s)||l<0||s<0||l+s<=0)
    return {status:"missing",side:0,title:"Myfxbook: campione insufficiente",detail:"Servono almeno 30 posizioni e lotti effettivi."};
  }
  const pct=lots?100*Number(current.lLots)/(Number(current.lLots)+Number(current.sLots)):Number(current.lPct);
  if(!Number.isFinite(pct)||pct<0||pct>100)return {status:"missing",side:0,title:source+" non valido",detail:"Distribuzione long/short non verificabile."};
  const side=pct>=70?1:pct<=30?-1:0;
  return {status:side?"extreme":"neutral",side,
   title:source+(side?" · prevalenza retail "+(side>0?"long":"short"):" · retail bilanciato"),
   detail:"Long "+pct.toFixed(1).replace(".",",")+"% nella propria popolazione. "+
    (lots?"Misura i lotti della community.":"Misura la quota di posizioni clienti.")+
    " Nessuna posizione istituzionale dedotta."};
 }
 function macroEvidence(info){
  if(!info||info.state==="unavailable")return {status:"missing",title:"Macro non disponibile",detail:"DXY e VIX non hanno entrambi una serie verificabile."};
  return {status:info.historical?"historical":"context",title:info.label||"Contesto macro disponibile",
   detail:(info.historical?"Ultima sessione del venerdì, non live. ":"")+
    "Il contesto DXY/VIX descrive il rischio generale, non aggiunge automaticamente un voto long o short."};
 }
 function evaluate({symbol,cot,price,myfxbook,capital,macro,now=Date.now()}={}){
  const items={
   cot:cotEvidence(cot),
   price:priceEvidence(price,now),
   myfxbook:retailEvidence(myfxbook,"Myfxbook",now),
   capital:retailEvidence(capital,"Capital.com",now),
   macro:macroEvidence(macro)
  };
  const c=items.cot,p=items.price;
  let state="incomplete",side=0,title="Prove insufficienti per un verdetto",
   narrative="Il quadro non contiene due conferme indipendenti e coerenti fra COT e prezzo.";
  if(c.status==="valid"&&p.status==="valid"){
   if(c.side===p.side){
    state="aligned";side=c.side;
    const strong=cot.state==="trend"&&price.state==="confirmed";
    title=strong?"Tracce concordi, da verificare":"Coerenza preliminare, da monitorare";
    narrative="La spinta speculativa COT settimanale e la struttura del prezzo indicano entrambe una direzione "+
     sideName(side)+". "+(strong?"Il prezzo conferma H4/H1/M15. ":"Mancano conferme tecniche o persistenza sufficienti. ")+
     "Non identifica acquisti o vendite istituzionali in tempo reale.";
   }else{
    state="divergent";title="COT e prezzo in contrasto";
    narrative="Il COT indica una spinta "+sideName(c.side)+
      ", mentre la struttura H4/H1 suggerisce un movimento "+sideName(p.side)+
      ". Non attribuire una direzione affidabile allo Squalo.";
   }
  }else if(c.status==="mixed"||p.status==="mixed"){
   state="mixed";title="Segnali principali non concordi";
   narrative="Almeno uno dei due fattori principali è internamente contraddittorio: nessun verdetto direzionale.";
  }else if(c.status==="stale"||p.status==="stale"){
   state="stale";title="Dati principali datati";
   narrative="L'analisi necessita di posizionamento COT e prezzo sufficientemente recenti.";
  }
  const retailNotes=[];
  for(const k of ["myfxbook","capital"]){
   const f=items[k];
   if(f.status==="extreme"){
    if(side&&state==="aligned")retailNotes.push(
     (k==="myfxbook"?"Myfxbook":"Capital.com")+
     (f.side===-side?" presenta un estremo retail opposto alla direzione COT/prezzo.":" presenta un estremo retail nella stessa direzione COT/prezzo.")+
     " È un indizio descrittivo, non una conferma istituzionale.");
    else retailNotes.push((k==="myfxbook"?"Myfxbook":"Capital.com")+
     " mostra un estremo retail, ma senza COT e prezzo concordi non è un segnale contrarian.");
   }
  }
  return {symbol:String(symbol||""),state,side,title,narrative,items,retailNotes,
   note:"Analisi descrittiva: COT settimanale, prezzi broker, due campioni retail diversi e contesto macro. Nessuna probabilità, ordine o promessa di rendimento."};
 }
 return Object.freeze({cotEvidence,priceEvidence,retailEvidence,macroEvidence,evaluate});
});
