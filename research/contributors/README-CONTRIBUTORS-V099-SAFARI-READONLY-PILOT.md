# REMURA Contributors v0.99 LAB — Pilot Safari: matrice di accesso in sola lettura
**23 novembre 2026 · Europe/Rome · RAMO ISOLATO · REAL PILOT NO-GO**

## Cosa è stato costruito (nuovo rispetto a v0.98)
Il ramo parte da `research/contributors-pilot-owner-guard-v098-20261123` e aggiunge:
1. `pilot_readonly_fixture_v099_lab.mjs`: una funzione riutilizzabile `runPilotReadOnlyFixtureV099` per verificare in **una sola esecuzione offline** le risposte GET delle aree private esistenti, senza nessuna POST.
2. `test_pilot_readonly_fixture_v099_lab.mjs`: **11 casi nuovi** con il vero router composito v0.98 e profili sintetici distinti OWNER, CONTRIBUTOR A, CONTRIBUTOR B e ANON, oltre a controlli di errore/privilegi/cache.
3. Workflow dedicato `remura-contributors-v099-readonly-fixture-only.yml`: Node standard su repository pubblico, checkout senza credenziali persistenti, no Secret, no deploy. La suite storica non viene rilanciata.

L'operatore può selezionare **1 OWNER + 1 oppure 2 CONTRIBUTOR sintetici**: vengono eseguiti rispettivamente **14 o 18 GET** e nessuna POST. Le richieste sono **sequenziali e senza retry**, non archiviano risposte, identità o corpi HTML. Si registrano solo ID dello scenario e risultato. Accettano esclusivamente `Response` attese, MIME corretto, nessun redirect e intestazione `Cache-Control: no-store`.

I percorsi verificati comprendono `/owner/`, `/owner/levels/`, `/contributors/`, `/contributors/levels/`, asset JS OWNER, accesso ANON, query non consentite e percorso API che rifiuta GET. Un contributor che ottiene HTTP 200 su un percorso OWNER produce **FAIL**, non PASS.

## Limiti espliciti (non inventare risultati)
- L'opzione **`mode='OFFLINE_FIXTURE_ONLY'` non può essere usata come abilitazione di staging**: la funzione non contiene fetch, URL reali, credenziali, login, logout, registrazione o accesso diretto a Cloudflare.
- Il callback `send` dei test è un harness sintetico; i ruoli e i profili non sono verificati in Cloudflare o nel D1 autentico. Anche `FIXTURE_MATCHES_DESIGN` pone `providerVerified=false`, `safariVerified=false`, `revocationVerified=false`, `deploymentAuthorized=false` e `pilotAllowed=false`.
- L'assenza di una risposta, un 200 inatteso, un redirect, una risposta cacheabile o un MIME sbagliato **bloccano** l'esito; mai considerare il silenzio come successo.
- La prima revisione non esegue **POST read-only** (`/api/profile`, `/api/receipts`, coda/audit) né scritture; la vera ownership dei record e il flusso approvazione/revoca richiederanno staging privato e consenso separato.
- Il codice è solamente preparato su GitHub: NON è montato come `default fetch`, non è un deploy del Worker già presente, non configura Access o D1.
- **CI remota:** verificare run e log sul commit del workflow prima di dichiarare 11/11 PASS. Il sorgente aggiunto non equivale a test superato.

## Evidenze Free già acquisite il 23 novembre: NON ripeterle
Questi dati sono osservazioni personali da screenshot dashboard, NON quote congelate per giorni futuri:
- Access Teams Free Base e overview users 1/50 (margine di posti apparente, Billing complessivo non ancora attestato).
- Workers Free: 486 richieste su 100.000 e 386 Observability su 200.000 (filtro Today, 20:18 CET).
- D1: 4 database su 10; 258 righe lette/5 milioni e 928 scritte/100.000; circa 7,61 MB/5 GB (Daily, 20:17 CET).
- Worker già esistente denominato Contributors Staging: versione distribuita; nessun URL abilitato nell'overview e **0 invocazioni/0 errori** nelle 24 ore; CPU **0 ms con No data**, che NON è una misura p95. Mai stimare CPU da questo zero.

Solo il successivo consumo reale di staging può misurare overhead CPU e letture D1 del wrapper v0.98. Nessun aumento di spesa autorizzato; policy prudente REMURA: almeno 25% di margine sui limiti Free dove previsto da v0.97. Fatturazione e add-on non ancora confermati dall'importo completo.

## Passaggi futuri dopo esplicita autorizzazione dell'OWNER
- **GATE 0**: tariffazione completa e servizi aggiuntivi, quote correnti e isolamenti D1/Access/Worker confermati in dashboard; costi e accessibilità del sito attuale valutati prima di qualsiasi modifica.
- **GATE 1**: autorizzazione separata per STAGING privato con credenziali minime; non usare database fixture o produzione. Controllo policy Access deny-by-default, JWT e binding reale lato Worker.
- **GATE 2**: Safari iPhone con identità distinte, login/logout OWNER e CONTRIBUTOR, verifica GET/POST/headers cache e assenza di escalation privilegi.
- **GATE 3**: con consenso separato, livello di prova inviato da A, ricevuta persistente, isolamento A/B, review OWNER e audit; niente auto-approvazione o retry incerti.
- **GATE 4**: prova di revoca completa in D1, policy Access e sessione; GET/POST vietate con tab già aperta e nuovo login negato; rollback e stop in caso di incertezza.
- **GATE 5**: registrare effettivo overhead Workers CPU, righe D1 e fatturazione; decidere un'eventuale apertura a collaboratori reali **solo con nuova autorizzazione esplicita**.

**Non ci sono adesso utenti reali, attivazione Access, esecuzione HTTP, deploy, modifica Cloudflare, SQL D1, nuovo DB, cambi Oracle, Mac o merge. La PR #105 resta Draft.**
