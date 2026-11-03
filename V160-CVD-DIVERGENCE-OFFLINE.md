# REMURA candidato v1.60 — Divergenze prezzo / CVD proxy, ricerca OFFLINE

Data: 3 novembre 2026. VPS LIVE: v1.59, SHA e924f4cf6f1a384fd84a3cef66c89a16e35de3fd verificato nella diagnostica privata #29. Nessun deploy da questo ramo.

## Origine
Porting pulito della vecchia PR #71 sul main v1.59, senza fondere i commit storici. Modulo JavaScript isolato cvd-divergence-core.js e 11 test sintetici in tests/cvd-divergence.test.js; CI corrente esegue controlli di sintassi e test.

## Limiti scientifici e tecnici
- Solo EURUSD e XAUUSD, M15, cTrader. CVD proxy = CLV × tick volume, non vero volume bid/ask eseguito o flusso istituzionale.
- Pivot stretti sinistra/destra 2/2 e conferma solo su barre chiuse, no look-ahead; errori/gap/stale/tick volume assente non generano eventi.
- confirmedAt è il momento teorico di conferma del pivot, non l'istante in cui il server ha raccolto e analizzato i dati.
- Nessuna richiesta broker/API, persistenza, notifica, nuovo segnale operativo, modifica UI, database o autoupdater. Il codice è solo in PR.

## Gate ancora aperti
1. CI offline verde contro main attuale; poi prova su storico di mercato non selezionato.
2. Benchmark contro pivot prezzo/ATR senza CVD e controlli permutando il tick volume.
3. Backend causale con parità numerica JS, deduplica, invalidazione, tempi collectedAt/detectedAt/deliveredAt.
4. Valutazione walk-forward con costi, spread, falsi positivi e rischio, senza promessa di guadagni.
5. Solo dopo: Radar e notifiche private iPhone opt-in, nuova versione e data/ora italiana su ciascuna pagina, backup e rollback.

Costi previsti da questo ramo: zero nuove API cTrader e zero nuovi servizi; quote Oracle/Firestore non certificate.
