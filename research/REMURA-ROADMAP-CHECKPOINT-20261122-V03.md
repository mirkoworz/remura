# REMURA — checkpoint multiplo v0.3 (22 novembre 2026, Europe/Rome)

**Nuovo avanzamento** su quattro filoni, sempre separato da `main`.
Il documento precedente rimane `research/REMURA-ROADMAP-CHECKPOINT-20261122.md`.
Nessuna modifica a Oracle live, Cloudflare, Secrets, utenti, trading operativo,
PR DRAFT o file Experience/Private Capture/Codex Mac.

## Operazioni appena concluse
| Filone | Nuovo branch / riferimento | Risultato verificato |
| --- | --- | --- |
| A — Shark Science | `research/cot-wal-reopen-v03-lab-20261122`; `research/cot/COT-WAL-REOPEN-V03-MAC-HANDOFF-20261122.md` | WAL + chiusura/riapertura su DB effimero, 15/15 PASS, Actions 44999165979 |
| D — Retail × COT | `research/retail-cot-asof-pair-v01-lab-20261122`; `research/retail/RETAIL-COT-ASOF-PAIR-V01-HANDOFF-20261122.md` | Confronto as-of sintetico per singola decisione, 20/20 PASS, Actions 44999167732 |
| B — TradingView | `research/tv-decision-evidence-contract-v0186-20261121` | Preflight holdout 23/11 già documentato, protocollo V2 NON toccato |
| C — Contributors | `research/contributors-access-free-hardcap-v092-20261121` | Gate del pilot 1–2 amici già documentato, nessuna registrazione, NO-GO reale |
| E — Mac | Experience v0.30, Private Capture v0.15, Oracle v1.65 custody | Nessuna sovrapposizione con Codex Mac |
| F — Quote | GitHub Actions usa workflow sintetici on push, no Cloudflare API | Margini residui Cloudflare UNKNOWN e non interpretati come zero |

**Nuove prove, non ripetizioni:** per COT v0.3 15 test nuovi; per Retail × COT 20 test nuovi. I 20/20 COT v0.1, 16/16 COT v0.2, 11/11 audit Myfxbook e 22/22 hardcap Contributors non sono stati rieseguiti.

## Decisioni di ammissione
- Un report COT corretto dopo una decisione non può sostituire i valori conosciuti prima.
  La prova ora copre anche persistenza dopo riapertura di un SQLite TEMPORANEO,
  ma NON un crash reale o Oracle.
- Myfxbook = retail; CFTC = futures per categorie; rapporto spot/futures non
  deducibile dal nome. Nuovo pairing produce solo una coppia dichiarata
  `LOCAL_PAIR_UNATTESTED_FIXTURE_ONLY`, mai prova di first-seen indipendente.
  Le versioni successive, i conflitti e i dati non comparabili sono rifiutati.
- Per il **23 novembre 2026, ore 00:00 UTC (01:00 Europe/Rome)**, la finestra
  holdout TradingView 1 si apre per calendario, NON per evidenza di CVD reale;
  resta NO-GO per inferenza senza dati autentici, anchor indipendente, mappa
  corretta e coverage M5, secondo V2 congelato.
- Contributors: no-gate per accesso di amici finché non sono confermati i
  limiti reali Workers/D1/Access e login/logout/revoca Safari iPhone fisico,
  con consenso specifico per ogni azione sul provider.
- Main al checkpoint iniziale `7c70bb9fd0e774d45c493217382c430b448af0e2`,
  ultimo aggiornamento automatico Myfxbook; confermare SHA solo se muta
  qualcosa e non confondere con commit LAB.

## Blocchi / prossime priorità
1. **COT in Mac (solo piano):** backup e migrazione additiva atomica soltanto
   dopo coordinamento Codex, crash/recovery su file realmente persistente,
   fonte/timestamp attestabili e autorizzazione dedicata.
2. **TradingView:** al cambio finestra classificare evidenze vere per decisione
   senza retrodatarle. Mancanza dati = UNKNOWN, non risultato negativo.
3. **Contributors:** verifica quote reali Cloudflare mediante consenso nuovo,
   poi staging privato controllato e prova iPhone reale.
4. **Retail:** collegare a osservazioni autentiche con payload storico,
   clock, origine e mapping indipendentemente verificato; solo dopo valutare
   la capacità di prevedere il futuro out-of-sample.
5. **Budget:** nessuna spesa nuova autorizzata; non assumere quote Free
   semplicemente dalla presenza di log GREEN.
6. **Version UI:** quando si toccano pagine vere REMURA, versione + data/ora
   Europe/Rome in cima a ogni pagina; questo checkpoint non modifica UI.

**Stato generale: LAB GREEN su nuovi fixture, pilot e alpha reali NO-GO.**


## Appendice operativa — avanzamento successivo del 22 novembre 2026
Questa sezione integra, senza annullare, i gate e le evidenze sopra.
Non sono state ripetute suite storiche.

| Nuovo filone LAB | Branch / commit checkpoint | Esecuzione nuova |
| --- | --- | --- |
| Retail vero, archivio puntuale EURUSD | `research/retail-replay-real-file-v02-20261122`, docs HEAD `6fd325906f1014f29d40cf01077f6b28687b25b6` | GitHub Actions `44999524905`, **12/12 GREEN** (log letto) |
| TradingView ledger v0.8.187 | `research/tv-prospective-admission-gate-v0187-20261122`, docs HEAD `af3448b114cc0a181d8b8a3d03686a37d293220d` | GitHub Actions `44999527898`, **20/20 GREEN** (log letto) |

**Retail osservato:** per la prima volta in questo sottotrack viene eseguito un
replay puntuale su **due file JSON reali del repository**, bloccati agli hash
Git blob del `main` `7c70bb9`. File `data/myfxbook/history/EURUSD.json`
e `data/myfxbook/latest.json`: esempio decisione
`2026-11-20T12:00:00Z` seleziona il campione locale precedente
`2026-11-20T11:18:32Z`, invece del valore del 22 novembre.
L'identità dei byte è verificata sul commit, NON il tempo di prima
pubblicazione o quello di ricezione osservato da un testimone indipendente.
Non è stato rifatto l'audit di tutti i 34 file, né effettuato un fetch Myfxbook.

**TradingView v0.8.187:** nuovo registro esclusivamente sintetico che controlla
gli ID di singole decisioni, il prezzo di confronto, la barra M5, la ricezione
dichiarata entro 120 secondi, la fascia holdout V2, la deduplicazione e il
riferimento witness **non verificato**. Ritorna sempre
`NO_GO_REAL_HOLDOUT_ADMISSION`: classificare record non significa autorizzare
i dati di mercato. Il denominatore è il numero di record forniti, **non** le
barre di mercato previste. Protocollo V2 e precedenti suite immutati.

Documenti:
- `research/retail/MYFXBOOK-PINNED-REAL-REPLAY-V02-CHECKPOINT-20261122.md`
  sul branch Retail reale.
- `tradingview/delta-peaks/TV-V0187-PROSPECTIVE-LEDGER-CHECKPOINT-20261122.md`
  sul branch TradingView v0.8.187.

**Stato:** 32 nuovi test GREEN; nessun deploy, merge, Secret, chiamata
Cloudflare, scraping provider, modifica Oracle o intervento al filone Mac.
Margini Free Cloudflare/Actions ancora UNKNOWN finché non attestati da fonte
idonea. Il primo holdout inizia il 23/11 alle 00:00 UTC ma resta scientificamente
NO-GO senza originale, timestamp indipendente, disponibilità e copertura reale.
