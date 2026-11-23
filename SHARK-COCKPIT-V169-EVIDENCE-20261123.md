# REMURA — Filone D · Shark Cockpit v1.69 LAB
**Checkpoint:** 23/11/2026 ore 13:30 CET, Europe/Rome
**Ramo UI indipendente:** `feature/shark-cockpit-v169-evidence-iphone-20261123`
**Origine:** `feature/shark-cockpit-v168-flow-anatomy-20261122` (nessun merge con main).

## Funzionalità realizzate
1. Pannello **Prima la qualità. Poi i numeri.** in `shark-cockpit.html`, con quattro sorgenti distinte: CFTC TFF, CFTC Disaggregated, retail Myfxbook, CVD.
2. Stato per dataset CFTC derivato dai report già presenti in RAM: RECENTE, PARZIALE, OBSOLETO, DA_VERIFICARE, NON_CONFRONTABILE o NON_DISPONIBILE; date di martedì, numero di report leggibili e confronti WoW. Un report recente ma senza martedì precedente non diventa movimento misurato.
3. Retail separato, con distinzione tra osservazioni recenti, archiviate e N/D. Nessuna media retail/CFTC.
4. **CVD N/D/non collegato** finché il Filone A non fornirà un'interfaccia validata. Il CVD proxy CLV × tick-volume non è flusso ordini istituzionali.
5. Momento di lettura browser in Europe/Rome separato dalla data di riferimento CFTC; primo istante indipendente e pubblicazione originale non attestati.
6. Navigazione iPhone per affidabilità, mover CFTC, contratti e retail; griglia responsiva, target touch e testo accessibile.
7. In alto nella sola pagina HTML aggiornata: **v1.69 LAB · 23/11/2026 13:30 CET (Europe/Rome)**. La nav condivisa delle altre pagine resta volutamente v1.68 LAB perché non è oggetto di questo ramo.
8. Nuovi moduli `shark-evidence-core.js` (puro e testabile), `shark-evidence-ui.js` (DOM-only). Nessun nuovo fetch, token, secret, storage, endpoint, provider, D1 o Cloudflare.
9. Cache shell PWA v83 con i due nuovi moduli; CFTC live NON memorizzata come dato di mercato nel service worker.
10. Preview iPhone autonoma non pubblicata: `preview/REMURA-Shark-Evidence-v169-iPhone-STANDALONE-LAB.html`, CSS e sei script inline, senza asset JS esterni. Il retail nella sola preview legge lo snapshot pubblico già esistente di main da raw.githubusercontent.com, non uno snapshot privato.

## Verifiche e limiti
- I vecchi test v1.68 erano 57/57 verdi al checkpoint precedente; **non attribuire automaticamente quel risultato alla v1.69**.
- Aggiunti **5 nuovi casi** in `tests/shark-evidence.test.js`, e allineati solo i test di wiring interessati dalle modifiche.
- Workflow di test specifico: `.github/workflows/remura-shark-cockpit-v169-evidence.yml`, permesso `contents: read`, timeout 4 minuti, senza credenziali o deploy; destinato a 62 verifiche (57 precedenti interessate + 5 nuove). **Esito CI da accertare separatamente**: non dichiarato verde in questo checkpoint.
- Safari su **questa** versione v1.69, CORS effettivo CFTC e risultato numerico sui mercati aperti sono **da confermare**. Nessun accesso a live feed o raccolta privata in questa lavorazione.
- La preview tramite servizi esterni come raw.githack è soltanto visualizzazione statica volontaria; non usare password, token o dati personali, e non aggirare eventuali avvisi Safari.
- Nessun nuovo costo cloud strutturale: riutilizza letture CFTC/Myfxbook già previste; non dimostra in assoluto bollettazione zero di servizi preesistenti.

## Gate prima della release
1. Verificare il job CI v1.69 e correggere **solo eventuali** regressioni nuove.
2. Aprire volontariamente la preview su iPhone/Safari e verificare layout/touch/scroll, N/D, CFTC CORS, retail e stato dati.
3. Allineare i numeri delle altre pagine e la cache solo in una futura release coordinata e autorizzata, integrando le modifiche indipendenti degli altri filoni.
4. Nessun merge, deploy, modifica Splash 3D Toro/Orso/SMF, backend Contributors, calcolo scientifico del Filone A o collector Mac.

**Interpretazione:** questo intervento migliora l'intelligenza *di presentazione* e la trasparenza della fonte; non produce né prova un vantaggio di trading.
