/* REMURA shark/remora launch splash: only PWA start page; no broker or billable API calls. */
(() => {
  "use strict";
  const ownOrigin = (() => {
    try { return document.referrer && new URL(document.referrer).origin === location.origin; }
    catch { return false; }
  })();
  // Navigating back to Home from within REMURA must not replay the splash.
  if (ownOrigin) return;
  const reduced = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const MIN_MS = reduced ? 180 : 1850;
  const CHECK_TIMEOUT_MS = 1100;
  const sharkSvg = `<svg viewBox="0 0 240 104" aria-hidden="true" focusable="false" width="100%" height="100%">
    <defs><linearGradient id="rmSharkPaint" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#a3e5e9"/><stop offset=".72" stop-color="#448ca8"/><stop offset="1" stop-color="#1e466d"/></linearGradient></defs>
    <path fill="url(#rmSharkPaint)" d="M19 53L0 25l2 32L0 91l34-24c23 4 52 6 81 5l-16 26 42-25c38-3 73-8 99-24-24-14-62-22-95-23L97 0l14 28c-30 0-60 7-86 17Z"/>
    <path fill="#c7edf0" d="M112 59c43 2 91-1 128-10-17 21-67 32-112 29Z"/><circle cx="193" cy="39" r="4" fill="#062638"/>
    <path d="M168 44l-5 17m-7-17-4 17m-7-17-4 17" stroke="#10455d" stroke-width="2.5" stroke-linecap="round"/>
    </svg>`;
  const remoraSvg = `<svg viewBox="0 0 110 58" aria-hidden="true" focusable="false" width="100%" height="100%">
    <path fill="#8ff5da" d="M3 29c18-20 46-24 74-12l25-13-5 25 5 25-25-13C42 54 18 44 3 29Z"/>
    <path fill="#43cdb9" d="M3 29c18 8 52 13 74 12 0 0-28 12-55 3Z"/><circle cx="21" cy="25" r="3" fill="#053b48"/>
    <path d="M37 15h28m-26 5h25" stroke="#0c817e" stroke-width="3" stroke-linecap="round"/>
    </svg>`;

  const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
  async function pingExistingHealth() {
    if (!/^https?:$/.test(location.protocol)) return {ok:false,reason:"anteprima locale"};
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), CHECK_TIMEOUT_MS);
    try {
      const response = await fetch("./private-api/health", {
        cache:"no-store", credentials:"same-origin", signal:controller.signal,
        headers:{"Accept":"application/json"}
      });
      if (!response.ok) return {ok:false,reason:"server non disponibile"};
      const contentType = response.headers.get("content-type") || "";
      if (!contentType.includes("json")) return {ok:false,reason:"risposta inattesa"};
      const payload = await response.json();
      if (!payload || typeof payload !== "object") return {ok:false,reason:"risposta non valida"};
      return {ok:true};
    } catch {
      return {ok:false,reason:"server non raggiungibile"};
    } finally {
      clearTimeout(timeout);
    }
  }
  function boot() {
    if (document.getElementById("rm-splash")) return;
    const splash = document.createElement("div");
    splash.id = "rm-splash";
    splash.setAttribute("role","status");
    splash.setAttribute("aria-label","REMURA: caricamento dell'applicazione");
    splash.innerHTML = `
      <div class="rm-splash-panel">
        <div class="rm-splash-overline">Avvio sistema · Segui gli squali</div>
        <div class="rm-splash-art" aria-label="Mascotte finanziaria REMURA">
          <img src="./splash-mascot.webp" alt="Mascotte REMURA: investitore con tablet e grafici" width="240" height="240" loading="eager" decoding="async">
        </div>
        <h1 class="rm-splash-logo">Remura<span>·</span></h1>
        <div class="rm-splash-release"></div>
        <div class="rm-splash-ocean" aria-hidden="true">
          <div class="rm-splash-shark">${sharkSvg}</div>
          <div class="rm-splash-fish">${remoraSvg}</div>
        </div>
        <div class="rm-splash-progress-wrap">
          <div class="rm-splash-progress-track" role="progressbar" aria-label="Avanzamento avvio" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0">
            <div class="rm-splash-progress-fill"></div>
          </div>
          <div class="rm-splash-progress-meta"><span>Preparazione interfaccia</span><span class="rm-splash-percent">0%</span></div>
        </div>
        <p class="rm-splash-state" aria-live="polite">Avvio REMURA…</p>
        <p class="rm-splash-note">Il caricamento verifica solo il server interno; i dati di mercato vanno controllati nelle rispettive schede.</p>
      </div>`;
    document.body.append(splash);
    const bar=splash.querySelector("[role=progressbar]");
    const fish=splash.querySelector(".rm-splash-fish");
    const status=splash.querySelector(".rm-splash-state");
    const stage=splash.querySelector(".rm-splash-progress-meta span");
    const percent=splash.querySelector(".rm-splash-percent");
    const release=document.getElementById("rm-release");
    splash.querySelector(".rm-splash-release").textContent =
      release ? release.textContent : "Versione e data visibili nel banner dell'app";
    let progress=0,closed=false;
    function update(value,message) {
      if(closed)return;
      progress=Math.max(progress,Math.min(value,100));
      splash.style.setProperty("--rm-progress",progress+"%");
      splash.style.setProperty("--rm-fish-left",(84-(progress/100)*53)+"%");
      percent.textContent=progress+"%";
      bar.setAttribute("aria-valuenow",String(progress));
      stage.textContent=message;
    }
    function close() {
      if(closed)return;
      closed=true;
      splash.classList.add("rm-splash-exit");
      setTimeout(() => splash.remove(),reduced?0:340);
    }
    update(20,"Interfaccia avviata");
    // Only one GET to an existing same-origin health endpoint. No scans or provider calls.
    const health = pingExistingHealth().then(result => {
      update(82,result.ok?"Server interno raggiungibile":"Server: controllo non riuscito");
      status.textContent=result.ok?"Preparazione dashboard…":"I dati potrebbero non essere disponibili.";
      return result;
    });
    Promise.all([health,wait(MIN_MS)]).then(([result]) => {
      update(100,"Avvio completato");
      fish.classList.add("rm-splash-attached");
      status.textContent=result.ok?"Squali individuati. Si parte! 🦈":"Interfaccia pronta · verifica la connessione";
      setTimeout(close,reduced?80:420);
    }).catch(close);
    // Never trap the user on a splash when unexpected JS or network failures occur.
    setTimeout(close,4500);
    window.addEventListener("pagehide",close,{once:true});
  }
  if (document.readyState==="loading") document.addEventListener("DOMContentLoaded",boot,{once:true});
  else boot();
})();
