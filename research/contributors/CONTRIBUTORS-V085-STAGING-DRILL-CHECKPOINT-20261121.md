# REMURA Contributors v0.85 LAB — STAGING E ROLLBACK REHEARSAL

**Checkpoint: 21 novembre 2026 · 18:19 CET (Europe/Rome)**

## GitHub effettivo
- Repository pubblico `mirkoworz/remura`; branch LAB isolato `research/contributors-staging-drill-v085-20261121`.
- Base confermata: `ef6c18051795128c353dc75d0d9f8a7fde54036b` (v0.84 LAB).
- Commit di CODICE testato: `bb1dd7fe152145f3c9bcae2cf006cb6fac5b0d4e`.
- GitHub Actions https://github.com/mirkoworz/remura/actions/runs/44929144889 — **conclusione SUCCESS**. Log verificato: `Ran 22 tests`, `OK`, `REMURA_V085_STAGING_DRILL=22_22_PASS`.
- **22/22 test NUOVI PASS**; non ritestate suite storiche. Nessun Secret, deploy, utente Access, D1 SQL, modifica collector, Oracle, merge o nuova spesa.

## Artefatti nuovi
- `staging_drill_v085_lab.py`: 14 verifiche documentali Free/Access/Workers/D1/fixture/Safari e percorso ordinato con 9 azioni per un futuro rollback, inclusi stop intake, deny policy, revoca sessioni, blocco scritture fixture, preservazione OWNER audit e RESERVED, rimozione route, verifica deny e signoff manuale OWNER. Nessuna di queste azioni viene eseguita.
- `test_staging_drill_v085_lab.py`: 22 test SOLO nuovi per dipendenze e ordine di rollback, dati sconosciuti, schema invalido, automazioni vietate e status NO_GO.
- `.github/workflows/remura-contributors-v085-one-shot-ci.yml`: runner standard pubblico GitHub, `contents:read` e `persist-credentials:false`, senza uso credenziali e senza chiamate Cloudflare.
- `CONTRIBUTORS-V085-OPERATOR-DRILL-RUNBOOK-20261121.md`: checklist manuale preparatoria, non autorizzante.
- Output forzato `stage=NO_GO`, `runtime_authorized=false`, `actual_provider_evidence_attested=false`, `automatic_deploy_allowed=false`, `automatic_rollback_allowed=false`, `automatic_retry_or_reserved_release_allowed=false`.
- Quattro UI private restano **v0.78 LAB**, banner versione/data già visibili in cima; nessuna pagina alterata. Readiness report statico rimane v0.80 LAB.

## Cloudflare Free e limiti
- Ultimo monitor D1 noto del 21 novembre: https://github.com/mirkoworz/remura/actions/runs/44919682812 — `REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA`, fallito/incompleto. `REAL_ACCOUNT_DAILY_USAGE=NOT_MEASURED`: NON si possono attestare righe read/write giornaliere né dedurre zero.
- Lo stesso monitor riportava Workers ~199 richieste giornaliere **stimate** e 0 errori stimati; D1 4 database, 6.557.696 bytes complessivi, TEST 6.266.880 bytes. Metadati e stime, NON fatturazione o prova seats.
- Posti Access Free e piano account reale **UNKNOWN**. Nessuno staging consentito, né vera migrazione/registrazione di collaboratori.
- La progettazione del rollback non certifica il comportamento effettivo di Cloudflare, JWT, logout o revoca. Prima del pilot serve consenso separato per collaudo di sola lettura sul provider, controllo della fatturazione e login fisico Safari.

## Roadmap generale
1. **Contributors v0.86**: completare una specifica precisa del *singolo* collaudo reale autorizzabile in lettura, con endpoint, dati minimizzati, budget richieste Free e divieto log PII. Non eseguire prima del consenso; evitare altro codice sintetico ripetitivo che non sblocca il provider.
2. Solo dopo quote e seats reali verificati: D1 fixture isolato/reversibile, allowlist e logout/revoca Safari, pilot 1–2 amici. Leggono REMURA, scrivono soltanto propri livelli autorizzati; OWNER approva con audit append-only. Original-level e amendment indipendenti, RESERVED nessuna liberazione o retry automatici, Telegram solo livelli approvati con autorizzazione.
3. TradingView v0.8.185 LAB su branch parallelo: ledger di evidenze M5 **sintetico e non ancorato**; holdout V2 immutati 23–29 novembre e 30 novembre–6 dicembre UTC. Non dichiarare alpha senza export completi e timestamp indipendenti.
4. Shark Science v0.4 LAB: COT/sentiment/delta CVD/assorbimento/Effort Result; proxy pubblici, non ordini istituzionali privati.
5. Experience v0.30 LAB splash toro/orso 3D, collisione/esplosione, REMURA pinna + logo/ringraziamento SMF, rimozione foto, Safari fisico futuro.
6. Private Capture v0.15 LAB NON attivato. Oracle collector attivo, autoupdater bloccato, v1.65 staged root-owned NON installare. Ampere Radar v0.36 Oracle Milano Telegram operativo. Backup reale, Squalincome e Telegram Contributors futuro preservati.
7. Niente Mac per attività GitHub LAB, non ripetere suite GREEN, monitorare quote gratis e fare passaggio di consegne con SHA/CI se la chat diventa pesante.

**Conclusione: v0.85 LAB 22/22 PASS; Cloudflare / staging / utenti reali NO-GO.**
