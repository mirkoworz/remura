/* Static LAB only. Never deploy to the operational origin. */
(function(){
 "use strict";
 const base=new URL('./',location.href), paths=new Set(['data/cot-history-public.json','data/myfxbook-latest.json','data/myfxbook-history.json'].map(p=>new URL(p,base).pathname));
 const original=window.fetch.bind(window);
 function permitted(input,init){try{const u=new URL(typeof input==='string'||input instanceof URL?input:input.url,base);const method=String(init?.method??input?.method??'GET').toUpperCase();return method==='GET'&&u.origin===base.origin&&paths.has(u.pathname)&&!u.search&&!u.hash;}catch{return false;}}
 window.fetch=(input,init)=>permitted(input,init)?original(input,{...init,credentials:'omit',redirect:'error'}):Promise.reject(new Error('REMURA LAB: rete operativa disabilitata'));
 if(window.XMLHttpRequest)window.XMLHttpRequest.prototype.open=function(){throw new Error('REMURA LAB: XHR disabilitato');};
 if(window.WebSocket)window.WebSocket=function(){throw new Error('REMURA LAB: WebSocket disabilitato');};
 if(window.EventSource)window.EventSource=function(){throw new Error('REMURA LAB: EventSource disabilitato');};
 try{navigator.sendBeacon=()=>false;}catch{}
 document.addEventListener('submit',e=>e.preventDefault(),true);
 document.addEventListener('DOMContentLoaded',()=>{const notice=document.createElement('p');notice.setAttribute('role','status');notice.textContent='PREVIEW ISOLATA · Archivi pubblici locali. Prezzi, servizi privati, login, scritture e dati live non disponibili.';notice.style.cssText='margin:0;padding:8px 16px;background:#17353e;color:#edf9f5;font:13px system-ui;text-align:center';document.body.prepend(notice);},{once:true});
})();
