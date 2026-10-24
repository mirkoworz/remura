/* REMURA v1.30 — deterministic and explainable COT shortlisting.
 * Diversity reduces overlapping FX currency exposures; it does not
 * establish statistical independence or predictive advantage.
 */
(function(root,factory){
 "use strict";
 const api=factory();
 if(typeof module==="object"&&module.exports)module.exports=api;
 else root.REMURA_SQUALINCOME_SHORTLIST=api;
})(typeof globalThis!=="undefined"?globalThis:this,function(){
 "use strict";
 const CCY=/^[A-Z]{6}$/;
 function exposures(candidate){
  const sym=candidate?.sym,group=candidate?.meta?.group;
  if(typeof sym!=="string"||group!=="forex"||!CCY.test(sym))return [];
  return [sym.slice(0,3),sym.slice(3)];
 }
 function select(rows,mode="diverse",limit=4){
  const n=Math.max(1,Math.min(4,Number.isInteger(limit)?limit:4));
  const valid=(Array.isArray(rows)?rows:[]).filter(x=>
   typeof x?.sym==="string"&&Number.isFinite(x.change)&&Math.abs(x.change)>=0.45
  ).slice().sort((a,b)=>Math.abs(b.change)-Math.abs(a.change)||a.sym.localeCompare(b.sym));
  if(mode==="strongest")return valid.slice(0,n);
  if(mode!=="diverse")throw Error("Modalità scanner non valida");
  const picked=[],remaining=valid.slice();
  while(picked.length<n&&remaining.length){
   const used=picked.flatMap(exposures);
   let best=0,bestScore=-Infinity;
   for(let i=0;i<remaining.length;i++){
    const c=remaining[i],fx=exposures(c);
    const overlap=fx.filter(currency=>used.includes(currency)).length;
    const score=Math.abs(c.change)/(1+1.2*overlap);
    if(score>bestScore+1e-12){bestScore=score;best=i;}
   }
   picked.push(remaining.splice(best,1)[0]);
  }
  return picked;
 }
 return {select,exposures};
});
