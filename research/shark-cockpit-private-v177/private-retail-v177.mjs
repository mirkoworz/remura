// REMURA D v1.77 LAB — 24/11/2026 Europe/Rome — REVIEW ONLY, not bundled or connected.
// Owner origin must be injected by a separately reviewed private deployment, never a query parameter.
// Client gate is NOT authentication: server-side Access/role enforcement is mandatory.
// Pass a bounded AbortSignal. No fallback, polling, persistence, vendor API or cross-origin calls.
export function makePrivateRetailReader({ownerOrigin,pageOrigin,fetchFn}){
  const allowed=typeof ownerOrigin==="string"&&/^https:\/\/[a-z0-9.-]+(?::[0-9]+)?$/.test(ownerOrigin)&&!/\.(?:pages\.dev|github\.io|workers\.dev)(?::\d+)?$/.test(ownerOrigin)&&ownerOrigin===pageOrigin&&typeof fetchFn==="function";
  return async function read(signal){
    const fail=state=>({state,source:"PRIVATE_VPS",doc:null});
    if(!allowed)return fail("DISABLED");
    if(!signal||signal.aborted)return fail("CANCELLED");
    try{
      const res=await fetchFn(ownerOrigin+"/private-api/retail/latest.json",{method:"GET",credentials:"same-origin",mode:"same-origin",redirect:"error",cache:"no-store",referrerPolicy:"no-referrer",headers:{Accept:"application/json"},signal});
      if(res.status===401||res.status===403)return fail("DENIED");
      if(!res.ok||res.redirected||!/^application\/json(?:\s*;|$)/i.test(res.headers.get("content-type")||""))return fail("UNAVAILABLE");
      const raw=await res.text();
      if(typeof raw!=="string"||raw.length>3000000)return fail("INVALID");
      if(signal.aborted)return fail("CANCELLED");
      const doc=JSON.parse(raw);
      if(doc?.status!=="ok"||doc.source!=="Myfxbook Community Outlook"||!doc.symbols||typeof doc.symbols!=="object"||Array.isArray(doc.symbols)||!Number.isFinite(Date.parse(doc.updatedAt)))return fail("INVALID");
      return {state:"LOADED",source:"PRIVATE_VPS",doc};
    }catch{return fail(signal.aborted?"CANCELLED":"UNAVAILABLE");}
  }
}

export function createRetailSession(){
 let generation=0, value={state:"NOT_LOADED",doc:null};
 return Object.freeze({
   begin(){generation++;return generation},
   accept(ticket,result){if(ticket!==generation)return false;value=result?.state==="LOADED"&&result.doc?{state:"LOADED",doc:result.doc}:{state:result?.state||"UNAVAILABLE",doc:null};return true},
   clear(){generation++;value={state:"CLEARED",doc:null}},
   snapshot(){return value}
 });
}
