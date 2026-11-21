# REMURA Contributors v0.84 LAB — PUBLIC EVIDENCE CONTRACT

**Checkpoint: 21 novembre 2026 · ore 18:14 CET (Europe/Rome)**

## Sorgenti ed esecuzione effettivamente verificati
- Repository `mirkoworz/remura`, pubblico. Branch isolato `research/contributors-public-evidence-v084-20261121`.
- Base v0.83 `c56cc9f88dcc15e412e0b36b45a68147ea8bfb28`; il branch `main` **non è stato modificato**.
- Commit di codice **testato** `ab9ac0cf2cab036573f0082f78b83c4e1e296db2`.
- GitHub Actions one-shot https://github.com/mirkoworz/remura/actions/runs/44928767068: **SUCCESS**, log controllato `Ran 25 tests`, `OK`, `REMURA_V084_PUBLIC_EVIDENCE=25_25_PASS`.
- **25/25 test nuovi PASS**, senza suite storiche; runner standard di repository pubblico, `contents:read`, `persist-credentials:false`, nessun Secret, token, Cloudflare reale, Oracle, deploy, merge, migrazione SQL o spesa.

## Aggiunte isolate
1. `public_evidence_v084_lab.py`: classifica **solo un dizionario fornito offline** a schema esatto, con contatori opzionali di D1 read/write, Workers requests, D1 storage e totale DB. Non legge account, non parla con provider e non prende percorsi a file o URL.
2. Gli input extra, campi riservati, valori negativi/booleani, numeri troppo grandi, timestamp non correnti, contatori D1 e storage parziali, seat count incoerenti vengono rifiutati **senza riportare la fonte non valida nell'output**. Nessuna email, ID account, JWT, token o log grezzo pubblicati.
3. Quando righe D1 giornaliere non sono presenti, `d1_daily=UNKNOWN_NOT_ZERO`; anche un valore zero fornito esplicitamente è una *stima adattiva offline*, non rendicontazione esatta o attivazione.
4. Soglia prudenziale al 70% e limiti di riferimento nominali (5M D1 rows read, 100K rows write, 100K Workers requests; 5 GB account D1 e 10 DB): non certifica il piano contrattuale o la fatturazione, non determina spese reali, non sostituisce snapshot Provider.
5. **Cloudflare Access**: anche una stima manuale plausibile di plan e seats lascia `access_seats=UNKNOWN_NOT_ATTESTED` — niente autenticazioni reali o dati personali in LAB.
6. `test_public_evidence_v084_lab.py`: **25 test esclusivamente nuovi** di minimizzazione, finestre UTC, limiti nominali, zero ≠ assenza, campi imprevisti, PII e comportamento NO_GO. Workflow `.github/workflows/remura-contributors-v084-one-shot-ci.yml`.
7. Semafori forzati: `source_trust=OFFLINE_UNVERIFIED`, `real_provider_attested=false`, `billing_attested=false`, `automatic_deploy_allowed=false`, `decision=NO_GO`. Nessun input può autorizzare staging.

## Cloudflare Free — problema aperto
- Ultimo monitor D1 provider giornaliero noto del 21/11/2026 https://github.com/mirkoworz/remura/actions/runs/44919682812: **FAILED / INCOMPLETE** con `REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA`; D1 rows read/write **NOT_MEASURED**. Non sostituire con il GREEN del 20/11 e non chiamare il provider nel nuovo workflow.
- Workers 199 richieste *stimate*, 0 errori stimati; D1 4 DB, 6.557.696 byte in totale, TEST 6.266.880 byte: osservazioni dello stesso monitor, **non fatturazione**.
- Access seats Free/account plan: ancora **UNKNOWN**; NO_GO per staging. Non interpretare metriche vuote come zero o margine Free automaticamente garantito.
- Limiti da verificare su pagine Cloudflare aggiornate prima di uso reale: https://developers.cloudflare.com/d1/platform/limits/ e https://developers.cloudflare.com/d1/platform/pricing/ . Metriche GraphQL https://developers.cloudflare.com/d1/observability/metrics-analytics/ .

## Stato UI e roadmap coordinata
- Le quattro pagine private rimangono **v0.78 LAB** con banner data/ora Europe/Rome in alto; la scheda read-only separata rimane v0.80 LAB. v0.84 è **solo infrastruttura LAB**, nessuna pagina modificata.
- **v0.85 LAB proposto**: rendere ancora più rigoroso il dossier rollback/revoca e il boundary dei ruoli senza attivazione Cloudflare; per provare piano, seats e consumo reale occorre consenso separato alla consultazione del provider, rispettando Secret e Free. La ripetizione continua di test sintetici non sostituisce le prove reali mancanti.
- **Pilot Contributors**: 1–2 amici invitati via sito Access privato, lettura REMURA ma scrittura soltanto dei propri livelli autorizzati; l'OWNER revisiona e approva. Nuovi original-level e amendment separati, RESERVED non auto-sbloccabili, richieste perse senza retry automatico, audit append-only, Telegram solo dopo approvazione e autorizzazione esplicita.
- **TradingView v0.8.184 LAB** sviluppato in branch separato: copertura M5 per gli slot richiesti, holdout V2 bloccati **23–29 novembre UTC**, **30 novembre–6 dicembre UTC**. Non alterare protocollo o valutare edge su fixture; Shark Science v0.4 COT/sentiment/delta/CVD, ER/assorbimento rimane in roadmap scientifica.
- REMURA Experience v0.30 LAB splash toro/orso 3D, esplosione e logo REMURA pinna/SMF, foto utente da rimuovere; Safari fisico in futuro.
- Private Capture v0.15 LAB NON attivo. Oracle collector operativo con autoupdater bloccato e v1.65 firmata staged ma **NON installare**. Ampere Radar v0.36 monitor Oracle Milano/Telegram funzionante; backup reale, Squalincome e futuro relay Telegram livelli approvati preservati.
- Monitorare quote Free reali; niente modifiche a `main`, Cloudflare, Oracle, credenziali o nuovi costi senza autorizzazione specifica. Continuare da iPhone con GitHub; evitare suite già GREEN. Quando chat pesante fornire passaggio di consegne.

**v0.84 LAB GREEN 25/25, staging reale NO_GO.**