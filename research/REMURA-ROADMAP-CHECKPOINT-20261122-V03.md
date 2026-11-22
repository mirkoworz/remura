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
