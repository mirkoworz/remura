# REMURA — ROADMAP CHECKPOINT V08 — 22 novembre 2026 (Europe/Rome)

**SOLO LAB. Checkpoint incrementale successivo a V07, senza modificare o sostituire V01–V07.**
Roadmap V07: research/remura-roadmap-v07-lab-20261122/research/REMURA-ROADMAP-CHECKPOINT-20261122-V07.md, commit 4ab8553cbf2342c6abc0e72f2a7c153927667d01. V07 rinvia ai checkpoint V01–V06, che restano integri.

## Lavori realmente eseguiti in questo passaggio

| Traccia | Branch e commit finale verificato | Nuovi test e prova GitHub Actions | Stato |
| --- | --- | --- | --- |
| A, COT v0.5 schema sidecar | research/cot-sidecar-cutover-v05-lab-20261122 @ 1625aad3bf20e19145f9fcda453cc6257c62991c | [45031817178](https://github.com/mirkoworz/remura/actions/runs/45031817178), **SUCCESS, 13/13**, log letto: Ran 13 tests, OK, REMURA_COT_SIDECAR_V05=13_13_PASS | LAB GREEN, Oracle NO-GO |
| C, Contributors v0.94 least privilege pilot scope | research/contributors-pilot-scope-v094-lab-20261122 @ c59ed284fa3a650ea28ec4456de3f8cf81e89f0a | [45031819839](https://github.com/mirkoworz/remura/actions/runs/45031819839), **SUCCESS, 16/16**, log letto: Ran 16 tests, OK, REMURA_CONTRIBUTORS_SCOPE_V094=16_16_PASS | LAB GREEN, pilot reale NO-GO |

Totale **29 test nuovi GREEN** senza eseguire alcuna suite storica v0.1–v0.4 COT o Contributors v0.92–v0.93. Nessuna API provider, nessuna chiamata Cloudflare, nessun Secret, nessun account reale, nessuna scrittura Oracle, nessuna spesa o merge.

### COT v0.5 — risultato tecnico e LIMITI
Codice: research/cot/cot_sidecar_cutover_v05_lab.py.
Test: research/cot/test_cot_sidecar_cutover_v05_lab.py.
Consegne Mac: research/cot/COT-SIDECAR-CUTOVER-V05-MAC-HANDOFF-20261122.md.

Il collector attuale scripts/cot_monitor.py contiene INSERT ... ON CONFLICT DO UPDATE sulla tabella cot_reports; cot_first_seen puo' restare alla prima osservazione mentre il valore viene sovrascritto. Questo e' un rischio reale nel CODICE, NON una corruzione Oracle dimostrata.

Il nuovo rehearsal usa esclusivamente SQLite **in memoria**, mai un percorso o una connessione reale. Replica le sole tabelle legacy necessarie, aggiunge tre tabelle nuove vuote con quattro trigger di immutabilita', esegue DDL in SAVEPOINT senza executescript() durante la transazione, verifica rollback con fault artificiale in due momenti e integrita' delle tabelle legacy prima/dopo. Non versione il legacy: gli snapshot passati restano UNATTESTED e non possono alimentare as-of scientifici. Nessun cutover sul collector vero, nessun backup reale, nessuna migrazione di produzione, nessun first-seen indipendente. Schema futuro solo preparatorio: Mac dovra' approvare backup reale, inventario schema, staging, prova recovery e dual-write prima di eventuale uso.

### Contributors v0.94 — risultato tecnico e LIMITI
Codice: research/contributors/contributors_pilot_scope_v094_lab.py.
Test: research/contributors/test_contributors_pilot_scope_v094_lab.py.
Consegne: research/contributors/CONTRIBUTORS-PILOT-SCOPE-V094-HANDOFF-20261122.md.

Piano deterministicamente compilato per un OWNER fittizio e 1–2 CONTRIBUTOR fittizi. Rifiuta identita' duplicate, stringhe non sintetiche, scope ampliato, approvazioni personali, lettura/scrittura su livelli di altri, accesso COT, Oracle, Secret e deploy. Il Contributor puo' consultare le sezioni previste e intervenire SOLO sui propri livelli; l'OWNER ha code, audit e approvazione di contributi di altri. Una impronta della matrice rileva alterazioni accidentali. Questa e' esclusivamente una **preview di intenti**: nessuna autenticazione Access JWT, autorizzazione server reale, ownership D1 effettiva, prova Safari o invito. I controlli veri restano sul Worker/D1 e richiedono integrazione successiva autorizzata. Il pilot e' NO-GO finche' quote, seats, piano, fatturazione e test fisico non saranno dimostrati.

## Stato degli altri filoni NON modificati
- B — TradingView v0.8.189: branch research/tv-per-decision-junction-v0189-lab-20261122, commit 1426e9e61128744ce65331e6f2517198ba9fa8fb, CI [45029099045](https://github.com/mirkoworz/remura/actions/runs/45029099045), 18/18 GREEN dopo correzione del solo caso test; v0.8.188 firewall 18/18 GREEN. Protocollo V2 immutato.
- D — Retail Myfxbook v0.6 receipts: branch research/retail-provenance-receipts-v06-lab-20261122, commit 458c57dcfd9c27ad5229059eae8d461b83efc815, CI [45029051564](https://github.com/mirkoworz/remura/actions/runs/45029051564), 14/14 GREEN. La catena locale hash NON e' prova notarizzata e il clock originario provider NON e' attestato. Myfxbook e' retail, non posizionamento istituzionale.
- A — COT revision v0.1 20/20, ingest atomico v0.2 16/16, WAL reopen v0.3 15/15, global integrity v0.4 12/12 GREEN; nuove prove v0.5 non sostituiscono questi risultati ne' autorizzano Oracle.
- C — Contributors v0.93 Free evidence gate 16/16 GREEN, PR #105 DRAFT NON MERGE; hardcap, revoca, ownership e router precedenti preservati; pilot NO-GO.
- E — Cloudflare Free: monitor .github/workflows/remura-cloudflare-budget-daily.yml gia' esistente, NON rilanciato. Run [44919682812](https://github.com/mirkoworz/remura/actions/runs/44919682812) e' FAILURE con D1 account quota **UNKNOWN_NO_GRAPHQL_DATA**. Workers, storage test e account nel log storico OK, NON certificano headroom attuale. Le due richieste GraphQL precedentemente autorizzate sono state consumate: non riusare consenso. Access seat count, billing e minuti GitHub Actions correnti UNKNOWN.
- F — Mac Codex Oracle, custodia backup, v1.65, autoupdater inibito e collector: NON TOCCATI; remura-collector branch codex/mac-custody-checkpoint-20261120, SHA noto 7a23f61b2cb1e520bff623348366231ee093bb3f. Experience v0.30 LAB: toro/orso 3D, collisione/loading, esplosione, REMURA/pinna, SMF ringraziamento e rimozione della foto, NON pubblicata. Private Capture v0.15 LAB isolato.
- G — Ampere Radar Oracle Milano e avviso Telegram gia' predisposti, NON riattivati.
- Altri — Shark Science, scoring istituzionale, forza relativa/Delta, Squalincome, condivisione livelli su Telegram rimangono roadmap, senza live attivazioni o rendimenti promessi.

## Protocollo scientifico V2 CONGELATO
- Development 16/11/2026 00:00 UTC -> 23/11/2026 00:00 UTC escluso.
- Holdout 1 23/11/2026 00:00 UTC -> 30/11/2026 00:00 UTC escluso (apertura 23 novembre alle **01:00 CET**).
- Holdout 2 30/11/2026 00:00 UTC -> 07/12/2026 00:00 UTC escluso.
- CVD vs price-only 60 minuti primario; 4h/24h secondari. FIFO M5, receipt entro close+120 s e prima del successivo close M5, 0/1/2 pip ipotetici, zero tuning e zero lookahead. Inizio finestra NON significa dati veri disponibili. Fino ad evidenza autentica temporale, comparatore verificato e coverage M5, **NO-GO alpha reale**.

## Prossime priorita' verso V09
1. Retail/TV: disegnare validazione dei veri payload temporali su singola decisione senza false firme o retrodatazioni; nessun witness installato automaticamente.
2. COT: coordinare con Mac una checklist di backup/schema/recovery e cutover additivo autorizzato; la V0.5 e' simulazione tecnica e basta.
3. Contributors: integrare solo dopo autorizzazione la futura matrice nel vero portale con enforce server-side, allineamento ruoli e test Safari iPhone; prima quota Cloudflare/Access/Actions corrente e costo Free effettivo.
4. Non eseguire di nuovo prove storiche gia' verdi, non modificare V2, non mischiare LAB e release app.
5. Qualsiasi vera pagina REMURA modificata in futuro deve mostrare **in alto** la versione pubblica aggiornata e data/ora Europe/Rome su ogni pagina. Nessuna pagina aggiornata qui.

**Verdetto V08:** 29 nuovi test GREEN su due branch isolati; LAB GREEN, pilot Contributors e trading edge reale NO-GO. Produzione, Oracle, Cloudflare, PR DRAFT e Mac preservati.
