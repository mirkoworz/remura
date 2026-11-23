# REMURA V20.9 — Freezer privato decisioni prospettiche e baseline prezzo-solo

Checkpoint: 23 novembre 2026, Europe/Rome. GitHub Actions run 45206560155 avviato 15:33:30 UTC = 16:33:30 CET. SOLO LAB, nessuna release o modifica HTML.

## Continuità e confini

Ramo indipendente research/remura-v209-private-decision-freezer-20261123 creato da SHA V20.8 cb1b3c1b5479f8c364ada361c38e3692cdb8da42. PR #107 V20.7 e PR #109 V20.8 restano Draft, nessun merge. Non toccati Mac/Codex, collector privato, Oracle, Cloudflare/D1, broker, Secrets, app LIVE o deploy. Repository pubblico: NON committare file con decisioni private, nonce e prezzi.

Conferme storiche NON ricalcolate:
- CVD TEST 12/12 ricevute M5 autentiche nella finestra ristretta del 23 novembre: https://github.com/mirkoworz/remura/actions/runs/45121703188 . Tutte OBSERVATION_ONLY, non direzioni operative e non trade.
- Lettore read-only V20.4 già testato 9/9: 12 M5 equivalgono a quattro potenziali istanti M15 correlati.
- V20.7 valutatore 12/12 e V20.8 verificatore GitHub 13/13; test temporale GitHub reale su hash SINTETICO https://github.com/mirkoworz/remura/actions/runs/45191640343 .
- Ancora ZERO decisioni reali orientate e precongelate e ZERO prezzi indipendenti EURUSD del 23/11 letti da questo filone: no risultati o alpha.

## Software V20.9 costruito ORA

research/v209_private_decision_freezer.py è un preparatore completamente locale, senza rete, che al massimo leggera' un DB SQLite cTrader ESISTENTE tramite l'adapter V20.4 (mode=ro, query_only) quando esplicitamente autorizzato. Non modifica la raccolta.

Accetta UNA dichiarazione locale di osservazione M5 su FX:EURUSD, contenente esattamente: schema remura-v209-local-cvd-observation-v1; symbol; event_close_utc; received_at_utc; source_event_sha256 (64 caratteri hex); cvd_side (LONG/SHORT/FLAT). Non ricava il lato CVD dal movimento successivo del prezzo. Non autentica l'evento da solo: etichetta esplicitamente LOCAL_ASSERTION_UNVERIFIED.

Requisiti anti-lookahead: candela M5 UTC correttamente allineata, ricevuta dopo close e non nel futuro, evento non oltre 12 minuti prima della preparazione; OHLC M15 ctrader validi, cinque M15 completate consecutive, nessuna candela futura, ultima M15 chiusa entro 20 minuti. Rifiuta gap, stale e payload sconosciuti.

Baseline price-only PRESPECIFICATA, senza ottimizzare soglie: M15_FIVE_CLOSED_CONTIGUOUS_CLOSE_MOMENTUM_SIGN_V1 = LONG se close quinta M15 maggiore del close prima M15, SHORT se inferiore, FLAT se uguale. Il lato baseline viene calcolato contemporaneamente alla registrazione CVD. Le cinque OHLC di input sono custodite solo nel ledger privato e sigillate mediante hash.

Il freeze genera un ledger compatibile con V20.7 e V20.8, comprensivo di ID deterministico per evento, timestamp di registrazione e congelamento, lato CVD dichiarato, lato price-only, digest dell'evento, 5 M15 e nonce privata casuale di almeno 128 bit. Genera separatamente un manifest che contiene SOLO schema e commitment_sha256, senza direzione, ID evento, nonce, ticker broker o prezzi.

La scrittura è disabilitata per impostazione predefinita. Solo --write-private crea DUE file locali 0600 in cartella privata 0700, OBBLIGATORIAMENTE fuori dal checkout pubblico GitHub. Le creazioni esclusive rifiutano duplicazione o sovrascrittura. Nessuna pubblicazione automatica di manifest o eventi.

Nel ledger appena creato anchor.workflow_run_id è ZERO (placeholder): NON è un first-seen verificato. Dopo eventuale futuro consenso, solo il file hash-only potrà essere pubblicato sul ramo witness V20.8 e il V20.8 controllerà SHA, workflow e run.created_at del server. Il tempo di ingresso teorico sarà la prima apertura M15 strettamente SUCCESSIVA al witness, non una data scritta a mano. Se l'anchor arriva troppo tardi, V20.7 rifiuta il candidato.

## Prove NUOVE (NON ripetute vecchie suite)

- research/test_v209_private_decision_freezer.py: 16 NUOVI test con SOLO eventi e OHLC sintetici, baseline LONG/SHORT/FLAT, M15 in futuro, gaps, session freshness, timestamp errati, fail-closed, nonce/hash, permessi 0600/0700, no overwrite, nessun output in repository e compatibilità con successiva prova V20.7.
- .github/workflows/remura-v209-private-decision-tests.yml: solo questi 16 test e controllo CLI vuoto, no Secrets o API.
- Prova GitHub https://github.com/mirkoworz/remura/actions/runs/45206560155 — SUCCESS; log ufficiale "Ran 16 tests ... OK" e marker "REMURA_V209_NO_INPUT_NO_PUBLIC_OR_PRIVATE_WRITES=PASS".

## Comando senza effetti: solo esplorazione del programma

python3 research/v209_private_decision_freezer.py

Senza argomenti NON consulta prezzi né crea file e produce NO_INPUT_NO_OUTPUT.

Per input REALI serviranno in futuro, SOLO dopo una nuova autorizzazione separata e coordinamento col Mac/Codex: --cvd-event-file /PERCORSO_PRIVATO/evento_m5.json --private-sqlite /PERCORSO_PRIVATO/prezzi.sqlite --private-dir /PERCORSO_PRIVATO/decisioni_0700. Senza --write-private è solo verifica; con tale flag crea file locali e non esegue push GitHub. Evitare di usare eventi storici, il loro time-to-freeze è oltre 12 minuti e giustamente viene rigettato.

## Gate scientifici ancora aperti

1. Accesso autorizzato ai prezzi cTrader locali EURUSD 23/11 in sola lettura tramite V20.4, senza ricominciare collector e senza esporre privati. Contare disponibilità quattro coorti sui 60m/4h/24h.
2. Raccogliere NUOVE decisioni CVD autentiche verificabili nel momento dell'arrivo; qui la direzione e il digest dell'evento sono ancora dichiarazioni locali, NON autenticazione del feed.
3. Archiviare hash-only su GitHub con prova server temporale; verificare timeliness e confronto con baseline prezzo-only fissata. Finché evento non è autenticato, l'hash prova solo che una dichiarazione era stata fissata.
4. Integrare costi reali storici, latenza, gap, benchmark a identico istante, embargo/overlap, campione sufficiente e test fuori campione. Nessun PnL, hit rate o alpha istituzionale dimostrati.

Budget: ZERO nuovi servizi, ZERO nuove richieste Cloudflare o provider, ZERO deploy, ZERO modifiche Oracle/Mac. Una breve CI GitHub con test sintetici. Non si presume che quote cloud/GitHub siano illimitate.
