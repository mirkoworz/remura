// REMURA Contributors v0.68 LAB — pure staging admission gates, no network or side effects.
// This is a candidate contract; real Cloudflare Access/JWT/D1 binding NOT activated.
const DENY='REMURA_V068_GATE_DENIED';
const fail=()=>{throw new Error(DENY)};
const roles=new Set(['CONTRIBUTOR','OWNER']);
const methods=new Set(['POST']);
const UUID=/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/;
const paths=Object.freeze({
 '/api/amendment/reconcile':Object.freeze({role:'CONTRIBUTOR',kind:'READ',body:['request_id']}),
 '/api/amendment/mine':Object.freeze({role:'CONTRIBUTOR',kind:'READ',body:['after']}),
 '/owner/amendment/reconcile-queue':Object.freeze({role:'OWNER',kind:'READ',body:['after']})
});
const keys=(obj,fields)=>obj!==null&&typeof obj==='object'&&!Array.isArray(obj)&&Object.getPrototypeOf(obj)===Object.prototype&&Object.keys(obj).length===fields.length&&fields.every(k=>Object.hasOwn(obj,k));
const origin=(value)=>{try{const u=new URL(value);return u.origin===value&&u.protocol==='https:'&&u.username===''&&u.password===''&&u.pathname==='/'&&u.search===''&&u.hash==='';}catch{return false}};
export function inspectStagingRequestV068(request,session,policy){
 if(!keys(policy,['origin','stage','enabled'])||!origin(policy.origin)||policy.stage!=='PRIVATE_STAGING'||policy.enabled!==true)fail();
 if(!keys(session,['role','trusted','active','audienceVerified','emailVerified','serviceToken'])||!roles.has(session.role)||session.trusted!==true||session.active!==true||session.audienceVerified!==true||session.emailVerified!==true||session.serviceToken!==false)fail();
 if(!keys(request,['url','method','headers','body'])||!methods.has(request.method)||typeof request.url!=='string'||!keys(request.headers,['origin','csrf','contentType']))fail();
 let u;try{u=new URL(request.url)}catch{fail()}
 if(u.origin!==policy.origin||u.search!==''||u.hash!==''||u.username!==''||u.password!==''||request.headers.origin!==policy.origin||request.headers.csrf!=='1'||request.headers.contentType!=='application/json')fail();
 const route=paths[u.pathname];if(!route||route.role!==session.role)fail();
 if(!keys(request.body,route.body))fail();
 if(route.body[0]==='after'&&(!Number.isSafeInteger(request.body.after)||request.body.after<0))fail();
 if(route.body[0]==='request_id'&&(typeof request.body.request_id!=='string'||!UUID.test(request.body.request_id)))fail();
 return Object.freeze({path:u.pathname,role:session.role,kind:route.kind,readOnly:true,requiresServerAuthorization:true,cacheControl:'no-store'});
}
export function stagingBrowserPolicyV068(originValue){
 if(!origin(originValue))fail();
 return Object.freeze({
 'Content-Security-Policy':"default-src 'none'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; form-action 'none'; style-src 'self'; script-src 'self'; connect-src 'self'",
 'Cache-Control':'no-store',
 'Referrer-Policy':'no-referrer',
 'X-Content-Type-Options':'nosniff',
 'Permissions-Policy':'camera=(), microphone=(), geolocation=()'
 });
}
export function classifyFreeTierEvidenceV068(evidence){
 if(!keys(evidence,['access','workers','d1Reads','d1Writes','d1Storage','githubActions','oracle','checkedAtUtc']))fail();
 const dimensions=['access','workers','d1Reads','d1Writes','d1Storage','githubActions','oracle'];
 if(typeof evidence.checkedAtUtc!=='string'||!Number.isFinite(Date.parse(evidence.checkedAtUtc))||!evidence.checkedAtUtc.endsWith('Z'))fail();
 const state=dimensions.every(k=>evidence[k]===true)?'REQUIRES_MANUAL_REVIEW':'UNVERIFIED_FREE_CAPACITY';
 // Evidence of measurements is not itself proof of sufficient quota or permission to deploy.
 return Object.freeze({state,canDeploy:false,canSpend:false,missing:Object.freeze(dimensions.filter(k=>evidence[k]!==true))});
}
export const STAGING_V068_ROUTES=paths;
