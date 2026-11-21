# REMURA — COT Revision Lineage LAB v0.1 — passaggio a Mac/Oracle
**Checkpoint:** 22 novembre 2026, circa 00:00 CET (Europe/Rome). **SOLO RICERCA.**

## Perché è un gate scientifico bloccante

Il collector `scripts/cot_monitor.py` nell'`main` `06ebde2ce740f92fd8b44d5eb3c9d6faa57c7a07` aggiorna le posizioni in `cot_reports` con
`INSERT ... ON CONFLICT(dataset,code,report_date) DO UPDATE`.
La tabella `cot_first_seen` è invece scritta solo per chiavi nuove (INSERT OR IGNORE,
senza backfill). **Le due tabelle NON attestano il contenuto originale di una
riga dopo una correzione CFTC.** Un backtest che associa al timestamp originale
valori revisionati successivamente incorre potenzialmente in lookahead bias.

La differenza è stata **riprodotta con il codice reale del collector**, chiamandolo
SOLO con un `fetch` sintetico iniettato e un SQLite temporaneo privato.
Nessuna modifica Oracle, richieste CFTC, scritture live, Cloudflare o Secret.

Non esiste alcuna evidenza, in questo test, che il database reale sia già stato
revisionato o contaminato. L'effetto è un rischio dimostrato del codice.

## Nuovo candidato: valore per valore e ora per ora

- Branch isolato `research/cot-revision-lineage-lab-20261121`;
- Modulo `research/cot/cot_revision_lineage_v01_lab.py`:
  database **esclusivamente in memoria**, accesso obbligatorio `synthetic=True`;
  conserva per ogni chiave CFTC (dataset, code, report_date) versioni append-only,
  timestamp locale dichiarato, digest SHA-256 e **cinque valori CFTC originali**.
  Trigger SQLite vietano UPDATE e DELETE delle versioni;
- `as_of(decision_utc)` restituisce solo la versione registrata localmente
  entro quella decisione. Se manca la cattura, risposta `UNKNOWN`: NON zero,
  NON retrodato, NON uso del COT corrente in backtest storico;
- L'orologio NON è attestato da terzi. Il digest locale NON firma la provenienza,
  non prova data pubblicazione CFTC, latenza, indipendenza o effettiva conoscibilità;
- `as_of` NON normalizza futures e spot FX: la mappatura è un lavoro distinto
  del filone Shark Science e richiede prova specifica;
- Non contiene alcun handler Worker, endpoint pubblico o automazione trading.

## Evidenza CI reale

- Run **[44959558919](https://github.com/mirkoworz/remura/actions/runs/44959558919)**, commit codice `df52f133cb59a28654ad102427c8a5b0df1e18f9`;
- **20/20 PASS**, zero fail. Log controllato:
  `REMURA_SHARK_COT_REVISION_LINEAGE=20_20_PASS`;
- 16 casi con la modifica iniziale inclusa, 4 casi aggiunti
  per recuperare valori autentici del fixture prima/dopo la revisione;
- Non sono stati rieseguiti i test precedenti di TradingView, Contributors,
  Mac Experience, Private Capture, Oracle witness, né il COT collector generale.

## Integrazione futura su Mac: NON ESEGUIRE SENZA VIA LIBERA

1. Coordinate con **Codex Mac**, proprietario dei lavori Oracle collector v1.65
   e custodia backup. Verificare lo SHA del suo branch corrente in
   `mirkoworz/remura-collector` prima di pianificare.
2. Non modificare `scripts/cot_monitor.py` nell'`main` operativo né
   il database Oracle senza autorizzazione specifica.
3. Predisporre *in una PR di staging separata* una migrazione **solo additiva**
   `cot_report_versions`, con trigger append-only e cutover osservazioni
   future. Nessuna popolazione retrodatata da `cot_first_seen`.
4. Acquisire una versione, la sua firma/integrità e il suo *time of reception*
   **nella stessa transazione** e prima di rendere disponibili i dati aggiornati
   ai consumer. Verificare comportamento in crash, transazione rollback, ripetizioni,
   conflitti e aggiornamento atomico. Stop alle revisioni se provenance non certa.
5. Ancorare indipendentemente il momento di ricezione, o dichiararlo non attestato.
   Conservare compatibilità con schema legacy e consumer, senza attribuire
   maggiore fiducia a `cot_first_seen` originale di quella dimostrata.
6. Backup SQLite nuovo e verificato, test offline + CI e recupero, controllo
   risorse Free, installazione protetta e revoca/rollback solo dopo consenso.
   Collector e autoupdater restano nelle condizioni già verificate su Mac.
7. Prima dell'holdout TradingView del 23/11 UTC, nessuna inclusione prospettica
   senza fonte realmente acquisita, identità decisione, clock e first-seen validi;
   nessuna conclusione di edge o profitto da soli test sintetici.

**Stato: NO-GO reale, LAB PASS; nessuna attivazione, deploy, merge o nuova spesa.**
