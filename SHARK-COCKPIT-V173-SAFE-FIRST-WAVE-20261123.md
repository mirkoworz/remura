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

## 23/11/2026 — Gate visibilità Pages verificato PRIMA del deploy
- Cloudflare Pages Direct Upload da dashboard **pubblica il sito quando si preme `Deploy site`**; l'indirizzo `<project>.pages.dev` è **pubblico per impostazione predefinita**. Non esiste un URL di preview "privato" per il solo fatto di chiamarlo preview.
- Cloudflare Pages `Settings → General → Enable access policy` protegge gli alias di preview, **NON il dominio base `<project>.pages.dev`**; per quest'ultimo serve policy Access dedicata, verificata sul dominio esatto. Guide: https://developers.cloudflare.com/pages/configuration/preview-deployments/ e https://developers.cloudflare.com/pages/platform/known-issues/#enable-access-on-your-pagesdev-domain
- La configurazione Cloudflare dell'utente non è accessibile tramite i connettori disponibili in questa chat; la creazione remota del progetto e la lettura di policy/quote reali **non sono state eseguite**. Non inferire un progetto esistente da un file ZIP o da PR #114.
- Aggiunto al solo **bundle di preview** `_headers` con `X-Robots-Tag: noindex, nofollow, noarchive` e `robots.txt` con `Disallow: /`. Questi sono **soltanto suggerimenti ai crawler**, non autenticazione o restrizione di accesso. `capital-cloud-config.js` resta nullo e `sw.js` escluso.
- Nuovo workflow **45280010488 SUCCESS, 6/6**, commit sorgente `a317577bb6d710b9f00a1d687ff3a63139bfb452`. Artifact ID `14869630156`, nome `REMURA-v1731-SAFE-WEB-PREVIEW-NOT-DEPLOYED`, validità fino al 24/11/2026 23:28 CET. ZIP interno: **104 file**, 1.226.531 bytes decompressed, SHA256 `54a580fce64ce62de5bf382451d0620a9cdda665728dbb78b034958c59a081f2`. Sostituisce l'artefatto a 102 file documentato sopra.
- **STOP pubblicazione** finché il proprietario non sceglie espressamente: (A) dominio `pages.dev` pubblico con soli dati già pubblici, oppure (B) configurazione e verifica Access per dominio prima della prima pubblicazione. L'autorizzazione a creare una preview *non* è automaticamente autorizzazione a rendere il dominio pubblico.
- In entrambi i casi, nuovo progetto completamente separato da REMURA live, piano Free verificato nella dashboard, zero merge/Cloudflare D1/Worker Contributors e nessun binding a dati privati. `main` invariato.

## 24/11/2026, 00:02 CET — OWNER conferma preview Pages pubblicata e funzionante
- Il proprietario ha autorizzato esplicitamente un **nuovo dominio pubblico `pages.dev`** per la sola preview v1.73.1 con file pubblici e pacchetto isolato, poi ha confermato in chat **«Ok ho fatto tutto funziona»** dopo i passi manuali in Cloudflare.
- **Stato evidenza:** `OWNER_REPORTED_PAGES_PREVIEW_WORKING` — conferma manuale positiva di creazione/caricamento/funzionamento percepito; **URL esatto non ancora comunicato**, nessuna verifica autonoma dei codici HTTP, del routing Home→Cockpit o delle risposte CFTC/Myfxbook sull'host nuovo. Non convertire la dichiarazione in test tecnico end-to-end attestato.
- Si presume il caricamento del ZIP `remura-v1731-webfirst-ISOLATED-NOT-PUBLISHED.zip` prodotto dal workflow **45280010488** (6/6 CI) perché è quello richiesto nelle istruzioni; **contenuto e checksum distribuiti non ancora verificati dal dominio**.
- La preview è **pubblica**, per scelta esplicita del proprietario; i suggerimenti anti-indicizzazione non limitano i visitatori. Bundle locale esclude Firebase reale e Service Worker, ma tale esclusione in produzione sull'URL non è ancora stata ispezionata direttamente.
- **NESSUN merge**: PR #114 ancora Draft e `main@4f8d8a707789eec29686a1568c4b8441e4c7d684` invariato al controllo del 24/11. Nessuna modifica all'account Cloudflare da questa chat, nessun Worker/D1/Access Contributor attivato per effetto della preview.
- **Gate prossimo:** ricevere il solo URL pubblico `https://<nuovo-progetto>.pages.dev` e svolgere smoke test HTTP non invasivo: Home, Cockpit, asset JS/CSS, JSON retail, header noindex, Firebase disabilitato e assenza di SW, con test Safari user-facing separato per CFTC reali. Misurare billing Pages reale nella dashboard Free e proteggere/ritirare il dominio se compaiono risorse private. Pubblicazione della nuova release ufficiale richiede autorizzazione distinta.

## 24/11/2026 00:08 CET — PAGES HTTP SMOKE AUTENTICATO DAL RUNNER PUBBLICO

Sito pubblico **esatto confermato dall'OWNER**: https://remura-lab-v1731-iphone.pages.dev/

Le richieste non hanno utilizzato credenziali né controllato il pannello Cloudflare. I primi accessi diretti con il lettore web della chat risultavano bloccati per limiti dell'ambiente; la prova esterna è quindi stata eseguita con GitHub Actions, su file **pubblici**, mediante GET HTTPS limitati e senza retry.

**A. Public smoke one-shot**: run **45285970670**, primo esito `10/11 PASS` (workflow formalmente FAILURE sul check che non seguiva redirect). Richieste singole e risultati:
- `/` HTTP 200, Home v1.73.1 con link Cockpit.
- `/shark-cockpit.html` HTTP **308**: canonicalizzazione Cloudflare, anziché 200 diretto. Questo NON è stato mascherato come pass.
- `/shark-cockpit.js`, `/shark-cockpit-core.js`, `/shark-focus-ui.js`, `/shark-cockpit.css`: tutti **HTTP 200** con verifiche di contenuto e riferimenti ai dataset pubblici.
- `/data/myfxbook/latest.json` HTTP 200: JSON parseabile con fonte Myfxbook e timestamp dichiarato.
- `/capital-cloud-config.js` HTTP 200: `window.REMURA_FIREBASE_CONFIG = null;`, nessuna chiave Firebase reale o `apiKey:`.
- `/robots.txt` HTTP 200 con `Disallow: /`.
- `/sw.js` HTTP 200 **ma fallback NON JS**; non è stato trovato un Service Worker eseguibile (Cloudflare Pages può fare SPA fallback con 200 su path non esistenti).
- `/private-api/health` HTTP 200 **ma fallback non JSON**; nessuna API privata identificata. Attenzione: questo 200 non è attestazione di una API attiva, né un codice 404.

**B. Follow-up esclusivamente sul punto irrisolto**: run **45286133985 SUCCESS**, due GET totali:
- `/shark-cockpit.html` → **HTTP 308** con `Location: /shark-cockpit`.
- `/shark-cockpit` → **HTTP 200**, `Content-Type: text/html`, versione `SHARK COCKPIT v1.73.1`, dipendenza script e riferimento Myfxbook presenti. `X-Robots-Tag: noindex, nofollow, noarchive`.
- La verifica non ha ripetuto i dieci controlli già superati; conteggio aggregato del perimetro: **11/11 coperti**, su due run distinti. Non falsificare la prima CI come tutta verde.

**Gate rimasti aperti**: funzionalità JavaScript/UI e fetch CFTC reali in Safari sul dominio (l'OWNER ha riferito che l'interfaccia funziona, ma non ci sono test browser automatizzati autenticati); no misure COT sul comportamento dei prezzi, nessun attestato di profitto; budget/quota Free Cloudflare account non letto dal connettore; deploy release ufficiale/merge resta NON autorizzato; Contributors reali ancora isolati e disattivati. `main` non è stato modificato dall'attività di smoke.

**Sicurezza**: nessuna chiamata alle API Cloudflare, nessuna credenziale, sessione, D1 o Secret, nessuna acquisizione CFTC realizzata da queste prove. Le intestazioni antiindicizzazione non rendono il sito privato: URL pubblico per scelta dell'OWNER.

## 24 novembre 2026 — v1.74 attestazione byte per byte della preview pubblicata

**GitHub Actions 45286745770 SUCCESS: sei GET HTTPS pubbliche, senza retry/credenziali/Cloudflare API/CFTC GET, tutte con SHA-256 esattamente uguale al sorgente verificato**. Sito `https://remura-lab-v1731-iphone.pages.dev`.
1. `/` → `index.html`: **EXACT_MATCH HTTP 200**.
2. `/shark-cockpit` (Cloudflare canonical) → `shark-cockpit.html`: **EXACT_MATCH HTTP 200**.
3. `/shark-cockpit.js`: **EXACT_MATCH HTTP 200**.
4. `/shark-cockpit-core.js`: **EXACT_MATCH HTTP 200**.
5. `/data/myfxbook/latest.json`: **EXACT_MATCH HTTP 200**.
6. `/capital-cloud-config.js`: **EXACT_MATCH HTTP 200**, con il contenuto deliberatamente sostituito `window.REMURA_FIREBASE_CONFIG = null;`, senza chiave/progetto Firebase live.

Codice attestazione `preview/attest_deployed_assets_v174.mjs` e workflow `.github/workflows/remura-v174-public-asset-attestation.yml`; esecuzione associata al commit **561105de27da1b0015b83d11e3322e2538a87dc1**. Le CI Splash e Insights legacy su quel commit sono anch'esse **SUCCESS** (45286754696 e 45286754709). Questo passaggio **non richiede di caricare di nuovo ZIP**: sono prove su ciò che è già online.

Limiti della prova: dimostra la **corrispondenza byte per byte di sei asset pubblicati**, non di tutti i 104 file del pacchetto; non certifica la corretta esecuzione JavaScript, la consultazione live dei dataset CFTC in Safari né un vantaggio predittivo. Tutte le POST, Access/D1 Contributors, Oracle, collector, backend e merge/deploy live sono rimaste intatte. La PR #114 resta Draft; `main` non modificato.
