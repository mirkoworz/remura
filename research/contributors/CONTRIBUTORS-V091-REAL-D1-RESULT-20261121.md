# REMURA Contributors v0.91 LAB — ESITO REALE D1 READ-ONLY (21 NOVEMBRE 2026)

Data osservazione: 2026-11-21 ore 18:55 UTC (19:55 CET Europe/Rome).
Questo checkpoint registra il risultato di una diagnosi reale autorizzata; non costituisce un GO per il pilot.

## Autorizzazione specifica e preflight

L'OWNER ha autorizzato in chat massimo due Cloudflare GraphQL POST di sola lettura (21 e 20 novembre UTC), senza retry, credenziali solo GitHub Secrets esistenti, zero SQL D1, deploy, utenti, Oracle o nuove spese. È stata verificata la documentazione Cloudflare GraphQL (https://developers.cloudflare.com/analytics/graphql-api/limits/): default 300 query per finestra 5 minuti, molto superiore alle due richieste previste. Il monitor del 21/11 (run 44919682812) mostrava Workers 199 richieste/giorno, 4 DB D1 e storage aggregato 6.557.696 byte; D1 daily rows UNKNOWN. Questi numeri sono precedenti alla diagnosi e non attestano il consumo successivo.

## Risultati GitHub verificati
- Branch: research/contributors-d1-diagnostic-v091-20261121, base v0.90 SHA e1693bb9b12b53bcd3af87b5b720abd6c63f2e55.
- Codice diagnostico byte-pinned: Git blob f5568f365232a943d6b53b6c8581cd158f21188e; fixture/query pinned SHA-256 483e14a113af7841fb69bdfdb7ea3fa3ee616b74f4f28b9cbc509b29d022754a.
- CI offline precedente 44937483269: 25/25 PASS, solo mock (nessuna chiamata provider).
- Primo consenso commit ca0892f55714cc3aebd6cf705fd3f1de58737e7f, run 44937995589: SKIPPED alla condizione GitHub-event. Zero richieste al provider.
- Fix CI guardia commit 760d95b870287ef20a523721c15c80461707e94d: verifica nel runner stesso, prima di esporre Secret, il file aggiunto da solo, commit messaggio esatto, data UTC, hash sorgenti, blocco rerun.
- Secondo commit consenso ac000344d5808c82bd6d57966b3caafa8d9b6e20, run https://github.com/mirkoworz/remura/actions/runs/44938092204: job completato con FAILURE INTENZIONALE di admission: contatori di oggi NON disponibili. Controlli preliminari GREEN. Nessun errore di autenticazione mostrato.
- Output sintetico reale: status=TODAY_EMPTY_PREVIOUS_PRESENT; utc_day_checked=2026-11-21; provider_post_count=2; provider_post_max=2; prior_utc_day_has_groups=true; daily_read_band=null; daily_write_band=null; secrets_logged=false; db_identifiers_logged=false; d1_sql_calls=0; automatic_retry=false; adaptive_metrics_not_exact_billing=true; access_seats_verified=false; free_plan_verified=false; staging_allowed=false; decision=NO_GO.
- Interpretazione: query UTC del 21/11 non ha dato gruppi D1; query UTC del 20/11 ha dato gruppi. Non equivale a consumo odierno zero e non certifica piano, quota D1 reale o numero posti Access.
- Tetto autorizzato consumato integralmente: DUE richieste provider, nessun retry, non fare una terza query senza nuova autorizzazione.
- Trigger temporaneo di consenso eliminato dal branch nel commit 46585a123fee335397fb758ee9c69486496305cf. Il workflow del monitor giornaliero esistente sul main non è stato alterato. Nessun ulteriore provider run deve risultare da questi consent marker storici.
- Gli identificativi del progetto e dei secret restano privati e non devono essere copiati in issue/README/commit.

## Stato Roadmap
Contributors v0.91 LAB: diagnostica reale eseguita, risultati odierni D1 UNKNOWN, pilot NO-GO; posti Access Free ancora UNKNOWN. v0.90 protezione POST candidate 34/34 PASS; UI private v0.78 LAB non distribuite; demo mobile v0.89 PASS e checker Free v0.88 PASS. Successivo passo SENZA API: dashboard Cloudflare privata per piano Free, posti Access usati/totali, Row Metrics D1 il giorno UTC indicato, solo numeri aggregati senza PII. Per pilot 1–2 collaboratori: previa autorizzazione nuova, staging isolato D1 fixture, deny-by-default Access, JWT e ruoli server, Safari login/logout/revoca e rollback. Contributor consulta REMURA e scrive propri livelli, OWNER approva/audita; original/amendment separati, RESERVED nessun retry o sblocco, Telegram solo dopo consenso.
TradingView v0.8.186: protocollo V2 holdout1 23–29/11 UTC e holdout2 30/11–06/12 UTC, no vero clock indipendente/ingest prospettico attestato, NO EDGE dimostrato. Shark Science v0.4: COT, sentiment, delta/CVD, Effort/Result con mapping delle fonti da attestare. Experience v0.30 splash toro/orso 3D esplosione, pinna REMURA e SMF. Private Capture v0.15 sintetico non attivo. Oracle collector operativo, autoupdater fermo, release v1.65 staged signed root-owned non installare; Ampere Radar v0.36 per Milano/Telegram attivo. Backup, Squalincome e Telegram livelli approvati in roadmap.

Nessuna nuova spesa, deploy, merge main, D1 SQL, accesso a utenti reali o modifica Oracle autorizzata o eseguita in questa attività. Non ripetere suite concluse; preservare SHA, runs e roadmap in passaggio di consegne.

VERDETTO: 2/2 GraphQL POST autorizzati consumati; oggi EMPTY, ieri PRESENT; dati di consumo oggi non attestati. NO-GO.
