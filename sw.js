/* REMURA PWA v1.72 RELEASE CANDIDATE LAB · 23/11/2026 21:17 CET (Europe/Rome).
 * Static public shell only. No API / protected endpoint fallback, no offline
 * replay of private responses, no deletion of unrelated apps' CacheStorage.
 * No runtime data is stored by this service worker.
 */
const CACHE="remura-shell-v87-v1.72-mainline-slice-lab";
const STATIC=["./","./shark-cockpit.html","./shark-cockpit.js","./shark-cockpit-core.js","./shark-evidence-core.js","./shark-evidence-ui.js","./shark-trends-core.js","./shark-trends-ui.js","./shark-focus-core.js","./shark-focus-ui.js","./shark-movers-core.js","./shark-movers-ui.js","./shark-cockpit.css","./index.html","./forex.html","./catalogo.html","./mercati.html","./statistica-squali.html","./statistica-squali.js","./statistica-squali-core.js","./dual24-core.js","./dual24-ui.js","./market-audit-core.js","./market-audit-ui.js","./case-audit-core.js","./case-audit-ui.js","./weekly-quality-core.js","./weekly-quality-ui.js","./cot-week-watch-core.js","./cot-week-watch-ui.js","./asset.html","./fonti.html","./impostazioni.html","./impostazioni.js","./resource-health.js","./resource-health.css","./stato-prezzi.html","./stato-prezzi.js","./price-status-core.js","./feed-health-core.js","./nav.js","./nav.css","./squalincome-diagnostics.js","./squalincome-freshness-core.js","./retail.css","./retail.js","./sentiment-trend-core.js","./sentiment-trend.js","./sentiment-trend.css","./insights-core.js","./cot-indices-core.js","./insights.js","./insights.css","./price-core.js","./price.js","./price.css","./sentiment-core.js","./capital-cloud-config.js","./capital-cloud.js","./sources.js","./sources.css","./manifest.webmanifest","./icon.svg","./splash.js","./splash.css","./splash-mascot.webp"];

const PUBLIC_SHELL_PATHS=new Set(STATIC.map(file=>new URL(file,self.registration.scope).pathname));
self.addEventListener("install",event=>event.waitUntil(
  caches.open(CACHE).then(cache=>cache.addAll(STATIC)).then(()=>self.skipWaiting())
));
self.addEventListener("activate",event=>event.waitUntil(
  caches.keys()
    .then(keys=>Promise.all(keys.filter(name=>
      name.startsWith("remura-shell-")&&name!==CACHE
    ).map(name=>caches.delete(name))))
    .then(()=>self.clients.claim())
));
self.addEventListener("fetch",event=>{
  const req=event.request, url=new URL(req.url);
  if(req.method!=="GET"||url.origin!==self.location.origin)return;
  // Only exact public static paths are eligible for an offline fallback.
  // Private /api, /owner, /contributors and unlisted future endpoints are
  // intentionally not intercepted, even when another cache contains them.
  if(!PUBLIC_SHELL_PATHS.has(url.pathname))return;
  event.respondWith(fetch(req).catch(async()=>{
    const shell=await caches.open(CACHE);
    return (await shell.match(req,{ignoreSearch:true}))||Response.error();
  }));
});
