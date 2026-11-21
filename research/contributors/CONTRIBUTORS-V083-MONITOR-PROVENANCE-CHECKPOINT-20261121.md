# REMURA Contributors v0.83 LAB — MONITOR PROVENANCE / NO FALSE ZERO

**Checkpoint: 21 novembre 2026 · 18:09 CET (Europe/Rome)**

## GitHub — solo nuove prove
- Repo `mirkoworz/remura` **pubblico**, branch isolato `research/contributors-log-provenance-v083-20261121`.
- Base esatta v0.82: `2b7b4b3d1e813d6e09095c0741761d1f4607deca`.
- Commit CODICE testato: `f85fec2d918828a713a0493ebeacb0a4a7dfc691`.
- Workflow: https://github.com/mirkoworz/remura/actions/runs/44928399560 — **SUCCESS**, log verificato: `Ran 20 tests`, `OK`, `REMURA_V083_PROVENANCE=20_20_PASS`.
- **20/20 nuovi test PASS**; nessuna suite storica rieseguita, nessun deploy/merge, Secret, D1 SQL, account reale, Oracle o spesa introdotta. `main` invariato.

## Cosa cambia
- Nuovo `research/contributors/monitor_provenance_v083_lab.py`: correlazione **OFFLINE su metadati e log già forniti** per monitor giornaliero Cloudflare Free, con ora UTC, branch `main`, SHA Git, run ID, nome workflow, stato della run, limite di età e parsing stretto in allowlist dei contatori D1.
- Blocca input ambigui: timestamp di ieri, run diversa, branch errato, counter duplicati, contatori invalidi, limiti di riferimento diversi, stati non riconosciuti. Log con token o dati estranei non vengono riflessi nei risultati.
- Un monitor `success` riportato da un input **non** attesta il provider; i valori `0` presenti in una fixture sono solo stime adattive fornite offline, non misura di fatturazione né autorizzazione staging.
- Nuova suite `test_monitor_provenance_v083_lab.py` (20 casi) e workflow one-shot `.github/workflows/remura-contributors-v083-one-shot-ci.yml`, runner Ubuntu standard pubblico, checkout senza credenziali, solo Python stdlib.
- Output sempre `decision=NO_GO`, `automatic_deploy_allowed=false`, `billing_attested=false`, `d1_usage_attested=false`, `access_free_seats=UNKNOWN`.
- **Limitazione**: il digest e la provenienza descrivono input supplied; non sono prova esterna immutabile, non effettuano telefonate GitHub/Cloudflare e non riparano l'Analytics GraphQL provider.

## Stato reale e costi (ultimi dati conosciuti)
- Monitor D1 21 novembre: https://github.com/mirkoworz/remura/actions/runs/44919682812 — FAILED/INCOMPLETE; `REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA`, `REAL_ACCOUNT_DAILY_USAGE=NOT_MEASURED`. Le righe giornaliere lette/scritte sono sconosciute; **UNKNOWN ≠ zero**. Ultimo precedente verde 20/11 non sostitutivo.
- Stesso run: Workers ~199 richieste stimate, 0 errori stimati; D1 4 database, 6.557.696 byte totali, TEST 6.266.880 byte. Non è rendicontazione economica o attestazione seats.
- Access Free piano e posti effettivamente disponibili: **UNKNOWN**. Nessun nuovo accesso, nuovo utente, deploy o risorsa Cloudflare.
- UI privata v0.78 LAB per le quattro pagine iPhone; pagina statica readiness v0.80 LAB; v0.83 è solo laboratorio infrastrutturale, non UI.

## Roadmap v0.84 e altre linee
1. Preparare un contratto di evidenza **pubblicabile e minimizzato** per verifica D1/Access, con contatori e sorgenti correnti sotto autorizzazione specifica, senza salvare log completi, email, ID account o Secret in repo pubblico. Quando Cloudflare GraphQL non risponde, mantenere NO_GO e continuare offline.
2. Dossier Access Free: policy allowlist deny-by-default, pianificazione 1–2 collaboratori, ruoli con `ctx.access` JWT, fixture D1 separata, login/logout/revoca Safari fisico e rollback **solo se autorizzati dopo verifiche quote**.
3. Original-level e amendment rigorosamente separati; risposta persa/RESERVED mai retry o release automatici, OWNER audit append-only e approvazione manuale, Telegram soltanto dopo approvazione e consenso.
4. TradingView v0.8.183 LAB procede in branch separato: holdout1 23–29/11 e holdout2 30/11–06/12 UTC, protocolli/preregistrazione V2 congelati, nessun edge dimostrato. Shark Science v0.4 LAB per COT/sentiment/delta/CVD/ER senza accesso a operazioni segrete.
5. Experience v0.30 LAB splash toro/orso 3D con esplosione, logo REMURA pinna, SMF e rimozione foto; Safari fisico futuro. Private Capture v0.15 LAB non attivato.
6. Oracle collector attivo, autoupdater bloccato, v1.65 firmata staged root-owned NON installata. Ampere Radar monitor Milano e Telegram operativo; backup reale, Squalincome e invio Telegram livelli approvati in futuro. No nuovi costi o Mac necessari.
7. Non rieseguire test GREEN precedenti. Verificare periodicamente margini Free e passare di chat con SHA/CI/roadmap quando opportuno.

**Staging reale, D1 reale, Access reale, merge main: NO-GO.**