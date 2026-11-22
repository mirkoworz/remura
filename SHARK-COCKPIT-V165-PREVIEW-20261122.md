# REMURA v1.65 LAB — SHARK COCKPIT PRODUCT PREVIEW
22 novembre 2026 ore 17:32 CET — Europe/Rome

**Nuova pagina reale dell'app, non un rendering e non una simulazione scientifica.**
Branch: feature/shark-cockpit-v165-preview-20261122
Non mergiata, non pubblicata su GitHub Pages o produzione.

## Che cosa è pronto
- Nuova pagina HTML iPhone/PWA shark-cockpit.html, CSS dedicato, JS UI e un core dati verificabile Node, senza dipendenze nuove.
- Menu condiviso nav.js: voce "Shark Cockpit · Fondi CFTC"; versione v1.65 LAB con 22/11/2026 17:32 CET in cima a tutte le pagine. Tutte le nove pagine precedenti e la nuova pagina referenziano nav.js?v=165, con modifica limitata alla stringa query sulle pagine precedenti.
- PWA service worker cache shell v79 incrementale, include quattro nuovi asset. Dati CFTC non archiviati come feed live dal service worker.
- 14 contratti ufficiali già mappati nella configurazione REMURA: futures per EUR/GBP/JPY/AUD/CAD/CHF/NZD; E-mini S&P/Nasdaq/Dow, USDX, oro/argento, WTI. Se CFTC non presenta un contratto risponde N/D.
- Browser legge CFTC Public Reporting attraverso le medesime API TFF gpe5-46if e Disaggregated 72hh-3qpy già usate dall'app; seleziona solo codici/colonne approvati e ultime 120 giornate. Nessun database/proxy/servizio nuovo. Una richiesta per dataset con eventuale fallback pubblico se fallisce il primo host: solo mentre la pagina è aperta o dopo click "Aggiorna".
- Differenza netta = (long-short)/open interest; cambio WoW in punti percentuali soltanto se due martedì consecutivi realmente presenti. Change a 4 settimane solo con cinque report consecutivi. Asset Manager/Leveraged Fund distinti e Managed Money/Producer Merchant identificati senza mediarli.
- Quarantena se due righe discordanti stesso contratto/stesso martedì, N/D su valori invalidi, tempo futuro, dato assente, report vecchio >14 giorni; nessuna selezione soglie su esiti.
- Filtri famiglia, ricerca, ordinamento maggior movimento/divergenze/data, cards responsive.
- Retail: GET same-origin data/myfxbook/latest.json esistente; massimo 7 coppie forex significative, percentuale lotti calcolata dai valori lLots/sLots e non presa come dato istituzionale, etichette recent (<3 ore) o archivio/stale. La coppia spot non viene convertita in contratto CFTC.
- Link CFTC officiali e a schede REMURA, nessun secret.
- Zero modifiche a collector Oracle, Mac Experience/Splash, TradingView, Cloudflare, Contributors backend o protocollo V2.

## Collaudo nuovo prodotto
Workflow .github/workflows/remura-shark-cockpit-v165-preview.yml, content read-only, timeout 4min, senza Secret o provider API.
CI iniziale run 45047433354 SUCCESS 24/24.
Dopo allineamento delle nove pagine esistenti al versionato nav.js?v=165, CI finale run 45047547629 SUCCESS 24/24, logs: # tests 24, # pass 24, # fail 0, REMURA_SHARK_COCKPIT_V165=PRODUCT_SMOKE_GREEN.
Delle 24 prove: 17 nuove unit/integration wiring, 7 test release consistency modificati/rieseguiti per il solo asset navigazione effettivamente cambiato. Non eseguiti tutti gli storici della ricerca.

**Limite dei test:** non è stato eseguito il caricamento remoto del provider da Safari, un test visivo reale su iPhone o una pubblicazione su GitHub Pages. I test verificano codice, output su fixture coerenti, wiring statico e regressione di release. NON rappresentano 14 contratti con dati live confermati.

## Next steps concreti per la prossima chat
1. Verificare coerenza visiva Safari e caricamento CFTC **dopo autorizzazione specifica per preview/deploy** oppure su un ambiente di anteprima autorizzato. Non pubblicare ora.
2. Valutare differenza con vecchio scanner mercati.html: il nuovo cockpit è volutamente *per singolo futures CFTC* e non dice che il futuro EUR = prezzo EURUSD o che due futures di un cross siano equivalenti.
3. Integrare un pannello Contributors autenticato vero, **solo dopo quota Cloudflare Free/Access verificata, test revoca/ruoli e consenso distinto**; vietare editor generale e modifiche Oracle.
4. In parallelo: verifica read-only dell'effettivo feed CVD TEST per holdout, SOLO previo controllo Free e nuove autorizzazioni. Non copiare Secret.
5. Prima di una release, verificare la compatibilità con l'Experience cinematografica del Mac e la roadmap Oracle v1.65 (numeri condivisi non implicano identità dell'artefatto). No merge automatico.

## Trasparenza scientifica
Il browser riceve una fotografia CFTC pubblica, **non** timestamp autenticato di pubblicazione originaria, first-seen indipendente o trade istituzionale individuale. Nessun edge, rendita o segnale automatico dimostrato. Retail distinto, futures != spot. Qui si crea un'interfaccia utile, non si proclama validazione alpha.

**FREE-FIRST:** nessun nuovo server, D1, Firestore, Cloudflare, servizio paid o scrittura di mercato. L'unica nuova attività eventuale da uso reale sarebbe GET al provider CFTC pubblico già interpellato da REMURA e GET allo snapshot statico Myfxbook esistente. Rate limit CFTC e disponibilità CORS dipendono dal provider e vanno collaudati in Safari prima del rilascio.
