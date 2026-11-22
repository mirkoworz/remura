# REMURA Retail — Myfxbook pinned real replay v0.2 LAB
**22 novembre 2026 (Europe/Rome), solo repository, nessuna acquisizione live.**

## Nuovo risultato controllato
- Branch: `research/retail-replay-real-file-v02-20261122`
  partito dal `main` `7c70bb9fd0e774d45c493217382c430b448af0e2`.
- Nuovo codice `research/retail/myfxbook_pinned_real_replay_v02_lab.py`.
- Nuovi 12 test in `research/retail/test_myfxbook_pinned_real_replay_v02_lab.py`.
- Log GitHub Actions **44999524905**
  https://github.com/mirkoworz/remura/actions/runs/44999524905
  **12/12 PASS**, `REMURA_RETAIL_PINNED_REAL_V02=12_12_PASS`.
- Input reale: `data/myfxbook/history/EURUSD.json`, blob Git
  `8e0ca3c9bae596c0d5145d1e9e6994cf6a39e5a9`, e
  `data/myfxbook/latest.json`, blob
  `c2c4dfc6546fa26e315400995132fc60170cede1`.
  Sono riferimenti del commit storico, non dati di mercato in diretta.
- Lo snapshot di fine archivio EURUSD in quel commit è
  `2026-11-22T01:36:15Z`. Una decisione di esempio
  `2026-11-20T12:00:00Z` seleziona soltanto il campione precedente
  `2026-11-20T11:18:32Z`, non quello del 22 novembre.
- Record precedente all'inizio dell'archivio => `UNKNOWN`, mai zero.
  Timestamp diversi da UTC canonico, file sostituiti e SHA di file mutati
  falliscono chiusi. Nessun file archivio è stato modificato.

## Interpretazione scientifica corretta
Questo è un **replay di valori reali conservati su GitHub**, non una verifica
della prima pubblicazione Myfxbook, del first-seen osservato da terzi,
dell'ora esatta di commit accettata da GitHub né della disponibilità per
l'operatore alla decisione storica. `t` è l'ora scritta nel record,
non un certificato indipendente. Il checksum Git certifica identità dei
byte rispetto al commit dato, non il tempo originale del provider.

Non è stato ripetuto l'audit generale storico (34 file / 3.984 osservazioni
in uno snapshot precedente), né è stato rifatto il fetch provider.
Nessun confronto futures/spot COT o TradingView ammesso; nessun edge,
segnale trading o rendimento attestato.

## Prossimo gate concreto
Per ogni campione da usare in prospettiva conservare payload **immutabile**,
identità decisione, ricezione locale e witness temporale indipendente quando
ottenibile. Per dati storici legacy senza prova di ricezione all'epoca,
conservare `REPOSITORY_REPLAY_UNATTESTED` e impedire qualsiasi promozione
automatica in un campione out-of-sample. Collegare CFTC solo con mapping
strumentale verificato e dati COT revisionati correttamente `as_of()`.

**Risultato: test real-file PASS, first-seen/scientific admission NO-GO.**
