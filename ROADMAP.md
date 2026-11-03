# REMURA — Roadmap operativa unica

## 03/11/2026 — STATO ATTUALE CERTIFICATO: v1.60 LIVE; v1.61 PROSSIMA RICERCA (NON LIVE)

**Questa sezione è quella aggiornata.** Le sezioni precedenti della roadmap sono mantenute come cronologia e possono descrivere versioni superate.

### P0 — Release affidabile e osservabilità: FATTO
- [x] **LIVE Oracle v1.60**, installata il 03/11/2026 ore **12:01 Italia** e confermata su iPhone. SHA applicativo e autoupdater `47d48e1b742358c45e04e980a7c81935d496644a` (`up_to_date`). PR [#78](https://github.com/mirkoworz/remura/pull/78) e [#79](https://github.com/mirkoworz/remura/pull/79) integrate in ordine; CVD PR #77 **non integrata**.
- [x] Installer SHA-only: preflight `PREFLIGHT_V160=OK`, 16 file, backup SQLite verificato, restore-test isolato, manifest rollback, servizio sano, riconciliazione `--check` e `--apply` separate con backup stato. CI `push/main` Insights/Price verdi.
- [x] Diagnostica privata **#32**, [run 41624984188](https://github.com/mirkoworz/remura-collector/actions/runs/41624984188), dopo deploy: **38/38** prezzi verificati e recenti; COT TFF **11/11**, Disaggregated **3/3**; Myfxbook VPS running; collector running, autoupdater allineato. Tick volume M15 EURUSD/XAUUSD **64/64** nell'ultima finestra campionata (non CVD aggressivo reale). RAM **27,7%**, disco **8,0%**; non certificano il billing Oracle. Capital VPS disabled; Firestore NON controllato da questo workflow.
- [x] Screenshot iPhone v1.60: banner italiano **03/11/2026 12:01**, pannello freschezza Squalincome coerente col run #32: **34** monitorati, **19** dati prezzo tecnicamente idonei, **15** fuori soglia H1, **0** non verificabili; **6** analizzati con COT/prezzo, **28** esclusi. Le **3** registrazioni di evento nell'archivio e le **2** visibili nello storico corrente NON sono 3 nuove occasioni operative. Nessun nuovo evento nell'ultima scansione; nessuna notifica attiva.

### P1 — v1.61: risolvere *l'osservabilità* della freschezza H1, senza falsi verdi
- [ ] **PRIVATO / OFFLINE PRIMA:** estendere l'audit su `remura-collector` usando **lo stesso GET** `/private-api/signals/status`: contare atomicamente `price_live_ready`, `price_stale`, `unverified`, età/soglie M15=180/H1=120/H4=300, timestamp della full scan e tempo server. Dati manomessi o non atomici -> `N/D` o `unverified`, mai `ready`. Nessun nuovo endpoint, broker call, secrets o strumento analizzato sul log.
- [ ] Osservare più full-scan reali in differenti fasi dei batch e confrontare le stesse soglie con i campioni **post-ingest** (attualmente v1.60: 21/21 post-ingest riusciti e 21/21 periodici nella diagnostica #32). Distinguere **tempo batch→analisi** da **candela→evento** e da una reale anticipazione di prezzo.
- [ ] Verificare sul server la schedulazione effettiva per mercato e gli errori collector, *prima* di usare `waiting_verified_batch`. La UI attuale mostra 0 per attesa attestata, perché il server **non** pubblica un orario successivo verificato. Non stimare `nextExpectedAt` tramite la media dei batch.
- [ ] Studiare offline una riorganizzazione a **budget broker identico** e dimostrare con misure, non con un'ipotesi, l'eventuale maggior copertura H1. Con 38 mercati, 5 per batch, 8 batch/120 minuti, alcune esclusioni H1 possono essere matematicamente inevitabili nel full-scan: vietato promettere 34/34 solo cambiando la UI o spostando l'orario delle scansioni.
- [ ] Se emerge un beneficio reale, preparare una release dedicata **v1.61** con test, SHA, backup SQLite+restore-test, rollback, riconciliazione e banner italiano sulle 9 pagine. **Niente deploy o merge di questo ramo ricerca per ora.**

### P2 — CVD proxy e divergenze causali: RICERCA, non segnale LIVE
- [x] Tick volume cTrader archiviato sulle nuove M15, CVD **proxy** `CLV × tick volume`; il volume non rappresenta ordini aggressori futures. Replay su EURUSD/XAUUSD e allineamento JS/Python del prototipo prezzo–CVD in PR [#77](https://github.com/mirkoworz/remura/pull/77) **draft separata**, non idonea a merge.
- [ ] Attendere sufficienti sessioni genuinamente complete con volumi (niente ricostruzione sintetica dei vecchi `v` assenti); campionare qualità, sessioni, spread, gap, M15/H1/H4 e contatori di API. Ultima diagnostica #32: solo **ultime 64 M15** con volume 64/64 su EURUSD/XAUUSD, non uno storico plurimensile.
- [ ] Validare divergenze rialziste LL prezzo/HL CVD e ribassiste HH prezzo/LH CVD con pivot confermati **senza look-ahead**, separando momento del pivot dalla disponibilità dell'informazione. Benchmark prezzo/ATR-only, falsi positivi, replay causale, test walk-forward con embargo e dati non selezionati ex post.

### P3 — Misurare un eventuale vantaggio statistico (prima di notificare)
- [ ] Registrare *ex ante* i candidati, poi MFE/MAE e outcome 1h/4h/24h con spread/slippage/commissioni realistici. Valutare expectancy, drawdown, numerosità effettiva e stabilità fuori campione, benchmark anche senza CVD/sentiment.
- [ ] Misurare separatamente il valore aggiunto di COT settimanale (ritardato), sentiment retail Myfxbook/Capital, struttura prezzo, volatilità e DXY/VIX. Non chiamare istituzionali le posizioni retail, né dedurre operazioni future certe.
- [ ] Solo con qualità e vantaggio almeno plausibile, notifiche private iPhone/Telegram *opt-in*, idempotenti, cooldown, tetto giornaliero e revoca. Nessun ordine automatico.

### P4 — Copertura asset, interfaccia e costi
- [ ] Verificare DAX/GER30, VIX, DXY, petrolio e indici: feed prezzo ≠ contratto futures CFTC; dove manca un dato comparabile mantenere `N/D`. Conservare fonti e orari di pubblicazione verificati.
- [ ] Raffinare il Radar in modo che spieghi **quale dato è recente, quali soglie supera e cosa manca**; distinguere divergenze **COT/prezzo** (già storico) da **prezzo/CVD** (ricerca).
- [ ] **GATE GRATIS:** leggere fatturazione e quote vere Oracle Always Free, minuti/storage GitHub Actions, Firestore read/write/storage e quote cTrader. Ultima misura risorse VPS favorevole, ma `Consumi: N/D` non equivale a costo zero; nessun servizio o acquisto autorizzato.
- [ ] Ogni release futura mantiene i vincoli: **versione+data/ora italiane in alto in tutte le 9 pagine**, staging CI verde, check SHA GitHub, backup+restore-test+rollback, preflight read-only, installazione separata e autoupdater riconciliato.

**Decisione tecnica:** si parte da P1 con audit privato read-only e nessun nuovo costo; CVD/benchmark P2-P3 procedono solo quando il dato consente inferenze oneste. Questo aggiornamento modifica **solo documentazione su un ramo ricerca**, non l'app LIVE.

---


## 03/11/2026 — v1.60 FRESCHEZZA PREPARATA, MA NON INSTALLATA (PR #79)

- [x] **LIVE ancora v1.59**, SHA `e924f4cf6f1a384fd84a3cef66c89a16e35de3fd` (diagnostica privata #31); `main` è avanzato di un solo commit dati Myfxbook, **non** di codice applicativo.
- [x] **PR #78**: snapshot qualità prezzi atomico nel monitor Squalincome, nuovi stati fail-closed e vista iPhone; non introduce nuovi segnali o nuove chiamate cTrader. `waiting_verified_batch` resta NON DISPONIBILE senza `nextExpectedAt` attestato.
- [x] **PR #79** [release protetta v1.60](https://github.com/mirkoworz/remura/pull/79), stack sopra #78, distinta da #77 CVD: tutte le **9 pagine** preparate per `nav.js?v=160`; banner `REMURA · Aggiornamento v1.60 · 03/11/2026 11:20 (Italia, preparazione)`, da timbrare con ora **reale** solo durante l'installazione; cache iPhone `remura-shell-v74-v1.60-squalincome-freshness`.
- [x] Installer candidato `deploy/oracle/release_v160.py`: 16 file approvati, pin `BASE_SHA` e 15 SHA Git blob v1.59, nessun JS nuovo già presente, require CI push main verde, integrità SQLite e spazio, `--check` lettura sola, `--apply` con backup SQLite+restore-test e rollback manifest SHA256 incluso nuovo JS. `deploy/oracle/reconcile_v160.py` usa blob immutabile release pinnato e riconcilia SOLO lo stato autoupdater in due passaggi separati. CI GitHub su PR #79: Insights e Private Price Engine verdi, inclusi test storici v1.58/v1.59 e i nuovi v1.60, ultimo codice verificato con run `41620370454`/`41620370443`.
- [x] Documentazione `V160-RELEASE-PLAN.md`: rilascio in due merge sequenziali (#78 poi #79), poi due CI **push/main** verdi, preflight VPS, applicazione manuale separata, eventuale rollback, riconciliazione SHA e diagnostica privata. **Nessuno di questi passi ha ancora installato la release.**
- [ ] **GATE LIVE 1**: review #79, poi merge controllato #78 → `main`, **retarget #79 da ramo #78 a `main`** con riesame del diff, infine merge #79 in `main` **senza PR #77**. Con due CI `push/main` verdi sullo SHA finale, nessun deploy automatico del codice server: autoupdater deve fermarsi a `manual_required`.
- [ ] **GATE LIVE 2**: recuperare in modo immutabile/verificato `release_v160.py` dal commit SHA, eseguire **solo allora** preflight `--check` read-only che verifica i 15 hash base effettivi su VPS v1.59. Qualsiasi drift ferma il rilascio: non bypassare. Solo se OK procedere separatamente con backup SQLite, restore-test, installazione e rollback pronto; poi `reconcile_v160.py --check/--apply` con codice verificato e stato solo dopo i controlli.
- [ ] **GATE LIVE 3**: diagnostica post-deploy, verifica 9 banner italiani, cache PWA aggiornata, 34 mercati Squalincome e 38 prezzi; falsi eventi assenti. Senza questo, LIVE resta da dichiarare v1.59.
- [ ] **GATE COSTI**: quote GitHub Actions, Oracle Always Free, storage, traffico e cTrader/Firestore da certificare sui rispettivi provider. Nessuna spesa autorizzata o incremento volontario delle API.
- [ ] **CVD su PR #77** sempre ricerca offline proxy (CLV × tick volume), volume storico genuino insufficiente per validazione, NON incluso nel rilascio v1.60 di freschezza.




## 03/11/2026 — PROTOTIPO SICURO STATI FRESCHEZZA (PR #78, NON LIVE)

- [x] Diagnostica privata #31 + simulazione PR privata #17: una rotazione ideale dei batch di circa 120 minuti può dare M15 recente mentre H1/H4 oltre soglia, senza necessariamente alcun errore di aggregazione; **non** abbassare le soglie per nasconderlo.
- [x] **App PR #78 aggiornata** [Squalincome backend + vista iPhone protetta](https://github.com/mirkoworz/remura/pull/78), distinta dalla PR #77 CVD. `scripts/signals_monitor.py` nel ramo candidato conserva metadata qualità/timestamp **nella stessa scansione** e riusa un unico audit OHLC per mercato; `squalincome-freshness-core.js` è ora caricato **solo nella vista mercati del ramo candidato**, non sulla VPS live v1.59, e ammesso nell'allowlist/precache del ramo. Stati: prezzo idoneo ai successivi gate, fuori soglia, non verificabile; `waiting_verified_batch` resta deliberatamente non disponibile finché un vero scheduler non attesti la prossima acquisizione. Nessun nuovo evento o ordine autorizzato (`signalAuthorized:false` sempre), niente API broker aggiuntive. Test backend/frontend e due workflow CI verdi su commit `6cd2efbcce9980e0dce2e7229eb814816a7fae2b` (ultimo codice testato prima del commit docs).
- [x] **Gate qualità atomica progettato nel candidato:** lo snapshot full-scan può contenere `priceQuality` e `timeframes` sullo stesso documento / tempo UTC, letto da `/private-api/signals/status` insieme a `serverTime` senza nuovo endpoint. Il backend LIVE v1.59 continua a NON esporre questi campi. Lato iPhone: oltre 20 minuti dall'ultima scansione mostra `non verificabile` anziché un verde storico.
- [ ] **Gate scheduling reale ancora aperto:** il collector non attesta `nextExpectedAt` per ciascun mercato: evitare di inventare lo stato giallo `in attesa`, anche se il ritmo normale è circa 2 ore. Sviluppare solo se i tempi di schedulazione e i fallimenti sono tracciabili in maniera affidabile; zero nuove chiamate cTrader.
- [x] **Prima vista esplicativa iPhone candidata** nel ramo PR #78: 34 mercati, contatori separati per freschezza e idoneità COT/prezzo, età M15/H1/H4, motivi di esclusione e storico; il sistema non inserisce segnali e non autorizza trading. Nessuna distribuzione LIVE.
- [ ] Prima della release, validare runtime Oracle reale e costo CPU della scansione (audit OHLC riusato una volta); confermare quote broker invariate e compatibilità con 34/38 mercati. Poi rilascio protetto v1.60 indipendente da CVD, banner versione+ora italiana 9 pagine, nuova cache PWA, backup/restore-test e rollback.
- [ ] Prima di qualsiasi release: CI verdi, revisione compatibilità con PR #77, numero di versione e data/ora italiane in testa alle **nove pagine**, backup SQLite, restore-test, rollback, pin SHA, riconciliazione autoupdater. **LIVE attuale v1.59 non toccata.**

## 03/11/2026 — GATE REPLAY #3 REALE e indagine delle 22 sessioni missing (stato odierno)

**LIVE confermata (ultima diagnostica #29): v1.59 su Oracle Always Free, SHA `e924f4cf6f1a384fd84a3cef66c89a16e35de3fd`.** La PR #77 è ancora solo ricerca offline v1.60. Non fondere su main né avviare autoupdater senza rilascio protetto, backup, restore-test e rollback.

- [x] Replay reale nel repository privato `remura-collector` workflow run #3 `41605130427` completato alle 08:41 UTC del 03/11, **solo due GET VPS già esistenti**, 0 nuove chiamate broker, nessuna scrittura VPS.
- [x] EURUSD 29 sessioni esaminate, 2 idonee, 22 `missing`, 5 `session_too_short`; 7 candidati prezzo/ATR maturi (5 favorevoli tecnici, 2 sfavorevoli); 0 CVD proxy. XAUUSD 29 sessioni, 1 idonea, 22 `missing`, 5 `session_too_short`, 1 `partial`; 1 candidato prezzo maturo sfavorevole; 0 CVD. **NON calcolare win rate, probabilità di profitto o PnL**. Tre rotazioni-volume non provano predittività; campione insufficiente.
- [x] Audit del codice: il rilevatore Python emette `missing` anche per tick volume `v` assente (o `null`) in M15 con prezzi presenti, quindi **22 `missing` non significano necessariamente 22 giorni senza prezzi**.
- [x] PR privata #14 integrata **dopo** il replay #3: introdotti contatori di copertura `SHORT`, `VOLUME_MISSING`, `MIDNIGHT_MISSING`, `M15_GAPS`, `ELIGIBLE`. Il run #3 non li contiene; non attribuire ancora una causa certa ai 22 `missing`.
- [x] PR privata **#15 integrata in collector main** (`4039e462c9482a20d19cc36613b27734dc48b781`), CI offline **11 test verdi**: separazione barre `v` mancanti/null/zero, sessioni senza volume/parziali/complete, controllo parità indipendente `PARITA_MISSING`, test offline e documentazione senza divulgazione di prezzi o broker IDs.
- [x] **Replay #6 reale completato**: [run privato 41608623429](https://github.com/mirkoworz/remura-collector/actions/runs/41608623429), success, codice pinnato e zero nuove chiamate cTrader. **Causa missing confermata**: EURUSD 2.240 M15 di cui 2.100 senza `v`; XAUUSD 2.148 M15 di cui 2.016 senza `v`. 26/29 sessioni UTC senza volume su entrambi, 3 sessioni con volume completo, zero parziali; `PARITA_MISSING=SI` (22 esclusioni ciascuno). Prezzi OHLC presenti, quindi NON sono 22 giorni senza prezzi. EURUSD 2 sessioni CVD idonee, XAUUSD 1.
- [x] **Provenienza della discontinuità verificata**: commit `55da32a4cdaceafb48f77b4d737076cf4e65fa31` del 02/11/2026 06:49 UTC ha introdotto `bar.volume` nel feed cTrader e sua conservazione in SQLite; prima veniva scartato. Nessuna ricostruzione lecita da OHLC o rollup H1/H4 (derivati dalle M15). Rapporto aggregato in `remura-collector/CVD-MISSING-AUDIT.md`.
- [x] **Nuovo dato replay #6**: EURUSD prezzo-only 8 candidati (7 maturi e 1 censurato), CVD 1 candidato **non maturo**. XAUUSD prezzo-only 1 maturo, CVD zero. Nessun vantaggio dimostrato; pending a chiusura sessione può non maturare per divieto di usare dati futuri di altre sessioni.
- [ ] **PROSSIMO GATE PRATICO:** continuare raccolta regolare dei tick volume realmente forniti da cTrader senza aumentare richieste; monitorare copertura e eventuali gap, rispettando finestra SQLite 45 giorni. Cercare solo eventuali altre copie già esistenti di M15 **con volume originale e provenienza verificabile**: nessuna interpolazione/backfill sintetico. Non rieseguire benchmark conclusivo finché il campione con volume non sarà adeguato.
- [ ] Migliorare campione **solo con storico genuino già registrato o con acquisizione futura ai ritmi già esistenti**; nessuna modifica di soglia per produrre segnali; differenziare giorni UTC non negoziati e parziali; riconciliare volume storico con timestamp di origine.
- [ ] Validare incrementalità con campione adeguato, splitting temporale walk-forward purgato/embargo, controlli negativi, indipendenza eventi, MFE/MAE, spread, slippage, commissioni, equity e drawdown prima di Radar / notifiche iPhone.
- [x] **Indagine codice H1 v1.59:** `signals_monitor.frame_direction` applica 120 minuti a H1, 180 a M15, 300 a H4; `private_server.collector_loop` distribuisce fino a 38 mercati in batch circa ogni due ore, `squalincome_loop` scansiona ogni 15 minuti. Diagnostica privata #29 al 03/11/2026 06:03:21 UTC: 11/34 `prices_stale` **esclusivamente H1**, età massima 123 minuti (M15 massima 108); questo suggerisce possibile disallineamento temporale del full-scan, **non dimostra un bug**.
- [x] **PR privata collector #16 integrata** con commit `b9e73174aa6dbee0db48ad96c1b16593983cee02`: diagnostica aggregata H1 120–135 minuti, relazione col close M15 e possibile incompletezza delle quattro M15. CI privata 29 test offline verdi (6 diagnostica base + 18 overview + 5 readiness), nessuna nuova GET o broker call, nessuna release live.
- [x] **Diagnostica H1 reale #31 completata:** [run 41611353786](https://github.com/mirkoworz/remura-collector/actions/runs/41611353786), full-scan del 03/11/2026 09:19:07 UTC, collector running, autoupdater up_to_date, SHA installato v1.59 `e924f4cf6f1a`. `prices_stale=8`; attribuzione H1=8, H4=8, M15=0. H1 età massima 139 (soglia 120), H4 319 (300), M15 109 (180); **8/8 H1 stale compatibili con l'ultima ora completa teoricamente consentita dalla M15**, 0 H1 ulteriormente arretrate, 0 metadati inattribuibili. Nessuna prova di bug aggregazione, causa più coerente è l'età degli ultimi dati nel modello batch/cadenza; i timestamp M15 da soli non provano continuità di tutti gli input. Rapporto nel repository privato `H1-BOUNDARY-DIAGNOSTIC.md`.
- [x] **Telemetria #31 maturata:** post-ingest 14/14 scansioni riuscite, mediana 269 ms; periodica 14/14, mediana 2194 ms. Nessun evento segnalato; tempistiche tecniche non sono predittività di mercato.
- [x] **Modello offline cadenza H1/H4 completato:** PR privata collector **#17** integrata con commit `cf26b575d99fdbea11b1dbd43498bf54db5a755c`, CI 33 test offline verdi. Simulazione ottimistica di 8 batch ogni 15 min su 120 min, 96 full scan giornalieri: 768 controlli di coorti astratte, 72 oltre soglia H1, 18 oltre soglia H4, 18 entrambi, 0 M15, **senza broker/dati reali**. Un caso con ultimo M15 teorico 07:30 UTC e scan 09:19 UTC produce età M15 109, H1 139, H4 319 minuti come possibile pattern della diagnostica #31. Non sono percentuali di trading; non dimostrano frequenza o causa di ogni singolo caso LIVE. Vedi rapporto privato `H1-H4-CADENCE-OFFLINE.md`.
- [ ] **Gate H1 successivo:** progettare e testare *solo offline* la distinzione UX/stati `dato storico archiviato`, `dato live eleggibile`, `in attesa del batch`, preservando esattamente le soglie 120/300/180 e scansioni post-ingest. Non falsificare freschezza, non sovrascrivere segnali validi con vecchi eventi e non introdurre nuove API broker. Per H4 occorre ancora verificare presenza delle sedici M15 contigue prima di concludere per i singoli mercati.

- [ ] Indagare 11 H1 stale in Squalincome (123 vs 120 minuti) comparando timestamp chiusure, aggregazione H1, scheduling e ritardi. Non aumentare quote cTrader né soglie solo per nascondere il problema.
- [ ] Certificare billing/crediti GitHub Actions, Oracle Always Free, Firestore e quote cTrader: **nessun nuovo costo autorizzato**; Capital VPS resta inattivo nell'ultima diagnostica e Firestore non confermato da quel run.
- [ ] Per qualsiasi futuro rilascio LIVE (non ora): versione/data/ora italiana sulla parte alta di **tutte le 9 pagine**; check SHA autoupdater, SQLite backup/restore-test e rollback prima di toccare main o VPS.

**Nota:** sezioni che seguono = cronologia dello sviluppo, non sostituiscono lo stato LIVE riportato qui.


## 03/11/2026 — v1.59 LIVE verificata; candidato divergenze CVD offline v1.60

- [x] REMURA v1.59 installata sulla VPS (14 file), backup/restore-test/rollback, SHA autoupdater e924f4cf6f1a384fd84a3cef66c89a16e35de3fd riconciliato.
- [x] Diagnostica privata GitHub #29 (run 41588151515, ore 07:10 Italia): servizio attivo, autoupdater up_to_date, 38/38 prezzi verificati/recenti, TFF 11/11, Disagg 3/3, Myfxbook operativo; EURUSD/XAUUSD tick volume 64/64, RAM 28.1%, disco 8.0%.
- [x] Timing Squalincome v1.59: post-ingest 1 campione 341 ms, periodic 1 campione 4580 ms, nessun errore/evento, fine batch→fine analisi 341 ms; diverso perimetro, NON prova di anticipo dei segnali.
- [ ] Accumulare campioni e monitorare H1: 11 stale su 34, età massima 123 minuti vs soglia 120; M15/H4 nessuno stale.
- [x] remura-collector PR #12 con nuovi contatori tramite gli stessi GET; nessuna chiamata broker aggiuntiva.
- [x] Candidato offline v1.60 sulla PR #77: vecchia PR #71 portata pulitamente sulla base v1.59, 11 test JavaScript invariati.
- [x] Backend di ricerca Python `scripts/cvd_divergence.py` allineato al rilevatore JS su **30 scenari sintetici**; orari causali e ID stabili, CI verde. Il modulo non è importato dal server VPS.
- [x] Benchmark di laboratorio `scripts/cvd_benchmark.py`: stessi pivot prezzo/ATR come baseline, sottoinsieme filtrato CVD, etichette a orizzonte prefissato (4 M15) e 3 rotazioni volumi, 7 test di sicurezza offline; NO PnL, NO profitti dimostrati.
- [ ] Prossimo gate: portare dati storici reali chiusi e puliti nel replay **senza nuove API broker**, completare campionamento multi-sessione, walk-forward e spread/slippage. Prima dell'integrazione server live serve una nuova release protetta con banner versione/ora italiana.
- [ ] H1: indagare le 11 esclusioni e ottimizzare il ritmo di ingest **senza aumentare quote cTrader** né rilassare artificiosamente la soglia 120m.
- [ ] Validazione prospettica, costi di trading, falsi segnali, ID evento, timestamp di conferma/ricezione/avviso, poi Radar e notifiche opt-in con nuova release protetta.
- [ ] Billing Oracle, consumi Firestore e limiti API cTrader ancora da certificare; Capital sulla VPS disattivato all'ultimo test.

Le sezioni sottostanti sono storico di progettazione e contengono stati pre-rilascio superati.


## 03/11/2026 — v1.59 preparata per rilascio protetto; VPS ancora v1.58

- [x] **PR #76:** telemetria `post_ingest` e `periodic` distinta, limite 256 misure private, nessun dato di prezzo/segreto o nuova chiamata broker; prototipo + test offline verdi.
- [x] **Installer candidato** `deploy/oracle/release_v159.py`: verifica SHA GitHub + CI main, 13 file live v1.58 con Git blob immutabili e data reale nav, flag post-ingest ON, backup SQLite e restore-test, lock autoupdater; installa 14 file incluso `scripts/squalincome_timing.py`, rollback conservato e testato.
- [x] **Riconciliazione candidata** `deploy/oracle/reconcile_v159.py`: pin blob dell'installer a commit Git immutabile, `--check` read-only, backup stato e lock in `--apply` separato; manifest con file nuovo senza sorgente v1.58; CI entrambe verdi su `23689f9404b5deb9e13e374cce84465e462adc16`.
- [x] Nove pagine preparate con banner v1.59, versionamento JS e cache PWA v73; **l'ora finale sarà quella reale dell'installazione**, non quella della preparazione.
- [ ] **Prima del deploy:** merge GitHub conservando il commit immutabile dell'installer (NO squash/rebase), entrambe le CI `push` verdi sullo SHA merge, assenza variazioni a `main` nel controllo, preflight VPS `--check`; soltanto dopo `--apply` separato.
- [ ] **Dopo il deploy:** check/apply riconciliazione SHA separati, diagnostica privata, almeno più cicli di raccolta e verifica tempi/scansioni; misurare se la latenza tecnica si riduce, senza affermare ancora vantaggio operativo o predittivo.
- [ ] Billing Oracle, consumo Firestore e quote cTrader **non certificati**: nessun nuovo servizio o chiamata broker introdotti.


## 03/11/2026 — pacchetto v1.59 preparato su PR #76, NON installato

- **VPS continua su v1.58**: post-ingest attivato, SHA codice `112da31cb10c34477642e2822c78b267cb88978d` (ultima verifica privata #27). GitHub `main` è avanzato con un commit di soli archivi Myfxbook, senza modifiche al codice.
- **Candidato offline v1.59**: misure di latenza aggregate, percorsi post-ingest e periodici distinti; ritenzione SQLite 256 righe, nessuna nuova chiamata cTrader.
- Le nove pagine HTML sono predisposte con `nav.js?v=159`; `nav.js` riporta la versione e un timestamp **di preparazione**, da sostituire soltanto con l'ora italiana dell'installazione reale. Cache PWA nuova.
- **Gate obbligatori ancora aperti:** installer verificato con hash esatti, backup e restore-test SQLite, rollback della nuova unità Python, controllo flag ON, `--check` e `--apply` separati; CI finale verde; riconciliazione SHA e diagnostica privata.
- PR #71 (divergenze prezzo–CVD proxy M15) resta distinta. Contabilità OCI, quote broker e Firestore non certificati.


## 03/11/2026 — stato v1.58 live verificato; telemetria v1.59 solo offline

- [x] VPS v1.58 installata, commit GitHub/SHA autoupdater `112da31cb10c34477642e2822c78b267cb88978d` riconciliato; diagnostica privata #27 `41546105605` verde; server attivo, 38/38 prezzi, TFF 11/11, Disagg 3/3, Myfxbook running, tick-volume M15 EURUSD/XAUUSD 64/64, RAM 27,7%, disco 7,9%.
- [x] `REMURA_SQUALINCOME_AFTER_INGEST_ENABLED=1` attivato con backup privato e verifica runtime; autoupdater invariato. Scan generale ultima diagnostica: 2 analizzati su 34, 12 prezzi H1 troppo vecchi (146 min massimi contro 120), M15/H4 zero esclusioni stale.
- [x] Diagnostica privata: 2 osservazioni successive alla scansione generale, **evidenza indiretta** non prova del post-ingest né anticipo di segnale.
- [ ] **Candidato v1.59:** misurare tempi di scansione periodic/post-ingest, completamento batch→analisi, errori/eventi, con retention limitata; approvare solo dopo CI, review e rilascio protetto con banner versione e ora italiana. Il batch-end non è l'orario del primo prezzo salvato e non misura la latenza candela→segnale.
- [ ] Prossima integrazione **PR #71** divergenze M15 prezzo–CVD (proxy CLV × tick volume); distinta da divergenze COT/prezzo, ancora offline e non installata.
- [ ] Radar divergenze: stati potenziale/confermata/invalidata, ID evento, tempi pivot/conferma/rilevamento, prova prospettica contro benchmark prezzo-solo; in seguito notifiche private anti-spam.
- [ ] Capitale Firestore/sincronizzazione, billing OCI e quote API reali ancora N/D; RAM/disco non certificano gratuità. Nessuna nuova API broker in questa preparazione.
- [ ] Valutare se archiviare il helper della PR #75 già usato nell'attivazione, senza merge a sorpresa che cambi lo SHA della VPS.

Lo storico che segue è mantenuto a fini di audit; le sezioni precedenti sui candidati v1.57/v1.58 descrivono snapshot superati.


## 02/11/2026 — candidato v1.58: installer protetto su GitHub (non installato)

- [x] Creata PR #74 dalla main v1.57 riconciliata, codice post-ingest identico al prototipo #72; 38 mercati, Myfxbook e autoupdater lasciati invariati sulla VPS.
- [x] Installer manuale release_v158.py candidato: check/apply separati, verifica dei 13 Git blob v1.57, CI main, rollback, SQLite backup + restore test, lock autoupdater e flag post-ingest OFF.
- [x] Predisposti banner v1.58 per 9 pagine, timestamp reale Europe/Rome solo all'installazione, cache PWA v72 e nav.js?v=158.
- [x] **Installer e riconciliazione SHA pronti offline**: `release_v158.py` + `reconcile_v158.py` con test su candidate archivio verificato, 13 file, CI main, manifest rollback, snapshot SQLite, stato autoupdater; Price Engine e Insights **verdi su commit 83380d9db78f** della PR #74.
- [ ] **Prima del merge**: CI verdi sull'HEAD definitivo (inclusi eventuali cambi documentali), nessun file o API inatteso, review finale; VPS rimane **v1.57**.
- [ ] **Prima di Termius**: merge main protetto, CI **push** verdi, SHA commit definitivo e blob immutabili; primo comando soltanto `release_v158.py --check`. `--apply` separato dopo esito verde, poi `reconcile_v158.py --check` e `--apply` separati, diagnostica privata conclusiva.
- [ ] Costi OCI/quote API/Firestore non ancora verificati nel pannello: N/D. Divergenze CVD PR #71 separata.


## Stato operativo consolidato — 02/11/2026, dopo diagnostica privata #24

- **VPS in produzione: v1.57**, installata manualmente; backup SQLite e test di ripristino/rollback superati nel rilascio controllato. **Nessun nuovo deploy** in questa fase.
- **GitHub main:** commit d445b17be20028fdb42ab303fa99718c1c33cd80, PR #73 integrata. **Price Engine e Insights verdi** sul merge commit.
- **Autoupdater VPS riconciliato:** diagnostica privata #24 (run 41537705649) ha letto installedSha=d445b17be200, targetSha=d445b17be200, up_to_date, server attivo e nessun blocco manuale. PR #69 chiusa, non integrata (sostituita da #73).
- **Dati reali diagnostica #24:** 38/38 prezzi verificati e recenti; COT TFF 11/11, Disaggregated 3/3; Myfxbook running; tick volume M15 EURUSD e XAUUSD 64/64; RAM 29,0%, disco 7,9%. Firestore e costi/quote OCI non certificati da questi test.
- **Squalincome (34 strumenti):** ultimo scan diagnostica #24: 9 esclusioni prices_stale, tutte H1; M15 e H4 zero; massima H1 145 minuti contro guardia 120. Le esclusioni multiple per ragione non si sommano come mercati unici.
- **Lavoro in corso v1.58:** reintegrazione prototipo PR #72 su ramo isolato integration/v158-after-ingest-main-20261102, **flag OFF di default**; nessuna modifica VPS, nessun cambio soglie, nuove chiamate broker zero. Test CI necessari prima di ogni merge. PR #71 prezzo–CVD rimane un lavoro offline successivo.
- **Gate rilascio v1.58:** solo dopo CI verde, review, preflight read-only, backup+restore, rollback e installazione reale con versione e data/ora italiana su ogni pagina; solo dopo abilitazione controllata del flag e diagnostica prospettica su latenza, duplicati, copertura, RAM/disco e quote.

## Archivio dei precedenti snapshot (preservato)



> **SNAPSHOT STORICO — 02/11/2026 ore 17:27 Italia (superato).** VPS **v1.57** (rilascio manuale riuscito); priorità EURUSD/XAUUSD **ON** dalle 17:08, ma intervalli effettivi ancora da collaudare; backup e rollback verificati. GitHub `main` ha v1.56, PR #69 ancora draft, e SHA autoupdater registrato alla v1.56. **Non** fare merge, `--init-sha` o nuovi deploy finché il collaudo intraday non è concluso. Questa modifica è solo documentazione: non cambia versione né servizi.

### Quadro rapido: fatto / in corso / da costruire

- **Fatto e verificato:** REMURA privata su Oracle, backup SQLite con restore-test, 38/38 mercati validi e recenti nella diagnostica #18, COT TFF (11/11) + Disaggregated (3/3) pronti, Myfxbook running, tick volume cTrader EURUSD/XAUUSD 64/64 M15, CVD **proxy CLV × tick volume** con UI e test.
- **In corso:** dimostrare la frequenza reale del collector prioritario (due o più giri), stabilità di tutti i 38, latenza M15/H1/H4 per Squalincome, quote cTrader/Oracle, qualità del proxy in diretta, collaudo della UI iPhone e verifica Firestore Capital/OCI billing (non dichiarare verificati).
- **Da costruire e validare:** rilevatore dedicato **prezzo–CVD** non-repainting, memoria eventi e Radar, misure statistiche prospettiche, notifiche private opt-in. Le "divergenze" Squalincome esistenti riguardano **COT contro prezzo**, non prezzo contro CVD.
- **Più avanti/opzionale:** tick Bid/Ask a granularità maggiore e vero trade-delta futures con licenze/prezzi, solo se produce un vantaggio verificabile.

**Nuovo progetto prioritario:** [CVD-DIVERGENZE-ROADMAP.md](./CVD-DIVERGENZE-ROADMAP.md) — regole LL/HL e HH/LH, pivot causali M15, controlli qualità, preavviso vs conferma, tracciamento eventi, benchmark prezzo-solo, Web Push iPhone/Telegram privato e anti-spam. **Non ancora implementato.**


**Aggiornata:** 01/11/2026 (Europe/Rome)  
**Baseline:** codice GitHub v1.55; l'installazione effettiva sulla VPS va verificata separatamente.  
**Scopo:** riconoscere possibili tracce dei grandi operatori combinando posizionamento COT, sentiment retail, struttura del prezzo e — come nuovo filone — volumi e order flow *stimato*; valutare le ipotesi con dati osservabili, test fuori campione e controllo dei costi. Nessun rendimento o anticipo delle mosse istituzionali è garantito.

## Regole che valgono per ogni fase

- **Gratis prima:** riutilizzare cTrader Open API, SQLite privato e Oracle Always Free finché sostenibile. Prima di aumentare frequenza, storage o servizi verificare quote reali, RAM, disco, traffico e possibili costi; una quota non misurata è **N/D**, non zero.
- **Nessun dato inventato:** mantenere fonte, broker, strumento, UTC, ora di acquisizione, granularità e qualità; se il feed è assente/stantio mostrare N/D. Distinguiamo forex/CFD dai futures sottostanti.
- **Sicurezza:** lettura soltanto, nessun invio ordini, token e database in `private/`, niente segreti/dati tick privati nel repository pubblico, backup SQLite prima delle migrazioni e rollback testato.
- **Versioning:** ogni *rilascio applicativo* aumenta la versione e mostra versione più data/ora italiana **in alto su ogni pagina**, con aggiornamento cache PWA e test. La sola modifica di questa roadmap non è un rilascio e non cambia v1.55.
- **Rilasci delicati:** i file `scripts/`, `deploy/oracle/` e i workflow richiedono il percorso di installazione manuale controllata; l'autoupdater evita di applicarli automaticamente.

## P0 — Completare la base esistente (priorità immediata)

- [ ] **Quando riaprono i mercati:** verificare acquisizioni reali per tutti i mercati configurati, copertura M15/H1/H4, rotazione, ritardi e gap di sessione, distinguendo weekend e feed rotto.
- [ ] Verificare COT settimanale (prima disponibilità effettiva, mapping futures/strumenti, freschezza), sentiment Myfxbook e Capital, e qualità temporale di ogni sorgente.
- [ ] Proseguire la **validazione prospettica Squalincome**: timestamp di conoscenza reale, coorti non duplicate, esiti 1/4/24h, confronti con benchmark, costi ipotetici (spread, slippage) e intervalli di confidenza; niente probabilità spacciate per affidabili con pochi casi.
- [ ] Ultimare Centro di Controllo: contatori **outbound per provider** (richieste, errori, limiti) distinti dalle chiamate in ingresso alla VPS; integrità/ultimo backup, dati da verificare su OCI/Firestore/GitHub senza fingere accesso ai contatori billing.

## P1 — Volumi da cTrader: primo incremento minimo e gratuito

- [ ] Verificare nel payload reale di `ProtoOAGetTrendbarsRes` il campo `volume` e la sua semantica: **tick volume**, non lotti o contratti transati.
- [ ] Estendere `scripts/ctrader_feed.py` per conservare il volume delle M15 chiuse invece di scartarlo in `convert_trendbar()`, senza alterare OHLC e senza cambiare l'origine broker.
- [ ] Estendere schema/ingestione di `scripts/price_feed.py` e `scripts/price_store.py` (versionamento compatibile con dati storici senza volume): M15 e aggregazione dei volumi in H1/H4 solo da barre M15 contigue, mai su gap.
- [ ] Test di regressione: valori negativi/assenti, volumi pari a zero, broker mismatched, timezone, doppio inserimento, fine sessione/weekend, database già esistente. Mostrare volumi e qualità su una scheda pilota.

**Gate P1:** volume storico reale verificato per EURUSD e XAUUSD; nessuna perdita di candele e backup/rollback verificati; risorse entro quote gratuite.

## P2 — Delta Volume *stimato* e CVD pilota

- [ ] **Baseline su candele:** costruire una prima stima direzionale basata su OHLC + tick volume, chiaramente etichettata **proxy** (es. allocazione per posizione della chiusura nel range, con trattamento neutro dei doji). Non chiamarla flusso buy/sell reale.
- [ ] **Miglioria tick:** valutare recupero dello storico tick Bid/Ask autorizzato e/o sottoscrizione spot live, classificazione della direzione dei tick e aggregazione per M1/M5/M15; confrontare costo, limiti e qualità con baseline a candele. Tick Bid/Ask **non sono trade prints**; non possono identificare con certezza ordini aggressivi o volumi reali.
- [ ] Definire un `delta_proxy` riproducibile e un `CVD_proxy = somma(delta_proxy)`: reset per sessione, gestione buchi/disconnessioni, sessioni del broker, segno, scala e soglia minima di campionamento.
- [ ] Salvare nel SQLite **aggregati** minuto/15 minuti e lo stato del feed; conservare i tick grezzi solo per finestra breve configurabile, se indispensabili, senza creare carico 24/7 su tutti i 38 mercati.
- [ ] Dashboard nelle pagine EURUSD e XAUUSD: prezzo vs CVD proxy, delta per intervallo, freschezza, copertura, metodo utilizzato e disclaimer visibile. Confrontare graficamente i due proxy senza confonderli con order flow futures.

**Gate P2:** pilota funzionante e riproducibile su due strumenti con timestamp corretti; nessun falso CVD durante disconnessioni; costo/risorse monitorati. Estensione agli altri mercati solo se utile.

## P3 — Analisi dello squalo: confluenze, NON segnali automatici

- [ ] Studiare separatamente divergenze prezzo–CVD, rotture confermate/smentite, possibili assorbimenti, esaurimenti, Wyckoff e sweep di liquidità. Una divergenza da sola non dimostra assorbimento o intervento istituzionale.
- [ ] Collegare il nuovo fattore **senza doppio conteggio** con struttura prezzo M15/H1/H4, COT settimanale pubblicato, variazione sentiment retail e livelli/volatilità.
- [ ] Introdurre nel Radar Squali/Squalincome uno stato interpretabile: `CONFERMA`, `DIVERGENZA`, `NESSUN DATO` con spiegazione basata su osservazioni, invece di un'etichetta categorica “istituzionali long/short”.
- [ ] Misurare il **valore incrementale**: confronto out-of-sample Squalincome con/senza CVD, precisione, falsi segnali, expectancy e drawdown **netti dei costi ipotizzati**, su orari e strumenti non selezionati ex post.
- [ ] Solo dopo test utili, aggiungere notifiche private per eventi significativi con deduplica, limiti di frequenza e spiegazione del motivo.

**Gate P3:** il CVD migliora davvero un benchmark fuori campione con campioni adeguati; in caso contrario resta metrica descrittiva, non filtro operativo.

## P3-bis — Divergenze prezzo–CVD e notifiche (nuova fase prioritaria)

- [ ] **DIV-0:** completare prima la validazione della priorità v1.57 e garantire tick volume, CVD proxy, qualità e freschezza osservabili. Evitare notifiche quando il CVD è `N/D`, `partial` o `stale`.
- [ ] **DIV-1:** algoritmo a pivot M15 confermati senza look-ahead/repainting: **rialzista** quando prezzo crea LL mentre CVD proxy crea HL; **ribassista** quando prezzo crea HH mentre CVD proxy crea LH. Timestamp pivot e timestamp di conferma distinti, tolleranze ATR e sessioni coerenti; le divergenze nascoste si aggiungono dopo.
- [ ] **DIV-2:** nuova scheda Radar/Squalincome con *preavviso*, *divergenza confermata*, *invalidazione*, due coppie di pivot, ragioni, qualità e prezzo/CVD affiancati. Non confondere col monitor esistente di divergenze COT/prezzo.
- [ ] **DIV-3:** salvare eventi privati deduplicati, test completi, ricerca di valore aggiuntivo **fuori campione** rispetto a pivot/prezzo+ATR da solo, misurare falsi positivi e MFE/MAE 1h/4h/24h netti dei costi ipotizzati.
- [ ] **DIV-4:** solo dopo, avvisi privati opt-in prima nell'app, poi Web Push nella web app iPhone o Telegram privato; cooldown, tetto giornaliero, revoca, consenso, fail-closed se dati insufficienti, nessun ordine automatico.

**Specifiche e criteri di uscita:** [CVD-DIVERGENZE-ROADMAP.md](./CVD-DIVERGENZE-ROADMAP.md). Il CVD basato su `CLV × tick volume` incorpora il prezzo: non considerare le sue divergenze una prova indipendente di acquisti/vendite istituzionali. Prima versione candidata **v1.58** solo dopo la verifica del collector v1.57, senza impegnare nuove API o risorse a pagamento.

## P4 — Order flow più fedele (opzionale, non presumibilmente gratis)

- [ ] Valutare su **futures** relativi a oro, DAX, petrolio (e altri, in ordine di utilità) feed con scambi eseguiti, Bid/Ask aggressor tagging, volume e profondità, distinguendoli da CFD/spot.
- [ ] Verificare disponibilità, licenza, uso privato, ritardo, condizioni di ridistribuzione e costi effettivi del provider. Nessun abbonamento prima di una valutazione costo/beneficio.
- [ ] Se disponibile, costruire un CVD da **transazioni reali**, separato dal `CVD_proxy`, con identificazione di exchange e contratto; non chiamarlo misura diretta di tutte le operazioni istituzionali.
- [ ] Validare se aggiunge informazione concreta al modello REMURA prima dell'adozione.

## Sequenza e decisioni

1. Al prossimo mercato aperto **P0**: collaudo feed e validazione in corso; sono prerequisiti per non interpretare dati stantii.
2. In parallelo, progettazione/test offline di **P1**; prima release piccola: **tick volume M15** su due strumenti.
3. Dopo collaudo P1, **P2**: proxy CVD da candele, quindi confronto con feed tick, solo se sostenibile.
4. Se i dati sono affidabili, **P3**: aggiunta a Squalincome e analisi statistica prospettica.
5. **P4** soltanto se servono esecuzioni reali per una strategia che ha già mostrato potenziale e sappiamo valutarne i costi.

## Stato iniziale verificato nel codice (01/11/2026)

- `scripts/ctrader_feed.py`: preleva `ProtoOAGetTrendbarsReq` M15 e in `convert_trendbar()` restituisce OHLC, **non** il campo volume.
- `scripts/price_feed.py`: modello candela OHLC; `scripts/price_store.py`: archivia OHLC privati, senza delta o CVD.
- `V155-THREE-LEVEL-MONITOR.md`: i consumi misurati finora sono in ingresso alla VPS, **non** chiamate broker o fatturazione OCI.
- **Non implementato in questa modifica:** acquisizione volumi, streaming tick, CVD, nuove API e UI. Questa è soltanto la roadmap.

## Criterio di completamento di ogni step

Specifiche + fonte ufficiale + test unitari/integrazione + metrica di qualità + misure risorse/costo + backup/rollback + verifica reale su VPS + versione/data ora in ogni pagina **quando c'è un rilascio applicativo**. Documentare esplicitamente ciò che resta N/D.

## 02/11/2026 — lavoro preparato per v1.56, non ancora distribuito

- [x] Ramo `feature/volume-cvd-proxy-v156`: tick volume cTrader conservato in candele M15 e SQLite, H1/H4 sommati solo con barre contigue e volumi completi; dataset precedenti senza volume supportati.
- [x] Delta/CVD **proxy** su M15 tramite Close Location Value × tick volume, reset giorno UTC, controlli per tick-volume mancante, gap e M15 stale.
- [x] Primo pannello grafico nel motore prezzi delle schede strumenti; stato N/D finché non arrivano volumi dal broker. Nessuna interpretazione automatica istituzionale.
- [x] Test unitari Python e Node aggiunti: conversione volume, aggregazione, persistenza SQLite, CVD, discontinuità; CI deve ancora concludersi.
- [ ] CI verde + revisione PR, backup SQLite coerente, rollback e **installazione manuale protetta del backend**. Non installare solo la UI senza il backend se il rollout è previsto come pacchetto.
- [ ] Collaudo *reale* VPS a mercato aperto: confronto volumi cTrader, copertura EURUSD/XAUUSD, fresco/stale, utilizzo Oracle e contatori outbound; non verificabile da GitHub.
- [ ] Fase successiva: valutare tick Bid/Ask storici/live, qualità e overhead (solo se sostenibile), poi test out-of-sample su Squalincome.


## 02/11/2026 — diagnostica mercati aperti e backup protetto (pre-rilascio)

- [x] VPS v1.55: 38/38 mercati recenti e verificati nella diagnostica delle 08:06 CET (OHLC; non è validazione di volume).
- [x] VPS v1.55: preflight privato #13 (~08:19 CET) rileva **64/64 M15 senza campo tick-volume** su EURUSD e XAUUSD, zero valori invalidi. Stato **atteso prima** dell'installazione del collector v1.56, non prova che cTrader non fornisca volumi.
- [x] Monitoraggio preflight: RAM usata **28%**, disco **7,9%**; non attestano quote o addebiti Oracle.
- [x] Aggiunto `deploy/oracle/backup_v156.py`: verifica SQLite esistente e spazio, genera snapshot consistente con SQLite Online Backup e lo ripristina in un database temporaneo isolato per verifica integrità/righe. Flag `--check` sola lettura e `--backup` esplicito; NON fa deploy o riavvio. Test automatici offline inclusi.
- [ ] Eseguire **effettivamente** backup e restore-test sulla VPS con autorizzazione manuale; non dichiarare eseguito sulla base dei soli test GitHub.
- [ ] Valutare *latenza per strumento*: al preflight EURUSD ultima apertura 05:15 UTC e XAUUSD 06:15 UTC; alle 08:19 CET risultavano rispettivamente circa **124** e **64** minuti dopo l'apertura. Il proxy attuale blocca il CVD se la candela è più vecchia di 90 minuti: con rotazione dei 38 mercati EURUSD può spesso essere N/D anche in condizioni di feed sano. NON rimuovere la guardia per produrre falsi segnali. Progettare un ciclo prioritario per EURUSD/XAUUSD solo dopo controllo delle quote cTrader e misure del carico.
- [ ] Rilasciare backend/UI v1.56 soltanto dopo backup reale, stadio verificato con hash, test cTrader reali, installazione protetta e possibilità di rollback; versioning/data ora su tutte le pagine.


## 02/11/2026 ore 08:45 Italia — v1.56 installata, inizio validazione live

- [x] Preflight server: `PREFLIGHT_V156=OK`, versione v1.55 prima del rilascio.
- [x] **Esecuzione manuale** dello script di rilascio verificato `deploy/oracle/release_v156.py` con commit fissato `3e0e34169ab89ccb2d6c09d777817ae3f705352b`: secondo lo screenshot terminale restituisce `RILASCIO_V156=OK` e `FILE_INSTALLATI=17`.
- [x] Prima dell'installazione: `BACKUP_SQLITE=VERIFICATO` e `RESTORE_TEST=OK`. I file originali sono stati conservati nel percorso privato `predeploy-backups/rollback-v156-...`; il database live non è stato sovrascritto dalla copia.
- [x] Lo script ha verificato la salute del backend dopo il riavvio; lo stato dell'autoupdater non è stato modificato.
- [ ] **Post-release da fare:** workflow diagnostico privato `remura-collector` su `main`, controllare salute server, 38 mercati, ultimo aggiornamento Myfxbook/COT/Squalincome, RAM/disco e soprattutto `TICK_VOLUME_EURUSD/XAUUSD`.
- [ ] Distinguere `PARZIALE` (storico pre-v1.56 senza `v`) da `ASSENTE` (nessun `v` nelle 64 M15) e `NON_VALIDO`; verificare più cicli chiusi e confrontare con l'origine cTrader.
- [ ] Test UI v1.56 su iPhone: banner versione/data e grafico CVD, stato `N/D` su dati incompleti/stale, niente falsi numeri di eseguiti.
- [ ] Riconciliare la PR `#68`, `main` e il tracciamento SHA dell'autoupdater **solo dopo collaudo live**, senza usare `--init-sha` alla cieca.
- [ ] Verifica esterna OCI billing/quota Always Free, non dimostrata dalle metriche sistema.

Il rilascio *riuscito* non dimostra ancora che i volumi cTrader siano stati acquisiti, né che il CVD abbia potere predittivo. Non ripetere `--apply` solo per ottenere nuovi dati.


## 02/11/2026 ore ~13:05 Italia — esito diagnostica #16 e candidato scheduler intraday v1.57

- [x] Diagnostica 02/11 ore ~11:27 Italia: 38/38 strumenti integri/recenti per criterio generale, ma Squalincome 4/34 analizzati e 14 esclusi `prices_stale`. Non è un errore di integrità: i criteri M15/H1/H4 e CVD sono più stretti del controllo generale.
- [x] EURUSD source `primary`, ultimo tentativo `2026-11-02T08:31:30Z` **ok**, ultima apertura M15 `08:15Z`, latenza dalla chiusura 118 minuti.
- [x] XAUUSD source `primary`, ultimo tentativo `2026-11-02T09:31:43Z` **ok**, ultima apertura M15 `09:15Z`, latenza 58 minuti. Questi risultati confermano successo del tentativo più recente registrato, ma non provano assenza assoluta di problemi del feed.
- [x] Sul ramo separato `feature/intraday-priority-v157` preparato un pianificatore *opt-in* `REMURA_PRIORITY_COLLECTOR_ENABLED=1`: due strumenti prioritari EURUSD/XAUUSD ai giri 1 e 5 di 8 (ogni 60 minuti, anziché ogni 120) senza aumentare i giri né il massimo di 5 simboli per batch. Gli altri 36 mantengono un tentativo per 8 cicli. Non altera le soglie dei segnali.
- [ ] **Costo richieste da misurare prima di attivare:** in 8 cicli, 38 acquisizioni diventano 40 (+2, circa +5,3% richieste per simbolo nella raccolta primaria; ciascun download storico può usare più richieste di trendbar). Nessun costo in euro garantito; verificare API limit/consumi e infrastruttura, non aumentare il carico alla cieca.
- [ ] Eseguire CI, revisione e release manuale protetta v1.57, con backup/rollback e versione/data/ora su ogni pagina. Il codice è solo un **candidato, mai installato**. Per impostazione predefinita il nuovo flag è disattivato.
- [ ] Prima di modificare la VPS, terminare la riconciliazione PR v1.56, main e autoupdater in modo che gli aggiornamenti successivi non sovrascrivano il backend live.
- [ ] Ripetere diagnostica di freschezza e tick-volume di EURUSD/XAUUSD dopo il rilascio, e confrontare le percentuali di esclusione Squalincome senza modificare retroattivamente le definizioni.

## 02/11/2026, ore 16:58 Italia — Diagnostica privata #18 dopo installazione v1.57

- [x] Accesso diretto ai log workflow privato **#18** (run `41476811725`, job `125384444819`): esito `success`, `SERVER_REMURA=ATTIVO`, `PREZZI_COLLECTOR=running`.
- [x] Prezzi **38/38 verificati e recenti** con 0 invalidi, mancanti, parziali o datati per controllo generale.
- [x] **EURUSD tick-volume COMPLETO: 64/64 M15** con `v` valido, 0 assenti, 0 invalidi; ultima apertura M15 14:15 UTC, ultimo tentativo `14:31:30Z` con esito `ok`, latenza misurata dalla chiusura **88 min**.
- [x] **XAUUSD tick-volume COMPLETO: 64/64 M15**, 0 assenti, 0 invalidi; ultima apertura 15:15 UTC, ultimo tentativo `15:31:43Z` `ok`, latenza **28 min**.
- [x] Squalincome: 34 monitorati, 4 analizzati, 30 esclusi; **0 esclusioni per prezzi stale** (diagnostica #17: 12). `price_no_direction=21`, `cot_group_conflict=14`, `cot_no_direction=9` sono cause NON mutuamente esclusive; nessun evento significativo.
- [x] COT 11 TFF + 3 Disaggregated `ready`; Myfxbook VPS `running` ultimo `15:55:15Z`; Capital Firestore non verificato (VPS collector disabled).
- [x] RAM 28,3%, disco 7,9%. Stato autoupdater `up_to_date` ma **SHA installato/target `d6e2cd7575e0` ancora v1.56**: coerente col rilascio manuale v1.57, da riallineare dopo merge e collaudo, senza `--init-sha`. Billing/quota Oracle non verificati.
- [ ] v1.57 ha il **nuovo codice scheduler**, ma la sua opzione è OFF fino all'attivazione esplicita e sorvegliata. La diagnosi #18 non certifica una frequenza di 60 minuti.
- [x] Preparato `deploy/oracle/priority_v157.py` con `--check` read-only, `--enable`/`--disable` separate: hash live backend v1.57, stato autoupdate, lock, salute, permessi; backup di `remura.env` segreto, cambio atomico flag e riavvio con verifica dell'ambiente effettivo del processo; rollback se errore. Test completamente offline. Non chiama broker e non modifica database.
- [ ] Eseguire `--check` con codice fissato a commit e Git blob dopo CI verdi; **nessun flag ancora attivato**, non cambiare la produzione prima di questo gate.
- [ ] Misurare due o più giri completi con nuovo flag, confrontando latenza realizzata, errori, copertura di tutti i mercati, log VPS e quote rate cTrader/Oracle.


## 02/11/2026 ore 17:08 Italia — priorità cTrader attivata sulla VPS

- [x] Dopo preflight `PRIORITY_PREFLIGHT=OK`, è stato eseguito manualmente `priority_v157.py --enable` da sorgente GitHub hash-verified (`7511f1edb58119ccdac2747fa235aedbf17fd8f7`, blob `f20e8c2ca1ac95e1100cbd73a7dc84fac42388a3`).
- [x] Screenshot Termius conferma `BACKUP_CONFIGURAZIONE=CREATO`, `PRIORITA=ATTIVA`, `SERVIZIO=ATTIVO`, `ENV_PROCESSO=VERIFICATO`, `BACKUP_PRIVATO=CONSERVATO`, `DATABASE_INVARIATO=SI`, `SHA_AUTOUPDATE_INVARIATO=SI`.
- [x] Il processo `remura-private.service` ora ha caricato `REMURA_PRIORITY_COLLECTOR_ENABLED=1`; codice v1.57 già presente. **Non ripetere --enable**.
- [ ] Il flag attivo **non certifica ancora** che il tentativo sia avvenuto ogni 60 minuti; servono misure `lastAttempt` in almeno 2–3 campioni distribuiti su ≥2 ore, sia per EURUSD sia per XAUUSD, ed esito `ok`.
- [ ] Verificare che restino 38/38 mercati con dati validi e che il tasso Squalincome `prices_stale` non aumenti; monitorare timeout, rifiuti e qualità CVD.
- [ ] Budget: 40 tentativi-simbolo teorici / 2 ore, contro 38 (+5,26%); controllare limiti cTrader e Oracle, senza affermare 0 euro dai soli indicatori RAM/disco. Nessun servizio a pagamento introdotto.
- [ ] Attivazione del flag e GitHub `main` sono indipendenti: PR #69 ancora draft, `main` e SHA autoupdate ancora da riallineare **dopo** collaudo. Non usare `--init-sha`, né modificare la VPS dalla diagnostica read-only.


## 02/11/2026 ore 19:30 Italia — controllo live dopo 2h22 dalla priorità ON

- [x] Diagnostica privata GitHub Actions `remura-collector`: workflow #18, **nuovo tentativo #2** avviato direttamente in sola lettura alle 19:29 CET; run `41476811725`, job `125468399872`, esito `success`; nessuna chiamata aggiuntiva al broker dal workflow.
- [x] `SERVER_REMURA=ATTIVO`; collector `running`; prezzi **38/38 verified**, **38/38 recent** nella diagnostica generale, 0 mancanti, invalidi, insufficienti.
- [x] EURUSD e XAUUSD: ultimo tentativo comune **18:01:30Z (19:01:30 CET)**, `ok`; ultima apertura M15 **17:45Z**, età dalla chiusura **30 min**; tick volume entrambi **64/64**, zero assenti o invalidi. Il piano prioritario è ON da 17:08 CET, ma un singolo campione post-attivazione **non** dimostra ancora intervalli esatti di 60 minuti.
- [x] COT: TFF 11/11 e DISAGG 3/3 pronti; Myfxbook `running`, aggiornamento **18:21:31Z**; Capital VPS disabled/Firestore non verificato.
- [x] Squalincome **34 monitorati, 5 analizzati, 29 esclusi**, `no_significant_event`. **9 esclusioni `prices_stale`** (erano 0 al precedente campione pre-attivazione). Altre cause non univoche: `price_no_direction=15`, `cot_group_conflict=14`, `cot_no_direction=9`; non sommare come mercati distinti.
- [!] **Nuovo problema di coordinamento:** `price_store.audit_market` segnala `recent` per ultimo M15 fino a 180 minuti, mentre `signals_monitor.frame_direction` rifiuta *ciascun timeframe* oltre **M15 180 min / H1 120 min / H4 300 min**. Con 36 simboli raccolti ogni ~2h, Squalincome può scartare 9 mercati se l'ultima H1 supera 2h anche quando il controllo generale è tutto verde. **Indagare per simbolo e timeframe con sola diagnostica metadata** prima di cambiare soglie o aumentare le API; possibili soluzioni: scansione coordinata a fine batch/aggiornamenti, migliori tempi per i simboli scartati, misurazione latenze H1/H4. Non mascherare vecchi dati con soglie arbitrarie.
- [x] VPS RAM **28,1%**, disco **7,9%**. Oracle billing e quote effettive non verificati; basso consumo RAM/disco non dimostra costo 0€. Backup SQLite non verificato dalla diagnostica GET, ma testato durante rilascio v1.57.
- [ ] Ripetere un altro campione read-only intorno alle **20:15–20:45 CET** per ricavare due orari post-attivazione per EURUSD/XAUUSD e valutare gli intervalli, mantenendo il flag ON se il server resta stabile.
- [ ] Dopo verifica cadenza e anomalie Squalincome, pianificare il gate PR #69 (rimuovere trigger CI temporaneo, merge con verifica file e successiva riconciliazione SHA autoupdater); **nessuna modifica ora alla VPS**.


## 02/11/2026 ore 20:34 Italia — validazione della prima cadenza prioritaria

- [x] Ho riavviato in sola lettura il job GitHub privato **#18, tentativo #3** (run `41476811725`, job `125502747029`), esito `success`. Nessuna scrittura sul server né nuove chiamate cTrader dal workflow.
- [x] **Cadenza di raccolta verificata su un intervallo consecutivo:** EURUSD e XAUUSD ultimo tentativo precedente `2026-11-02T18:01:30Z` e successivo `2026-11-02T19:01:30Z`, **esattamente 60 minuti**; entrambi `ok`. Non equivale alla conferma di regolarità futura continua.
- [x] EURUSD/XAUUSD ultima apertura M15 `2026-11-02T18:45:00Z`, 34 minuti dalla chiusura; tick volume **64/64** M15 per entrambi. Collector `running`, prezzi **38/38 verified e recent**, 0 mancanti o invalidi.
- [x] COT 11+3 contratti pronti, Myfxbook VPS running, RAM **28,1%**, disco **7,9%**. Costi OCI reali, quote broker e Capital Firestore **non verificati** dalla diagnostica.
- [!] Squalincome **34 monitorati, 5 analizzati, 29 esclusi**, **8 cause `prices_stale`** (erano 9 alle 19:30), `no_significant_event`. Non interpretare tutte le esclusioni come guasti; i motivi possono sovrapporsi.
- [x] Preparata e integrata nel solo repository diagnostico `remura-collector` la **PR #9** (`5f2f6775d092bcdfa374c4a932510fd3ae0164d8`), con test CI verdi: conteggi *aggregati* di quali timeframe M15/H1/H4 superino le soglie nel campione di `prices_stale` e quanti non siano attribuibili. Usa soltanto i GET già esistenti, nessun nome mercato, OHLC, token, codice live o deploy.
- [ ] Eseguire una nuova `workflow_dispatch` sul **main di remura-collector** per leggere i contatori nuovi `SQUALINCOME_STALE_FRAME_M15/H1/H4/NON_ATTRIBUIBILI`, prima di correggere la logica; il rerun di un vecchio workflow non esegue automaticamente il codice appena integrato.
- [ ] Collaudare più cicli e verificare stabilità dei 36 strumenti, rate/quota API e fatturazione Oracle; non aumentare la frequenza senza misure.


## 02/11/2026 ~21:07 Italia — diagnostica privata #21 con nuova attribuzione timeframe

- [x] Workflow **#21** manuale su `remura-collector/main` al commit `5f2f6775d092bcdfa374c4a932510fd3ae0164d8` (run `41516228498`, job `125520382723`): `success`, diagnostica sola lettura. `PREZZI_VERIFICATI=38`, `PREZZI_RECENTI=38`, collector running, server attivo.
- [x] **EURUSD/XAUUSD** `lastAttempt=20:01:30Z`, entrambi `ok` da `primary`; precedente 19:01:30Z, prima 18:01:30Z. **Tre tentativi successivi, due intervalli da 60 minuti esatti**, non garanzia permanente. Ultima apertura M15 `19:45Z`, età dalla chiusura 7 minuti. Tick-volume M15 **64/64 ciascuno**, 0 assenti/invalide.
- [x] **Squalincome**: 34 monitorati, 6 analizzati, 28 esclusi, `prices_stale=0` (alle 19:30 era 9; alle 20:34 era 8); nessun evento significativo. Nuovi contatori `SQUALINCOME_STALE_FRAME_M15=0`, `H1=0`, `H4=0`, `NON_ATTRIBUIBILI=0` e `ESCLUSIONI_ESAMINATE=0`. **Non attribuiscono le precedenti 8–9 esclusioni**, perché nel campione della nuova scansione `19:54:09Z` non c'era alcun `prices_stale`.
- [x] COT TFF 11/11 e disagg 3/3 ready, Myfxbook running ultimo 20:01:31Z; RAM 27,9% e disco 7,9%. Capital Firestore, quota/costi reali Oracle non verificati; stato autoupdater ancora `d6e2cd7575e0` della v1.56, mentre codice v1.57 è operativo manualmente.
- [ ] **Bug intermittente Squalincome da approfondire**: monitorare anche la *distanza dalla soglia* per ciascuno dei tre timeframe su tutti i 34 strumenti, usando metadata già presenti; non limitarsi alle sole scansioni con `prices_stale`. Non innalzare artificialmente i limiti, né aumentare la frequenza cTrader per tutti.
- [ ] Poi consolidare in sicurezza v1.57 su GitHub `main`, rimuovere trigger CI temporaneo e riallineare SHA autoupdater dopo verifica del codice effettivo, conservando backup/rollback; v1.58 divergences resta solo offline.


## 02/11/2026 ~21:13 Italia — nuovo controllo preventivo Squalincome pronto

- [x] Merge `remura-collector` PR #10, commit `2f3760a73791cc140903975737ee841ae354e303`, CI `success`. Nuova diagnostica **read-only** `SQUALINCOME_HEADROOM_{M15,H1,H4}_{KNOWN,OVER_LIMIT,NEAR_30M,UNKNOWN,OLDEST_AGE_MIN}` calcolata sullo stesso GET già utilizzato per la scansione.
- [x] Il controllo segnala *anche in assenza di esclusioni* quante serie M15/H1/H4 sono vicine alle soglie (entro i 30 minuti precedenti) e quante l'hanno superata o hanno timestamp assente, usando **lastScanAt** per non misurare ritardi fittizi della richiesta GitHub.
- [x] Nessuna modifica VPS, SQLite, segreti, frequenza cTrader, condizioni Squalincome o CVD; nessuna chiamata broker aggiunta. Validato con test offline e privati.
- [ ] Eseguire in futuro nuova **workflow_dispatch su remura-collector/main** (non rerun vecchia run) per osservare i nuovi 15 valori aggregati e individuare timeframe a rischio anche nei campioni con `prices_stale=0`. Nessun merge PR v1.57 su main finché non abbiamo completato i gate di rilascio e riconciliazione.


## 02/11/2026 ~21:15 Italia — diagnosi conclusiva H1 (workflow #23)

- [x] Nuovo workflow privato `remura-collector` **#23** (`41517411632`, job `125524382487`), main diagnostic SHA `2f3760a73791cc140903975737ee841ae354e303`, esito `success`, six GET preesistenti, 0 broker calls da diagnostica. `PREZZI_VERIFICATI=38/38`, `PREZZI_RECENTI=38/38`.
- [x] **Causa degli scarti individuata:** Squalincome `prices_stale=14` su 34 (30 esclusi totali, 4 analizzati). Attribuzione `M15=0, H1=14, H4=0, non attribuibili=0`. Headroom su tutti i 34: **M15** 34 validi, 0 oltre soglia (180min), più vecchia età 114min; **H1** 34 validi, **14 oltre soglia 120min**, età massima **129min**, 0 prossimi alla soglia entro 30min; **H4** 34 validi, 0 oltre 300min, più vecchia 249min. Tutti i 14 hanno H1 tra >120 e <=129min; scarto immediato ≤9min. Esclusioni intermittenti 9 (19:30) → 8 (20:34) → 0 (21:07) → 14 (21:15). **Non è incoerenza né volume assente**.
- [x] Verificato nel codice: `price_store.market_document` rigenera le H1/H4 solo dalle M15 effettivamente acquisite; `signals_monitor.frame_direction` impone H1 ≤120min dopo la chiusura, mentre il controllo generale richiede soltanto ultima M15 ≤180min. Con rotazione regolare di 36 mercati ogni ~120min e bucket H1 orari, la scansione ogni 15min può leggere H1 poco oltre 120min. Un ricalcolo locale senza M15 nuove **non può rendere freschi dati vecchi**.
- [x] EURUSD/XAUUSD ultimo tentativo `20:01:30Z`, success `ok`, ultima M15 aperta `19:45Z`, latenza 15min; entrambi volume 64/64 e source primary. RAM 28,4%, disco 7,9%, COT 11+3 ready, Myfxbook running. Billing OCI e Capital Firestore non verificati.
- [ ] **Candidato correzione v1.58, esclusivamente offline e con test:** Squalincome event-driven all'**ingest riuscito** dei batch, limitando la scansione ai simboli appena aggiornati (o snapshot causale coerente). Senza nuove API broker, per non perdere le occasioni già fresche; registrare per ogni segnale il timestamp della M15/H1 usata e l'ora reale del calcolo. Mantenere la guardia H1 di 120 minuti, niente finta “freschezza” o alert retroattivi. Occorre verificare lock/concorrenza SQLite, baseline COT e idempotenza.
- [ ] Per avere **tutti** i 34 strumenti sotto H1 120min in ogni istante sarà probabilmente necessario un feed più frequente (incrementale/live subscribe) o maggiore carico API. Misurare prima costi/rate broker, disponibilità feed e beneficio rispetto al prezzo-only; **non** passare indiscriminatamente a polling dei 38 ogni 15min.
- [ ] PR #69 v1.57 resta draft e attualmente non mergeabile perché `main` è avanzata su workflow, riconciliazione e dati. Preparare integrazione conservativa con test a commit finale e pianificare riallineamento autoupdater v1.57 separato, **non** fare merge alla cieca. VPS v1.57 attiva e stabile.
