# REMURA Contributors v0.89 LAB — PILOT INTERATTIVO iPHONE

**Checkpoint 21 novembre 2026, Europe/Rome · banner UI: v0.89 LAB, 21/11/2026 19:03 CET.**

## GitHub, prove e integrità
- Repository pubblico `mirkoworz/remura`; branch indipendente `research/contributors-interactive-pilot-v089-20261121`.
- Base esatta: Contributors v0.88 LAB `5a00cc756b8ca56fd24df532a0cccda5598d4292`.
- **Commit codice testato:** `2a4f92366f2e779f6c333597bcb5951a6004cd9e`.
- GitHub Actions https://github.com/mirkoworz/remura/actions/runs/44933509006: job **SUCCESS** e log diretto `tests 30`, `pass 30`, `fail 0`, `REMURA_V089_PILOT_SIMULATOR=30_30_PASS`. 30/30 **nuovi test**; niente suite vecchie duplicate.
- File aggiunti: `research/contributors/contributors_pilot_interactive_v089_lab.html`, `research/contributors/test_pilot_interactive_v089_lab.mjs`, workflow one-shot `.github/workflows/remura-contributors-v089-one-shot-ci.yml`.
- Nessun deploy, `main` non modificato; nessun Cloudflare, D1 SQL, Access, Secret, Oracle o servizio live. Nessun uso di API, CDN, fetch, storage, cookie, localStorage. Il simulatore è interamente in memoria.

## Capacità effettive del file HTML su iPhone
- Pagina indipendente con stile REMURA dark, banner versione/ora in alto, due modalità dimostrative selezionabili con pulsanti: CONTRIBUTOR e OWNER. **Il selettore di ruolo NON è autenticazione**.
- CONTRIBUTOR aggiunge proposte originali sintetiche (strumenti fittizi `DEMO:EURUSD`, `DEMO:GBPUSD`, `DEMO:XAUUSD`) e richieste di correzione ad un originale dimostrativo già approvato. Le correzioni sono in un registro separato e non sovrascrivono l'originale. Cap massimo di 12 originali e 12 correzioni per una singola demo.
- OWNER approva o rifiuta solo proposte originali `UNREVIEWED` o correzioni `UNREVIEWED`, su due code separate, e vede audit demo append-only; non approva due volte una stessa proposta.
- Il pulsante `Simula risposta persa` registra una proposta `RESERVED` e blocca nuovi invii dalla vista CONTRIBUTOR. OWNER può solo osservarla senza sbloccarla o trasformarla in ricevuta. Il pulsante `Azzera solo questa demo` azzera la **RAM locale**, non rappresenta riconciliazione o cancellazione di un tentativo reale.
- Tre schede consultative COT, Sentiment, Delta/CVD sono esplicitamente `SEGNAPOSTO LAB` e prive di numeri, raccomandazioni, dati dal mercato o dichiarazioni di edge.
- I dati dinamici sono mostrati con `textContent`, non `innerHTML`. CSP connessioni negate, nessun form, campo con PII, servizio di rete o persistenza. Il demo mostra in alto e sul pannello `STAGING REALE NO-GO`.
- Visualizzazione locale e flusso UX non dimostrano l'isolamento ruoli del server; la sicurezza reale è affidata ad Access JWT e ruolo D1/OWNER lato Worker.

## Colli di bottiglia reali
- Ultima misura giornaliera D1 nota (21 novembre run https://github.com/mirkoworz/remura/actions/runs/44919682812): `REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA` e `REAL_ACCOUNT_DAILY_USAGE=NOT_MEASURED`, non consumo zero. Posti Cloudflare Access sconosciuti.
- v0.86 piano diagnostica read-only fino a due POST GraphQL, mai eseguito: richiede specifica autorizzazione, previa verifica limiti gratuiti.
- Quattro pagine protette v0.78 LAB ancora non pubblicate, byte-pinned e non modificate. Pilot 1–2 utenti reali resta vietato senza quota e seat reali, D1 fixture separata, allowlist fail-closed, login/logout/revoca Safari e rollback testati/approvati.
- L'URL GitHub della pagina HTML è disponibile, ma GitHub mostra di default il codice; per Safari da iPhone scaricare la pagina HTML tramite Raw e aprirla localmente. La preview effettiva su Safari fisico **non** è stata ancora attestata; passano solo i test JavaScript/HTML CI Linux.

## Roadmap generale dopo v0.89
1. Priorità operativa: controllo quote D1 e seats reali con consenso specifico; staging private pilot solo dopo gate Free e sicurezza. Una demo in-memory non sostituisce un'infrastruttura privata con ruoli.
2. TradingView v0.8.186 LAB: protocollo V2 pinned, inizio holdout1 `2026-11-23T00:00Z`, holdout2 `2026-11-30T00:00Z`; nessuna cattura live attribuibile e ancoraggio indipendente ancora non attivo. Non ricostruire retroattivamente.
3. Shark Science v0.4 LAB COT/sentiment/CVD/ER, matching delle fonti per decisione e clock ancora non autenticati, nessun alpha dimostrato. Documento TV-Shark real provenance bridge precedente `research/tv-shark-source-bridge-20261121`.
4. Experience v0.30 LAB splash toro/orso 3D ed esplosione, REMURA pinna/SMF e rimozione foto; Safari fisico futuro. Private Capture v0.15 LAB solo sintetico.
5. Oracle collector attivo e autoupdater bloccato, v1.65 firmata root-owned staged **NON installare**. Ampere Radar v0.36 capacità Milano/Telegram operativo. Backup reale, Squalincome, Telegram levels solo dopo approval e permesso preservati.
6. Niente Mac necessario per i test GitHub, nessuna spesa; non ripetere suite storiche GREEN. In caso di chat pesante fare passaggio di consegne con SHA, run CI, branch e roadmap.

**Esito: Demo v0.89 funzionante in laboratorio, 30/30 PASS. Cloudflare e pilot REALI NO-GO.**