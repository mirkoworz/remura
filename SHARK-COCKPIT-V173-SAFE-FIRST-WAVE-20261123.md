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


## 23/11/2026 — conferma prova manuale iPhone e stato release
Il proprietario ha comunicato **«Ok funziona»** dopo aver aperto l'anteprima HTML autonoma su iPhone. Questa è **un'evidenza manuale positiva del pacchetto standalone v1.72**, con gli stessi principali moduli UI del candidato v1.73.1. Non certifica che la Home/il menu della PR #114 o i fetch CFTC/retail sul futuro dominio siano stati provati in staging, né che la PWA aggiorni correttamente la cache dopo un deploy.

CI GitHub sulla PR #114:
- `45268730798` SUCCESS: nuova integrazione web-first (5/5).
- `45268742108` SUCCESS: regressione Splash legacy (corretta dopo failure iniziale).
- `45268742168` SUCCESS: compatibilità Insights legacy.
- `45269060595` SUCCESS Splash e `45269061100` SUCCESS Insights sull'HEAD documentale precedente. Le modifiche aggiuntive qui sono soltanto note, senza codice funzionale.
- `main` ancora `4f8d8a707789eec29686a1568c4b8441e4c7d684` al controllo; PR #114 **Draft**, PR #113 **Draft**.

Passaggio di rilascio:
1. Verificare consenso specifico per **preview/staging web** su URL isolato, senza alterare `main` o REMURA live.
2. Solo in un ambiente di test autorizzato verificare version stamp, menu Home→Cockpit→scanner, CFTC reali, Myfxbook, preferiti persistenti, assenza dati, reload, disconnessione e fonte/orario lettura.
3. Svolgere review/backup/rollback con attività Mac/Codex e A+B; una release live richiede **autorizzazione separata di merge e deploy** e nuova verifica SHA.
4. Il pilot Contributors ha gate e autorizzazione separati; mai fondere una PR UI con un Worker autenticato.

**Nessun costo nuovo/abbonamento/Cloudflare deploy/merge introdotto.** La fatturazione totale resta non certificata; usare Free come vincolo, non come promessa di consumo 0.

## 23/11/2026, 23:17 CET — Artifact isolato Cloudflare Pages Free (NO DEPLOY)
Per il futuro collaudo Safari ospitato, **senza modificare produzione, Pages esistente, `main` o Secret**, è stato realizzato un bundle ZIP statico tramite GitHub Actions.

- Sorgenti: `preview/build_isolated_webfirst_v173.py` + `preview/test_isolated_webfirst_v173.py`; workflow `.github/workflows/remura-v173-isolated-preview-package.yml`.
- Build eseguita da `ea578d3cae6b484cd27c8b2911be0f2627aaea7d`. Run **45278300046 SUCCESS** con **5/5 nuovi test**: pagina Home→Cockpit identica al ramo, nessun asset privato/deploy, Firebase disattivato, Myfxbook pubblico datato, SHA256 per ogni file + ricostruzione deterministica.
- Nome artifact: `REMURA-v1731-SAFE-WEB-PREVIEW-NOT-DEPLOYED` (GitHub Actions artifact ID `14868361866`, scadenza 24/11/2026 23:17 CET). Al suo interno `remura-v1731-webfirst-ISOLATED-NOT-PUBLISHED.zip`: **102 file, 1.226.329 byte decompressi**, SHA256 `0a37665e05ab0b014faee3490640838fda0b80c4c4af0041ac6ca90b1924ac2a`.
- Protezioni intenzionali **solo del bundle**: `capital-cloud-config.js` sostituito da `window.REMURA_FIREBASE_CONFIG = null` per impedire accessi alla Firebase personale; `sw.js` escluso; `research/`, `deploy/`, `scripts/`, `.github/`, test e config di deploy esclusi. `REMURA-PREVIEW-MANIFEST.json` documenta SHA e differenze. **Il bundle non è identico alla produzione** e NON è un test di PWA offline o di Firestore.
- Il CFTC viene interrogato dal browser solo quando la pagina sarà aperta online; **nessun accesso CFTC/Cloudflare eseguito dal workflow**. I JSON Myfxbook rimangono snapshot con timestamp, non dati live garantiti.

**Opzione gratuita verificata documentalmente**: Cloudflare Pages Direct Upload accetta ZIP da drag and drop, massimo **1.000 file** e **25 MiB per file** con upload UI; Free fino a 20.000 file per sito e 500 build/mese dichiarate da Cloudflare. I 102 file e le dimensioni del bundle stanno sotto i limiti tecnici citati; **disponibilità del piano e utilizzi correnti dell'account non ancora controllati**, nessun progetto creato. Fonti Cloudflare 23/11/2026:
- https://developers.cloudflare.com/pages/get-started/direct-upload/
- https://developers.cloudflare.com/pages/platform/limits/
- https://developers.cloudflare.com/pages/configuration/preview-deployments/

**Attenzione privacy:** i nuovi URL `pages.dev` sono accessibili pubblicamente per impostazione predefinita, a meno di specifica policy Access per il dominio (la sola protezione degli alias di preview può non coprire il dominio principale). Prima di pubblicare occorre autorizzazione specifica, valutazione della visibilità e verifica che il progetto sia **isolato** da quello REMURA esistente. L'artifact contiene solo file di presentazione pubblici e snapshot retail già nel repo, ma **non autorizza** deploy implicitamente.

**NO-GO invariato**: PR #114 Draft; collaudo Safari su URL reale, integrazione Mac/A+B, Free account e autorizzazione separata per merge/deploy live restano aperti. Il pilot Cloudflare Contributors v1.03 è un ramo diverso e non viene toccato.
