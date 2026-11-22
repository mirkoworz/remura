# REMURA — ROADMAP CHECKPOINT V09 — 22 novembre 2026 (Europe/Rome)
SOLO LAB. Incrementale: V01–V08 preservati e non sovrascritti. Ultima V08: research/remura-roadmap-v08-lab-20261122/research/REMURA-ROADMAP-CHECKPOINT-20261122-V08.md, commit 0793352c83ae773d1e55cfcf77bbfb29d798d59b.

## Nuove attività completate e controllate attraverso GitHub Actions

1. COT v0.6 FORWARD-ONLY SIDECAR (SOLO RAM)
Branch research/cot-forward-only-v06-lab-20261122
HEAD 1ead210ee31528ab379287814d9ea9ed33478a91
Modulo research/cot/cot_forward_only_v06_lab.py
Test research/cot/test_cot_forward_only_v06_lab.py
Consegne Mac research/cot/COT-FORWARD-ONLY-V06-MAC-HANDOFF-20261122.md
CI https://github.com/mirkoworz/remura/actions/runs/45038207853
SUCCESS, log letto: Ran 17 tests, OK, REMURA_COT_FORWARD_ONLY_V06=17_17_PASS.
Basato su sidecar v0.5 SQLite solo :memory:. Scrive soltanto FUTURE catture sintetiche in transazione atomica capture event + nuova versione immutabile + puntatore corrente. Quarantena legacy, as-of sconosciuto prima dell'osservazione, nessun recupero retroattivo; rifiuta stesso timestamp conflittuale, clock retrodatato, duplicazioni, mutazioni di versioni. Failpoint sintetici per rollback dopo evento e versione; audit hash e relazione evento/versione/current_head. I timestamp sono LOCALI e NON attestati. Lo script operativo scripts/cot_monitor.py mantiene un rischio nel codice ON CONFLICT DO UPDATE, NON corruzione Oracle dimostrata. Prototipo non installabile, non migrazione reale. Gate Mac: backup database+WAL con restore verificato, analisi schema e spazio, compatibilità reader e dual-write, consenso separato.

2. TRADINGVIEW v0.8.190 FROZEN FOLD MATURITY (SOLO OFFLINE)
Branch research/tv-fold-boundary-v0190-lab-20261122
HEAD f17c7b7604329787c03d52331b02730a69842ab4
Modulo tradingview/delta-peaks/frozen_fold_maturity_v0190_lab.py
Test tradingview/delta-peaks/test_frozen_fold_maturity_v0190_lab.py
Consegne tradingview/delta-peaks/TV-V0190-FOLD-MATURITY-HANDOFF-20261122.md
CI https://github.com/mirkoworz/remura/actions/runs/45038211575
SUCCESS, log letto: Ran 16 tests, OK, REMURA_TV_FOLD_MATURITY_V0190=16_16_PASS.
Riusa il v0.8.189 per identità CVD, prezzo, retail e COT sulla singola decisione. Controlla inoltre che le barre CVD e price-only M5 siano NELLO STESSO HOLDOUT della decisione e che gli orizzonti 60/240/1440 min non attraversino il termine esclusivo del fold. Un orologio di valutazione autodichiarato serve soltanto per pending/elapsed, senza outcome né attestazione. NO-GO per alfa reale, niente tuning o editing V2.

## Test nuovi
TOTALI 33/33 PASS in due run GREEN specifiche. Nessuna vecchia suite COT, TradingView, Retail o Contributors ripetuta. Nessun Secret, provider, Oracle, Cloudflare, attivazione, spesa o merge.

## Stato preservato degli altri filoni
- COT v0.1 20/20, v0.2 16/16, v0.3 15/15, v0.4 12/12, v0.5 13/13, ora v0.6 17/17, tutti LAB: non è attestazione di pubblicazione CFTC.
- TradingView v0.8.188 firewall 18/18, v0.8.189 per-decision 18/18, ora v0.8.190 16/16; PR #106 DRAFT, protocollo prospettico V2 FROZEN.
- Retail Myfxbook v0.5 provenance 16/16 su commit reali, v0.6 receipt ledger 14/14 GREEN: orari/sha locali non sono first-seen indipendente. Myfxbook è sentiment retail, non istituzionali.
- Contributors v0.93 free proof 16/16 e v0.94 scope 16/16 GREEN; ownership/revoca/hardcap precedenti preservati, PR #105 DRAFT, pilot reale NO-GO.
- Cloudflare: monitor già esistente, non riavviato; run 44919682812 mostra D1 account quota UNKNOWN_NO_GRAPHQL_DATA, stato budget INCOMPLETE_OR_CRITICAL. Margine Free Cloudflare, Access seats, piano e GitHub Actions non completamente attestati. Le precedenti 2 richieste GraphQL autorizzate sono state consumate. Nuove chiamate/attivazioni richiedono consenso.
- Mac/Oracle: collector e autoupdater preservati, v1.65 root-owned NON installata, backup/recovery/anti-rollback sotto responsabilità Mac Codex. Branch noto remura-collector codex/mac-custody-checkpoint-20261120, SHA 7a23f61b2cb1e520bff623348366231ee093bb3f, non rivalidato qui.
- Experience v0.30 LAB (scontro cinematografico toro/orso 3D, barra di caricamento, esplosione, logo REMURA/pinna, SMF e ringraziamento, togliere fotografia) NON pubblicata; Private Capture v0.15 LAB non attivato.
- Ampere Radar Milano con avvisi Telegram già operativo al checkpoint, non duplicato; Shark Science, scoring, Squalincome, Telegram Contributors rimangono nella roadmap.

## Protocollo e data imminente
Development 16/11 00:00 UTC–23/11 00:00 UTC (estremo escluso).
Holdout1 23/11 00:00 UTC–30/11 00:00 UTC (estremo escluso); apre il 23/11 alle 01:00 Europe/Rome.
Holdout2 30/11 00:00 UTC–07/12 00:00 UTC (estremo escluso).
Primario CVD vs price-only a 60 minuti; secondari 4h/24h; M5 FIFO, ricezione <=close+120 sec e prima del prossimo close M5; costi ipotetici 0/1/2 pip, zero tuning. L'apertura del fold NON equivale a dati autentici già ricevuti.

## Roadmap V10
A. Ottenere per DECISIONE prove indipendenti di clock, contenuto sorgente CVD, comparatore price-only, copertura M5 e mapping spot/futures senza retrodatazioni; ricerca LAB fino a nuova autorizzazione per servizi.
B. Mac: preparare backup reale e piano forward-only COT prima di ogni intervento su collector.
C. Contributors: dopo specifico consenso e quote Free complete, staging privato, Access reale, Safari iPhone fisico, revoca e isolamento; fino ad allora pilot NO-GO.
D. Evitare duplicazioni, costi, esecuzioni storiche. Main e PR DRAFT intoccati.
E. Ogni vera pagina REMURA modificata deve riportare in ALTO versione pubblica e data/ora Europe/Rome; nessuna pagina app modificata adesso.

VERDETTO: due nuovi sviluppi LAB +33 GREEN; nessun reale edge provato, NO-GO per pilot e migrazione Oracle, produzione intatta.
