// REMURA Experience v0.4 LAB — 20/11/2026 16:49 CET
// Readiness coordinator, inert: no fetch, credentials, storage, timers or DOM.
// The supplied server authorization is the security boundary, not this UI helper.
export function createReadiness({shell,authorize,loadApproved,onStep=()=>{}}){
 for(const f of [shell,authorize,loadApproved,onStep])if(typeof f!=="function")throw Error("invalid_readiness_adapter");
 let epoch=0,active=null;
 function cancel(){epoch++;active?.abort();active=null;}
 async function start(){
  cancel();const id=epoch,ctrl=new AbortController();active=ctrl;
  const live=()=>id===epoch&&!ctrl.signal.aborted;
  const step=(state,completed)=>{if(live())onStep(Object.freeze({state,completed,total:3}));};
  try{
   step("SHELL",0);await shell(ctrl.signal);if(!live())return {state:"CANCELLED"};
   step("AUTHORIZATION",1);
   const p=await authorize(ctrl.signal);if(!live())return {state:"CANCELLED"};
   if(!p||p.authorized!==true||!["OWNER","CONTRIBUTOR","VIEWER"].includes(p.role)){
    step("DENIED",1);return {state:"DENIED"};
   }
   const role=p.role;step("APPROVED_VIEW",2);
   if(!live())return {state:"CANCELLED"};
   const view=await loadApproved(role,ctrl.signal);
   if(!live())return {state:"CANCELLED"};
   if(!view||view.ready!==true)throw Error("view_not_ready");
   step("READY",3);
   if(!live())return {state:"CANCELLED"};
   return {state:"READY",role,view};
  }catch{
   if(!live())return {state:"CANCELLED"};
   try{step("BLOCKED",null);}catch{}
   return {state:"BLOCKED"};
  }finally{if(id===epoch)active=null;}
 }
 return Object.freeze({start,cancel});
}
