/* Shell only. API CFTC is never cached as live data. */
const CACHE="remura-shell-v36-v1.21-macro-context";
const STATIC=["./","./index.html","./forex.html","./catalogo.html","./mercati.html","./asset.html","./fonti.html","./impostazioni.html","./impostazioni.js","./stato-prezzi.html","./stato-prezzi.js","./price-status-core.js","./feed-health-core.js","./nav.js","./nav.css","./retail.css","./retail.js","./sentiment-trend-core.js","./sentiment-trend.js","./sentiment-trend.css","./insights-core.js","./cot-indices-core.js","./insights.js","./insights.css","./price-core.js","./price.js","./price.css","./sentiment-core.js","./capital-cloud-config.js","./capital-cloud.js","./sources.js","./sources.css","./manifest.webmanifest","./icon.svg"];
self.addEventListener("install",event=>event.waitUntil(
  caches.open(CACHE).then(cache=>cache.addAll(STATIC)).then(()=>self.skipWaiting())
));
self.addEventListener("activate",event=>event.waitUntil(
  caches.keys().then(keys=>Promise.all(keys.filter(name=>name!==CACHE).map(name=>caches.delete(name)))).then(()=>self.clients.claim())
));
self.addEventListener("fetch",event=>{
  const url=new URL(event.request.url);
  if(url.pathname.includes("/private-api/"))return; // NEVER cache authenticated price/health responses.
  if(event.request.method!=="GET"||url.origin!==self.location.origin)return;
  event.respondWith(fetch(event.request).catch(async()=>await caches.match(event.request,{ignoreSearch:true})||Response.error()));
});
