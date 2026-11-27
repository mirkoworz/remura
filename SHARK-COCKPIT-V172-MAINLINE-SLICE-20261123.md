# REMURA Filone D — v1.72 MAINLINE SLICE (LAB)
**23 novembre 2026 · 21:17 CET (Europe/Rome) · NON LIVE · NESSUN MERGE**
**Base esatta**: `main@4f8d8a707789eec29686a1568c4b8441e4c7d684`.
**Origine moduli**: `feature/shark-cockpit-v171-my-sharks-iphone-20261123@6dfd56cb82c8db69522d2db17b9ed1f7f7909046`.
**Target isolato**: `feature/shark-cockpit-v172-mainline-slice-20261123`.

## Scopo
Prima integrazione **vera su base main**, non mockup isolato: aggiunge la pagina `shark-cockpit.html`, gli 11 asset JS/CSS necessari copiati come blob identici dal LAB, un link minimo in `nav.js` esistente, la cache PWA protetta `sw.js`, un nuovo test di connessione a main e un workflow specifico. Sorgente CFTC ufficiale caricato dal browser, lettura Myfxbook da `data/myfxbook/latest.json` già presente su main.

## Perimetro volutamente ristretto
- Invariati **index, forex, mercati, asset, fonti, impostazioni, splash.js, splash.css, manifest, backend, collector, prezzi, CVD e COT core di A+B**. Nessun lavoro su Mac/Codex o su Contributors.
- `nav.js` diff locale: link menu `Shark Cockpit`, evidenziazione della voce sul percorso e build stamp visibile v1.72 (non tocca la lista mercati). Nessun cambio delle pagine legacy.
- `sw.js`: attivazione solo della cache `remura-shell-` propria; shell pubblica consentita da allowlist; nessuna cache delle API e degli accessi protetti; cache v87 per nuovo insieme di file.
- `shark-cockpit.html`: timbro in alto `v1.72 RELEASE CANDIDATE LAB · 23/11/2026 21:17 CET`; nessun nuovo ordine, automatismo o dato sintetico.
- I 77 test delle formule UI v1.71 restano attestati su run 45256941259; cinque test cache dedicati su 45256975610. Qui si eseguono solo **sei nuovi controlli** della composizione main + nuova pagina.

## Gate per poterla usare davvero in produzione (non verificati)
1. CI v1.72 sul commit nuovo: controllare il risultato remoto, non dare PASS senza log.
2. Safari iPhone: caricamento reale pagina su URL di staging/autorizzato; report CFTC, Myfxbook e N/D; preferiti/storico/gap; rete assente; barra versione e menu.
3. Approfondire collisioni con Mac Splash e C/A+B, test backup/rollback e Service Worker; main può cambiare nel frattempo.
4. Aggiunta fattori CFTC B e risultati A **solo** con contratti autentici versionati; non inventare fattori o miglioramenti scientifici.
5. La futura release deve essere autorizzata con merge/deploy distinto; mantenere separata l'eventuale attivazione Cloudflare Contributors.

**Condizioni economiche**: file statici, un solo fetch CFTC per dataset come codice LAB precedente, Myfxbook su snapshot same-origin. Non si introducono Workers, D1, nuovi utenti, nuove spese cloud, né scheduler. Non è confermato l'intero billing. Candidato NON PUBBLICATO.
