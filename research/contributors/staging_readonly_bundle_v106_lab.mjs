// REMURA Contributors v1.06 LAB — 24/11/2026 11:09 CET (Europe/Rome)
// Derived from pinned b49de0afe389ac37a14695fb3d177f0c92679937; no deployment or enrollment. No network dependencies.
// Exact eight GET routes; legacy write modules excluded. Keep STAGING_ENABLED=DISABLED.
const PACKAGE_ROUTES=new Set(["/owner/","/owner/levels/","/contributors/","/contributors/levels/","/owner/contributors_private_recovery_v076_lab.css","/owner/levels/contributors_private_levels_v076_lab.css","/contributors/contributors_private_recovery_v076_lab.css","/contributors/levels/contributors_private_levels_v076_lab.css"]);
const accessBinding=(()=>{
// REMURA Contributors v0.31 LAB — 16/11/2026 09:08 CET
// Offline candidate; no fetch handler, no env binding/config change, no enrollment endpoint.
// Direct Access-authenticated Worker context only. An env secret must be independently provisioned.
const AUD=/^[a-f0-9]{64}$/, ACCOUNT=/^[a-f0-9]{32}$/;
const UUID=/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/;
const EMAIL=/^[^\s@\u0000-\u001f\u007f-\u009f]{1,64}@[^\s@\u0000-\u001f\u007f-\u009f]{1,189}$/;
const HEX=/^[a-f0-9]{64}$/;
const deny=()=>Error("access_denied");
const hex=b=>Array.from(new Uint8Array(b),x=>x.toString(16).padStart(2,"0")).join("");
async function accessBinding(ctx,env,expected=undefined){
 try{
  if(env?.STAGING_ENABLED!=="D1_CANDIDATE"||typeof env.ACCESS_AUD!=="string"||!AUD.test(env.ACCESS_AUD)||
     typeof env.ACCESS_ACCOUNT!=="string"||!ACCOUNT.test(env.ACCESS_ACCOUNT)||
     typeof env.IDENTITY_HMAC_KEY!=="string"||!HEX.test(env.IDENTITY_HMAC_KEY)||/^0+$/.test(env.IDENTITY_HMAC_KEY))throw deny();
  const access=ctx?.access;
  if(!access||access.aud!==env.ACCESS_AUD||typeof access.getIdentity!=="function")throw deny();
  const i=await access.getIdentity();
  if(!i||i.account_id!==env.ACCESS_ACCOUNT||typeof i.user_uuid!=="string"||!UUID.test(i.user_uuid)||
     typeof i.email!=="string"||!EMAIL.test(i.email)||i.service_token_status!==false||
     (i.service_token_id!==undefined&&i.service_token_id!==null&&i.service_token_id!==""))throw deny();
  const key=await crypto.subtle.importKey("raw",Uint8Array.from(env.IDENTITY_HMAC_KEY.match(/../g),x=>parseInt(x,16)),{name:"HMAC",hash:"SHA-256"},false,["sign"]);
  const tag=async (domain,value)=>hex(await crypto.subtle.sign("HMAC",key,new TextEncoder().encode(JSON.stringify(["remura-contributors-v1",env.ACCESS_ACCOUNT,env.ACCESS_AUD,domain,value]))));
  const actor=Object.freeze({subject:await tag("uuid",i.user_uuid),email_tag:await tag("email",i.email)});
  if(expected!==undefined&&(!expected||expected.subject!==actor.subject||expected.email_tag!==actor.email_tag))throw deny();
  return actor;
 }catch{throw deny();}
}

return accessBinding;
})();
const profile=(()=>{
const SQL=Object.freeze({profile:"SELECT 'OWNER' AS role,'owner' AS slot,s.write_enabled,s.read_enabled,s.recovery_enabled FROM lab_owner i CROSS JOIN lab_state s WHERE i.id=1 AND i.subject=? AND i.email_tag=? AND i.revoked=0 AND s.id=1 AND (s.write_enabled=1 OR s.read_enabled=1 OR s.recovery_enabled=1) UNION ALL SELECT 'CONTRIBUTOR',i.slot,s.write_enabled,s.read_enabled,0 FROM lab_identities i CROSS JOIN lab_state s WHERE i.subject=? AND i.email_tag=? AND i.revoked=0 AND s.id=1 AND (s.write_enabled=1 OR s.read_enabled=1)"});
const deny=()=>Error("denied");
async function rows(db,sql,args,max){
 const x=await db.withSession("first-primary").prepare(sql).bind(...args).all();
 if(x?.success!==true||x.meta?.served_by_primary!==true||!Array.isArray(x.results)||x.results.length>max)throw deny();
 return x.results;
}
async function profile(ctx,env,expected){
 const a=await accessBinding(ctx,env,expected),db=env.CONTRIBUTORS_DB;
 const x=await rows(db,SQL.profile,[a.subject,a.email_tag,a.subject,a.email_tag],1);
 if(x.length!==1)throw deny();
 const r=x[0];
 if(!((r.role==="OWNER"&&r.slot==="owner")||(r.role==="CONTRIBUTOR"&&["friend-a","friend-b"].includes(r.slot)&&r.recovery_enabled===0))||
   ![r.write_enabled,r.read_enabled,r.recovery_enabled].every(v=>v===0||v===1))throw deny();
 return {role:r.role,can_write:r.write_enabled===1,can_read:r.read_enabled===1,can_recover:r.recovery_enabled===1};
}

return profile;
})();
const privateAssetFilesV096=Object.freeze({"contributors_recovery_v078_private_lab.html":"READONLY_RENDER_REQUIRED","contributors_owner_recovery_v078_private_lab.html":"READONLY_RENDER_REQUIRED","contributors_levels_v096_lab.html":"READONLY_RENDER_REQUIRED","owner_levels_v078_lab.html":"READONLY_RENDER_REQUIRED","contributors_private_recovery_v076_lab.css":"/* REMURA Contributors v0.76 LAB · 21/11/2026 15:57 CET */\n:root{font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#e9fbf9;background:#061018;font-synthesis:none}\n*{box-sizing:border-box}html{color-scheme:dark}body{margin:0;min-height:100vh;background:radial-gradient(ellipse at 80% -15%,#1b5051 0,transparent 42%),linear-gradient(150deg,#061018 8%,#09212b 62%,#061018)}\n.version{position:relative;z-index:5;padding:11px max(16px,env(safe-area-inset-left));background:#042d31;color:#8af3d8;border-bottom:1px solid #277469;font-size:.71rem;letter-spacing:.06em;font-weight:650}\n.shell{width:min(1200px,100%);margin:auto;padding:0 max(17px,env(safe-area-inset-left))}\n.masthead{padding:26px 0 22px;display:flex;align-items:center;justify-content:space-between;gap:15px;border-bottom:1px solid #28434a}.brand{font-weight:850;letter-spacing:.23em;font-size:1.12rem}.fin{font-size:1.5rem;color:#77f2d6}.subbrand{color:#83b8bb;letter-spacing:.075em;font-size:.61rem}.laboratory{font-size:.64rem;letter-spacing:.06em;color:#e6ba7e;border:1px solid #8f775a;border-radius:8px;padding:9px 11px;text-align:center}\nmain{padding:48px 0 52px}.eyebrow{color:#85e9ce;letter-spacing:.24em;font-size:.72rem;font-weight:850;display:flex;gap:18px;align-items:center}.line{height:1px;background:#397a73;flex:1;max-width:65px}h1{font-size:clamp(2.25rem,5vw,4.6rem);line-height:1.08;letter-spacing:-.035em;margin:13px 0 20px;font-weight:790}h1 em{font-style:normal;color:#85e9ce}.lead{max-width:690px;color:#aacbce;line-height:1.65;margin:0 0 35px;font-size:1rem}\n.cards{display:grid;grid-template-columns:minmax(0,1.03fr) minmax(0,.97fr);gap:19px}.panel{background:linear-gradient(155deg,rgba(20,56,61,.92),rgba(7,25,34,.98));border:1px solid #35636a;border-radius:22px;padding:clamp(21px,3vw,32px);box-shadow:0 22px 55px #0004;min-width:0}.hero{position:relative;overflow:hidden}.hero:before{content:'';position:absolute;right:-70px;top:-75px;border:1px solid #417f7425;border-radius:50%;width:250px;height:250px;box-shadow:0 0 0 55px #50aa8720,0 0 0 100px #3e998614;pointer-events:none}.heading{display:flex;align-items:center;gap:12px;margin-bottom:29px}.heading h2{font-size:1.02rem;margin:0;line-height:1.4}.number{background:#77e3cb;color:#073532;padding:8px 9px;font-size:.72rem;font-weight:900;border-radius:9px}.dot{margin-left:auto;width:9px;height:9px;border-radius:50%;background:#74efd1;box-shadow:0 0 18px #65ddc7}\n.kicker{font-weight:800;font-size:.7rem;letter-spacing:.16em;color:#96d1c6}.state-code{width:fit-content;max-width:100%;overflow-wrap:anywhere;border:1px solid #39746d;border-radius:8px;color:#91e6d3;background:#0b3539;padding:9px 12px;font-size:.74rem;font-weight:850;letter-spacing:.055em}.hero h3{font-size:clamp(1.5rem,3vw,2.2rem);margin:25px 0 10px}.hero p#recoverySummary{color:#b6d4d4;line-height:1.6;min-height:4.5rem}.lock{border:1px solid #977647;border-radius:12px;padding:13px 15px;background:#47361b50;color:#f2d19d;font-size:.77rem;line-height:1.55;font-weight:750}\n.actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:25px}button{font:inherit;min-height:46px;border:0;border-radius:10px;background:#81ead0;color:#06312e;font-size:.87rem;font-weight:850;padding:12px 16px;cursor:pointer}button.outline{background:transparent;border:1px solid #5f9995;color:#d2f4ec}button:disabled{opacity:.48;cursor:not-allowed}button:focus-visible{outline:3px solid #c5ffef;outline-offset:3px}button.quiet{background:transparent;border:1px solid #4d7279;color:#bad5d6;margin:26px 0 0;font-size:.8rem}.helper,.privacy{font-size:.76rem;color:#8fb8bb;line-height:1.6}.helper{margin-bottom:0}\n.results{display:flex;flex-direction:column}.entries{list-style:none;margin:0;padding:0;display:grid;gap:10px;min-height:130px}.entries li{border:1px solid #38636a;background:#0a2933;border-radius:13px;padding:14px;display:grid;gap:9px;overflow-wrap:anywhere}.entries strong{font-size:.86rem}.entries small{color:#8fbab8;font-size:.73rem;line-height:1.5}.empty-note{font-size:.77rem;color:#94b6ba;line-height:1.6;border-top:1px solid #2c4c52;margin-top:16px;padding-top:17px}.results button{margin-top:20px;align-self:flex-start}.hidden-control{display:none}\n.flow{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:22px}.flow>div{padding:15px 12px;background:#0d2730;border:1px solid #2a4650;border-radius:11px;display:grid;gap:8px}.flow b{color:#8df0d2;font-size:.8rem}.flow span{color:#c2d9d7;font-size:.74rem;line-height:1.4}.privacy{max-width:780px;margin-top:17px}footer{border-top:1px solid #2a444d;padding:22px 0 40px;font-size:.7rem;color:#7c9eaa}\n@media(max-width:780px){main{padding:29px 0 36px}.cards{grid-template-columns:1fr}.masthead{padding:19px 0}.subbrand{display:block;margin:3px 0 0 27px}.laboratory{max-width:126px;font-size:.58rem}.flow{grid-template-columns:repeat(2,minmax(0,1fr))}.panel{border-radius:18px}.lead{font-size:.91rem}}\n@media(max-width:400px){h1{font-size:2.23rem}.version{font-size:.64rem}.brand{font-size:.96rem}.actions{display:grid}.actions button{width:100%}.flow{gap:8px}.flow>div{padding:12px}}\n@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation:none!important;transition:none!important;scroll-behavior:auto!important}}\n\n/* v0.76 · 21/11/2026 15:57 CET — visible role-limited navigation */\n.private-nav{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0 24px}.private-nav a{display:inline-flex;align-items:center;justify-content:center;min-height:46px;padding:10px 16px;border:1px solid #4e998d;border-radius:12px;color:#b7ffeb;background:#102b35;font-weight:700;text-decoration:none;text-align:center}.private-nav a:focus-visible{outline:3px solid #7cf4d4;outline-offset:3px}.private-nav .nav-note{width:100%;font-size:12px;opacity:.85}\n","contributors_private_levels_v076_lab.css":"/* REMURA Contributors v0.76 LAB · 21/11/2026 15:57 CET */\n/* REMURA Contributors v0.74 LAB — 21/11/2026 15:36 CET · private levels candidate */\n\n:root{color-scheme:dark;--bg:#07121a;--panel:#101f2a;--panel2:#132531;--outline:#203642;--ink:#e8f4f3;--muted:#8ba7ae;--aqua:#69edca;--orange:#e2b97c;--radius:19px}*{box-sizing:border-box}body{margin:0;font:16px/1.45 Inter,-apple-system,BlinkMacSystemFont,\"Segoe UI\",sans-serif;color:var(--ink);background:var(--bg)}main{max-width:600px;margin:auto;padding:22px 14px calc(44px + env(safe-area-inset-bottom))}.release{background:#102c35;border-bottom:1px solid #39655d;color:#b9f8df;font-size:11px;font-weight:700;text-align:center;padding:6px 10px;padding-top:max(6px,env(safe-area-inset-top))}.brand{display:flex;align-items:center;gap:12px;color:var(--aqua);font-size:13px;font-weight:850;letter-spacing:.12em}.brand-mark{width:43px;height:43px;border-radius:14px;display:grid;place-items:center;background:linear-gradient(140deg,#163e45,#10303a);border:1px solid #2e6970}.brand-mark svg{width:28px;height:28px}small{color:var(--muted)}h1{font-size:32px;letter-spacing:-.045em;margin:18px 0 4px}h2{font-size:19px;letter-spacing:-.02em}p{line-height:1.5}.panel{background:linear-gradient(180deg,#10222e,#101e29);border:1px solid var(--outline);border-radius:var(--radius);padding:18px;margin:18px 0;box-shadow:0 12px 34px #00000016}label{display:block;font-weight:650;margin:15px 0 7px}input,select,textarea,button{font:inherit;width:100%;border:1px solid #37606a;border-radius:12px;padding:12px;min-height:46px;color:var(--ink);background:#102b35}textarea{resize:vertical;min-height:80px}button{background:var(--aqua);color:#052c28;font-weight:800;cursor:pointer;margin-top:16px;border:0}button.secondary{background:#18313a;border:1px solid #2b4b55;color:#d6eff0}button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible{outline:2px solid var(--aqua);outline-offset:3px}.notice,.tag{color:var(--orange)}.status{min-height:28px;margin-top:12px}.receipt{overflow-wrap:anywhere;border-top:1px solid var(--outline);padding:12px 0;line-height:1.6}.tag{font-size:13px}[hidden]{display:none!important}\n\nbutton:disabled{opacity:.5;cursor:not-allowed}.muted{color:var(--muted)}.receipt strong{color:var(--aqua)}.receipt pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}.release{position:sticky;top:0;z-index:1}\n\n.panel .notice{display:block;margin-bottom:8px}.receipt{overflow-wrap:anywhere}select{max-width:100%}@media(max-width:360px){.panel{padding:14px}main{padding-inline:12px}}\n\n/* v0.76 · 21/11/2026 15:57 CET — private navigation and exit */\n.private-nav{display:flex;flex-wrap:wrap;gap:10px;margin:12px 0 22px}.private-nav a{color:#b7ffeb;font-weight:750;text-decoration:none;background:#15333d;padding:11px 14px;min-height:46px;border-radius:12px;border:1px solid #356d71;display:inline-flex;align-items:center}.private-nav a:focus-visible{outline:3px solid #69edca;outline-offset:3px}.private-nav .nav-note{flex-basis:100%;font-size:12px;color:#8ba7ae}\n"});
const REMURA_V096_ALLOWED_STATIC=Object.freeze({areas:Object.freeze({RECOVERY:Object.freeze(["contributors_private_recovery_v076_lab.css"]),LEVELS:Object.freeze(["contributors_private_levels_v076_lab.css"])})});
const privateReadOnlyStagingV101=(()=>{
// REMURA Contributors v1.01 LAB — 23/11/2026 Europe/Rome.
// NEW, read-only, direct Access Worker staging candidate. NEVER deployed.
// Purpose: authenticate GET pages/assets using real ctx.access + D1 profile;
// every POST/PUT/DELETE is denied. No default fetch export, no Worker setup.

const ROUTES=Object.freeze({
  '/contributors/':{role:'CONTRIBUTOR',area:'RECOVERY',file:'contributors_recovery_v078_private_lab.html'},
  '/contributors/levels/':{role:'CONTRIBUTOR',area:'LEVELS',file:'contributors_levels_v096_lab.html'},
  '/owner/':{role:'OWNER',area:'RECOVERY',file:'contributors_owner_recovery_v078_private_lab.html'},
  '/owner/levels/':{role:'OWNER',area:'LEVELS',file:'owner_levels_v078_lab.html'}
});
const HEADERS=Object.freeze({
  'Cache-Control':'no-store, max-age=0',
  'X-Content-Type-Options':'nosniff',
  'Referrer-Policy':'no-referrer',
  'X-Frame-Options':'DENY',
  'Cross-Origin-Resource-Policy':'same-origin',
  'Permissions-Policy':'camera=(), microphone=(), geolocation=()',
  'Content-Security-Policy':"default-src 'none'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'; form-action 'none'; style-src 'self'; script-src 'self'; connect-src 'self'"
});
const denied=()=>new Response('{"error":"denied"}',{status:403,headers:{
  ...HEADERS,'Content-Type':'application/json; charset=utf-8'
}});
function goodOrigin(origin){
  if(typeof origin!=='string'||origin.length>250)return false;
  try{const u=new URL(origin);
    return u.protocol==='https:'&&u.origin===origin&&u.pathname==='/'&&!u.search&&!u.hash&&!u.username&&!u.password;
  }catch{return false}
}
function fileFor(path){
  const page=ROUTES[path];
  if(page)return page;
  const m=/^\/(owner|contributors)\/(levels\/)?([a-z0-9_.-]+)$/.exec(path);
  if(!m)return null;
  const role=m[1]==='owner'?'OWNER':'CONTRIBUTOR', area=m[2]?'LEVELS':'RECOVERY',file=m[3];
  if(!REMURA_V096_ALLOWED_STATIC.areas[area].includes(file))return null;
  if(['owner_level_audit_ui_v077_lab.mjs','owner_level_integrity_ui_v078_lab.mjs'].includes(file)
      &&!(role==='OWNER'&&area==='LEVELS'))return null;
  return {role,area,file};
}
function validProfile(p,expected){
  // Read-only pilot: neither role needs mutation or recovery capability.
  return p&&p.role===expected&&p.can_read===true&&p.can_write===false&&p.can_recover===false;
}
function mime(file){
  return file.endsWith('.html')?'text/html; charset=utf-8':
    file.endsWith('.css')?'text/css; charset=utf-8':'text/javascript; charset=utf-8';
}
function createStagingReadOnlyV101({authenticate,profileRead,assetFiles}){
  if(typeof authenticate!=='function'||typeof profileRead!=='function'||
    !assetFiles||typeof assetFiles!=='object'||Array.isArray(assetFiles))throw Error('V101_BAD_DEPENDENCIES');
  return async function stagingReadOnly(req,env,ctx){
    try{
      if(env?.PRIVATE_WORKER_V078!=='STAGING_AUTHENTICATED_READONLY'||
        env?.STAGING_ENABLED!=='D1_CANDIDATE'||
        env?.CONTRIBUTORS_STAGE_READONLY!=='EXPLICIT_STAGING_ONLY'||
        !goodOrigin(env?.STAGING_ORIGIN)||typeof env?.CONTRIBUTORS_DB?.prepare!=='function')return denied();
      if(!(req instanceof Request)||req.method!=='GET'||req.body!==null)return denied();
      const u=new URL(req.url);
      if(u.origin!==env.STAGING_ORIGIN||req.url!==u.origin+u.pathname)return denied();
      if(!ctx?.access||ctx.access.aud!==env.ACCESS_AUD||
        typeof ctx.access.getIdentity!=='function')return denied();
      const route=fileFor(u.pathname);
      if(!route||!Object.hasOwn(assetFiles,route.file)||
        typeof assetFiles[route.file]!=='string'||assetFiles[route.file].length===0||
        assetFiles[route.file].length>120000)return denied();
      const actor=await authenticate(ctx,env);
      if(!actor||!/^[a-f0-9]{64}$/.test(actor.subject??'')||
        !/^[a-f0-9]{64}$/.test(actor.email_tag??''))return denied();
      // Always use a fresh D1 profile: a revoked contributor with an open Safari tab
      // must fail on the next GET. No request-shared cache or client role headers.
      const p=await profileRead(ctx,env,actor);
      if(!validProfile(p,route.role))return denied();
      return new Response(assetFiles[route.file],{status:200,headers:{
        ...HEADERS,'Content-Type':mime(route.file)
      }});
    }catch{return denied()}
  };
}
// This is NOT an active Worker entrypoint. Real Access/D1 data have not been
// verified, and no configuration or deploy is part of the v1.01 checkpoint.
const privateReadOnlyStagingV101=createStagingReadOnlyV101({
  authenticate:accessBinding,profileRead:profile,assetFiles:privateAssetFilesV096
});
const V101_STATE=Object.freeze({
  version:'1.01',mode:'INERT_LAB',getOnly:true,allWritesDenied:true,
  requiresDirectAccess:true,requiresFreshD1Profile:true,
  stagingAuthorized:false,accessRuntimeVerified:false,safariVerified:false,
  deployAuthorized:false,pilotAllowed:false
});

return privateReadOnlyStagingV101;
})();
const privateStagingSafeReadV103=(()=>{
// REMURA Contributors v1.03 LAB · 23/11/2026 23:05 CET (Europe/Rome).
// Non-interactive presentation after real Access + D1 gate v1.01.
// Does not replace authentication or bypass role checks: authenticated GET only.
// Prevents accidental submission and client-side attempts at locked POST APIs.
// NO Cloudflare activation, Secret, database write, or deployment in this module.
const PAGES=Object.freeze({
 '/contributors/':Object.freeze({title:'Consultazione collaboratore',role:'CONTRIBUTOR',
   css:'./contributors_private_recovery_v076_lab.css',
   message:'Consultazione autenticata. Le proposte di livelli non sono abilitate in questa prima prova.',
   link:'/contributors/levels/',linkLabel:'Verifica area livelli'}),
 '/contributors/levels/':Object.freeze({title:'I tuoi livelli',role:'CONTRIBUTOR',
   css:'./contributors_private_levels_v076_lab.css',
   message:'Le proposte e le ricevute saranno abilitate in una fase successiva, dopo autorizzazione e verifica dei registri reali.',
   link:'/contributors/',linkLabel:'Torna alla consultazione'}),
 '/owner/':Object.freeze({title:'Pannello OWNER',role:'OWNER',
   css:'./contributors_private_recovery_v076_lab.css',
   message:'Accesso OWNER in sola lettura. Approvazione, revoca e audit attivi solo dopo separato collaudo.',
   link:'/owner/levels/',linkLabel:'Verifica area livelli'}),
 '/owner/levels/':Object.freeze({title:'Verifica livelli OWNER',role:'OWNER',
   css:'./contributors_private_levels_v076_lab.css',
   message:'Nessun livello può essere approvato o modificato da questo staging in sola lettura.',
   link:'/owner/',linkLabel:'Torna al pannello OWNER'})
});
const DENY_HEADERS=Object.freeze({
 'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store, max-age=0',
 'X-Content-Type-Options':'nosniff'
});
const deny=()=>new Response('{"error":"denied"}',{status:403,headers:DENY_HEADERS});
// All page content is static, reviewed text. No actor data, tokens, API endpoints,
// scripts, forms or controls that might imply the ability to submit a level.
function pageHtml(p){
 return `<!doctype html>
<html lang="it">
<head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow,noarchive">
<title>REMURA Contributors v1.03 LAB · ${p.title}</title>
<link rel="stylesheet" href="${p.css}">
</head>
<body>
<div class="version" role="status">REMURA Contributors v1.03 LAB · 23/11/2026 23:05 CET (Europe/Rome) · Staging candidato, NON attivo</div>
<main class="shell">
<header class="masthead"><div class="brand">REMURA / CONTRIBUTORS</div><span class="laboratory">SOLA LETTURA · ${p.role} · LAB</span></header>
<h1>${p.title}</h1><p class="lead">${p.message}</p>
<section class="panel"><h2>Accessi e permessi</h2>
<p>La vista richiede un'identità Cloudflare Access e un ruolo attivo nel database di staging.
Non sono disponibili invii, approvazioni, modifiche o dati personali di altri utenti.</p>
<p>Questa fase verifica soltanto login, permessi di consultazione e revoca.</p></section>
<nav class="private-nav" aria-label="Navigazione privata"><a href="${p.link}">${p.linkLabel}</a></nav>
<footer>REMURA v1.03 LAB · Non pubblicato · Nessuna azione di scrittura</footer>
</main>
</body></html>`;
}
function createStagingSafeReadV103({guardedGet}){
 if(typeof guardedGet!=='function')throw Error('V103_AUTHENTICATED_READER_REQUIRED');
 return async function safeRead(req,env,ctx){
  try{
   if(!(req instanceof Request)||req.method!=='GET')return deny();
   const url=new URL(req.url);
   // Never serve client scripts in a read-only session. Every form is absent
   // from the four pages and no submit handler can be loaded from this Worker.
   if(url.pathname.endsWith('.mjs')||url.pathname.endsWith('.js'))return deny();
   const candidate=PAGES[url.pathname];
   const response=await guardedGet(req,env,ctx); // same Access/D1 checks; no new reads
   if(response?.status!==200)return response??deny();
   if(!candidate)return response; // authenticated CSS only, other paths base denies
   const headers=new Headers(response.headers);
   headers.set('Content-Type','text/html; charset=utf-8');
   headers.set('Cache-Control','no-store, max-age=0');
   headers.set('X-Robots-Tag','noindex, nofollow, noarchive');
   return new Response(pageHtml(candidate),{status:200,headers});
  }catch{return deny()}
 };
}
const privateStagingSafeReadV103=createStagingSafeReadV103({
 guardedGet:privateReadOnlyStagingV101
});
const V103_READONLY=Object.freeze({
 version:'1.03',mode:'INERT_LAB',requiresAccessAndD1:true,
 allMutationsDenied:true,scriptRequestsDenied:true,formsVisible:false,
 extraD1Reads:0,realAccessTested:false,deployAuthorized:false
});

return privateStagingSafeReadV103;
})();
const privateStagingCspV104=(()=>{
// REMURA Contributors v1.04 LAB — 24/11/2026 00:12 CET (Europe/Rome).
// Authenticated read-only Worker hardening: inert until separately authorized.
// No new API or D1 operation: delegates to v1.03, which delegates to
// v1.01 Access/D1 fail-closed guard. NEVER attaches to the public Pages site.

const PAGE_PATHS=new Set(['/owner/','/owner/levels/','/contributors/','/contributors/levels/']);
const OLD_VERSION='REMURA Contributors v1.03 LAB';
const NEW_VERSION='REMURA Contributors v1.06 LAB';
const OLD_AT='23/11/2026 23:05 CET';
const NEW_AT='24/11/2026 11:09 CET';
const STRICT_CSP="default-src 'none'; base-uri 'none'; object-src 'none'; "+
 "frame-ancestors 'none'; form-action 'none'; script-src 'none'; "+
 "connect-src 'none'; img-src 'none'; style-src 'self'; font-src 'none'";
const DENY_HEADERS=Object.freeze({
 'Content-Type':'application/json; charset=utf-8',
 'Cache-Control':'no-store, max-age=0',
 'X-Content-Type-Options':'nosniff',
 'X-Frame-Options':'DENY',
 'Content-Security-Policy':STRICT_CSP
});
const deny=()=>new Response('{"error":"denied"}',{status:403,headers:DENY_HEADERS});

function createStagingCspV104({guardedRead}){
 if(typeof guardedRead!=='function')throw Error('V104_GUARDED_READER_REQUIRED');
 return async function cspRead(request,env,ctx){
  try{
   if(!(request instanceof Request)||request.method!=='GET'||request.body!==null)return deny();
   const path=new URL(request.url).pathname;
   const response=await guardedRead(request,env,ctx);
   if(response?.status!==200)return response??deny();
   if(!PAGE_PATHS.has(path))return response; // CSS remains Access/D1 gated.
   const type=response.headers.get('Content-Type')||'';
   if(!/^text\/html(?:;|$)/i.test(type))return deny();
   const oldHtml=await response.text();
   if(oldHtml.length>20000||!oldHtml.includes(OLD_VERSION)||
     !oldHtml.includes(OLD_AT)||!oldHtml.includes('SOLA LETTURA')||
     /<(?:form|script|iframe|object|embed|input|button|base)\b/i.test(oldHtml)||
     /\son(?:click|load|error|submit)\s*=/i.test(oldHtml))
       return deny();
   const html=oldHtml.replaceAll(OLD_VERSION,NEW_VERSION)
      .replaceAll('REMURA v1.03 LAB','REMURA v1.06 LAB')
      .replaceAll(OLD_AT,NEW_AT);
   const headers=new Headers(response.headers);
   headers.delete('Content-Length');
   headers.set('Content-Type','text/html; charset=utf-8');
   headers.set('Content-Security-Policy',STRICT_CSP);
   headers.set('Cache-Control','no-store, max-age=0');
   headers.set('X-Content-Type-Options','nosniff');
   headers.set('X-Frame-Options','DENY');
   headers.set('X-Robots-Tag','noindex, nofollow, noarchive');
   headers.set('Referrer-Policy','no-referrer');
   headers.set('Cross-Origin-Resource-Policy','same-origin');
   return new Response(html,{status:200,headers});
  }catch{return deny();}
 };
}

const privateStagingCspV104=createStagingCspV104({
 guardedRead:privateStagingSafeReadV103
});
const V104_READONLY=Object.freeze({
 version:'1.04',mode:'INERT_LAB',noScripts:true,noConnections:true,
 noForms:true,cssSameOriginOnly:true,ownerContributorRoleSeparation:true,
 additionalD1Reads:0,accessRuntimeVerified:false,
 workersDeployed:false,usersCreated:false,realPilotAllowed:false
});

return privateStagingCspV104;
})();
// REMURA Contributors v1.02 LAB · 23/11/2026 Europe/Rome.
// A real Workers module entrypoint candidate for an independently approved,
// Access-protected direct Worker (no Static Assets router, no service binding).
// INERT until separately configured and deployed by the OWNER. No POST permitted.
// v1.04: deny all scripts and client connections by CSP after v1.03 role gate.
const CLOSED_HEADERS=Object.freeze({
 'Content-Type':'application/json; charset=utf-8',
 'Cache-Control':'no-store, max-age=0','X-Content-Type-Options':'nosniff'
});
const deny=()=>new Response('{"error":"staging_not_authorized"}',{status:403,headers:CLOSED_HEADERS});
function stagingReady(env,ctx){
 return env?.PRIVATE_WORKER_V078==='STAGING_AUTHENTICATED_READONLY'&&
   env?.CONTRIBUTORS_STAGE_READONLY==='EXPLICIT_STAGING_ONLY'&&
   env?.STAGING_ENABLED==='D1_CANDIDATE'&&
   typeof env?.ACCESS_AUD==='string'&&/^[a-f0-9]{64}$/.test(env.ACCESS_AUD)&&
   typeof env?.ACCESS_ACCOUNT==='string'&&/^[a-f0-9]{32}$/.test(env.ACCESS_ACCOUNT)&&
   typeof env?.IDENTITY_HMAC_KEY==='string'&&/^[a-f0-9]{64}$/.test(env.IDENTITY_HMAC_KEY)&&
   !/^0+$/.test(env.IDENTITY_HMAC_KEY)&&
   typeof env?.CONTRIBUTORS_DB?.prepare==='function'&&
   typeof env?.CONTRIBUTORS_DB?.withSession==='function'&&
   ctx?.access?.aud===env.ACCESS_AUD&&
   typeof ctx?.access?.getIdentity==='function';
}
export default {
 async fetch(req,env,ctx){
  try{
   if(!(req instanceof Request)||req.method!=='GET'||!stagingReady(env,ctx))return deny();
   if(!PACKAGE_ROUTES.has(new URL(req.url).pathname))return deny();
   return await privateStagingCspV104(req,env,ctx);
  }catch{return deny()}
 }
};
export const V102_ENTRY=Object.freeze({
 version:'1.06',mode:'INERT_DEPLOYMENT_CANDIDATE',onlyGet:true,
 directAccessRequired:true,stagingUrlConfigured:false,
 providerVerified:false,authorized:false,deployed:false,readOnlyPresentation:true,strictCsp:true
});

