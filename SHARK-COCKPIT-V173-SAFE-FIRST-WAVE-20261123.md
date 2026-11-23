# REMURA D — v1.73 LAB, first-wave mainline candidate
**23 novembre 2026 · 22:17 CET · Europe/Rome · NESSUN MERGE/DEPLOY**
Base `main@4f8d8a707789eec29686a1568c4b8441e4c7d684`.

Questa variante web-first aggiunge i moduli Cockpit v1.71 già verificati in LAB, una nuova pagina realmente navigabile e un solo collegamento dalla Home. **Non modifica nav.js, sw.js, Splash, Oracle, Mac/Codex, collector, Contributors, COT core, CVD o prezzi A+B.**

Problema risolto in modo sostanziale: la v1.72 tentava di aggiornare il banner condiviso e la cache root, incontrando i vincoli di release legacy e la custodia storica v1.58. Qui i componenti legacy restano realmente immutati (blob identici a main); il nuovo Cockpit ha timbro v1.73 proprio e il banner delle sole pagine modificate viene allineato durante DOMContentLoaded. Non alterare o disattivare i test legacy.

**Limiti espliciti:** il vecchio SW v1.64 resta operativo sulle pagine precedenti, quindi il Cockpit web-first richiede rete e non è dichiarato compatibile con uso offline/installazione PWA. Questa è una prima ondata online; la cache PWA v1.72.1 ha codice pronto su un altro ramo, ma la distribuzione richiede la gestione coordinata dei release gate con Mac. Nessun dato CFTC viene inventato e nessun invio di trading è attivo.

**Gate residui:** CI specifica + tre suite PR globali sullo SHA effettivo, prova Safari iPhone su hosting autorizzato, backup/rollback e futura gestione SW approvata con Mac, integrazione fattori B e risultati scientifici A solo quando reali. Non sostituisce la PR #113 fino all'esito integrato.


## 23/11/2026, 22:20 CET — Correzione Splash v1.73.1 e CI
La prima proposta v1.73 `df6f326f` ha FALLITO due CI della PR #114: Splash e Insights richiedono che il tag `<script src="./splash.js?v=164"></script>` segua IMMEDIATAMENTE `<body>`; il timbro aggiunto prima dello script lo aveva spostato. Non è un falso positivo: testavano un reale contratto di avvio.

Corretto con commit `878a58b526c84979187dfc6d6e3835b51629908c`:
- Script splash nuovamente immediatamente dopo il tag body, senza modificarne un byte.
- Timbratura progressiva v1.73.1 / 23/11/2026 22:20 CET nelle due pagine cambiate (Home e Cockpit); il banner condiviso solo su queste pagine viene aggiornato da una callback DOMContentLoaded, senza modificare `nav.js`.
- `nav.js` e `sw.js` **restano identici a main**: è una web-first release, non una promessa offline.
- CI aggiornate **SUCCESS**: v1.73 compatibility run `45268730798`, Splash run `45268742108`, Insights run `45268742168`. Non ritestare suite storiche già superate se il codice resta identico.
- PR #114 resta **Draft**, PR #113 rimane Draft e non va fusa. Nessun deploy/merge o Cloudflare Worker/DB coinvolto.

**Residuo**: prova visiva su Safari con HTML portabile v1.72 disponibile nel precedente artifact (stessi moduli Cockpit), e poi collaudo end-to-end del v1.73.1 tramite un URL di staging dopo autorizzazione; conservazione backup e rollback Mac, controllo compatibilità con A+B e produzione. Prima del merge va controllato il SHA corrente di main.
