/* REMURA v1.6 - verification of sample freshness; never infer freshness from HTTP success. */
(function(root,factory){const api=factory();if(typeof module==="object"&&module.exports)module.exports=api;if(root)root.REMURA_FEED_HEALTH=api;})(typeof window!=="undefined"?window:null,function(){
 "use strict";
 function inspect(doc,expected=[],now=Date.now(),limit=3*3600000){
  if(!doc||doc.status!=="ok"||!doc.symbols||typeof doc.symbols!=="object"||Array.isArray(doc.symbols))
   return {valid:false,recent:false,reason:"Archivio non valido"};
  const ms=Date.parse(doc.updatedAt||"");
  if(!Number.isFinite(ms))return {valid:false,recent:false,reason:"Timestamp assente"};
  const age=now-ms,wanted=Array.isArray(expected)?[...new Set(expected)]:[];
  return {valid:true,recent:age>=-300000&&age<=limit,ageMinutes:Math.max(0,Math.floor(age/60000)),
   total:Object.keys(doc.symbols).length,covered:wanted.filter(k=>doc.symbols[k]&&typeof doc.symbols[k]==="object").length,
   expected:wanted.length,updatedAt:new Date(ms).toISOString(),reason:age>limit?"Dati datati":age< -300000?"Timestamp futuro":"Dati recenti"};
 }
 return {inspect};
});