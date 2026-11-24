const appRoot = new URL('./', import.meta.url);
const workerUrl = new URL('sw.js', appRoot);
const appDocument = new URL('index.html', appRoot);

export async function mountPwa(statusElement) {
  const setStatus = message => {
    if (statusElement) statusElement.textContent = message;
  };
  const page = new URL(location.href);
  if (page.origin !== appRoot.origin ||
      (page.pathname !== appRoot.pathname && page.pathname !== appDocument.pathname)) return;

  const workers = navigator.serviceWorker;
  if (!workers) {
    setStatus('La copia offline richiede un browser compatibile e HTTPS oppure un indirizzo locale.');
    return;
  }
  const controlled = () => workers.controller?.scriptURL === workerUrl.href;
  setStatus(controlled() ? 'Copia offline disponibile su questo dispositivo.' : 'Preparazione della copia offline…');

  try {
    const registration = await workers.register(workerUrl, { scope: appRoot.href, updateViaCache: 'none' });
    if (registration.scope !== appRoot.href) {
      setStatus('Copia offline non disponibile.');
      return;
    }
    workers.addEventListener('controllerchange', () => {
      if (controlled()) setStatus('Copia offline disponibile su questo dispositivo.');
    });
    if (controlled()) setStatus('Copia offline disponibile su questo dispositivo.');

    function watchInstall() {
      const installing = registration.installing;
      if (!installing) return;
      installing.addEventListener('statechange', () => {
        if (installing.state === 'redundant' && !controlled()) setStatus('Copia offline non disponibile.');
      });
    }

    registration.addEventListener('updatefound', watchInstall);
    watchInstall();
    if (registration.active && !controlled()) {
      setStatus('Copia offline pronta. Ricarica la pagina per attivarla.');
    }
  } catch {
    if (!controlled()) setStatus('Copia offline non disponibile.');
  }
}
