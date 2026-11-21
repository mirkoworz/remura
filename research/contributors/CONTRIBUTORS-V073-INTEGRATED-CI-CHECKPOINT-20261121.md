# REMURA Contributors v0.73 LAB — 24 INTEGRATION TESTS ATTESTATI

**21 novembre 2026, 13:24 CET (Europe/Rome)**

## Checkpoint e riferimenti immutabili

- Repo: `mirkoworz/remura` (**repository pubblico**), branch isolato `research/contributors-v070-one-shot-ci-20261121`.
- Base di partenza v0.72: `b1cb671c50328e449bec5081ca87b1eb4b161464`.
- Workflow eseguito SOLO sul branch isolato: `.github/workflows/remura-contributors-v070-one-shot-ci.yml`. Il file verifica il messaggio del commit e il percorso esatto; l'evento è `push` e il filtro `paths` limita l'avvio alle modifiche del solo workflow.
- Runner GitHub-hosted `ubuntu-24.04`, Node.js `22.16.0`, `node:sqlite` sperimentale. Workflow `permissions: contents: read`, `persist-credentials: false`, **nessun GitHub Secret**, `npm install`, Cloudflare, Oracle, D1 reale, deploy, merge o spesa.
- Runner standard su repository pubblico: gratuità confermata dalla documentazione GitHub: https://docs.github.com/en/actions/concepts/billing-and-usage

## Risultati REALMENTE eseguiti in GitHub Actions

**Run conclusivo GREEN: https://github.com/mirkoworz/remura/actions/runs/44903608070**

- SHA eseguito: `c0a0b1d99283e8b66137f83ce0b0bd828c6e5724`.
- **24 test eseguiti, 24 PASS, 0 FAIL**, controllato anche dal log del job.
- Marker univoco nel log: `REMURA_V070_INTEGRATED=24_24_PASS`.
- Eseguita **soltanto** la suite `research/contributors/test_protected_read_integrated_v070_lab.mjs`, non le suite storiche v0.66/v0.67 né v0.68/v0.69/v0.71/v0.72.
- Il test utilizza fixture originale v0.66 su SQLite in memoria, moduli Access/HMAC, profilo D1 `first-primary`, bridge HTTP read-only, separazione OWNER/CONTRIBUTOR, limitatore, revoche, no-store, blocco impersonificazione e mutazioni.
- Non dimostra Access reale, Cloudflare Worker/D1 reale o effettiva revoca token provider.

### Percorso di diagnosi — da NON ripetere

1. Primo push `2e2dd7ee442d2ac226e1981a9362dacb9001964e`: file YAML con due punti nel valore della condizione non incapsulato; GitHub ha segnalato workflow failure con **zero job**.
2. Secondo push `38256300f0dbd8b59191027734e868b0bcd6aea3`: YAML corretto, 24 suite eseguita, **22 PASS / 2 FAIL**: i test 02 e 07 presumevano inizialmente ricevute di amendment nel fixture, ma conteneva soltanto livelli originali.
3. Corretto ESCLUSIVAMENTE il file test v0.70 `test_protected_read_integrated_v070_lab.mjs` per creare prima proposte sintetiche tramite l'originale `submitWith`, quindi verificare ricezione e isolamento Alice/Bob. **Nessuna modifica alla logica applicativa.**
4. Terzo push `c0a0b1d99283e8b66137f83ce0b0bd828c6e5724`: run 44903608070 **SUCCESS / 24 PASS**.

## Free-first e sicurezza

- Ultimo report Cloudflare account read-only verificato dal GitHub Actions runner il 20 novembre 2026: https://github.com/mirkoworz/remura/actions/runs/44772218921; 4 D1, 6.275.072 byte di storage D1, stima 417 richieste Workers al giorno, stima 196 righe D1 lette e 784 scritte nel giorno del report; limiti Free non vicini, ma **non equivalgono alla fatturazione esatta o al margine attuale**.
- Non usare documenti, identità, credenziali o indirizzi reali nel repository pubblico. I vecchi stati LAB continuano a usare solo dati sintetici. Le chiavi e i pin non devono transitare nei commit.
- Il portale iPhone di recupero e coda OWNER è alla **v0.72 LAB**, con badge versione e data ora in cima alle due pagine. v0.73 è **checkpoint di collaudo**, non rilascio UI: nessuna pagina live modificata.
- Il modulo read-only `protectedReadCandidateV069` rimane candidato senza entrypoint Worker o route. Niente deploy/staging Access/registrazioni; nessuna modifica a Oracle collector/autoupdater.

## Prossima roadmap senza Mac

1. **NO GO staging reale** finché Access application con policy allowlist, identità e slot revocabili, pubblico/privato/routing `ctx.access` e Cloudflare Free seat usage non sono verificati.
2. Preparare il singolo Worker protetto che serve HTML/CSS/JS e API senza inoltrare `ctx.access` tramite Service Binding/Static Assets; mappa assets strettamente per ruolo e verifica ogni GET/POST lato server.
3. Testare sessione Access reale, logout, revoca, D1 `first-primary`, audit e rate-limiting con fixture isolato, **solo dopo autorizzazione specifica**.
4. Recupero e ricevute non equivalgono a una schermata completa di **inserimento livelli**: l'input originale autorizzato, le modifiche, l'OWNER review e le garanzie di scrittura/idempotenza devono seguire un percorso separato; mai confondere il doppio passaggio reservation+insert con una transazione atomica.
5. Confrontare nuova telemetria Free prima di deploy; niente nuove spese senza consenso.

## Filoni invariati

TradingView v0.8.181 LAB (holdout 1 23–29 novembre UTC; holdout 2 30 novembre–6 dicembre UTC), Shark Science v0.4 LAB, Experience v0.30 LAB splash toro/orso/pinna e SMF, Private Capture v0.15 LAB inattivo, Ampere Radar v0.36 operativo, Oracle collector attivo con autoupdater bloccato e pacchetto v1.65 NON installato, backup, Telegram Contributors futuro e Squalincome non modificati.
