# REMURA TradingView — ROADMAP PROSPECTIVE + FREE QUOTA LAB v0.8.4
**Aggiornamento roadmap: 11/11/2026, ore 18:37 CET**
**PR #102 DRAFT/OPEN — NO MERGE, NO DEPLOY, NO WEBHOOK, NO ORDINI.**

## CHECKPOINT D1 UE CONFERMATO — 11/11/2026 18:37 CET
- [x] Screenshot Cloudflare D1 Settings del database ricreato dall'utente:
  **Jurisdiction = The European Union**, **Region = Eastern Europe**,
  **Read replication = Disabled**. Verificata la giurisdizione europea dopo
  sostituzione del precedente DB senza giurisdizione.
- [ ] **Nome D1 non visibile** nello screenshot; prima di qualsiasi
  query verificare che sia proprio `remura-tv-lab-eu` e che non sia
  uno dei servizi esistenti.
- [ ] D1 creato, ma **schema tv_flow_events non ancora applicato**.
  Passaggio utente iPhone: aprire Console nel DB UE corretto;
  incollare SQL `gateway-lab/schema.sql` contenente unicamente
  CREATE TABLE/INDEX IF NOT EXISTS; Execute; verificare
  che compaia la tabella `tv_flow_events`, gli indici e 0 righe.
  Non applicare SQL sul DB precedente o su altri servizi.
- [ ] Gateway/Worker non distribuito, nessun secret, webhook o
  heartbeat attivato. Dati reali non ancora raccolti.



**PR #102 DRAFT/OPEN — NO MERGE, NO DEPLOY, NO WEBHOOK, NO ORDINI.**

## CHECKPOINT D1 CREATO DALL'UTENTE — 11/11/2026 18:31 CET
- [x] Screenshot D1 Database Overview dell'utente: database appena
  inizializzato, **0 tabelle**, **0 query**, **0 righe lette**, **0 righe
  scritte**, **12,29 kB** storage base. Da verificare nome effettivo
  `remura-tv-lab` e giurisdizione/location: NON sono visibili
  nel ritaglio dello screenshot. Non dichiarare nome verificato.
- [x] I due Workers preesistenti rimangono intatti.
- [ ] Prossimo passaggio manuale nel database **solo dopo verifica nome**:
  tab `Console`, applicare **solo** SQL non distruttivo
  [schema D1 LAB](gateway-lab/schema.sql) (CREATE TABLE/INDEX IF NOT EXISTS).
  Verificare poi `Number of Tables: 1`; nessun evento memorizzato.
- [ ] Non creare Worker/alert/secret, non abilitare webhook o heartbeat
  finché non sono completati i controlli successivi e autorizzati.



**PR #102 DRAFT/OPEN — NO MERGE, NO DEPLOY, NO ORDINI.**

## CHECKPOINT CLOUDFARE FREE ACCOUNT — 11/11/2026, 18:24 CET
- [x] Screenshot forniti dall'utente della dashboard Workers & Pages:
  **204/100.000 richieste oggi** e **301/200.000 eventi Observability oggi**.
  Workers già presenti: `mirko-news-calendar`, `telegram-mirko-bridge`.
  **Non modificare o riutilizzare questi Workers.**
- [x] Screenshot forniti dall'utente della dashboard D1:
  **0/10 database**, **0/5M letture giornaliere**, **0/100k scritture giornaliere**,
  **0B/5GB spazio totale**. Anche la vista mensile mostra 0 DB, 0 letture,
  0 scritture, 0B spazio, alla data 11/11/2026.
- [x] Le quote reali account Cloudflare per Workers+D1 sono state
  verificate **al momento degli screenshot**; limiti futuri e CPU
  dell'eventuale Worker LAB ancora da misurare. Il modello di budget
  resta prudenziale.
- [ ] **Prossima azione esclusivamente manuale dall'iPhone:** creare
  nel piano Free un D1 dedicato `remura-tv-lab`, previa verifica
  dettagli nella schermata `Create Database`. Preferire giurisdizione
  UE, se disponibile; WEUR location hint non equivale a vincolo legale UE.
  NON attivare Worker/alert/webhook, non applicare schema SQL prima
  della conferma della creazione D1.
- [ ] Verificare ID e configurazione del nuovo database **senza
  pubblicare segreti**. Configurazione, schema, Worker e webhook rimangono
  attività successive isolate e autorizzate.



**PR #102 DRAFT/OPEN — NO MERGE, NO DEPLOY, NO LIVE, NO ORDINI.**

## CHECKPOINT v0.8.4 (11/11/2026 18:05 CET)
- [x] Aggiunti [QUOTA GUARD gratuito](quota_budget_v1.py) e
  [7 prove automatiche](test_quota_budget_v1.py), per proteggere
  costi/storage durante il futuro pilota `FXCM:EURUSD` M5.
- [x] Stimati limiti con **guardrail interni** 10% richieste e scritture Free
  giornaliere, 65% spazio DB da 500 MB; 20KB/evento, overhead 1.4×,
  ritentativi 1.1×. Un simbolo M5/30gg rientra nel modello; due simboli
  M5/30gg superano lo spazio **prudenziale**, due/14gg rientrano.
  Sono stime massime, non consumo reale account.
- [x] Totale suite automatica prevista: **62 test sintetici**
  (16 schema + 18 esiti + 7 quota + 21 gateway Node).
  Run verde sul codice [#43064598345](https://github.com/mirkoworz/remura/actions/runs/43064598345)
  HEAD `fc6ce03b1e730b3cbf252b799cd38d4bca8c1d74`; test
  confermati sul runner, nessun endpoint realmente collaudato.
- [x] Inventario riutilizzo: in `main` sono presenti configurazione Firebase
  Web e piano Firestore privato Capital.com; non sono una destinazione
  webhook autenticata pronta, né attestano quota disponibile.
  Prima scelta: gateway Cloudflare/D1 di laboratorio isolato; valutare
  accesso REMURA C a dati riassuntivi solo dopo coordinamento.
- [x] Aggiornata [guida gateway](gateway-lab/README.md) con limiti,
  modello risparmio e motivi dell'isolamento.
- [ ] Non sono verificabili da GitHub: **utilizzo reale del tuo account
  Cloudflare**, CPU Worker per request, durata reale D1, consegna alert.
  Occorre il dashboard/account, consenso per deploy isolato e
  successivo test sintetico prima di attivare TradingView.
- [ ] Alert TradingView v0.8.1 resta **telemetryEnabled=false** e
  **heartbeat=false**. Nessun dato prospettico reale raccolto da
  questo filone. Per avviare con affidabilità occorrerà
  prova di consegna e heartbeat di tutte le barre M5.
- [ ] Restano fuori da questo filone A/B/C, merge, deploy e ordini.



**PR #102 DRAFT, OPEN — NESSUN MERGE, DEPLOY, WEBHOOK O ORDINE.**

## CHECKPOINT v0.8.3 — 11/11/2026 18:01 CET
- [x] Verificate oggi le condizioni Workers Free e D1 Free alle fonti
  ufficiali Cloudflare: **100.000 richieste Worker/giorno, 10ms CPU/request;
  D1 5M righe lette/giorno, 100.000 righe scritte/giorno,
  500 MB per database e 5 GB/account, max 10 database Free**.
  Le quote sono condivise; **utilizzo reale account Cloudflare NON VERIFICATO**
  e nessun login/account o deploy è stato effettuato.
- [x] Conservati v0.7 funzionante e Pine v0.8.1 confermato funzionante
  dall'utente; nessuna nuova prova Pine necessaria in questa fase.
- [x] Gateway v0.8.2 Cloudflare/D1 e autenticazione/anti-duplicato rimangono
  **soltanto sorgenti offline**. Prove GitHub CI eseguite, nessun URL webhook
  o database realmente creato.
- [x] Creato [OUTCOME AUDIT v0.8.3](outcome_audit_v1.py) e
  [18 regressioni sintetiche](test_outcome_audit_v1.py); aggiornato
  [protocollo](PROTOCOLLO-PROSPETTICO-V08.md).
  Misura **15/30/60 minuti (3/6/12 M5)** su snapshot chiusi con ricezione
  prospettica entro 120s, OHLC/ATR, MFE/MAE, retest RIFIUTO/ROTTURA/
  INDEFINITO, coorti ER e sostituzioni livello senza look-ahead.
- [x] Mancanza di barre M5, timestamp ricezione, ATR o cambio anchor
  produce **esito mancante**. Livelli riclassificati si valutano con
  identità di nascita, non col rank finale. Nessun esito reale finora.
- [x] Confronto baseline descrittivo solo se abbiamo barre `HEARTBEAT`
  complete della stessa data/fascia UTC prefissata: 00–08 / 08–16 / 16–24.
  Nessuna inferenza di profitto: benchmark a segno permutato, intervalli
  di confidenza e walk-forward OOS **ancora da implementare**.
- [x] Aggiornata CI Python per includere 16+18=34 regressioni sintetiche
  e aggiunte alle 21 regressioni Node del gateway = **55 test**;
  risultato verde [run #43063528207](https://github.com/mirkoworz/remura/actions/runs/43063528207)
  sul commit `b27f2f38c4e9f6c5d06bba2b81a339b1da75477b`.
  Riconfermare sull'ultimo HEAD dopo la modifica roadmap.
- [ ] Verificare quanto già utilizza l'**account Cloudflare** dell'utente:
  nessun plugin Cloudflare disponibile, serve controllo via dashboard
  prima di creare risorse.
- [ ] Approvazione esplicita **solo prima** di creare Worker/D1 o abilitare
  alert/webhook; prima effettuare preflight piano Free e misurare costo/CPU.
- [ ] In futuro: test ricezione sintetica isolata e quote, monitor buchi,
  eventuale heartbeat BAR M5 dopo consenso, esportazione dei record veri;
  solo allora valutare prospetticamente ER/RT.
- [ ] Filoni A/B/C, REMURA live e trading automatico rimangono intatti.



**PR #102 DRAFT, OPEN — NO MERGE, NO DEPLOY, NO WEBHOOK, NO ORDINI.**

## CHECKPOINT CONFERMATO — 11/11/2026 17:52 CET
- [x] **Pine v0.8.1 compila e funziona in TradingView**, conferma esplicita dell'utente il 11/11/2026 dopo l'ultima prova. Non richiedere nuovamente questo controllo; il payload runtime e la consegna webhook **NON** sono ancora testati.
- [x] Verificati i requisiti TradingView: webhook JSON `application/json`, 2FA, timeout remoto 3 secondi, quattro IP pubblicati ufficialmente, porte 80/443; chiamate possono essere perse.
- [x] [Creato GATEWAY LAB v0.8.2](gateway-lab/README.md) Workers + D1 come codice offline: [receiver](gateway-lab/worker.mjs), [schema](gateway-lab/schema.sql) e [21 test sintetici](gateway-lab/worker.test.mjs), senza token, webhook URL, account cloud o deploy.
- [x] Sicurezza fail-closed, IP allowlist + hash token solo configurabile fuori repository, schema JSON versione, body limit 20KB, controllo tempi, deduplica tramite D1, limite best-effort 20 record/min, nessun accesso remoto ai dati né routing a B/C.
- [x] Aggiornata GitHub Actions `.github/workflows/remura-tv-telemetry-lab.yml` per eseguire **16 test Python + 21 test Worker Node** (no network/no third-party dependencies); run verde [43062097541](https://github.com/mirkoworz/remura/actions/runs/43062097541) per SHA `633ae6cae73934f5746dedb79a848a41c6c881b7`. Le successive esecuzioni su nuove modifiche vanno verificate di nuovo.
- [x] Confronto quote ufficiali Cloudflare Workers Free: 100k richieste/giorno, 10ms CPU; D1 Free: 5M righe lette/giorno, 100k righe scritte/giorno; quote condivise con eventuali altre risorse. Nessun costo o risorsa cloud nuovi.
- [ ] Verificare **CI finale** dopo ultime modifiche alla documentazione/test, senza confondere i mock locali con un endpoint reale.
- [ ] **NON AUTORIZZATO:** creare Worker/D1, impostare segreti, attivare Cloudflare o TradingView webhook: prima verifica quote e decisione esplicita dell'utente.
- [ ] Prima attivazione futura: prova endpoint isolato e payload sintetico; verificare che consegna, token/allowlist, latenza <3s e storage siano corretti. Tutto senza REMURA live.
- [ ] Per studio prospettico completo serviranno **tutte le barre M5** (heartbeat TradingView inizialmente OFF), monitoraggio gap, ER/RT 3/6/12 barre, falsi positivi, replacement drift e benchmark; attivare soltanto nella finestra di ricerca concordata.
- [ ] Nessuna modifica ai filoni A/B/C, nessun trade o promessa statistica; confrontare livelli WEEK/MONTH con metodo del collaboratore dopo acquisizione prospettica.



**PR #102 DRAFT, OPEN — NO MERGE, NO DEPLOY, NO WEBHOOK, NO ORDINI.**

## CHECKPOINT v0.8.1 — 11/11/2026 16:26 CET (SOLO OFFLINE)
- [x] Verificata PR #102 DRAFT/OPEN, branch `research/tradingview-delta-peaks-20261111`, v0.7, manuale, schema e piano webhook; v0.7 resta conservata senza modifiche.
- [x] Creato [REMURA v0.8.1 TELEMETRY](REMURA-ALL-IN-ONE-Premium-v0.8-TELEMETRY.pine) come nuovo script **separato**, `telemetryEnabled=false` e heartbeat OFF di default; `alert()` JSON solo a candela chiusa/realtime.
- [x] Un solo JSON per M5 confermata, per non perdere eventi simultanei con frequenza once_per_bar_close; include OHLC+prev_close+ATR, delta, ER, footprint, snapshot livelli, origine dei livelli, punteggi DAY, nuovi livelli/sostituzioni e flags per quattro tipi di retest.
- [x] Conservati 4 `alertcondition()` legacy, una `request.footprint()` e una `tv.requestVolumeDelta()` (verifica statica).
- [x] [PROTOCOLLO PROSPETTICO](PROTOCOLLO-PROSPETTICO-V08.md): regole **congelate prima degli esiti** per ER e RT 3/6/12 M5, falsi positivi, benchmark e replacement drift; dati **simulati non validi** come prove di efficacia.
- [x] Creati [validatore Python](validate_telemetry_v1.py) e [16 test sintetici](test_telemetry_v1.py) senza dipendenze terze.
- [x] Aggiunto workflow GitHub Actions *solo su file di questo laboratorio* `.github/workflows/remura-tv-telemetry-lab.yml`, sola lettura, no segreti, no deploy, per regressioni Python; runner GitHub standard pubblico gratuito secondo documentazione ufficiale.
- [x] Verifica pubblica quote: Workers Free 100.000 richieste/giorno e 10ms CPU/req; D1 Free 5 milioni righe lette/giorno, 100.000 scritte/giorno, 5GB account **e 500MB/database**; oltre quota il Free blocca operazioni. Nessuna nuova risorsa creata.
- [x] **CI verificata VERDE**: run [43048503823](https://github.com/mirkoworz/remura/actions/runs/43048503823) per HEAD `aaae10c4e6d59951e0b0bb0d4a2c07be27ead5a3`: regressioni sintetiche Python + `py_compile` completati con successo. NON è una compilazione Pine.
- [x] **Pine v0.8.1 COMPILATO in TradingView**, funzionamento confermato esplicitamente dall'utente il 11/11/2026; verifica ancora da fare sul JSON generato a runtime e webhook, senza creare alert.
- [ ] Gateway di test: definire autenticazione sicura compatibile TV, con IP allowlist, body/rate limit, D1/KV retention e deduplica; verificare il consumo di risorse condivise prima di un qualsiasi deploy.
- [ ] Misurazione reale **NON AVVIATA**: può iniziare solo dopo receiver autorizzato, conservazione eventi real-time, e feed M5 prospettico per barre senza eventi.

### Blocco rigoroso prima del collegamento REMURA B/C
Le misurazioni a 15/30/60 minuti devono includere **ogni evento**, non soltanto vincitori.
Finché non emergono confronti out-of-sample credibili, REMURA non deve trasformare
ER+, ER-, POC o RT in ordini o probabilità di successo. Filoni A/B/C non modificati.
Il Free Trial Oracle con scadenza prevista 15/11/2026 è seguito dal Filone A.




## CHECKPOINT CONFERMATO — 11/11/2026, ore 13:55 CET

- [x] **L'utente conferma che la v0.7 funziona** nel Pine Editor/TradingView su FXCM:EURUSD M5, incluse le linee giornaliere. **È una conferma di funzionamento UI, non di correttezza statistica del metodo.**
- [x] Pubblicato il [MANUALE DI STUDIO v0.7](MANUALE-V07-ORDER-FLOW.md): spiegazione puntuale della tabella, regole, sorgenti e protocollo manuale sui livelli/ritorni. CVD eventuale del grafico nativo resta separato dal Pine.
- [x] Creato il [PIANO WEBHOOK TradingView → REMURA](PIANO-WEBHOOK-REMURA.md): JSON dinamico con `alert()`, eventi chiusi, gateway HTTPS e archivio senza attivazione live. PR #102 resta DRAFT.
- [ ] **Prima implementazione successiva**: verificare schema eventi/bar-close, generazione JSON offline, ricezione in test (nessun segreto in GitHub), non attivare ordini o webhook live prima di sicurezza e consenso.
- [ ] Misurazione prospettica su ER e retest DAY a 15/30/60 minuti, benchmark e fallimenti; considerare anche riclassifica dei livelli TOP3 durante la sessione.
- [ ] Verificare una seconda volta su TradingView modalità `HL2` vs `POC FOOTPRINT`, cambio giorno e disponibilità PREVIOUS DAY/MONTH, non sovrapporre retrospettiva al live.

**Prossimo filone TradingView**: v0.8 TELEMETRY JSON verso gateway di test isolato, poi scoring REMURA B/C solo dopo qualità dati validata. Nessun merge, deploy, acquisto o operazione di trading autorizzata. Il periodo Oracle Free Trial previsto in scadenza 15/11/2026 resta responsabilità del Filone A, quindi la nuova architettura deve tollerare un'eventuale assenza VPS.

## NUOVO CHECKPOINT — v0.7 DAY DELTA PEAKS (11/11/2026 13:19 CET)

- [x] Creato [REMURA-ALL-IN-ONE-Premium-v0.7.pine](REMURA-ALL-IN-ONE-Premium-v0.7.pine), lasciando v0.6 intatta.
- [x] **Top3 DAY** su `abs(delta intrabar)` di barre confermate: linee viola, arancione e azzurra dinamiche, filtro minimo 1.5x, nessuna modifica alle metriche ER esistenti.
- [x] **PREVIOUS DAY** massimo in grigio puntinato e reset di giornata al `timeframe.change("1D")`.
- [x] **Retest**: prima intersezione confermata del range High-Low su livelli gia' creati, soltanto da candele successive; marcatori RT, conteggi e quarta condizione di alert.
- [x] **Vista COMPLETO** ampliata ai tre DAY, precedente giorno, conteggi di retest e storico eventi. Conservo le viste isolate RADAR/FOOTPRINT.
- [x] Test strutturali di codice e cardinalita' di chiamate: un solo Footprint, un solo Delta intrabar, una tabella, 4 condizioni di alert.
- [x] **Compilazione e funzionamento v0.7 confermati verbalmente dall’utente** su `FXCM:EURUSD` M5; mancano test quantitativi e verifica completa dei singoli contatori/edge case.
- [ ] Controllare il cambio sessione/giorno, storico parziale, POC N/D e possibili livelli coincidenti.
- [ ] Registrare prospetticamente ogni retest e valutare reazione successiva a 3/6/12 barre senza modificare parametri a posteriori.
- [ ] Confrontare i livelli DAY/WEEK/MONTH coi video di riferimento; distinguere picco di barra da delta cumulativo del periodo.

**Regole scientifiche**: livelli selezionati solo dopo chiusura; la loro classificazione puo' cambiare con nuovi massimi, percio' in analisi prospettica salvare sempre il momento in cui un livello e' nato e quello in cui e' stato sostituito. Le linee non sono ordini istituzionali osservati. Costi addizionali zero, PR #102 DRAFT, no merge/deploy.

## CHECKPOINT v0.6 — ALL-IN-ONE Premium (11/11/2026, ore 12:58 CET)

- [x] Verificato che la precedente v0.5 conteneva gia' i calcoli WEEK/CURRENT MONTH/PREVIOUS MONTH, ma erano leggibili in tabella solo dalla vista RADAR.
- [x] Creato **[REMURA-ALL-IN-ONE-Premium-v0.6.pine](REMURA-ALL-IN-ONE-Premium-v0.6.pine)** separato, senza sostituire i file testati.
- [x] Aggiunta vista default `COMPLETO` con delta intrabar e footprint, Sforzo/Risultato, POC/VAH/VAL, imb, 3 livelli e 3 eventi.
- [x] Conservate viste `FOOTPRINT` e `RADAR`, disegno dei tre livelli, marcatori ER e 3 alert confermati.
- [x] Verificati riferimenti statici: **1 request.footprint**, **1 requestVolumeDelta**, **1 table**, 4 marcatori e 3 alert.
- [ ] Prova **reale di compilazione v0.6** in TradingView EURUSD FXCM M5 e verifica della vista COMPLETO, delle linee e delle altre due viste.
- [ ] Validare visivamente il PREVIOUS MONTH con sufficiente profondita' storica (puo' essere parziale).
- [ ] Stabilire il protocollo di misurazione prospettica ER a 3, 6, 12 barre M5, senza cambiare retroattivamente le soglie o usare dati futuri.
- [ ] Confrontare definizione dei livelli coi video del metodo del collaboratore.

**Vincoli**: no merge/deploy e nessuna modifica ai filoni A/B/C. Nessun nuovo costo; Premium gia' posseduto dall'utente. Il Footprint Forex resta classificazione intrabar del feed, non dati ordini istituzionali CME. Prossima fase statistica senza promettere profitti.

## Nuovo checkpoint visuale v0.5 — 11/11/2026 12:48 CET

- [x] **FOOTPRINT v0.5 visibile e dati nativi presenti** su `FXCM:EURUSD` M5 (screenshot utente). Indicatore `REMURA Order Flow Radar Premium LAB v0.5` compilato e pannello presente.
- [x] Verifica qualitativa di Buy 92, Sell 109, Delta -17, Delta/Volume circa -8,5%, 0 righe BUY imbalance e 0 righe SELL imbalance su candela LIVE. POC/VAH/VAL visibili: dati provvisori, nessuna interpretazione istituzionale.
- [ ] Verificare **vista RADAR** del medesimo script v0.5 e confronto dei marker ER con v0.4.
- [ ] Verificare variazioni durante la candela e dati della candela chiusa; differenze footprint vs delta stimato.
- [ ] Avviare protocollo di misurazione a 3/6/12 barre (M5), prima ipotesi e benchmark fissati *prima* di interpretare gli esiti.

Nota: nel grafico l'utente ha attivato anche il tipo **Footprint volume nativo**. Le celle colorate appartengono al tipo di grafico TradingView, NON alla tabella disegnata dallo script Pine.

## Checkpoint
- [x] Laboratorio indipendente `tradingview/delta-peaks/`, PR #102 DRAFT.
- [x] **v0.1**: primo indicatore con delta stimato, segnalazioni ER e livelli, verificato in screenshot TradingView.
- [x] **v0.2**: soglia delta su 30 barre precedenti, distanza minima 6 barre, riduzione rumore.
- [x] **v0.3**: formule numeriche Sforzo/Risultato/Efficienza e test visivo su EURUSD FXCM M5.
- [x] **v0.4**: radar con colorazione dinamica delta, intensita' 1–5, picchi arancioni, anomalie viola, stato LIVE/CONFERMATO, storico di 3 picchi confermati, barre colorate solo su richiesta.
- [ ] **Compilazione v0.4** e screenshot del radar durante una barra aperta e alla chiusura.
- [ ] Verificare l'assenza di segnali aggiunti o rimossi rispetto a v0.3 a parametri identici.
- [ ] Verificare gestione di dati NA/zero, ATR non disponibile, storico intrabar limitato, cambio timeframe e ricarica.
- [ ] Confrontare livelli WEEK/CURRENT MONTH/PREVIOUS MONTH con i video del metodo di riferimento.

## Codice v0.4
- **Sforzo**: `abs(deltaBar) / SMA(abs(deltaBar[1]), 30)`.
- **Risultato**: `sign(deltaBar) * (close - open) / ATR(14)`.
- **Efficienza**: `Risultato / Sforzo`.
- **ER**: Sforzo >=3.5, Efficienza <=0.07, gap minimo 6 barre e barra confermata.
- **LIVE**: anteprima aggiornata mentre la candela e' aperta, mai salvata come segnale definitivo.
- **CONFERMATO**: marcatori, allarmi e ultime 3 anomalie/picchi solo a barra chiusa.
- **Livelli**: per ora massimo |delta| della candela in periodo, prezzo hl2, non un livello istituzionale identificato.

## Test Premium riuscito e integrazione v0.5 (11/11/2026, ore 12:40 CET)

- [x] `REMURA-Footprint-Premium-Probe.pine` si compila e produce dati in TradingView su **FXCM:EURUSD M5** (screenshot utente). POC/VAH/VAL e imbalance valorizzati; sulla candela LIVE osservati buy 16, sell 23, delta -7, POC 1.11335, VAH 1.11340, VAL 1.11330, BUY IMB=0, SELL IMB=1.
- [x] Creata **[REMURA-Order-Flow-Radar-Premium-v0.5.pine](REMURA-Order-Flow-Radar-Premium-v0.5.pine)** come nuovo file separato. Condivide in un unico script il radar v0.4 e i campi Footprint Premium, con viste RADAR/FOOTPRINT selezionabili; una sola `request.footprint()`.
- [x] Preservati ER, marcatori, ultimi tre picchi, livelli Week/Monthly e alert solo su barre confermate.
- [ ] **Test compilazione** v0.5 in Pine Editor + screenshot delle viste FOOTPRINT e RADAR; controllare feed N/D e aggiornamento LIVE.
- [ ] Confronto su alcuni eventi della differenza tra delta intrabar stimato e footprint (non forzarne uguaglianza).
- [ ] Valutare se POC/imbalance migliorano la capacità di leggere Sforzo/Risultato in modo prospettico, senza introdurli ancora nei segnali.
- [ ] Definire le metriche di efficacia a 15/30/60 minuti su dati prospettici e procedere alla loro misurazione. Includere falsi positivi e benchmark.

**Limite:** footprint FXCM non identifica esecuzioni CME o banche. v0.5 ancora senza test sul grafico; resta una ricerca separata in PR #102 DRAFT.

## Nuovo filone Premium — test footprint (11/11/2026 11:58 CET)
- [x] Confermata da documentazione TradingView disponibilita' di `request.footprint()` per piano **Premium**.
- [x] Creato **[REMURA-Footprint-Premium-Probe.pine](REMURA-Footprint-Premium-Probe.pine)** su questo ramo: prova isolata di BUY/SELL classificati, delta footprint, POC, VAH/VAL, conteggio imbalance per riga.
- [ ] **Compilare il test** in TradingView su `FXCM:EURUSD` M5 e verificare che non sia tutto N/D; acquisire screenshot.
- [ ] Ripetere, se possibile, su un future CME con dati autorizzati e distinguere volume reale da tick volume forex. **Non acquistare feed senza preventivo e autorizzazione.**
- [ ] Confrontare i delta della v0.4 (requestVolumeDelta con 1m) con il delta footprint nativo (granularita' interna differente), senza sommarli o considerarli uguali.
- [ ] Solo dopo prova positiva: pianificare integrazione POC/imbalance in una **v0.5 del RADAR**, mantenendo toggle e fallback N/D, e successiva misurazione prospettica ER a 15/30/60 minuti.

Il piano Premium e' gia' attivo secondo l'utente; **nessun ulteriore abbonamento** necessario per la funzione Pine Premium. L'accesso a particolari dati futures CME in tempo reale potrebbe richiedere un abbonamento dati distinto. Nessun deploy di REMURA live.

## Registro nuovo
- **11/11/2026 11:58 CET — Footprint Premium PROBE v0.1**: aggiunta una prova nativa autonoma alla PR #102 DRAFT; Radar v0.4 lasciato invariato. Attesa compilazione in TradingView.

## Fase successiva — MISURA
1. Definire ora, prima di osservare i risultati, una metrica per ogni evento ER confermato: prezzo, delta, effort, efficiency, ATR, simbolo, timeframe, istante e origine del feed.
2. Misurare reazioni a **3, 6 e 12 barre M5** (15/30/60 minuti), MFE/MAE e spostamento in ATR, senza classificare ER+ come SELL o ER- come BUY senza test.
3. Confrontare con le normali candele e con picchi non-ER; includere i falsi positivi e la dipendenza da sessioni e notizie.
4. Documentare versione e parametri per evitare ottimizzazioni retrospettive.
5. Dopo: valutare la fedelta' alla metodologia Week e Monthly con esempi verificabili, eventuali modifiche ai livelli e solo poi integrazione REMURA.

## Regole del laboratorio
- Priorita' al gratuito, monitorare quote e limiti TradingView prima di usare alert o webhook.
- Nessuna dichiarazione di ordine istituzionale da tick volume/volume FXCM.
- No merge, deploy, credenziali, webhook o modifiche ai filoni A/B/C.
- Sempre versione e data/ora CET/CEST in testa a script e documenti.
- Compilazione in Pine Editor e comportamento LIVE vanno osservati separatamente dai test di statistica e predittivita'.

## Registro
- v0.1 — 11/11/2026 08:41 CET: prototipo.
- v0.2 — 11/11/2026 08:54 CET: selezione picchi e pulizia.
- v0.3 — 11/11/2026 09:03 CET: metriche ER.
- 11/11/2026 09:39 CET: screenshot di v0.3, compilazione e grafico apparentemente corretti.
- **v0.4 — 11/11/2026 11:26 CET**: Order Flow Radar colorato, LIVE/CHIUSA, intensita' e registro ultimi tre picchi. **In attesa di compilazione sul grafico**.
