# REMURA Contributors v0.79 LAB — FREE VISIBILITY E STAGING SOURCE LOCK

**Checkpoint confermato: 21 novembre 2026 · ore 17:12 CET (Europe/Rome)**

## Repository, branch e prova verificata
- Repository: `mirkoworz/remura` (**pubblico**), branch isolato `research/contributors-free-visibility-v079-20261121`.
- Base v0.78, mantenuta e non modificata: `14c3207a6b7508bbc181f825cad36a0e933bc3fd`.
- GitHub Actions v0.79 GREEN (solo dati sintetici e sorgenti del repository): https://github.com/mirkoworz/remura/actions/runs/44922951396
- Commit sottoposto a test: `c57f738c0f921988abbc7d6e2a3e802fc064ab13`.
- **89 test nuovi PASS / 0 FAIL**, log `Ran 89 tests`, `OK`, `REMURA_V079_FREE_VISIBILITY=89_89_PASS`.
- **53/53** controlli quote e anomalie; **36/36** verifiche di integrità byte, sorgenti pinned e assenza di attivazione.
- La CI compila solo i nuovi file v0.79; non rieseguiti v0.78 (50/50), v0.77 (56/56), v0.76 (64/64), v0.75 (50/50), v0.74 (55/55), v0.70 (24/24), v0.66/v0.67.
- Nessun deploy Cloudflare, Secret/identità, SQL su D1 reale, merge, Oracle, collector, nuove spese o modifica `main`.
- **Release UI privata resta v0.78 LAB**: nessuna delle quattro pagine iPhone è stata modificata in questo filone v0.79. Tutte e quattro mostrano già versione/data v0.78 in alto. v0.79 è esclusivamente un aggiornamento LAB di monitoraggio e sicurezza con data/ora qui in cima; non spacciare una versione UI nuova.

## Problema D1 del 21 novembre — risolto o no?
**NON RISOLTO sul provider**. Il monitor quotidiano:
https://github.com/mirkoworz/remura/actions/runs/44919682812
ha `REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA` / `REAL_ACCOUNT_DAILY_USAGE=NOT_MEASURED`, ed è terminato `INCOMPLETE_OR_CRITICAL` / failure per mancanza dei dati GraphQL giornalieri D1.

Le altre osservazioni dello stesso run:
- Workers adaptive estimate `OK`, **199 richieste/giorno UTC**, **0 errori**;
- D1 TEST storage `OK`, **6.266.880 byte** (1,2534% dei 500.000.000 byte nominali);
- D1 account storage `OK`, **4 database**, **6.557.696 byte** in totale su 5.000.000.000 byte nominali;
- contatori D1 rows read / rows written **NON MISURATI** il 21/11, e Access seats Free **NON VERIFICATI**.
- Il report GREEN D1 del **20 novembre** non può diventare prova dei consumi del **21 novembre**.
- Fonti ufficiali consultate: https://developers.cloudflare.com/d1/observability/metrics-analytics/ (aggiornata 6/11/2026); https://developers.cloudflare.com/d1/platform/limits/ ; https://developers.cloudflare.com/d1/platform/pricing/ . `d1AnalyticsAdaptiveGroups` registra eventi quando raggiungono l'SQL, e non prova zero uso quando vuoto.
- Impostazione adottata: **NO_GO** staging se quota D1 giornaliera sconosciuta; non significa superamento quota o costo addebitato. Non invocare query di test per produrre metriche.

## Nuovi strumenti offline, nessun segreto
1. `free_quota_evidence_v079_lab.py`: parser di soli log pubblicabili, include quattro gruppi (D1 row daily, Workers daily, D1 TEST storage, D1 account metadata); verifica data UTC corrente, sorgente Adaptive GraphQL, presenza contatori, limiti Free nominali, soglia prudenziale al 70%, aggregati coerenti e Access Free seats come evidenza separata. Input reali mancanti ⇒ `NO_GO`. Nel caso sintetico completo con indicazione seats, output massimo `LAB_REVIEW_ONLY`; campo `automatic_deploy_allowed=false` sempre. **NON è un sistema per autorizzare deploy** né usa rete, token, OAuth o Cloudflare.
2. `diagnostic(today,yesterday)` nello stesso modulo: classifica presenza/assenza dei dataset GraphQL **forniti come fixture**. Zero gruppi oggi e gruppi ieri resta UNKNOWN, non zero consumi. Non effettua nuove chiamate al provider.
3. `staging_source_lock_v079_lab.py`: confronto offline con gli SHA-1 **Git blob** di **14 file critici** esatti della baseline v0.78 (composizione, router, asset bundle, Access, D1, nuovi livelli, audit, SQL, HMAC). Se un file è assente, modificato, symlink o dimensione sospetta ⇒ errore; controllo che il runtime sia candidato NON deployabile. Lo SHA-1 blob è un controllo deterministico di byte Git, **non una firma crittografica del deploy**.
4. `test_free_quota_evidence_v079_lab.py`: **53 casi** di metriche mancanti/vecchie/contraffatte, zero vero vs zero non misurato, limiti e soglie, source metadata, sanitizzazione log, output non autorizzante, access seats non certificati, argomenti CLI.
5. `test_staging_source_lock_v079_lab.py`: **36 casi** (14 blob univoci, 22 controlli) per drift, manipolazione file, SHA, NUL Git, symlink, path escape, validità bundle, no deployment.
6. Workflow isolato `.github/workflows/remura-contributors-v079-one-shot-ci.yml`: branch pinned + messaggio commit esatto; GitHub pubblico runner standard, `permissions: contents:read`, checkout `persist-credentials:false`, nessun Secret, npm, Cloudflare o deploy. La CI non ha attivato il monitor reale del branch main.
7. `CLOUDFLARE-D1-GRAPHQL-UNKNOWN-V079-RUNBOOK-20261121.md`: runbook a costo zero, con cause possibili, diagnosi senza query SQL, nessuna falsa compensazione con vecchi dati e approvazioni specifiche richieste.

## Stato semafori
| Dimensione | Esito |
|---|---|
| Nuove verifiche v0.79 | GREEN sintetico, 89/89 |
| Source lock v0.78 | 14/14 Git blob byte match |
| Monitor Workers 21/11 | OK, **stime**, non fatturazione |
| D1 Storage account | OK, snapshot di metadati |
| **D1 righe lette/scritte oggi** | **UNKNOWN — NO_GO** |
| **Access Free seats effettivi** | **UNKNOWN — NO_GO** |
| Access JWT e logout reali Safari | **NON COLLAUDATI — NO_GO** |
| D1 staging isolato/migrazioni | **NON ATTIVATI** |
| Production / release Web | **NON ATTIVATA** |
| Spese nuove | **Nessuna autorizzata o introdotta** |

## Roadmap completa e prossimi passi
1. **Contributors v0.80 LAB**: preparare una procedura di diagnosi read-only SOLO su evidenze recenti Cloudflare D1, confrontando oggi/ieri senza trasformare `UNKNOWN` in zero, e verificare in modo conservativo se l'uso reale può essere attestato. Se manca metrica, fermarsi senza deploy.
2. Affinare il prototipo Access: policy allowlist, same-origin direct Worker con `ctx.access`, roles D1, Secret non versionati, Worker asset bundle dichiarativo senza default fetch attivo. Preparare un piano di rollback e prova Safari senza richiedere Mac.
3. Ottenere autorizzazione specifica per staging Cloudflare Free **soltanto dopo** un report contatori completo e seats Access confermati; usare fixture dedicato, snapshot prima/dopo, revoca/login/logout e nessun profilo reale all'inizio.
4. Pilot 1–2 collaboratori: consultare REMURA ma scrivere **esclusivamente** i livelli propri autorizzati; OWNER approva e registra evidence audit, nessun invio automatico a Telegram prima di approvazione. I flussi `original-level` vs `amendment` non vanno mescolati.
5. TradingView v0.8.181 LAB: holdout1 23–29 novembre UTC, holdout2 30/11–06/12 UTC, nessuna pretesa di alpha senza holdout; Shark Science v0.4 LAB (COT, sentiment, delta/CVD come proxy e non accesso a ordini segreti).
6. Experience v0.30 LAB splash toro/orso 3D ed effetti, logo REMURA pinna e ringraziamento SMF; Private Capture v0.15 LAB STOP; Ampere Radar v0.36 operativo; Oracle collector attivo, autoupdater bloccato, v1.65 NO-GO install; backup, Squalincome e futuro relay Telegram preservati.
7. Mantenere monitor Free; se una misura diventa UNKNOWN, spiegare la mancanza e non presumere né costo zero futuro né quota superata.

## Sicurezza e versioni
- Repo `remura` è **pubblico**: NO email/nomi reali/chiavi HMAC/Cloudflare/IDs di account/token/password/livelli privati nei commit.
- Nessuna nuova risorsa GitHub a pagamento: un solo job sintetico standard pubblico, già completato.
- UI v0.78 (non cambiata); **v0.79 è checkpoint infrastruttura**. Data/ora di checkpoint disponibile in alto.
- Non serve il Mac per la prossima attività LAB; non ripetere le suite già concluse.

**NO-GO staging reale. Fine checkpoint v0.79.**
