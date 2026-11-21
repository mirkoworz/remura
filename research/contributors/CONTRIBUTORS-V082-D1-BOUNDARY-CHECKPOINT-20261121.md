# REMURA Contributors v0.82 LAB — D1 TRANSPORT BOUNDARY E STAGING GATES

**Checkpoint: 21 novembre 2026 · dopo GitHub Actions delle ore 18:00 CET (Europe/Rome)**

## Stato verificato
- Repo: `mirkoworz/remura` **pubblico**.
- Branch isolato: `research/contributors-offline-d1-boundary-v082-20261121`.
- Base: v0.81 `d0a89ebf5ded48ff759bca7f00ec07db388011ba` (source lock v0.78 mantenuto; `main` NON modificato).
- Commit **effettivamente testato**: `f81f5482f3483217da847842fc74b7bdfa532067`.
- Nuova run: https://github.com/mirkoworz/remura/actions/runs/44927671870 — conclusione **SUCCESS**.
- Log verificati: `Ran 24 tests` / `OK`; `Ran 14 tests` / `OK`; `REMURA_V082_OFFLINE_BOUNDARY=38_38_PASS`. Totale **38/38 nuovi test PASS**.
- Non rieseguite suite v0.81/v0.80/v0.79 né test storici; CI read-only, senza Secret e senza chiamate Cloudflare, Oracle, market data, deploy, merge o costi approvati.

## Due lavori svolti nello stesso aggiornamento
1. `d1_evidence_boundary_v082_lab.py`: classifica **solo buste GraphQL fornite offline** per la finestra UTC oggi e ieri. Casi: risposta HTTP 200 JSON, 401/403, 429, 5xx, timeout, errore di rete, body troppo grande, timestamp futuro/stale, inventario D1 invalido, errori GraphQL, gruppi vuoti oggi e ieri. Riuso della funzione di triage già collaudata v0.80. Non accetta URL, token o argomenti per vere query; non estrae identificativi in output.
2. `staging_gate_matrix_v082_lab.py`: matrice di **14 gate** fra Free plan, D1 daily, Workers, Access billable seats, allowlist/JWT, ruoli, asset privati, fixture isolata, Safari reale, flussi `original-level` e `amendment` distinti, RESERVED fail closed, OWNER audit append-only e rollback. In nessuna condizione un input LAB produce autorizzazione staging.
3. Due suite aggiunte (`test_d1_evidence_boundary_v082_lab.py`, `test_staging_gate_matrix_v082_lab.py`), 24 + 14 casi nuovi; workflow one-shot `.github/workflows/remura-contributors-v082-one-shot-ci.yml`.
4. `query_digest`, `inventory_digest` e `run_id` sono **metadati inseriti nel campione**, non ricevute indipendenti o attestazioni di Cloudflare. Un gruppo presente è una stima adattiva, non fatturazione; `[]` oggi NON dimostra zero.
5. Output `decision=NO_GO`, `automatic_deploy_allowed=false`, `d1_daily_usage_attested=false`, `input_attested=false`. Il contratto ruoli è documentale: non costituisce test runtime degli Access JWT reali.

## Cloudflare reale — BLOCCO PERSISTENTE
- Ultimo monitor Cloudflare giornaliero trovato, **21/11**: https://github.com/mirkoworz/remura/actions/runs/44919682812, **FAILED** per `REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA`. D1 rows read/write quotidiane **NOT_MEASURED** e Access Free seats **UNKNOWN**: `NO_GO`.
- Nella stessa run: Workers ~199 richieste stimate e ~0 errori; 4 D1 database, storage 6.557.696 byte totali e 6.266.880 byte TEST. Nessuna di queste evidenze prova il consumo di righe D1 odierno o seats fatturabili.
- Il monitor del 20/11 GREEN è storico e non deve essere riusato per riempire il vuoto del 21/11.
- Nessun uso dei Secret esistenti, nessuna modifica al monitor `main`, nessuna query SQL su D1, nessun provider runtime.
- Dati reali su piano Free e Access seats richiedono verifica autorizzata e con provenienza; non inserirli nel repo pubblico.
- Fonti Cloudflare da ricontrollare prima di un'eventuale attivazione: https://developers.cloudflare.com/d1/observability/metrics-analytics/ ; https://developers.cloudflare.com/d1/platform/limits/ ; https://developers.cloudflare.com/cloudflare-one/team-and-resources/users/seat-management/

## Roadmap completa preservata, prossimo filone v0.83
1. Preparare offline una **specifica di acquisizione di sole evidenze consentite e anonimizzate** per il monitor D1/Access, con timeout, campi in allowlist, controllo provenienza e divieto echo di identità; eventuale interrogazione live con Secret necessita **consenso specifico**. Se dati mancanti, `NO_GO`.
2. Verificare Access Free plan/seats effettivi, allowlist deny-default, JWT `ctx.access`, same-origin, D1 fixture separata e rollback PRIMA di login reale; test Safari login/logout/revoca solo dopo autorizzazione staging.
3. Pilot 1–2 Contributors: leggono REMURA, propongono **solo** i livelli propri autorizzati, ricevute personali; OWNER approva/audita, senza auto retry, auto unlock RESERVED, livelli esterni né Telegram pre-approvazione.
4. TradingView v0.8.181 LAB e preparazione calendario v0.8.182 su branch separato: holdout1 23–29/11 UTC, holdout2 30/11–06/12 UTC; protocollo prospettico immutato, nessuna prova di edge prima dei risultati OOS validi. Shark Science v0.4 LAB analizza COT, sentiment, delta/CVD, assorbimento, ER come proxy.
5. Experience v0.30 LAB: toro/orso 3D, collisione, esplosione, logo pinna REMURA e ringraziamento SMF, rimozione foto; verifiche iPhone/Safari fisico future.
6. Private Capture v0.15 LAB STOP; Oracle collector operativo, autoupdater fermo, v1.65 firmata staged root-owned **NON installare**. Ampere Radar v0.36 con monitor Oracle Milano e Telegram operativo; backup reale, Squalincome e Telegram per livelli approvati rimangono in roadmap.
7. Monitorare quote Free reali senza presumere zero se `UNKNOWN`. Quando chat pesante, consegna con branch SHA, CI, stato semafori; niente Mac richiesto per LAB.

## Versioni UI
Nessuna UI privata modificata in v0.82. Le quattro pagine private restano **v0.78 LAB con data/ora in alto**; la pagina snapshot readiness esterna resta v0.80 LAB. La v0.82 è update tecnico: non dichiarare release live.

**Staging e release reali: NO_GO.**
