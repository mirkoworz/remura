# REMURA v0.80 LAB — CHECKPOINT COMPLETO E PASSAGGIO DI CONSEGNE

**21 novembre 2026 · ore 17:22 CET (Europe/Rome)**  
**Repository:** `mirkoworz/remura` (pubblico).  
**Branch corrente:** `research/contributors-access-d1-preflight-v080-20261121`.  
**Base preservata:** `research/contributors-free-visibility-v079-20261121`, SHA `eaa6805b3db8fce29a736d0ab47211c925cda055`.  
**CI v0.80:** https://github.com/mirkoworz/remura/actions/runs/44923942230 — commit testato `fdf753c96136623e485baefeb8910dfa6af5a033`.  
**Stato:** 92/92 NUOVI TEST PASS; nessun deploy, Cloudflare reale, GitHub Secret, merge, Oracle o spesa.

## Cosa è stato completato

1. `access_seat_inventory_v080_lab.py`: interprete OFFLINE del risultato API Cloudflare `GET /accounts/{id}/access/users` (che NON viene chiamata). Controlla tutte le pagine, la coerenza dei conteggi, identità duplicate, valori booleani `access_seat`, e dati invalidi. Rilascia solo aggregati e nessun nome/email/user ID. Cloudflare `access_seat=true` indica che un utente si è autenticato con Access, **NON** prova un seat fatturabile ancora occupato. Piano/posti Free account restano sconosciuti.
2. `d1_two_day_visibility_v080_lab.py`: analisi OFFLINE di `d1AnalyticsAdaptiveGroups` con dati giornalieri simulati oggi/ieri: presenza dati ≠ conteggio esatto; `[]` ≠ zero righe. Valida data UTC, database UUID (non esposti), contatori, massimo 10 gruppi, errori e coerenza.
3. `staging_preflight_v080_lab.py`: aggrega il report v0.79, l'inventario utenti e il confronto D1; fornisce semafori manuali e restituisce **sempre NO_GO**, `automatic_deploy_allowed:false`, anche con tutti i dati sintetici favorevoli. È un dossier tecnico, non un meccanismo di deploy.
4. `test_access_seat_inventory_v080_lab.py`: **41/41** controlli nuovi PII/no billing, paginazione, UUID, false/true, duplicati, incompletezza, limiti, zero utenti, CLI offline.
5. `test_d1_two_day_visibility_v080_lab.py`: **32/32** nuovi casi, due giorni, gruppi vuoti, valori zero validi ma osservati, GraphQL errors, gruppi duplicati, limiti, privacy.
6. `test_staging_preflight_v080_lab.py`: **19/19** nuovi casi, mancanza D1 novembre 21, Access, source, plan, Safari, secure credential handling e manual sign-off.
7. Workflow one-shot `.github/workflows/remura-contributors-v080-one-shot-ci.yml` isolato sul branch: runner pubblico Ubuntu gratuito, `permissions: contents:read`, `persist-credentials:false`, no Secret, no network, no Cloudflare, no deploy, no `main` changes. Output del log: `REMURA_V080_SELF_CHECK=NO_LIVE_ACTIONS`, `Ran 92 tests`, `OK`, `REMURA_V080_ACCESS_D1_PREFLIGHT=92_92_PASS`.
8. Documentazione di verifica: `CONTRIBUTORS-V080-ACCESS-D1-FREE-PREFLIGHT-20261121.md` spiega verifiche future senza dati personali, piano/seat/budget, rollback, e distinzione D1 daily vs storage.

## Realtà Cloudflare e costo — PROVE NON EQUIVALENTI

- Monitor reale read-only **21/11/2026**, run https://github.com/mirkoworz/remura/actions/runs/44919682812: `REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA`, contatori D1 rows read/write giornalieri NON MISURATI; workflow fallito per evidence incomplete. **Non significa spesa o quota sforata.**
- Lo stesso report ha restituito da metadati **4 database D1** e **6.557.696 byte** occupati (circa 6,56 MB), **6.266.880 byte** database TEST, e dal monitor Workers **199 richieste giornaliere stimate**, zero errori stimati. Questi valori non certificano il piano di fatturazione, l'uso D1 giornaliero né il numero di posti Cloudflare Access.
- Cloudflare D1 metriche: https://developers.cloudflare.com/d1/observability/metrics-analytics/ ; il dataset `d1AnalyticsAdaptiveGroups` potrebbe omettere richieste non arrivate all'esecuzione SQL. Usare il 20/11 per inventare 21/11 è VIETATO.
- Cloudflare Access API users: https://developers.cloudflare.com/api/resources/zero_trust/subresources/access/subresources/users/methods/list/ ; la risposta contiene email/identità e `access_seat` booleano, che non basta per certificare l'uso di posti Free.
- Zero Trust sedi per la verifica dell'account: Settings > Billing/Cloudflare One plan e Team & Resources > Users; rimozione, revoca e blocco con policy sono azioni diverse: https://developers.cloudflare.com/cloudflare-one/faq/getting-started-faq/
- Repo **pubblico**: non caricare alcun dato account, Access user identity, HMAC secret, token, screenshot con email o dati mercato riservati.
- **NO_GO** allestimento staging D1/Access o pilot finché non è possibile verificare consumi, posti e policy con evidenza autorizzata.
- Nessun monitor Cloudflare `main` modificato o riavviato in v0.80.

## UI/versioni e precedenti da NON ritestare

- Le 4 pagine iPhone del portale private rimangono alla **Contributors v0.78 LAB**, tutte con data/ora `21/11/2026 16:56 CET` in alto; non sono state modificate in v0.79 né v0.80, perché si lavora a monitoraggio esterno.
- v0.78 Branch `research/contributors-owner-integrity-v078-20261121` SHA `14c3207a6b7508bbc181f825cad36a0e933bc3fd`, **50/50 PASS**; OWNER read-only integrity.
- v0.77 Branch `research/contributors-owner-audit-v077-20261121` SHA `ecab6f33d22e2c48fdb071db86c8cc0e3c125ffa`, **56/56 PASS**; immutable evidence audit, NO automatic release.
- v0.76 Branch `research/contributors-durable-level-v076-20261121` SHA `efe4f2236efd959f178250d7061931db58c1e306`, **64/64 PASS**; durable RESERVED/COMMITTED journal, dual tab, lost response.
- v0.75 Branch `research/contributors-private-navigation-v075-20261121` SHA `d12a99a491a0f6a26d7e62ffb51f491cdaf80bdd`, **50/50 PASS**; private navigation and immutable asset bundling.
- v0.74 Branch `research/contributors-level-intake-v074-20261121` SHA `89701c87850af0523ab371ba23a790bd05167ac3`, **55/55 PASS**; signed level submit + OWNER review.
- v0.70 original integration: 24/24 PASS su GitHub, v0.71 router 42/42 PASS offline. Non ripetere suite storiche.

## Roadmap coordinata

1. **Prossima v0.81 LAB:** progettare un controllo PII-safe e read-only del *piano reale* e *Access seats* in modo conservativo, con evidenze autorizzate; rafforzare la validazione della configurazione di staging Worker+Access+D1 senza deploy, e magari provare il client mobile con fixture locale e rendering Safari-compatible (non equivalente a Safari fisico).
2. **Autorizzazione futura specifica, non implicita:** prima di usare credenziali Cloudflare o GitHub Secret reali, verificare se già esistono permessi strettamente read-only, seats Free e data GraphQL; chiedere una conferma distinta per ogni nuova attivazione, anche solo staging.
3. **Pilot Contributors:** 1–2 amici invitati tramite sito web privato; possono leggere REMURA, proporre soltanto i propri livelli esatti autorizzati, consultare solo le proprie ricevute; OWNER può revisionare e registrare audit. Nessun accesso di modifica agli altri moduli, nessun invio Telegram automatico senza livello approvato.
4. **TradingView v0.8.181 LAB:** holdout1 23–29/11/2026 UTC e holdout2 30/11–06/12 UTC, non ritoccare parametri già congelati; nessun edge dichiarato finché validazione out-of-sample non esiste.
5. **Shark Science v0.4 LAB:** COT, sentiment, delta/CVD, absorption e Effort/Result; usare solo informazioni legali e pubbliche, senza affermazioni di accesso a ordini privati degli istituzionali.
6. **Experience v0.30 LAB:** splash toro/orso 3D con collisione, caricamento, esplosione, REMURA logo pinna, ringraziamento SMF; completamento Safari fisico e nuova release futura.
7. **Private Capture v0.15 LAB** STOP sintetico; **Ampere Radar v0.36** monitor Oracle Milano operativo/Telegram; **Oracle collector** attivo, autoupdater bloccato, pacchetto firmato v1.65 root-owned **NON installato**; backup reali, Squalincome e Telegram Contributors futuro invariati.
8. Verificare periodicamente quote D1/Workers/Access; non attribuire costi a nuove prove sintetiche. **Nessun Mac richiesto per LAB**.

**Stato finale v0.80: GitHub GREEN 92/92, account Cloudflare giornaliero D1 UNKNOWN, seats Access UNKNOWN, staging NO_GO.**
