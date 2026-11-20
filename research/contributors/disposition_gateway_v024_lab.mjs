// REMURA Experience v0.24 LAB — 20/11/2026 CET
// Offline boundary ONLY. Injected verifiers are mocks, NOT production authentication.
import {validateV2} from './consumer_v021.mjs';

const VIEW='REMURA_SHARED_VIEW_FIXTURE_V2';
const HEAD='REMURA_AUTHORITY_HEAD_FIXTURE_V024';
const RESP='REMURA_DISPOSITION_STATUS_FIXTURE_V024';
const CACHE='no-store, max-age=0';
const HEX=/^[a-f0-9]{64}$/;
const STATUS={409:'PENDING',410:'ABANDONED',403:'DENIED',503:'UNAVAILABLE'};

function response(status, payload){
  return Object.freeze({status,headers:Object.freeze({'Cache-Control':CACHE,'Content-Type':'application/json; charset=utf-8','Vary':'Cookie, Authorization'}),body:typeof payload==='string'?payload:JSON.stringify({schema:RESP,state:STATUS[status]??'UNAVAILABLE'})});
}
function safeIdentity(a){
  return a&&Object.getPrototypeOf(a)===Object.prototype&&a.role==='CONTRIBUTOR'&&typeof a.subject==='string'&&a.subject.length>0&&a.subject.length<=64&&typeof a.session_version==='string'&&a.session_version.length>0&&a.session_version.length<=128;
}
function sameIdentity(a,b){return safeIdentity(a)&&safeIdentity(b)&&a.subject===b.subject&&a.session_version===b.session_version;}
function safeHead(h){
  return h&&Object.getPrototypeOf(h)===Object.prototype&&h.schema===HEAD&&h.generation==='fixture-v024-disposition'&&
   Number.isSafeInteger(h.sequence)&&h.sequence>=1&&h.sequence<=32&&h.revision===h.sequence&&
   typeof h.intent_id==='string'&&h.intent_id.length>0&&h.intent_id.length<=64&&
   typeof h.audience_subject==='string'&&h.audience_subject.length>0&&h.audience_subject.length<=64&&
   [h.candidate_digest,h.journal_tag,h.authority_tag].every(v=>typeof v==='string'&&HEX.test(v))&&
   ['PUBLISHED','ABANDONED','PENDING'].includes(h.disposition)&&
   Number.isSafeInteger(h.expires_at_ms)&&Number.isSafeInteger(h.signed_at_ms)&&h.signed_at_ms>=0&&h.expires_at_ms>=0;
}
function safePin(p){return p&&Object.getPrototypeOf(p)===Object.prototype&&Number.isSafeInteger(p.sequence)&&p.sequence>0&&typeof p.authority_tag==='string'&&HEX.test(p.authority_tag);}
function samePin(p,h){return safePin(p)&&p.sequence===h.sequence&&p.authority_tag===h.authority_tag;}
function nowMs(clock){const x=clock();if(!Number.isSafeInteger(x)||x<0)throw Error('invalid clock');return x;}

/** Never supply client-controlled data as an authority, verifier or independent pin.
 * readConsistent() MUST return an atomically acquired {head,view} candidate.
 * verifyAuthority() MUST authenticate the head and its disposition against a real independent trust root.
 * readIndependentPin() MUST access a monotonic witness outside the snapshot restore domain.
 * This file intentionally implements none of those guarantees: LAB-only seam.
 */
export function makeDispositionGatewayV024({readConsistent,verifyAuthority,readIndependentPin,authorize,clock}){
  if(![readConsistent,verifyAuthority,readIndependentPin,authorize,clock].every(f=>typeof f==='function'))throw Error('NO_TRUST_ADAPTER');
  return async function fixtureRequest(){
    let initial,firstPin,head,view;
    try{
      const start=nowMs(clock);
      initial=await authorize();
      if(!safeIdentity(initial))return response(403);
      const snapshot=await readConsistent();
      if(!snapshot||Object.getPrototypeOf(snapshot)!==Object.prototype)return response(503);
      ({head,view}=snapshot);
      if(!safeHead(head)||head.signed_at_ms>start)return response(503);
      if(head.audience_subject!==initial.subject)return response(403);
      firstPin=await readIndependentPin();
      if(!samePin(firstPin,head)||await verifyAuthority(head,firstPin)!==true)return response(503);
      let numeric=null;
      if(head.disposition==='PUBLISHED'){
        if(start>head.expires_at_ms||view===null||typeof view!=='object')return response(503);
        const clean=validateV2(view,start);
        if(clean.schema!==VIEW||clean.revision!==head.revision||clean.as_of===undefined)return response(503);
        numeric=JSON.stringify(clean);
        if(numeric.length>16384||new TextEncoder().encode(numeric).length>16384)return response(503);
      }
      // Recheck AFTER any async verifier and projection before exposing the response.
      const end=nowMs(clock);
      const second=await authorize();
      const secondPin=await readIndependentPin();
      if(!sameIdentity(initial,second))return response(403);
      if(!samePin(secondPin,head)||secondPin.sequence!==firstPin.sequence||secondPin.authority_tag!==firstPin.authority_tag)return response(503);
      if(end<start||end-start>5000||end<head.signed_at_ms)return response(503);
      if(head.disposition==='ABANDONED')return response(410);
      if(head.disposition==='PENDING')return response(409);
      if(end>head.expires_at_ms||!numeric)return response(503);
      // No public v0.23/v0.24 disposition metadata appended to the V2 body.
      return response(200,numeric);
    }catch{return response(503);}
  };
}
