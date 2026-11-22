# REMURA TradingView v0.8.187 LAB — evidence ledger
**22 novembre 2026 (Europe/Rome). Pronto per diagnostica, non per dichiarare risultati.**

## Nuovo lavoro
- Branch `research/tv-prospective-admission-gate-v0187-20261122`.
- Codice puro offline `holdout_evidence_ledger_v0187_lab.py`.
  Usa il `guard()` già registrato di `holdout_freeze_v0182_lab.py`,
  mantenendo congelato byte per byte `CVD-PROSPECTIVE-PROTOCOL-V2.md`.
- `test_holdout_evidence_ledger_v0187_lab.py`: **20 test nuovi**.
- GitHub Actions run https://github.com/mirkoworz/remura/actions/runs/44999527898
  SUCCESS; verificato `Ran 20 tests`, `OK`,
  `REMURA_TV_V0187_HOLDOUT=20_20_PASS`.
- Classifica soltanto record sintetici forniti esplicitamente:
  singola identità decisione, orario chiusura M5, ricezione dichiarata,
  SHA-256 dichiarato, ID del confronto price-only e riferimento testimone.
  Se ricevuto oltre close+120 secondi o con timestamp conflittuale => no;
  se non esiste timestamp => UNKNOWN; duplicati => quarantena.
  La presenza di riferimento witness **non equivale alla sua verifica**.
- Conteggia le classi per fold. Il denominatore sono i record **forniti**,
  non le ore di mercato o le barre che si sarebbero dovute ricevere.
  Nessun outcome, FIFO applicato, PnL, backfill o tuning.

## Vincoli congelati
- Development [16/11 00:00 UTC, 23/11 00:00 UTC).
- Holdout 1 [23/11 00:00 UTC, 30/11 00:00 UTC).
- Holdout 2 [30/11 00:00 UTC, 07/12 00:00 UTC).
- Primario CVD vs price-only **60 minuti**; secondari 4h e 24h,
  costi ipotetici 0/1/2 pip secondo protocollo V2.
- Nessuna modifica al protocollo; nessuna acquisizione reale.
- Al 23/11 alle 01:00 italiane cambia la finestra **di calendario**,
  non lo stato delle evidenze. Non inventare quote, riscontri, dati CVD o
  timestamp indipendenti.

## Prima di autorizzare osservazioni vere
Richiedere originali TradingView autentici con percorso di ricezione,
identità M5, durata e fonte, SHA del payload, clock credibile,
verifica indipendente del testimone, controllo duplicati, esatti ID
della decisione e comparator, copertura reale e definizione di missingness.
Mantenere le classificazioni `NO_GO_REAL_HOLDOUT_ADMISSION` fino alla
prova di tutti i gate. Nessuna inferenza di edge o profitto.

**Risultato: ledger fixture 20/20 PASS; evidenza prospettica reale NO-GO.**
