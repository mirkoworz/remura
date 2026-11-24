const root = new URL(self.registration.scope);
const cachePrefix = 'remura-lab:' + encodeURIComponent(root.href) + ':';
const releaseCache = cachePrefix + 'v1.80';
const appDocument = new URL('index.html', root);
const releaseFiles = [
  'index.html',
  'app.mjs',
  'experience.mjs',
  'markets.mjs',
  'retail-history.mjs',
  'pwa.mjs',
  'remura.css',
  'manifest.webmanifest',
  'assets/app-icon-180.png',
  'assets/app-icon-192.png',
  'assets/app-icon-512.png',
  'assets/experience/intro.css',
  'assets/experience/smf.webp',
  ...Array.from({ length: 9 }, (_, index) => `assets/experience/frame-${index}.webp`),
  'data/cot-b223.json',
  'data/myfxbook-latest.json',
  'data/myfxbook-history.json',
];
const releaseUrls = new Set(releaseFiles.map(path => new URL(path, root).href));

self.addEventListener('install', event => {
  // Fetch a complete release before activation. Keep old pages on their own worker until they close.
  const requests = [...releaseUrls].map(url => new Request(url, {
    cache: 'reload',
    mode: 'same-origin',
    redirect: 'error',
  }));
  event.waitUntil(caches.open(releaseCache).then(cache => cache.addAll(requests)));
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys
      .filter(key => key.startsWith(cachePrefix) && key !== releaseCache)
      .map(key => caches.delete(key)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== root.origin) return;

  const navigation = request.mode === 'navigate';
  const shellNavigation = navigation && (
    url.pathname === root.pathname || url.pathname === appDocument.pathname
  );
  if (navigation ? !shellNavigation : !releaseUrls.has(url.href)) return;
  const key = shellNavigation ? appDocument.href : url.href;
  event.respondWith((async () => {
    const response = await caches.match(key, { cacheName: releaseCache });
    return response || fetch(request);
  })());
});
