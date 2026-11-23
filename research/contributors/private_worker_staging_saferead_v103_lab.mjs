// REMURA Contributors v1.03 LAB · 23/11/2026 23:05 CET (Europe/Rome).
// Non-interactive presentation after real Access + D1 gate v1.01.
// Does not replace authentication or bypass role checks: authenticated GET only.
// Prevents accidental submission and client-side attempts at locked POST APIs.
// NO Cloudflare activation, Secret, database write, or deployment in this module.
import {privateReadOnlyStagingV101} from './private_worker_staging_readonly_v101_lab.mjs';
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
export function createStagingSafeReadV103({guardedGet}){
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
export const privateStagingSafeReadV103=createStagingSafeReadV103({
 guardedGet:privateReadOnlyStagingV101
});
export const V103_READONLY=Object.freeze({
 version:'1.03',mode:'INERT_LAB',requiresAccessAndD1:true,
 allMutationsDenied:true,scriptRequestsDenied:true,formsVisible:false,
 extraD1Reads:0,realAccessTested:false,deployAuthorized:false
});
