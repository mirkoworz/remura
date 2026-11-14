# REMURA TradingView — ROADMAP v0.8.63-lab (CVD transition preflight)
**Aggiornamento 14/11/2026 CET — compilazione Pine confermata, preflight TEST**
**PR #102 DRAFT/OPEN — nessun merge, nessun nuovo deploy, nessun ordine.**

## CHECKPOINT v0.8.63 — PINE COMPILATO E PREFLIGHT TRANSIZIONE
- [x] Utente conferma compilazione Pine v0.9.1 CVD TELEMETRY PREVIEW. Non implica trasmissione live o verifica runtime del nuovo payload. Indicatore originale e alert BTC non modificati dal repository.
- [x] v0.8.62 CI Telemetry #43592148416 SUCCESS 190 Python; dry-run #43592148446 e #43592145314 FAILURE perché test attende ValueError invece di AuditError sul manifest irrisolto. Fail-closed corretto. Corretto solo test con eccezione e messaggio esatti per entrambi i casi, nessun allentamento.
- [x] Nuovo preflight GET-only per stato LEGACY TEST ON, hash secret nome/tipo, D1 EU distinto, limiter noto; rifiuta stato CVD già attivo e stati inattesi. Tre test mock, aggiunti al dry-run. Nessun accesso live/stima billing implicita.
- [ ] Verificare CI aggiornata; predisporre workflow owner-only read-only per preflight e matrice rollback, poi workflow di transizione con guardia specifica. Nessun deploy prima di prova e approvazione esplicita. Non attivare alert CVD; stop BTC domenica sera. PR #102 DRAFT. Produzione intatta.

## CHECKPOINT v0.8.62 — TRANSIZIONE CVD E ROLLBACK
- [x] v0.8.61 CI #43591911967 e dryrun legacy #43591911943 SUCCESS, 190 test Python e 6 Node CVD, parità sui fixture. Legacy worker.mjs confrontato byte per byte col pin weekend effettivamente distribuito 9b6fae547761153c5d4d0b9aa8b7ec3e281f6662: identico.
- [x] Nuovo cvd_transition_bundle_v1.py: riconosce soltanto quinto binding CVD_PREVIEW_ENABLED noto e delega i 4 originali alla guardia già esistente, prepara due bundle privati, candidato e rollback con sorgente legacy identico; default OFF, dry-run CLI solo ID sintetici. 6 test sicurezza e Wrangler compile-only su entrambi. Lettore CVD ora ha CLI esplicita con log aggregato sanificato.
- [ ] CI da verificare. Importante: vecchi workflow di emergenza/refresh non riconoscono quinto binding, NON distribuire candidato finché guardia dedicata non è disponibile su main e non è provato rollback con metadati attuali. Prima compilare Pine v0.9.1 su TradingView senza abilitare alert. Nessun deploy, nessun cambio BTC o produzione, nessuna risorsa nuova, quote reali ancora non misurate.

## CHECKPOINT v0.8.61 — LETTORE DEDICATO E PARITÀ VALIDATORI
- [x] Gateway candidato distingue retry byte-identico da payload conflittuale (409, conserva prima riga). Non è ledger persistente dei conflitti: non dichiarare assenza di conflitti solo da D1. Legacy invariato.
- [x] Lettore CVD TEST dedicato (SELECT con simbolo/versione/finestra esplicita, verifica identità EU TEST, cap 100 righe + sentinella). Conteggi qualità CVD, baseline, eventi delta, footprint, confronto delta e diagnostica matematica; raw non loggato; is_timely=0 obbligatorio, no ammissione scientifica. Nessun workflow live aggiunto ancora.
- [x] Test reader e parità accettazione/chiave JS-Python su fixture sintetiche condivise, CI da verificare. CVD-only eventi conteggiati separatamente da event_type legacy.
- [ ] Compilare v0.9.1 separatamente, predisporre manifest/gate TEST esplicito e verifica live dopo riapertura. Non collegare nuovo payload al vecchio Worker. BTC/produzione e PR #100 invariati. Consumi effettivi non misurati.

## CHECKPOINT v0.8.60 — GATEWAY CVD SEPARATO, NO DEPLOY
- [x] v0.8.59 CI #43591645674 e dry-run #43591645688 SUCCESS: 184 test Python, 8 nuovi CVD.
- [x] Nuovo worker_cvd_candidate.mjs: deriva dal gateway v0.8.40, aggiunge esclusivamente schema CVD preview FX:EURUSD/FX M5 con flag CVD_PREVIEW_ENABLED=true, configurazione congelata e controlli qualità, pivot, 120s. Legacy FXCM/BTC invariati. Auth/allowlist/limiter e cap body invariati. Identità CVD per barra/versione e is_timely=0 per escludere vecchi lettori scientifici; tempestività trasporto verificata separatamente. Raw envelope archiviato nella tabella già esistente (no migrazione necessaria); INSERT OR IGNORE conserva prima riga, non rileva conflitto su duplicato, limite da risolvere prima di pilot. Event_type legacy riguarda delta e non comprende CVD-only, reader dedicato dovrà distinguere.
- [x] Aggiunti 6 test Node con mock D1 e integrazione CI offline. Manifest/deploy esistenti puntano ancora worker.mjs; nessun deploy candidato. Nessun costo nuovo.
- [ ] Verificare CI, aggiungere lettore CVD dedicato, test parità JS/Python su stessi fixture, doppioni conflittuali, gate deploy TEST e compilazione Pine v0.9.1. Non inviare nuovo formato al vecchio webhook. Raccolta BTC invariata. PR #102 DRAFT.

## CHECKPOINT v0.8.59 — CVD INTEGRATO SU FX:EURUSD
- [x] Foto utente 14/11/2026 circa 12:45 CET: Pine v0.9 CVD LAB su EURUSD M5, chart ID FX:EURUSD (non FXCM:EURUSD), qualità 5/5 OK, CONTINUO, CVD giorno -2.073K, segmento circa -2.06K/287 barre, prezzo/CVD 30/6, marcatori CV+/CV- visibili con RT e livelli. Conferma rendering e calcolo storico, non parità numerica certificata, cattura live o edge; nessuna nuova validazione alert BTC.
- [x] Gateway TEST attuale ammette esattamente FXCM:EURUSD/FXCM (o BTC nella finestra). FX:EURUSD/FX NON equivale automaticamente a quel cohort. Mantenerli distinti e non inviare nuovi payload al Worker attivo.
- [x] Pine v0.9.1 CVD TELEMETRY PREVIEW separato: sender OFF per default, nuovo envelope e snapshot versionati, solo FX:EURUSD M5 standard/M1, unico alert per barra realtime confermata quando abilitato, heartbeat sempre; configurazione Delta+CVD dichiarata, stato qualità/segmento, flag prezzo/CVD e timestamp pivot. Correzione gap M5 intraday invalida giornaliero. Originale v0.9 visivo e v0.8.1 live restano immutati.
- [x] cvd_telemetry_preview_v1.py validatore offline: schema strict, nuova identità per barra, ricezione entro 120s, coorte FX distinta, config di riferimento D0.8 port, null preservati, subset benchmark, conferma pivot, controllo disponibilità delta e CVD. Confronto delta non prova accuratezza feed. Non connesso al Worker o a B/D4; nessuna ammissione scientifica. 8 regressioni candidate, CI da verificare.
- [ ] Verifica compilazione v0.9.1 dopo CI, sempre nuovo indicatore separato senza abilitare alert/webhook. Poi gateway TEST compatibile e migrazione separata con autorizzazioni/gate, reader e prova reale alla riapertura. Non modificare raccolta BTC. Nessun nuovo costo, quote effettive ancora non misurate.

## CHECKPOINT v0.8.58 — COMPILAZIONE VISUALE BTC CONFERMATA
- [x] CI Telemetry LAB #43587330856 e Wrangler dry-run #43587330870 SUCCESS; log 176 test Python principali, 7/7 nuovi statici, markers D-B e copertura CVD sintetici PASS.
- [x] Foto utente 14/11/2026 (orologio grafico circa 12:39 CET): indicatore ALL-IN-ONE Premium v0.9 CVD LAB caricato sul grafico BINANCE:BTCUSDT M5, livelli e pannelli visibili; compilazione/rendering confermati dal riscontro utente. Gate CVD mostra SOLO EURUSD M5 STANDARD / M1, N/D; non è evidenza del calcolo CVD su EURUSD. Telemetria BTC originale non modificata né nuovamente verificata in questo checkpoint.
- [ ] Verifica visuale CVD su EURUSD M5 standard, lowerTF=1, senza sostituire alert BTC; mercato chiuso non impedisce verifica storico disponibile. Confronto feed FX vs FXCM e qualità M1; se disponibile storico, osservare CVD e Data Window. Nessuna conclusione di parità runtime o edge dal solo screenshot BTC. Poi preparare schema CVD versionato, compatibilità gateway e test separati. Nessun deploy o costo aggiunto.

## CHECKPOINT v0.8.58 — RECUPERATO CVD D0.8, PINE INTEGRATO v0.9
- [x] Recuperato D0.8 da PR #100 branch experiment/track-d-tv-fxcm-cvd-20261109, blob immutabile 4160994d14240ab2af5eff0c67d00c95671d7567. Protocollo storico congelato resta intatto. D0.8 su FX:EURUSD: 4679/4679 delta continui uguali a CVD nativo nel CSV storico; 439 candidati prezzo, 87 con CVD, differenza media 1h -0.6680 pip (non prova di edge, nessun miglioramento storico primario). Non equiparare FX:EURUSD e FXCM:EURUSD né cumulare coorti o attribuire aggressioni istituzionali.
- [x] Nuovo [Pine v0.9 CVD visual-only](REMURA-ALL-IN-ONE-Premium-v0.9-CVD-LAB.pine) commit 37377a79dd9f2735e7f464ab80a080a1b911ad94 e 2a1832dd39445e4c7a0e70ae29d6459a7f10a073: preserva corpo Delta/ER/Footprint/livelli; port D0.8 M1 x5, stesso grafico standard M5 e lowerTF=1, feed FX o FXCM distinti; warmup, segmento, reset giorno, gap, pivot causali, benchmark prezzo-only, marcatori CV+/CV- barra conferma; pannello bottom-left e Data Window con differenza delta indipendente vs delta esistente. Una sola request.footprint; nessun alert()/alertcondition e nessuna telemetria. Compilazione TradingView NON verificata (CI statica). D0.8 e v0.8.1 live invariati, nessuna modifica worker/schema o alert BTC. Nuova revisione non ancora paragonata al CSV.
- [x] 7 regressioni statiche commit d49801a0f84bb0b52fb4200f6495ae55e18fae15. CI da verificare. Prossimo passaggio manuale indispensabile per compilazione visuale su EURUSD M5, NON sostituire alert esistente; verificare identità feed e confronto native delta. Solo dopo si potrà preparare telemetria CVD versionata e validatore/gateway compatibile. Usare benchmark storico D0.8 congelato, non ottimizzare a posteriori.
- [ ] Pilot FX v1 già predisposto alla riapertura, non bloccato da prova visuale v0.9. D4/D5 v0.8.57 169 test verdi, CVD B proxy separato, sentiment non ancora riconciliato. PR #102 DRAFT, nessun merge o deploy, quota effettiva non verificata. Stop alert BTC domenica sera.

## CHECKPOINT v0.8.57 — BATCH INTEGRATO D4/D5, STRATEGIE E COPERTURA CVD
- [x] v0.8.56 commit 6376929c5fcc23c2d6e6d78c0b6457b74bbca804: CI #43586913453 e dry-run #43586913460 SUCCESS. 162 test principali, marker REMURA_D_B_CROSS_TRACK_SYNTHETIC=PASS (reale codice B pin, fixture sintetica, nessun DB live).
- [x] Rafforzato dossier: limita finestra B/FX e blocca mismatch dei campi config v1 prima di confrontare relazioni. Correlazioni descrittive, non segnali. Dashboard aggiornata alla v0.8.57 con data/ora e cutoff.
- [x] Valutazione esiti: mediana ritorni close-to-close in ATR e media baseline di sessione pesata per evento; 15/30/60 minuti. Contatori maturazione e missing preservati. Ritorni descrittivi, non PnL eseguibile; overlap, spread, slippage e OOS ancora non verificati. Nessuna ammissione scientifica.
- [x] Nuovo bridge read-only CVD opzionale: usa audit B esistente con due snapshot query_only, HMAC privato fornito dal runtime, restituisce esclusivamente copertura B separata (mai presumere abbinamento allo stesso segnale TV). Fixture reale codice B in memoria aggiunta a CI. Retail resta UNKNOWN; riconciliazione shard e prova per singola decisione richiedono evidenze effettive e coordinamento B. Nessun segreto o DB privato usato.
- [x] CI v0.8.57 #43587025521 e dry-run #43587025566 SUCCESS, 169 test principali. Marker REMURA_D_B_CROSS_TRACK_SYNTHETIC=PASS e REMURA_B_CVD_COVERAGE_SYNTHETIC=PASS; fixture B reale, sintetica soltanto. Workflow FX su main commit `1968376958c7875e2edb712cd1b85707b88d3af6`, pin `3aaad585d9f2dde996facae6a6fe7fcc055107b7` verificato per includere esiti descrittivi. Nessuna attività manuale ora. Produzione e A/B/C intatti, PR #102 DRAFT. Pilot FX alla riapertura, stop BTC domenica sera; quota effettiva non misurata. Nessun nuovo server/deploy/costo.

## CHECKPOINT v0.8.56 — DOSSIER D4/D5 E TEST CROSS-TRACK
- [x] v0.8.55 CI #43586726553 e Wrangler dry-run #43586726572 SUCCESS.
- [x] D4: dossier con audit causale B esistente (pin 8dc51e8a199dc1cfd45e4cd2e7b339510af2eb2b), connessione SQLite query_only esplicita, join esatto M15/M5, ricevuto prima osservazione, denominatori e UNKNOWN distinti. Relazioni COT/delta intrabar/corpo/footprint descrittive; CVD e retail UNKNOWN, nessun calcolo score operativo. Riuso esiti v0.8.54.
- [x] D5: renderer HTML responsive offline e notifica diagnostica solo anteprima con ID deterministico. Nessun server, pubblicazione, invio, credenziale, costo nuovo o collegamento live. Separazione SYNTHETIC/LOCAL_SNAPSHOT. Nessun dato privato nei log.
- [x] Test sintetici unitari e fixture end-to-end con B realmente importato da checkout separato pin immutabile, DB SQLite in memoria, CI senza segreti. Esito CI da verificare.
- [ ] Se CI positiva, valutare evidenze CVD e sentiment realmente causali disponibili in B (non sostituire UNKNOWN con zero), dashboard TEST solo a seguito revisione. Pilot EURUSD alla riapertura, stop BTC domenica sera. Quote effettive non ancora verificabili dal connettore. PR #102 DRAFT, nessun merge, Worker/DB e A/B/C intatti.

## CHECKPOINT v0.8.55-lab — RACCORDO DECISIONE B M15 / TRADINGVIEW M5
- [x] v0.8.54 CI #43586578003 e dry-run #43586578075 SUCCESS, 8/8 nuovi test e 149 principali; workflow manuale EURUSD su main aggiornato al pin `dd6855f189c85633b366bf84c561131d4056ce9e`, commit `8aa90fec0a6d5ff33c852fa38cf46cfa17326e1a`. Nessun deploy.
- [x] Consultato in sola lettura Filone B PR #89 HEAD 8dc51e8a199dc1cfd45e4cd2e7b339510af2eb2b, schema effettivo research_signal_ingest_source_links e vincoli clock/ID di shark_signal_ingest_decision_link.py. Nuovo [raccordo offline](fx_m15_decision_preview_v1.py) commit `9d380b4dbe9dd01471acfa463fdeb1e455efe54c`: esatto close M15 EURUSD → M5 FXCM EURUSD, receipt D <= observed B, nessun fallback su altre barre, audit cutoff e finestra B, forma hash e ID. Input B dichiarato dal chiamante, non verificato contro DB, niente COT/CVD/retail verificati, nessuna equivalenza prezzi cross-feed o integrazione live. [6 regressioni](test_fx_m15_decision_preview_v1.py) commit `29831f2adb086cede55c8991abdff1221164ee4e`, CI da verificare.
- [ ] Continuare offline con raccordo a prove B effettive e dashboard diagnostica; coordinare con B prima di qualunque scrittura o collegamento live. Nessuna modifica ai filoni A/B/C o produzione. BTC già validato sul campione di 42 barre, non ripetere subito; lasciare raccolta e spegnere alert domenica sera. Pilot EURUSD alla riapertura secondo runbook. Quote effettive da verificare.

## CHECKPOINT v0.8.54-lab — ESITI MATURI E RUNBOOK EURUSD
- [x] v0.8.53 CI #43586450902 e dry-run #43586450921 SUCCESS; 6/6 test envelope e 141 test principali.
- [x] [fx_outcome_readiness_v1.py](fx_outcome_readiness_v1.py) commit `84188f95da7a0ab90d639d402cac80d61e8b04f5`, 8 regressioni `e7d020be25e9344171a3ed9739d949210ccda6be`: riuso funzioni outcome v0.8.3, identità D1 e conflitti verificati prima, solo FX, cutoff as-of esplicito, 15/30/60 minuti con 120s di maturazione, distingue pending e missing, controlli baseline HEARTBEAT stessa fascia UTC, nessun prezzo/esito per-barra nei risultati. Input non attestati, nessun edge o ammissione scientifica.
- [x] Integrato nel reader FX candidato `cf3842ae843886496ee1f3643217aff588957286`, cutoff limitato a end+120s per non dichiarare esiti oltre finestra. [Runbook pilota](PILOT-EURUSD-RUNBOOK.md) commit `06fe6b3ec58edf6157685cf26de49a3af83ba846`: stop BTC domenica sera, verifica input effettivi, alert FX v1 e primo timestamp reale, workflow già pronti. Nessun nuovo deploy/credenziale/risorsa.
- [ ] CI v0.8.54 da verificare; aggiornare pin del workflow FX solo dopo successo. Nessuna lettura BTC necessaria ora; raccolta continua. Quote effettive ancora da verificare. Nessuna modifica ai filoni A/B/C o produzione. PR #102 DRAFT.

## CHECKPOINT v0.8.53-lab — BTC 42 BARRE E CONFIGURAZIONE TELEMETRICA
- [x] [Run #43586332330](https://github.com/mirkoworz/remura/actions/runs/43586332330), job #132421515016 SUCCESS alle 11:39 CET. v0.8.49 COMPLETE_WINDOW: 42/42 M5 08:10–11:35 CET, 31 heartbeat, 11 BAR_EVENT, zero gap/invalidi/conflitti/duplicati, 42 tempestivi entro 120s, max lag 6322ms. Footprint 36/42 (6 mancanti). 275 controlli matematici applicabili coerenti, 12/12 effort default30, 11/11 nuove visite; totale 298 controlli applicabili coerenti. DAY1=2 DAY2=3 DAY3=6; nessun ER o PEAK osservato. Parametri e tolleranze restano non attestati/calibrati, BTC escluso dalla ricerca FX.
- [x] [Configured envelope preview](configured_envelope_preview_v1.py) commit `85edbdd1017a79e3e8c3e4075ccf83b88c89be8d` e 6 regressioni sintetiche `2811584d4eb169cd7f5de94220b77b7c68273742`: struttura candidata schema+snapshot v1+config dichiarata; validazione stretta FXCM EURUSD M5, parametri coerenti col riferimento, timestamp gateway, cap byte, nessuna ammissione predittiva. SHA256 calcolato lato lettore, non prova di configurazione autentica. CI da verificare; non è accettato dal gateway live. Non modificare alert o deploy.
- [ ] Prossimo passo: preparare piano pilot EURUSD v1 alla riapertura (workflow già pronto) e migrazione configurazione separata dopo revisione. Non sono necessarie ulteriori letture BTC ravvicinate; lasciare raccolta e spegnere alert entro domenica sera. Quote effettive account non verificate. A/B/C e produzione intatti.

## CHECKPOINT v0.8.52 — WORKFLOW EURUSD PRONTO (11:25 CET)
- [x] CI finale `8c3cdfdb56f2d5988c4d62b485ecfc68069c05db` Telemetry LAB #43582958403 e Wrangler dry run #43582958372 SUCCESS; log confermano 8/8 test specifici del lettore FX, 135 test Python principali.
- [x] Creato [workflow owner-only REMURA EURUSD TEST Analytic Reader](https://github.com/mirkoworz/remura/actions/workflows/remura-tv-fx-analytic-readonly-manual.yml) su main, commit `2a376012cc7c294787852a9a851948753d6452f8`, pin immutabile del candidato CI verificato. Input start_utc/end_utc espliciti in UTC e READ_FX_TEST_ANALYTICS_ONLY; token D1 read solo step live, regressioni senza segreti, nessun cron/deploy/scrittura. Non eseguito perché mercato chiuso. Al pilot scegliere prima chiusura reale dopo attivazione, non una data stimata.
- [x] Controllo sequenziale previsto per le 11 già eseguito alle 10:54 (run #43582760320): 33/33, 3/3 effort e 10/10 retest coerenti. Alle 11:25 ultimo run disponibile ancora quello; nuova lettura BTC opzionale, non ripetere per necessità di validazione già soddisfatta. Solo proprietario può avviare manualmente; nessuna automazione aggiunta.
- [ ] Prossima fase: attestazione config e raccolta EURUSD dopo riapertura; restano da verificare quote effettive account. PR #102 DRAFT, nessuna modifica alla produzione o ai filoni A/B/C. Stop alert BTC domenica sera prima del 16/11 01:00 CET.

## CHECKPOINT v0.8.52-lab — LETTORE EURUSD TEST OFFLINE
- [x] v0.8.51 CI Telemetry LAB #43582860610 SUCCESS; dry run #43582860601 non ancora verificato. Worker candidato già distribuito v0.8.40 accetta EURUSD M5 indipendentemente dal limite temporale BTC; nessun nuovo deploy necessario per payload v1.
- [x] [Lettore FX TEST](gateway-lab/fx_pilot_analytic_reader_v1.py) commit `6b9f74313d64e88a53a32b8e2efee66ade18eae6` e [8 regressioni](test_fx_pilot_analytic_reader_v1.py) commit `a4670a4be7191831ec1fcc6241412d2c14ca49d2`. SELECT parametrizzata, ID D1 TEST EU verificato e distinto, solo FXCM:EURUSD M5, intervallo esplicito UTC da 16/11 00:00 UTC in poi, massimo 72 slot maturi, 100 righe + sentinella; versione non filtrata a priori per non occultare incompatibilità. Conteggi di qualità, configurazione v1 osservabile, latenza, gap, retest e effort; niente log raw o prezzi. Gap su slot richiesti, non prova di disservizio o calendario aperto. Nessuna ammissione scientifica o attestazione input.
- [ ] CI candidata da verificare; poi workflow owner-only manuale con pin immutabile e token read esistente isolato nello step live. Non avviare ora: mercato chiuso. Finestra da impostare in base alla prima chiusura effettiva dopo attivazione FX, non assumere un orario di apertura. Nessuna modifica alert BTC/Pine/Worker/database o A/B/C. Disattivare BTC domenica sera prima delle 01:00 CET di lunedì.
- [ ] Configurazione reale alert e provenienza scientifica da attestare; costi effettivi account ancora da verificare. Non ricreare token o ripetere audit BTC già conclusi.

## CHECKPOINT v0.8.51-lab — SEQUENZA REALE E CONFIGURAZIONE FX
- [x] [Run #43582760320](https://github.com/mirkoworz/remura/actions/runs/43582760320), job 132410812719 SUCCESS alle 10:54 CET. v0.8.49: COMPLETE_WINDOW 33/33 M5 08:10–10:50 CET; 23 heartbeat, 10 BAR_EVENT, zero invalidi/duplicati/conflitti/gap. Max lag 5524ms, 33 entro 120s. Footprint 27 presenti/6 mancanti. 211 controlli matematici applicabili coerenti (135 footprint +66 ER aritmetica +10 retest); 3/3 ricostruzioni effort DEFAULT30 coerenti, 30 warmup non valutabili, 10/10 RETEST_NEW_VISIT_CONSISTENT. Label DAY1=1, DAY2=3, DAY3=6. Nessuna prova di vantaggio, tolleranze provvisorie, parametri alert non attestati. BTC escluso dalla ricerca FX.
- [x] v0.8.50 CI #43582223412 e dry run #43582223419 SUCCESS; log 10/10 handoff e 121 test Python principali.
- [x] [fx_pilot_config_v1.py](fx_pilot_config_v1.py) commit `ddff62be3e326ee606e671a10b38c3caf74fae7e`: configurazione riferimento FXCM:EURUSD M5, default protocollo + heartbeat/telemetry ON; campi esatti, tipi, confronto e SHA256 canonico della configurazione dichiarata. Confronto dei 5 campi osservabili v1, il resto resta non attestato. Nessuna ammissione scientifica. [6 test sintetici](test_fx_pilot_config_v1.py) commit `59d72dff906c1a16666c4c296880bed4740a0624`; CI da verificare.
- [ ] Non necessario ripetere subito BTC audit già riusciti. Lasciare raccolta diagnostica attiva e disattivare alert domenica 15/11 sera prima del 16/11 01:00 CET. Nessuna modifica Pine, Worker, DB, main, A/B/C. Prossimo passo: predisporre pilot EURUSD alla riapertura, prima ricezione e continuità, attestazione parametri effettivi da risolvere. Quote reali Free non verificate. Riprendere da questo checkpoint.

## CHECKPOINT v0.8.50-lab — HANDOFF CAUSALE FX OFFLINE
- [x] PR #102 DRAFT verificata su precedente HEAD; ultimo run reale rimane #43578611804, nessuna nuova lettura avviata autonomamente. Consultato filone B PR #89 DRAFT in sola lettura (shark_sample_admission.py), senza modifica.
- [x] [fx_asof_handoff_v1.py](fx_asof_handoff_v1.py) commit `70146599ce3210aa749dc34c297fbc5ce4be7a16`: solo FXCM:EURUSD M5; finestra decisione esplicita, ricevuti dopo decisione esclusi, nessun fallback a barra vecchia, blocco invalidi/conflitti/late/review; partial con null preservati. Solo candidato descrittivo, provenance export e input alert non attestati. Nessuna ammissione istituzionale/predittiva, ordini, notifiche o integrazione B attiva.
- [x] Dieci regressioni sintetiche `f8e2ca4c16fd2a35b39b23d0bafa22380e8ed1fa` e [contratto D-B](HANDOFF-D-B-V0850.md) `a6c1b48b9cbabd2b44de4085e5c0e212fb728f37`: piano futura attestazione parametri Pine e join as-of indipendente fonti. Nessuna modifica Pine, Worker, D1, main o filoni A/B/C in questo checkpoint. CI da confermare.
- [ ] Ora possibile lettura sequenziale BTC v0.8.49 con stesso workflow READ_TEST_ANALYTICS_ONLY (primo slot valutabile 10:40 CET + 120s). Leggere aggregati, non ricreare alert. Non cambiare pin: handoff v0.8.50 non richiesto per BTC.
- [ ] Prima di pilot FX scientifico: attestazione config effettiva, provenienza e decisioni; futuro schema versionato offline e coordinamento B, quote reali Free da verificare. Ricordare stop BTC domenica sera.

## CHECKPOINT v0.8.49-lab — DIAGNOSTICA MATEMATICA REALE E SEQUENZIALE
- [x] [Run #43578611804](https://github.com/mirkoworz/remura/actions/runs/43578611804), job #132398292616, SUCCESS, 10:02 CET. Marker v0.8.48: COMPLETE_WINDOW, 23/23 M5 08:10–10:00 CET, 16 HEARTBEAT, 7 BAR_EVENT, zero gap/invalidi/duplicati/conflitti; tutte 23 consegne entro 120s, max lag 4312ms. Footprint presente 18, non disponibile 5. Tutti 143 controlli applicabili coerenti (5*18 footprint + 2*23 risultato/efficienza + 7 retest); 25 footprint NOT_EVALUABLE, ER assente. Retest DAY2=3, DAY3=4. Tolleranze provvisorie, nessuna prova di feed accuracy o profitto. BTC diagnostica, dati Forex non contaminati.
- [x] [Diagnostica sequenziale](volume_sequence_v1.py), commit `82b53c207781a8dbed6a1482f6b6baf635e3926f`: ricostruzione effort solo usando 30 delta precedenti consecutivi, tempestivi, disponibili, stesso simbolo/timeframe; gap/late azzerano storico. Lookback 30 valore Pine default NON attestato nello snapshot alert, confronto condizionale, non errore certo. Controllo nuovi retest rispetto a intersezione barra precedente per identità origine/prezzo, anche con cambio rank; ignora assenze/future e non ricostruisce reset sessione o toggle non telemetrizzati.
- [x] Otto test sintetici `57fdbe76595cf7bdb14caf2c81f0a5ed9c96f0ec`; integrato nel reader aggregato `999469dd57943da95064d5b881478982a44a80c0`. CI Telemetry LAB #43578705420 SUCCESS: log 8/8 nuovi test, 111 nel gruppo Python principale. Dry-run non ancora verificato. Nessuna modifica a Pine, Worker, D1 o filoni A/B/C.
- [x] Aggiornato pin dello stesso workflow READ_TEST_ANALYTICS_ONLY su main (commit `c827e213d9a106ebe2a2bf30cb5479a2fe7411e9`, pin `999469dd57943da95064d5b881478982a44a80c0`), nessun deploy.
- [ ] Primo slot con 30 barre precedenti dal 14/11 10:40 CET, utile nuova lettura non prima delle 10:42 CET (120s di maturazione); preferire ore 11:00 o dopo. Nessuna necessità di ricreare alert o verificare di nuovo prima. 
- [ ] Proseguire con telemetria parametri effettivi, continuità retest/sessioni, controlli scientifici e piano quote reali; nessun segnale operativo. Ricordare stop BTC domenica sera prima del 16/11 01:00 CET.

## CHECKPOINT v0.8.48-lab — PRIMA ANALISI REALE COMPLETA
- [x] [Run #43576754550](https://github.com/mirkoworz/remura/actions/runs/43576754550), job #132392552941, SUCCESS alle 09:38 CET. Marker REMURA_TV_TEST_ANALYTIC: COMPLETE_WINDOW, 18/18 slot M5 da 08:10 a 09:35 CET, 12 HEARTBEAT, 6 BAR_EVENT, 18 consegne entro 120s, max lag 4312ms, zero righe invalide/duplicate/conflitti/quarantena, zero slot non osservati. Footprint disponibile 13/18, 5 parziali per footprint mancante. Label RETEST_DAY2=2, RETEST_DAY3=4; nessun ER/picco riportato. Raw JSON letto solo in memoria da D1 TEST, non loggato. BTC esclusivamente diagnostico; nessuna validazione statistica o trading.
- [x] Nuovo [modulo qualità](volume_quality_v1.py) commit `9dcfa3ed6a4367dda5ba98539deff72385c11818`: 12 controlli diagnostici su quantità footprint, somma BUY+SELL, differenza, percentuale, ordinamento VA, risultato ATR, efficienza, segno ER, retest con origine precedente/range intersecato. Stati CONSISTENT/REVIEW/NOT_EVALUABLE/NOT_APPLICABLE. Tolleranze provvisorie; nessuna dichiarazione di accuratezza assoluta o causa del footprint assente. Sforzo baseline, soglie Pine, reset e retest tra barre non ancora ricostruiti.
- [x] Collegamento feature e aggregati diagnostici (commit `176ad8d9b1abe8b613e3502478bbe8203398ed00`, `8b44edd0b154a9c9d9e52a620523589d6daf6baf`); 8 regressioni nuove + 1 integrazione aggregati, sorgente candidato `88016b26286527a0e7779497790e0bdd303055cf`. CI Telemetry LAB #43576933589 SUCCESS, log confermano 9/9 nuovi test e 103 test Python principali. Wrangler dry-run non ancora verificato a questo aggiornamento. Nessuna modifica Pine, Worker, D1 o motori A/B/C.
- [x] Aggiornato lo stesso workflow manuale TEST su main (commit `1a6fe39c7d118da0e698b207b745b17c8d663f82`), pin `88016b26286527a0e7779497790e0bdd303055cf`; regressioni offline prima di leggere D1, token solo step live.
- [ ] Proprietario avvia READ_TEST_ANALYTICS_ONLY per leggere diagnostic_check_counts reali; non ripetere audit metadati. Il footprint assente non equivale a zero né prova di disservizio, causa da investigare.
- [ ] Prossimi passi: controlli sequenziali su retest e baseline effort, confronto dati disponibili/mancanti, protocollo di validazione FX; controllo quote reali del piano Free. Disattivare alert BTC domenica 15/11 sera, prima del 16/11 ore 01:00 CET.

## CHECKPOINT v0.8.47-lab — 17 RICEZIONI REALI E PRIMI BAR_EVENT
- [x] [Run #43576218225](https://github.com/mirkoworz/remura/actions/runs/43576218225), job #132390929891, completato SUCCESS alle 09:31 CET; job deploy skipped. Log effettivi: RECEIPTS_PRESENT, SAMPLE_ROWS=17, MORE_AVAILABLE=False, HEARTBEATS=11, BAR_EVENTS=6, TRANSPORT_WITHIN_120S=17, FIRST_RECEIVED_MS=1794640201649, MAX_BAR_CLOSE_LAG_MS=4312. Conteggio compatibile con 17 chiusure 08:10–09:30 CET, ma timestamp individuali non ancora verificati. SELECT D1 TEST metadati, raw JSON non letto; nessun dato scientifico Forex, nessuna prova di efficacia.
- [x] CI finale v0.8.46 su `c7a77c11f6bf90a7a6e92ca4eeef358d75b2c5dc` SUCCESS (#43570296161 e #43570296168); tutti 14 nuovi test feature confermati nei log #43570270744.
- [x] [Reader analitico TEST](gateway-lab/pilot_analytic_reader_v1.py) commit `5059f9acf0c81d1beb618660f4248eaf0a745ff2`: riusa motore v0.8.46; SELECT parametrizzata solo su D1 TEST EU verificato, esclusivamente BTC M5; massimo 72 slot maturi e cap 100 righe + sentinella. Finestra parte dalla prima chiusura verificata 08:10 CET e scorre dopo 6 ore; attende 120s per ogni slot, verifica anche gap iniziali/finali. Solo conteggi aggregati, no raw JSON/prezzi nei log, no export o scritture. Distinzione tra lettura fallita, nessuna riga, finestra incompleta e incompatibilità/conflitti. Completezza di trasporto non implica accuratezza dati.
- [x] [11 regressioni sintetiche/mock](test_pilot_analytic_reader_v1.py) commit `62b83f1d16ee3aa83cea943348c8f9e7ef39e679`; CI #43576368525 e #43576368482 SUCCESS; log job #132391374712 confermano tutti gli 11 nuovi test ok, 94 test nel gruppo Python principale. Nessun accesso live effettuato dal reader nuovo.
- [x] Creato [workflow manuale owner-only READ_TEST_ANALYTICS_ONLY](https://github.com/mirkoworz/remura/actions/workflows/remura-tv-btc-analytic-readonly-manual.yml) su main (commit `dc6815fd7aabcab4c46037b7491e1ca6429a96c1`), pin immutabile `62b83f1d16ee3aa83cea943348c8f9e7ef39e679`, token D1 read esistente solo nello step live. Nessun merge della PR, deploy, nuova risorsa o accesso D1 produzione.
- [ ] Proprietario esegue una volta READ_TEST_ANALYTICS_ONLY; leggere marker REMURA_TV_TEST_ANALYTIC e distinguere incompatibilità, missing e gap. Workflow non ancora eseguito. Non ricreare alert BTC.
- [ ] Spegnere alert domenica 15/11 sera prima del 16/11 ore 01:00 CET. Proseguire D3 con controlli coerenza numerica/rilevamento retest e D4 solo dopo osservazioni valide. Quote effettive da verificare separatamente. Filoni A/B/C invariati.

## CHECKPOINT v0.8.46-lab — BRIDGE VOLUMETRICO OFFLINE
- [x] HEAD precedente v0.8.45 `e062092c62bb339da52d8f3140bc36e0992914c9` e PR #102 DRAFT/OPEN verificati. Primo heartbeat BTC reale già attestato da run #43569836612; non ripetere autenticazione, configurazione o deploy.
- [x] Riutilizzati validatore e bridge v0.8.15 esistenti. Nuovo [volume_features_v1.py](volume_features_v1.py), commit `ce4bf6ab89b756423b256e4e603aee46d34b1c57`: normalizza export privati D1, verifica identità e feed, M5 completo, origine livelli non futura, finestra BTC e is_timely=0; espone OHLC, delta stimato, effort/risultato/efficienza riportati, footprint/POC/imbalance, distanza livelli in ATR e intersezioni solo con livelli già nati. BTC escluso da ipotesi e ricerca FX anche con trasporto tempestivo.
- [x] Duplicati identici ignorati; conflitti su stessa barra (anche HEARTBEAT/BAR_EVENT) quarantinati. Conteggi di slot non osservati solo tra prima/ultima barra osservata, non prova di outage; nessun calendario Forex implicito. Null distinti da zero. Ipotesi ER e discordanza direzione prezzo/delta non equivalgono a conferma di assorbimento/esecuzioni istituzionali. Nessun segnale, probabilità o ordine. Non pubblicare export o output per-barra nei log.
- [x] [14 test sintetici](test_volume_features_v1.py), commit `45cdcf1978e15442229757be2af2223c2f5fd50a`, scoperti dalla CI Python esistente. Esito CI non ancora osservato al momento della scrittura. Nessuna nuova risorsa cloud e nessuna modifica a Worker, D1 o filoni A/B/C.
- [ ] D1: aggiungere report continuità live TEST a finestre limitate e senza raw JSON; audit precedente campiona solo prime 100 righe. Metadati vuoti != lettura fallita; gap != evento assente. Iniziare con nuovo READ_BTC_RECEIPTS_ONLY manuale (connector GitHub non espone dispatch parametrico). Non rieseguire job di deploy.
- [ ] D2/D3: aggiungere reader TEST-only separato, SELECT strettamente limitata, aggregati redatti; non usare il reader v0.8.16 che punta a D1 principale. Verificare campione reale, coerenza numerica footprint ed ER, qualità retest, esaurimento e confluenze; solo dopo eventuale confronto prospettico con B. Nessun dato BTC scientifico.
- [ ] Verificare CI aggiornata e quote account effettive, poi estendere controllatamente a FXCM:EURUSD M5 e successivamente Gold; nessuna promozione live.
- [ ] Disattivare alert BTC domenica 15/11 in serata, prima di lunedì 16/11 01:00 CET. Promemoria ChatGPT non creato: limite 5/5 automazioni attive. Non cancellare altri promemoria senza consenso.

## CHECKPOINT v0.8.45-doc — PRIMO WEBHOOK REALE BTCUSDT RICEVUTO — 14/11/2026, 08:11 CET
- [x] Dopo rotazione hash e sostituzione URL utente ha eseguito READ_BTC_RECEIPTS_ONLY. [Run #43569836612](https://github.com/mirkoworz/remura/actions/runs/43569836612) completed SUCCESS, job #132371598282 SUCCESS, deploy skipped. Marker effettivi `REMURA_BTC_TEST_RECEIPTS=RECEIPTS_PRESENT`, SAMPLE_ROWS=1, MORE_AVAILABLE=False, HEARTBEATS=1, BAR_EVENTS=0, TRANSPORT_WITHIN_120S=1, FIRST_RECEIVED_MS=1794640201649 (2026-11-14T07:10:01.649Z), MAX_BAR_CLOSE_LAG_MS=1649 (1.649 s dalla chiusura barra). SELECT D1 TEST, raw JSON non letto, validazione segnali non effettuata.
- [x] Prima prova end-to-end di trasporto reale TradingView -> gateway TEST autenticato -> D1 TEST con heartbeat BTCUSDT BINANCE M5. Il corretto URL dopo rotazione è coerente con l'ipotesi hash invece di raw token; nessun codice HTTP del vecchio errore osservato. Nessuna prova di BAR_EVENT, accuratezza footprint/delta, stabilità lunga, rilevazione istituzionali o profitto. BTC is_timely=0, esclusione ricerca FX, nessuna operazione trading.
- [ ] Lasciare alert BTC attivo durante finestra weekend già autorizzata, fino a 16/11/2026 01:00 CET esclusa; fermarlo prima della scadenza. Raccogliere almeno alcune chiusure M5 consecutive, poi leggere conteggio, lag e presenza BAR_EVENT; successivamente costruire bridge analitico offline e validare payload/feature in ambiente isolato, senza promuovere BTC a dato scientifico FX. Al riavvio Forex, pilota FXCM:EURUSD M5 previsto e audit EUR dedicato. Nessun nuovo abbonamento; consumo reale e quote account da verificare separatamente. Nessuna modifica produzione; PR #102 DRAFT.

## CHECKPOINT v0.8.44-doc — ROTAZIONE HASH TEST RIUSCITA — 14/11/2026, 08:10 CET
- [x] Utente conferma nuova coppia generata e aggiornamento GitHub Secret esistente. Run [#43569707989](https://github.com/mirkoworz/remura/actions/runs/43569707989) completed SUCCESS, job #132371212812 tutti gli step verdi; marker effettivi `REMURA_ROTATION_HASH_FORMAT=VALID_NOT_ECHOED`, `Success! Uploaded secret WEBHOOK_TOKEN_SHA256`, `REMURA_TEST_HASH_ROTATION_POSTCHECK=ON_WITH_HASH_SECRET`. Stato TEST ON+hash, D1 TEST e limiter verificati. Nessun deploy codice, nuovo API token, SQL write o intervento in produzione. Version ID aggiornato non letto; non inventare. Corrispondenza raw token con hash ancora da verificare end-to-end.
- [ ] Utente sostituisce intero URL webhook nell'alert BTCUSDT M5 usando **Copia URL webhook TEST** della nuova coppia già salvata, senza ricomporlo, senza usare hash. Non generare un'altra coppia. Attendere nuova chiusura M5 e controllare registro, eseguire READ_BTC_RECEIPTS_ONLY. Non riportare segreti o URL privato in chat.

## CHECKPOINT v0.8.43-doc — ALERT SCATTA, ROTAZIONE HASH TEST PREDISPOSTA — 14/11/2026, 08:04 CET
- [x] Screenshot confermano input LAB JSON+heartbeat, condizione qualsiasi alert(), M5 e webhook selezionato. Avviso arancione riguardava repainting, non errore bloccante. Dopo ricreazione alert utente riferisce evento scattato; causa precedente probabilmente snapshot obsoleto, non dimostrata.
- [x] Seconda lettura BTC [#43569048472](https://github.com/mirkoworz/remura/actions/runs/43569048472), job #132369192654 SUCCESS, `NO_MATCHING_RECEIPTS`, zero heartbeat/eventi, nessuna latenza. Consegna ancora non dimostrata.
- [x] Verificato sorgente generatore: raw token base64url 43 caratteri, digest SHA-256 esadecimale 64 caratteri. Utente ha riportato in chat un URL dal segmento finale compatibile con digest, non con raw token del generatore. NON riportare il valore in roadmap, issue, codice o log; non aprire URL privato. Ipotesi doppio hash -> 403, non confermata da log HTTP.
- [x] Predisposto [workflow manuale di rotazione](https://github.com/mirkoworz/remura/actions/workflows/remura-tv-test-rotate-hash-manual.yml) commit `907d503718278f78c0bc79d56c7895c38cdb60a8`, pin candidato già testato/deployato `9b6fae547761153c5d4d0b9aa8b7ec3e281f6662`. Owner-only main, concurrency condivisa, preflight TEST ON+hash, format 64 hex, dry-run, secret put sul solo Worker TEST e postcheck ON+hash; crea una versione Worker nuova per rotazione, non esegue deploy codice o D1 write. Finestra weekend invariata, nessun token API nuovo. Non eseguito; valore del secret non accessibile/readback non prova corrispondenza.
- [ ] Azione utente: generare una sola nuova coppia, usare bottone **Copia URL webhook TEST** per salvare URL completo privato in Password e **Copia solo l'hash** per aggiornare il Secret GitHub ESISTENTE `REMURA_CF_TV_TEST_WEBHOOK_SHA256`. Non assemblare manualmente né rigenerare fra due copie. Poi dispatch esplicito ROTATE_TEST_HASH_KEEP_GATEWAY_ON, controllare log; solo dopo sostituire URL completo nell'alert BTC. Nessun valore in chat. Verificare successivo webhook e D1. Non modificare Pine, infrastruttura o produzione.

## CHECKPOINT v0.8.42-doc — PRIMA LETTURA BTC TEST RIUSCITA, ZERO RIGHE — 14/11/2026, 07:51 CET
- [x] Run manuale READ_BTC_RECEIPTS_ONLY [#43568259551](https://github.com/mirkoworz/remura/actions/runs/43568259551), avviato 07:50:17 CET, job #132366774473 SUCCESS; deploy saltato. Log effettivi `REMURA_BTC_TEST_RECEIPTS=NO_MATCHING_RECEIPTS`, SAMPLE_ROWS=0, HEARTBEATS=0, BAR_EVENTS=0, MORE_AVAILABLE=False, FIRST_RECEIVED_MS=None, MAX_BAR_CLOSE_LAG_MS=None. SELECT D1 TEST riuscita, nessuna prova di webhook consegnato. Non interpretare verde come ricezione.
- [ ] Primo controllo avvenuto poco dopo chiusura M5 07:50 CET, circa un minuto dopo deploy 07:49:05. Verificare prima che alert TradingView BTCUSDT BINANCE M5 sia attivo, snapshot entrambi input LAB ON, condizione qualsiasi alert(), registro alert / stato webhook. Chiedere solo screenshot registro senza URL o token. Poi nuova lettura dopo almeno una chiusura M5 successiva; distinguere nessun evento, errore HTTP e D1 vuoto. Non cambiare codice/credenziali o ripetere deploy senza evidenze. PR #102 DRAFT, produzione invariata.

## CHECKPOINT v0.8.41-doc — BTC WEEKEND DEPLOY REALE RIUSCITO — 14/11/2026, 07:49 CET
- [x] Proprietario ha avviato DEPLOY_BTC_WEEKEND_TEST. [Run #43568131360](https://github.com/mirkoworz/remura/actions/runs/43568131360) completed SUCCESS; job #132366387268 tutti gli step verdi, job read-only saltato come previsto. Deploy reale solo remura-tv-webhook-test 14/11/2026 07:49:05 CET; versione Cloudflare `313fcee3-31f3-4709-bde6-4a13a05d3ada`. Preflight e postcheck `TEST_GATEWAY_ON_WITH_HASH_SECRET`, marker `REMURA_BTC_WEEKEND_DEPLOY=COMMAND_SUCCEEDED_PENDING_POSTCHECK` seguito dal postcheck positivo. Sorgente v0.8.40 pin `9b6fae547761153c5d4d0b9aa8b7ec3e281f6662`. D1 TEST e limiter invariati; produzione non coinvolta.
- [x] CI documento precedente #43568097384 e #43568097383 SUCCESS.
- [ ] Dopo almeno una candela M5 chiusa successiva al deploy (07:50 CET o successiva), con alert BTC attivo e input LAB abilitati, eseguire una volta READ_BTC_RECEIPTS_ONLY sullo stesso [workflow](https://github.com/mirkoworz/remura/actions/workflows/remura-tv-btc-weekend-test-manual.yml). Leggere conteggi e lag, verificare log TradingView. Al checkpoint nessuna ricezione reale ancora dimostrata, nessun dato o profitto inventato. BTC autorizzato fino a 16/11/2026 ore 01:00 CET esclusa, restano esclusione dal cohort Forex e stessa autorizzazione FXCM:EURUSD.
- [ ] Nessuna ulteriore modifica live necessaria prima della verifica. Nessun nuovo abbonamento o token.

## CHECKPOINT v0.8.40 — TEST TRASPORTO BTC WEEKEND — 14/11/2026, 07:48 CET
- [x] Utente ha scelto `BINANCE:BTCUSDT` spot su TradingView durante chiusura Forex. Non confondere USD con USDT, né spot con perpetual. M5, versione indicatore TELEMETRY v0.8.1-lab, stessi token/URL TEST; entrambi input LAB abilitati da verificare nella creazione alert.
- [x] Gateway candidato v0.8.40 sul branch PR #102 DRAFT: BTC solo `BINANCE:BTCUSDT` + feed BINANCE + M5, finestra tempo ricevitore UTC 14/11 00:00 inclusa → 16/11 00:00 esclusa (01:00 CET lunedì); `is_timely=0` sempre per BTC, nessuna eleggibilità ricerca FX. Simbolo EURUSD invariato, stesso rate limiter combinato 20/60, schema e auth immutati. BTC e FX separati per symbol/event_key; validatore Python FX e bridge invariati. BTC non è un dato sintetico ma trasporto diagnostico, non prova profitto. Nessun DB nuovo, nessuna scrittura effettuata da questa preparazione.
- [x] Nuovi test finestra temporale, feed/timeframe non consentiti, deduplica, IP e separazione ricerca. Manifest refresh richiede stato già `TEST_GATEWAY_ON_WITH_HASH_SECRET` e scadenza non trascorsa; vecchia modalità ON da OFF invariata. Verificatore BTC `test_btc_weekend_receipt_audit_v1.py` legge solo metadati prime 100 righe + sentinella, latenza dalla chiusura barra, con `is_timely=0`, nessun raw JSON nel log. CI pinned `9b6fae547761153c5d4d0b9aa8b7ec3e281f6662` [#43567826288](https://github.com/mirkoworz/remura/actions/runs/43567826288) e [#43567826307](https://github.com/mirkoworz/remura/actions/runs/43567826307) entrambe SUCCESS.
- [x] Workflow manuale su main [REMURA BTCUSDT Weekend TEST](https://github.com/mirkoworz/remura/actions/workflows/remura-tv-btc-weekend-test-manual.yml) commit `92b18cb02a4808239e3710138faf360689619e7f`, checkout pin sopra, concurrency condivisa con emergency, owner-only. Scelta di default `READ_BTC_RECEIPTS_ONLY` esegue esclusivamente lettura; scelta esplicita `DEPLOY_BTC_WEEKEND_TEST` esegue test offline, preflight ON+hash, dry-run, GET fresh, guard orario e deploy al solo Worker TEST. Readback ON+hash. **NON AVVIATO** al checkpoint. Nessuna nuova credenziale o upgrade. Non reattiva Worker spenti. STOP emergenza esistente invariato.
- [ ] Proprietario esegue DEPLOY_BTC_WEEKEND_TEST su main. Verificare run/log postdeploy e version ID, poi dopo almeno una chiusura M5 con alert attivo eseguire READ_BTC_RECEIPTS_ONLY sullo stesso workflow. Non dichiarare successo trasporto finché non ci sono righe D1 corrispondenti e log alert. Se 422, verificare payload e simbolo; se 403 auth/edge; se 503 storage. Nessuna modifica produzione; alla scadenza cessare alert BTC per evitare richieste inutili, tornare al pilota FX.

## CHECKPOINT v0.8.39 — HEALTH HTTP TEST CONFERMATA DA IPHONE — 14/11/2026, 07:41 CET
- [x] Il proprietario ha riportato la risposta di `https://remura-tv-webhook-test.mirkoworz.workers.dev/health`: `{"status":"lab_only","accepting":true}`. Evidenza **HTTP reale da iPhone riportata dall'utente**: gateway pubblico raggiungibile e prerequisiti runtime riconosciuti. Non è un POST TradingView: corrispondenza token originale/digest, allowlist IP, scrittura D1, deduplica e prestazioni ancora da provare. Non ripetere health salvo guasto.
- [x] Il proprietario ha detto "Ok fatto" dopo il recupero del suo URL privato; non rigenerare token. L'effettiva configurazione completa dell'alert (due input LAB, FXCM:EURUSD M5, qualsiasi alert()) non è ancora attestata separatamente; mantenere l'alert attivo se già configurato. Mai chiedere screenshot del token.
- [x] CI preparazione verificatore ricezione [#43564547527](https://github.com/mirkoworz/remura/actions/runs/43564547527) e [#43564547535](https://github.com/mirkoworz/remura/actions/runs/43564547535) entrambe SUCCESS.
- [ ] Prima prova reale attesa alla riapertura FXCM EURUSD: controllare log alert TradingView e poi eseguire una volta [REMURA TEST First Webhook Receipt](https://github.com/mirkoworz/remura/actions/workflows/remura-tv-test-first-receipt-readonly.yml), owner-only manuale, SELECT TEST. Se assenza eventi non equiparare a successo/fallimento del trasporto; verificare stato alert. Il risultato deve distinguere ricezione assente, lettura fallita, heartbeat/eventi, latenza di chiusura barra. Solo dopo esito reale procedere al bridge e all'analisi scientifica.
- [ ] Nel frattempo possibile lavorare offline a bridge/analisi e verifiche quote senza toccare gateway ON, D1 produzione, PR #102 DRAFT o Oracle. Nessun altro deploy Cloudflare o alert sintetico effettuato. 

## CHECKPOINT v0.8.38 — GATEWAY TEST ON REALMENTE DISTRIBUITO; PRIMO ALERT DA CONFIGURARE — 14/11/2026 ore 07:05 CET
- [x] Proprietario ha avviato il workflow manuale [#43564400558](https://github.com/mirkoworz/remura/actions/runs/43564400558): **completed SUCCESS**. Job #132354954983, tutti gli step verdi, preflight `TEST_GATEWAY_OFF_WITH_HASH_SECRET`, compilazione, deploy Wrangler reale del solo `remura-tv-webhook-test`, Cloudflare Version ID `abbd45b0-3926-472a-a613-025d37308746` alle 07:03:11 CET. Readback `TEST_GATEWAY_ON_WITH_HASH_SECRET`, D1 EU `remura-tv-lab-test`, limiter 20/60, flag `INGEST_ENABLED=true`, Secret hash conservato. Worker production, D1 main e Oracle non coinvolti.
- [x] Pine esistente `REMURA-ALL-IN-ONE-Premium-v0.8-TELEMETRY.pine` v0.8.1-lab verificato nel sorgente: `telemetryEnabled` e `telemetryHeartbeat` sono input OFF di default; emette JSON `remura.tv.flow.v1` via `alert(payload, alert.freq_once_per_bar_close)` solo su barre realtime confermate, eventi o heartbeat. Non riscrivere codice né creare token nuovo. Gateway accetta ESCLUSIVAMENTE `FXCM:EURUSD`, M5, versione v0.8.1-lab, IP TradingView previsti, token URL corrispondente al digest.
- [ ] **AZIONE iPhone**: grafico TradingView FXCM EURUSD M5, candele standard, indicatore TELEMETRY v0.8.1, abilitare prima entrambi gli input LAB (alert JSON + heartbeat), poi creare alert sull'indicatore con **Qualsiasi chiamata alla funzione alert()**, URL webhook TEST privato salvato prima nell'app Password, 2FA abilitata; nessun token nel messaggio/script/chat. Payload JSON viene generato dal Pine, non scriverlo a mano. Nominare alert REMURA TEST EURUSD M5. Se non si trova il selettore indicatore, verificare versione corretta. Alert mantiene snapshot degli input: ricreare se modificati. È sabato: niente prova su closed bars storiche/replay; aspettarsi i primi dati dopo riapertura del feed. Nessuna promessa di ora esatta.
- [x] Nuovo verificatore `gateway-lab/test_pilot_receipt_audit_v1.py` (branch PR #102, commit `137bde6f1083f9477087be66b3d0ac3aca85aa30`): solo inventario D1 GET e SELECT parametrizzata via POST sul D1 TEST EU verificato, da istante attivazione 06:03:11 UTC, filtri FXCM:EURUSD M5 v0.8.1-lab, prime 100 righe + sentinella, esclude record sintetico LAB:TEST_ONLY. Riporta conteggi campione, heartbeat/eventi, timely, lag; no raw JSON, token, UUID, prezzi, ordini o writes. 8 test offline; CI su `ab5505390af7511b636fcf065ace05a6cae97164` [#43564547527](https://github.com/mirkoworz/remura/actions/runs/43564547527) in verifica all'ultimo controllo. 
- [x] Workflow owner-only [First Webhook Receipt](https://github.com/mirkoworz/remura/actions/workflows/remura-tv-test-first-receipt-readonly.yml) su main commit `759d5eb48a0ab856bd55e71c8a1b91779d356c99`, pin `ab5505390af7511b636fcf065ace05a6cae97164`, solo manuale, prima self-test poi SELECT read-only. **Non eseguito**. Usare dopo primo alert effettivo, mai su D1 main. Nessuna raccolta reale dimostrata al momento.
- [ ] Salute HTTP pubblica, consegna TradingView, scritture D1 reali, latenza e quote effettive ancora non dimostrate; non confondere metadata ON con ricezione reale. Controllare il log Webhook status e lettura D1, poi bridge scientifico separato. Stop emergenza TEST pronto e non eseguito; non fare merge della PR #102 DRAFT. Piano Free invariato, nessun upgrade; monitorare budget CPU/requests del servizio condiviso e pause se anomalie.

## CHECKPOINT v0.8.37 — HASH TEST REALMENTE INSTALLATO; PREPARAZIONE INGEST ON SOLO MANUALE — 14/11/2026 ore 01:54 CET
- [x] L'utente ha generato sul proprio iPhone l'URL/token TEST e inserito **soltanto il relativo SHA-256** in GitHub Secret `REMURA_CF_TV_TEST_WEBHOOK_SHA256`, senza condividerli in chat o codice. Non richiedere più di ripetere questi passaggi.
- [x] Su `main`, workflow [`REMURA TEST Webhook HASH SECRET` run #43536663737](https://github.com/mirkoworz/remura/actions/runs/43536663737) avviato dal proprietario e terminato **SUCCESS**; ogni job step incluso il postcheck riuscito. Log: `REMURA_TEST_HASH_FORMAT=VALID_64_HEX_NOT_ECHOED`, `REMURA_TEST_HASH_SECRET_PREFLIGHT=OFF_NO_SECRET_VERIFIED`, `REMURA_TEST_HASH_DRY_RUN=PASS`, `REMURA_TEST_EMERGENCY_PREFLIGHT=TEST_GATEWAY_OFF_NO_SECRET`, `Success! Uploaded secret WEBHOOK_TOKEN_SHA256`, POST-CHECK `REMURA_TEST_EMERGENCY_PREFLIGHT=TEST_GATEWAY_OFF_WITH_HASH_SECRET`. Cloudflare conserva il SOLO **hash come Secret**, non il raw token. Nessun alert, webhook, SQL dati live o trade.
- [x] Il Worker `remura-tv-webhook-test` è ancora **INGEST_ENABLED=false** nell'ultimo GET autenticato post-installazione, con binding D1 UE `remura-tv-lab-test` e limiter `20/60`. Version ID post secret put non estratto: non inventarlo. Worker Production `remura-tv-ingest-lab` e D1 MAIN non toccati. Non equiparare hash installato a ricezione live verificata.
- [x] Preparato su PR #102 DRAFT `gateway-lab/prepare_test_ingest_on_v1.py`: **solo due GET metadata** e bundle temporaneo `0600`, richiede stato esatto `TEST_GATEWAY_OFF_WITH_HASH_SECRET`, D1 TEST EU distinto da main e limiter verificato, manipola **esclusivamente** il flag effimero OFF→ON senza includere alcun token o hash nel manifest; il codice non esegue deploy o SQL. Dieci nuovi test avversariali `test_prepare_test_ingest_on_v1.py`: mancanza Secret, già ON, DB main, Worker diverso, binding inattesi, rate limiter alterato, CPU/quote non assunte; [Telemetry LAB #43537187218](https://github.com/mirkoworz/remura/actions/runs/43537187218) **SUCCESS** su `759d0236e79e42141a6402c717b5e5a663dac8e9`. Wrangler dryrun #43537187209 ancora **IN PROGRESS** all'ultimo GET, verificare esito prima di eventuale autorizzazione.
- [x] Creato su `main` workflow [`REMURA TEST Gateway INGEST ON (manual only)`](https://github.com/mirkoworz/remura/actions/workflows/remura-tv-test-ingest-on-manual.yml) al commit `92a4d5e60a3a60b1d00615a6a09710c8bf528abe`, checkout immutabile `759d0236e79e42141a6402c717b5e5a663dac8e9`, solo `workflow_dispatch` proprietario su main, scelta esplicita `ENABLE_TEST_INGEST_ONLY_AFTER_SEPARATE_CONSENT`. Prima del deploy eseguirà suite Node/Python, D1 TEST+binding GET, dry-run Wrangler, secondo GET stato OFF+hash; dopo richiederà GET stato ON+hash. **NON AVVIATO, NON AUTORIZZATO implicitamente dalla prova hash**; concurrency condivisa con hash/deploy/rollback/emergency.
- [x] Il workflow emergency STOP [`remura-tv-emergency-stop-test-manual.yml`](https://github.com/mirkoworz/remura/actions/workflows/remura-tv-emergency-stop-test-manual.yml) è già pronto in `main` per futuri ON/Secret, non è stato eseguito né provato live dopo ON.
- [ ] **Gate prima di primo webhook reale**: confermare 2FA TradingView e capacità del piano di inviare webhook, URL privato da copiare dal vault dell'utente SOLO nell'alert; test autentico `FXCM:EURUSD` M5 e JSON `remura.tv.flow.v1`; calcolare costi/quote/CPU Workers Free e possibili 403 edge, non attivare produzione. TradingView ufficiale: IP webhook 52.89.214.238, 34.212.75.30, 54.218.53.128, 52.32.178.7, HTTPS 443 e timeout 3 secondi. Il codice gateway include già la lista.
- [ ] **Solo dopo consenso ulteriore** avviare manualmente workflow INGEST ON; primo dato prospettico atteso soltanto a mercati aperti e alert operativo; controllare HTTP edge, D1 TEST, deduplica, errori/CPU/budget, quindi STOP TEST temporaneo se necessario. Zero ordini eseguibili.
- [x] Nessun nuovo servizio a pagamento né upgrade, PR #102 ancora DRAFT e REMURA LIVE su Oracle non aggiornato. Webhook ancora OFF al checkpoint.

## CHECKPOINT v0.8.36 — TOKEN SU IPHONE E GITHUB INSTALLER HASH TEST, TUTTO ANCORA OFF — 13/11/2026, ore 23:20 CET
- [x] Creato il generatore `tradingview/delta-peaks/crea-token-test.html`: Web Crypto usa 32 byte casuali (`crypto.getRandomValues`), costruisce un segmento URL base64url di 43 caratteri e calcola SHA-256 sul dispositivo. Due copie distinte: **hash per GitHub Secret** e **URL originale da incollare solo in TradingView**. CSP `connect-src 'none'`, nessun fetch/cookie/storage o dipendenza esterna. NON generare né pubblicare raw token in chat, GitHub o log.
- [x] Test JavaScript `test_local_token_keygen.test.mjs`: entropia WebCrypto, hash corretto, URL esclusivamente Worker TEST, copia/cancellazione, fail closed in browser non sicuro, assenza richieste di rete. CI v0.8.35 [#43517264232](https://github.com/mirkoworz/remura/actions/runs/43517264232) e [Wrangler #43517264181](https://github.com/mirkoworz/remura/actions/runs/43517264181) entrambi **SUCCESS**.
- [x] Copia identica del generatore statico pubblicata su `main` commit `d18ee78d14a730f04ae8584e416cdb40a49fda9b` per futura apertura da iPhone, URL atteso `https://mirkoworz.github.io/remura/tradingview/delta-peaks/crea-token-test.html`. [Pages build #43517880644](https://github.com/mirkoworz/remura/actions/runs/43517880644), [Price #43517881014](https://github.com/mirkoworz/remura/actions/runs/43517881014) e [Insights #43517881059](https://github.com/mirkoworz/remura/actions/runs/43517881059) **SUCCESS**; HTTP effettivo della nuova pagina NON verificato esternamente, quindi non chiamare HTTP accessibilità certificata. Nessun servizio esterno contattato dal generatore.
- [x] Sul branch PR #102, `gateway-lab/prepare_test_hash_secret_v1.py` verifica con due GET autenticati D1 UE e Worker TEST: richiede `TEST_GATEWAY_OFF_NO_SECRET`, flag OFF, D1 TEST, limiter esatto, Secret assente. Controlla solo il formato di 64 esadecimali minuscoli del hash futuro, mai raw URL token, crea manifest temporaneo `0600` per l'operazione successiva, senza Cloudflare mutations. Test negativi di ON, Secret esistente, DB MAIN e token mancante. [Telemetry #43517614571](https://github.com/mirkoworz/remura/actions/runs/43517614571) e [Wrangler #43517614990](https://github.com/mirkoworz/remura/actions/runs/43517614990) **SUCCESS** sul pin `af67fda26aae215da0a6157e79f73ef9b76a9a3b`.
- [x] Su `main` creato workflow **owner-only, solo manuale** [`REMURA TEST Webhook HASH SECRET`](https://github.com/mirkoworz/remura/actions/workflows/remura-tv-test-hash-secret-manual.yml), commit `34af821be7f1461352e8af43ee4964b149b06efd`, checkout immutabile `af67fda26aae215da0a6157e79f73ef9b76a9a3b`; quando l'utente sceglierà `INSTALL_ONLY_TEST_HASH_KEEP_INGEST_OFF`, userà solo il futuro GitHub Secret `REMURA_CF_TV_TEST_WEBHOOK_SHA256` (hash, non raw token), token Editor limitato al Worker TEST, preflight/last GET e `wrangler secret put WEBHOOK_TOKEN_SHA256`; postdeploy verifica rigorosa `TEST_GATEWAY_OFF_WITH_HASH_SECRET`. Nessuna esecuzione di questo workflow né Secret GitHub creato adesso.
- [ ] **Prossimo gate MANUALE indispensabile soltanto quando pronti all'alert**: da iPhone generare URL/test-hash sul client, conservare il raw URL con cura, inserire SOLO hash nel nuovo GitHub repository Secret e avviare l'azione manuale; non copiare URL in chat. Verificare che il run sia realmente verde e flag OFF prima di qualunque apertura ingest.
- [ ] Sono ancora **NO-GO**: attivazione `INGEST_ENABLED=true`, alert TradingView, POST reali, qualità eventi, quota CPU/limiter e prima integrazione Track B/C. Emergency-stop disponibile come workflow MANUALE ma mai testato LIVE con Secret/ON. L'operazione `wrangler secret put` creerà un nuovo deploy del SOLO Worker TEST, quindi richiede conferma owner separata e controllo postdeploy, non è un semplice salvataggio passivo.
- [x] Fino a qui nessuna mutazione di Cloudflare successiva al TEST-OFF v0.8.34, nessun ordine, LIVE Oracle/Worker Production/D1 MAIN non toccati; la PR #102 resta DRAFT.

## CHECKPOINT v0.8.35 — EMERGENCY STOP TEST ON/OFF+SECRET PREPARATO, NO LIVE — 13/11/2026, ore 23:07 CET
- [x] Partenza dal **v0.8.34 già verificato**: [deploy #43515467198](https://github.com/mirkoworz/remura/actions/runs/43515467198) SUCCESS, Worker `remura-tv-webhook-test` codice gateway completo `v0.8.6`, **Version ID `1d47f428-c176-48d3-8d80-10ed0a94a43e`**, binding TEST D1/limiter 20/60, `INGEST_ENABLED=false`, nessun Secret TEST. Non ripetere deploy/audit precedenti.
- [x] Aggiunto al branch DRAFT PR #102 `gateway-lab/emergency_stop_test_guard_v1.py`, con guard **sola lettura**: solo due GET autenticati ai metadata D1+settings del Worker TEST, UUID D1 EU verificato e diverso dal MAIN, namespace limiter previsto, flag `true/false`, esattamente i tre binding attesi più l'eventuale `WEBHOOK_TOKEN_SHA256` di tipo `secret_text`. Rifiuta stato/Worker/DB o binding imprevisti senza leak di segreti. Non contiene deploy né modifica Cloudflare.
- [x] `test_emergency_stop_test_guard_v1.py`: suite avversariale di casi sintetici, con ON/OFF + secret, DB MAIN, duplicati, limiter alterato, metadata mancanti e verifica della non divulgazione. CI su commit `be11918d619121ce7c1388a987e78db576709e65`: [Telemetry #43516433373](https://github.com/mirkoworz/remura/actions/runs/43516433373) **SUCCESS** + [Wrangler dry-run #43516433311](https://github.com/mirkoworz/remura/actions/runs/43516433311) **SUCCESS**. Sono test di codice, NON prova di rollback live.
- [x] Sul solo `main` installato il workflow owner-only [`REMURA TEST Worker EMERGENCY STOP (manual only)`](https://github.com/mirkoworz/remura/actions/workflows/remura-tv-emergency-stop-test-manual.yml), commit `0bd2e87b57dfc53f8b9ceb769b5c011cbd0b1685`, checkout immutabile `be11918d619121ce7c1388a987e78db576709e65`, selezione `STOP_TEST_TO_INERT_BOOTSTRAP` e concurrency comune agli altri deploy TEST. Non parte automaticamente: richiede un futuro consenso manuale e **NON è stato eseguito**.
- [x] Il futuro stop di emergenza, se autorizzato, effettua test, preflight GET, build/dry-run del solo `bootstrap_test_worker.mjs` inerte (nessun D1, limiter, var o preview), **secondo** preflight immediatamente prima del deploy, e verifica postdeploy GET: consentiti zero binding oppure **solo** il vecchio Secret hash ancora conservato (mai letto, non più usato dal codice inerte). Il vecchio rollback v0.8.32 resta OFF-only e NON sostituisce il nuovo stop; nessuna revoca di Secret o verifica traffico edge implicita.
- [ ] **Gate ancora APERTI**: disponibilità effettiva e costo limiter (le quote Workers non bastano a dimostrarlo), prova HTTP edge non inconcludente, verifica del comportamento del rollback dopo la prima attivazione reale; generazione del token forte *sul dispositivo dell'utente*, hash SHA-256 messo in GitHub Secret solo dopo istruzioni/consenso, mai raw token in repository/chat/log/Pine; comando GitHub separato per inserire in Cloudflare **solo hash**, mantenendo OFF e prima di qualunque webhook.
- [ ] Prima del primo POST TradingView: protezione contro richieste anonime e controllo quote/CPU, test con Secret, istruzioni Alert M5 su `FXCM:EURUSD`, conferma 2FA e consenso per `INGEST_ENABLED=true`. Misurare latenza/deduplica e dati D1 TEST; non esportare a produzione e non dichiarare segnali operativi né edge scientifico.
- [x] Nessun workflow emergenza avviato, nessun webhook reale o ordine, nessun nuovo token/costo, Worker TEST **continua OFF** all'ultimo stato verificato v0.8.34, Worker Production `remura-tv-ingest-lab` e LIVE Oracle invariati, PR #102 DRAFT.

## CHECKPOINT v0.8.34 — DEPLOY GATEWAY COMPLETO TEST OFF VERIFICATO — 13/11/2026, ore 23:00 CET
- [x] L'utente ha autorizzato con `workflow_dispatch` su `main` la prima installazione del **solo** gateway TEST con `INGEST_ENABLED=false`. Esecuzione [#43515467198](https://github.com/mirkoworz/remura/actions/runs/43515467198): `completed/SUCCESS`, job `deploy-gateway-test-off-only` e tutti gli step applicabili **SUCCESS**.
- [x] Test offline, identificazione GET-only di D1 TEST EU e Worker TEST bootstrap vuoto, bundle privato effimero, Wrangler 4.157.0 dry-run, ultimo controllo binding vuoti, deployment e readback postdeploy superati; nessuna credenziale richiesta all'utente oltre ai GitHub Secrets già esistenti.
- [x] Log del deploy: `Uploaded remura-tv-webhook-test`, `Deployed remura-tv-webhook-test triggers`, Cloudflare **Version ID `1d47f428-c176-48d3-8d80-10ed0a94a43e`**. Binding elencati da Wrangler: `TELEMETRY_DB -> remura-tv-lab-test`, `INGEST_RATE_LIMITER=20/60`, `INGEST_ENABLED="false"`; `preview_urls=false` nel manifest. Nessun Secret webhook.
- [x] Verifica LIVE postdeploy delle settings tramite GET autenticati: `REMURA_TEST_ROLLBACK_PREFLIGHT=TEST_GATEWAY_OFF_STRICT_NO_SECRET`, verifica UUID D1 TEST distinto da MAIN e limiter vincolato; non equivale a prova dell'HTTP edge, allocazione traffico o reale ingest. Il bundle temporaneo è stato rimosso; D1 principale e Worker Production `remura-tv-ingest-lab` non modificati.
- [x] Warning **non bloccante** Wrangler `Unexpected fields found in top-level field: "$comment"` su un manifesto temporaneo generato da template: compilazione, deploy e readback riusciti. Eliminare il campo commento soltanto da un futuro bundle temporaneo testato prima della prossima installazione; non rifare per questo il deploy già avvenuto.
- [ ] **Prossima attività OFFLINE**: progettare un Secret TEST completamente separato e custodito esclusivamente in GitHub Secrets/Cloudflare (mai in Pine o JSON), prima del primo POST live; implementare rollback/spegnimento d'emergenza che funzioni **anche dopo** l'aggiunta Secret e con ingest ON (l'attuale workflow rollback v0.8.32 blocca ON/Secret). Verificare costo del rate limiter e sicurezza endpoint prima di ON; deploy ON solo con autorizzazione specifica.
- [ ] Dopo il nuovo gate: configurare l'alert webhook TradingView su `FXCM:EURUSD` M5 con JSON `remura.tv.flow.v1` e 2FA, provare risposta accettata/deduplica/rifiuti, misurare latenza e throughput D1 TEST senza esportazione a produzione. La disponibilità di `/health` edge e la consegna reale TradingView restano **NON VERIFICATE**.
- [x] PR #102 resta DRAFT; nessun merge o release REMURA Oracle, nessun nuovo ordine o notifica, nessuna evidenza di vantaggio scientifico. Main aggiornato soltanto con workflow manuale, monitor budget protetto.

## CHECKPOINT v0.8.33 — WORKFLOW GATEWAY TEST OFF PRONTO, MA NON AVVIATO — 13/11/2026, ore 22:36 CET
- [x] Ripreso il punto v0.8.32 senza ripetere audit D1/Workers/Account, creare token o modificare Oracle. GitHub PR #102 rimane DRAFT/OPEN; `main` non contiene il codice del gateway e l'app LIVE non cambia versione.
- [x] Preparato `gateway-lab/prepare_test_off_bundle_v1.py` su PR #102: usando soltanto **due GET autenticati**, legge inventario D1 UE e settings del Worker **TEST** già esistente; richiede bootstrap con `bindings=[]`; rifiuta configurazioni impreviste, Worker Production, D1 principale, ingest ON e Secrets. Deriva UUID D1 TEST e namespace limiter `20/60` solo nella memoria del runner; il bundle effimero (due file `0600`) non entra nel repository né negli artifact. **Non effettua deploy.**
- [x] Aggiunti **11 test sintetici** `test_prepare_test_off_bundle_v1.py`; una prima CI ha identificato il mock di Account ID con hash fisso e la sola fixture di test è stata corretta, senza allentare la protezione del codice reale. Su commit `004af2df1b54ffcdc8a222ce54cce7cb59fc52f3`: [Telemetry LAB #43511982060](https://github.com/mirkoworz/remura/actions/runs/43511982060) **SUCCESS**, [Wrangler DRY RUN #43511982049](https://github.com/mirkoworz/remura/actions/runs/43511982049) **SUCCESS**. CI offline e compilazione, non deploy.
- [x] Sul solo `main` è disponibile workflow **esclusivamente manuale** [`REMURA TEST Worker GATEWAY OFF`](https://github.com/mirkoworz/remura/actions/workflows/remura-tv-gateway-test-off-manual.yml), commit `39fcce1cbaca2479228c37536eab382975cd203e`, checkout **immutabile** di `004af2df1b54ffcdc8a222ce54cce7cb59fc52f3`. Richiede `github.actor=mirkoworz`, branch `main`, opzione esatta `DEPLOY_GATEWAY_TEST_OFF_ONLY`; concurrency condivisa con bootstrap e rollback manuale; GitHub `contents:read`.
- [x] Flusso futuro: test offline → GET D1 TEST/Worker TEST → manifest temporaneo `INGEST_ENABLED=false`, preview OFF, D1 TEST + limiter `20/60`, nessun Secret → Wrangler `--dry-run` → **ultimo GET** di binding vuoti → deploy **solo su azione manuale esplicita** → lettura settings strict TEST-OFF, altrimenti NO-GO. Il bundle viene eliminato al termine. Il rollback separato v0.8.32 resta pronto per uso manuale, non è stato lanciato.
- [ ] **Azione successiva SOLO con consenso proprietario:** avviare il workflow owner-only su main dopo valutazione quota/costo effettivi del Rate Limiting e protezione del gateway. Per il primo TEST **OFF** non serve creare nuovi token. Se il manifest o i binding reali non coincidono, il workflow deve bloccarsi; un deploy o postdeploy fallito non equivale a successo. Non abilitare `INGEST_ENABLED=true`, non creare Secret TEST, non configurare alert TradingView in questa fase.
- [ ] In seguito, prove separate (prima nuovo consenso): HTTP `/health` affidabile, Secret TEST non nel JSON, prima consegna TradingView in DB TEST, latenza/duplicati/heartbeat, limiti Free e eventuale rollback con ON/Secret (non ancora coperto). Solo poi possibile bridge di ricerca verso Track B/C. Nessun dato di trading prospettico o vantaggio predittivo dimostrato.
- [x] **NESSUN dispatch, deploy o POST** avviato durante v0.8.33; Worker TEST ancora bootstrap inerte all'ultimo audit, Production `remura-tv-ingest-lab` e D1 MAIN invariati. Il deploy rimane un'azione futura distinta; `main` ha aggiunto soltanto il workflow manuale.

## CHECKPOINT v0.8.32 — ROLLBACK MANUALE WORKER TEST PREPARATO, NON ESEGUITO — 13/11/2026, ore 21:08 CET
- [x] Creato `gateway-lab/worker_rollback_preflight_v1.py`: soli **due GET autenticati** (inventario D1 UE e settings del solo Worker TEST), confronto della destinazione D1 TEST e namespace limiter candidato senza stampare identificativi. Consentiti soltanto il bootstrap vuoto o il gateway `INGEST_ENABLED=false` con binding D1 TEST e limiter 20/60; tutti gli stati sconosciuti vengono bloccati.
- [x] Sei nuovi test mock in `test_worker_rollback_preflight_v1.py` verificano target TEST, DB MAIN proibito, assenza credenziali, nessuna SQL e mancata esposizione token. [Actions #43498033946](https://github.com/mirkoworz/remura/actions/runs/43498033946) **SUCCESS**, inclusi i 12 test preesistenti del guard di rollback e quelli del laboratorio.
- [x] Installato su `main`, senza avvio automatico, `.github/workflows/remura-tv-rollback-test-manual.yml` (ultimo commit `347a2a2942faecaa35882da1c7d9b66699464417`): `workflow_dispatch` solo per proprietario su main, scelta obbligatoria `ROLLBACK_TEST_TO_BOOTSTRAP_OFF`, permessi `contents:read`, checkout sorgente pinned `ac68fabf95a26ec9c62f4e2cd270661c32622578`. Prima dei comandi mutativi esegue test e preflight autenticato; se autorizzato in futuro potrà distribuire solo bootstrap inerte sul Worker TEST con `preview_urls:false`, poi verificare binding vuoti. Concurrency condivisa con precedente workflow di bootstrap: no due modifiche TEST simultanee. **Workflow NON eseguito, NESSUN deploy né rollback live eseguito.**
- [ ] **Limite del rollback attuale:** gestisce solo bootstrap o gateway già OFF **senza Secret**. Prima della prima ingestione ON e dell'aggiunta di un Secret TEST, occorrerà estenderlo affinché una condizione d'emergenza ON possa davvero tornare a OFF; NON dichiararlo pronto per il trading live.
- [ ] Prossimo percorso: completare workflow separato e manuale di **deploy del gateway TEST OFF** con D1 TEST/limiter e doppio preflight, avvio solo dopo nuova autorizzazione; dopo, una fase distinta per Secret TEST e primo webhook TradingView. Non effettuare ora deploy.
- [x] Worker TEST bootstrap live ancora immutato, nessuna nuova scrittura D1, nessun webhook, Worker Production `remura-tv-ingest-lab` invariato, PR #102 DRAFT e budget `main` intatto.

## CHECKPOINT v0.8.31 — POSTDEPLOY LIVE VERIFIED E GATEWAY TEST OFFLINE FAIL-CLOSED — 13/11/2026, ore 21:00 CET
- [x] Ripresa da v0.8.30 e PR #102 OPEN/DRAFT, senza rifare verifiche D1 TEST già concluse o sonda GitHub GET 403 identica. Worker Production `remura-tv-ingest-lab` NON modificato; attuale Worker TEST mantiene il bootstrap inerte realmente deployato 13/11 ore 20:45 CET.
- [x] Nuovo audit **LIVE soltanto control-plane Cloudflare, GET autenticati** `bootstrap_postdeploy_audit_v1.py`: verifica risorsa Version ID `f5a43b49-f07f-404b-a9dd-4606a22afa3c` esistente e senza binding, e impostazioni correnti Worker TEST senza binding. **[GitHub run #43496120098](https://github.com/mirkoworz/remura/actions/runs/43496120098) SUCCESS**, 8 test sintetici PASS; `EXPECTED_TEST_VERSION_CONFIRMED`, `CURRENT_SETTINGS=NO_BINDINGS`. Questo conferma versione e metadati, **NON** 100% traffic allocation, GET /health pubblico o TradingView in ingresso; quei due aspetti restano UNKNOWN. Il controllo WEB `/health` da navigatore di ricerca non è accessibile: esito INCONCLUSIVO, non è stato interpretato come errore Worker.
- [x] Documentazione Cloudflare più recente verificata: `preview_urls:false` disabilita esplicitamente i Version URLs pubblici anche con `workers_dev:true`. Aggiornato il **solo esempio NON DEPLOYABILE** `wrangler.webhook-test.EXAMPLE.json` a v0.8.31; esteso `predeploy_test_manifest_guard_v1.py` per BLOCCARE preview `true`, omissione o tipo errato. Vedi https://developers.cloudflare.com/workers/versions-and-deployments/version-urls/ . Il bootstrap **LIVE** resta con precedente configurazione preview di default, NON modificata in questo checkpoint.
- [x] `test_manifest_guard_v1.py` e `test_build_test_worker_dryrun_v1.py` proteggono il flag OFF, destinazione D1 TEST, Preview URLs OFF e nessuna custom route. [Wrangler CI #43496797754](https://github.com/mirkoworz/remura/actions/runs/43496797754) **SUCCESS**: compilazione con UUID e limiter sintetici, `deploy --dry-run` senza Cloudflare API/deploy. Gli eventuali job cancellati per `concurrency` mentre arrivavano nuovi commit NON sono errori live; la verifica finale è verde.
- [x] Nuovo `gateway_off_candidate_v1.py` **in sola lettura**: controlla tramite GET D1 reale sia `remura-tv-lab` sia `remura-tv-lab-test`, UUID distinti/UE, crea **esclusivamente in memoria** candidato gateway sul Worker `remura-tv-webhook-test`, `INGEST_ENABLED=false`, D1 TEST, limiter `20/60`, preview disattivata, SENZA Secret nuovo. UUID e namespace non vengono persistiti né riportati nei log; 10 mock test `test_gateway_off_candidate_v1.py` superati. **[Run #43496787646](https://github.com/mirkoworz/remura/actions/runs/43496787646) SUCCESS**: `VERIFIED_IN_MEMORY_ONLY` e `D1_MAIN=NOT_TARGETED`; NON è un deploy, e il namespace candidato ha collisioni con altri namespace **non verificabili** da questa prova.
- [x] Nuovo controllo offline di **rollback sicuro** `off_gateway_rollback_guard_v1.py` con `test_off_gateway_rollback_guard_v1.py`: permette solo bootstrap senza binding o set preciso `TELEMETRY_DB` → DB TEST verificato, `INGEST_RATE_LIMITER` 20/60 e `INGEST_ENABLED=false`; rifiuta DB principale, ingest ON, Secret imprevisto, namespace diverso o binding sconosciuti. [CI #43497283571](https://github.com/mirkoworz/remura/actions/runs/43497283571) **SUCCESS**, 12 test rollback offline; integrazione Python+Node esistente verde. **Guard testato offline, NON è ancora un workflow rollback reale né un deploy di rollback.**
- [x] Permesso Cloudflare Individual Worker Editor TEST già funzionante dal run v0.8.30; piano Workers Free $0 confermato in UI. Quote pubblicate 100k request/giorno/account, 10 ms CPU/invocazione. Rate limiting Cloudflare `namespace_id` stringa intero, enforcement approssimativo per location, NON quota assoluta; disponibilità effettiva su questo account Free e budget CPU ancora **non dimostrati**. Fonti https://developers.cloudflare.com/workers/platform/limits/ , https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/ .
- [ ] Prossima fase **senza deploy automatico**: predisporre workflow di rollback manuale reale con source bootstrap pinned, preflight test gateway OFF e metadata binding; SOLO POI proporre workflow manuale di prima distribuzione gateway completo **INGEST_ENABLED=false**, D1 TEST, limiter verificato e preview OFF. Prima di questo deploy richiedere autorizzazione distinta; qualsiasi primo webhook TradingView richiederà ulteriore consenso e Secret TEST separato. Nessun token da incollare in chat.
- [x] Nessuna nuova scrittura D1, nessun POST webhook, alert TradingView OFF, nessun trade, nessun nuovo servizio a pagamento, filoni A/B/C e monitor giornaliero su `main` invariati; PR #102 continua DRAFT. Versione Worker Production non toccata; non affermare live ingest verificato OFF oltre al codice bootstrap e ai metadata.

## CHECKPOINT v0.8.30 — PRIMO DEPLOY LIVE SOLO BOOTSTRAP INERTE DEL WORKER TEST — 13/11/2026 ore 20:45 CET
- [x] L'utente ha effettuato un **nuovo** `workflow_dispatch` esplicito dal modulo `main`, dopo modifica `confirmation` in `type:choice`. [GitHub Actions #43495068875](https://github.com/mirkoworz/remura/actions/runs/43495068875) **completed/SUCCESS**, head `1892085aaab994bf27fcc77593f64c03580daabc`; job `bootstrap-existing-test-only` e tutte le 8 fasi principali **SUCCESS**. Il primo run #43494222257 rimane **SKIPPED** e non va ritentato.
- [x] Test offline Node+9 regression Python del guard PASS; `GET` API Cloudflare autenticata pre-deploy ha dato `REMURA_BOOTSTRAP_PREFLIGHT=EXISTING_TEST_ONLY_NO_BINDINGS`. Confermati Worker **esistente e senza binding prima del deploy**; nessun secret/token in log.
- [x] Wrangler `4.157.0 deploy --dry-run` superato, poi **deploy reale del SOLO `bootstrap_test_worker.mjs` inerte**, con codice immutabile checkout `6f7ae923261ca1bc0d1099188b1edfbe5c333d4a`, nome `remura-tv-webhook-test`, config senza D1/Secrets/limiter, `workers_dev:true`. Log: `Uploaded remura-tv-webhook-test`, `Deployed remura-tv-webhook-test triggers`, versione Cloudflare `f5a43b49-f07f-404b-a9dd-4606a22afa3c`. Indirizzo `https://remura-tv-webhook-test.mirkoworz.workers.dev`. **Il log è evidenza LIVE di deployment**, non ancora prova HTTP end-to-end TradingView.
- [x] Codice distribuito restituisce `GET /health` con `status:bootstrap_only,accepting:false`; ogni altro metodo/path, incluso webhook POST, restituisce `503 disabled`. Queste garanzie derivano da codice pinned e test offline; **la risposta reale HTTP /health non è stata verificata separatamente**. Non chiamare servizio con vecchia sonda GET runner che già diede 403 inconcludente, preferire futuro canale di verifica affidabile.
- [x] Wrangler ha emesso **WARNING Preview URLs ON di default** in quanto `preview_urls` non era impostato e `workers_dev` è abilitato. Nessun webhook è attivo nel bootstrap, ma pianificare una **revisione sicura di preview_urls/workers.dev** prima della fase gateway completo; non cambiare impostazioni senza consenso appropriato. Il rate limiter e i Secrets TEST non sono presenti, come previsto per il solo bootstrap.
- [ ] Prossimo intervento: verificare metadata del deploy e/o risposta /health con metodo non equivalente alla sonda GitHub 403 già inconcludente; definire policy preview, quindi preparare SOLO OFFLINE gateway completo TEST con D1 TEST (mai principale), limiter e Secret TEST distinto. Deploy successivo e ingest ON richiedono autorizzazioni separate. Monitorare Free Workers, CPU, D1 e risultati, senza promettere profitto.
- [x] **Nessun dato D1 scritto né letto nel deploy**, nessun webhook TradingView, nessun ordine, nessun deploy Production; `remura-tv-ingest-lab` invariato, PR #102 OPEN/DRAFT, budget daily `main` v0.8.14 invariato, filoni A/B/C non toccati.

## CHECKPOINT v0.8.29 — PRIMO BOOTSTRAP DISPATCH SKIPPED, NESSUN DEPLOY — 13/11/2026, ore 20:43 CET
- [x] L'utente ha avviato manualmente il workflow `REMURA TEST Worker BOOTSTRAP (manual only)` su `main`; screenshot mobile scattato mentre risultava `Queued`. La verifica GitHub successiva [run #43494222257](https://github.com/mirkoworz/remura/actions/runs/43494222257) indica **`completed/skipped`** con job `bootstrap-existing-test-only` **SKIPPED** e **nessuno step eseguito**. Nessun deploy, nessun POST, nessun cambiamento Worker o database.
- [x] Il job ha una condizione preventiva con repository, ref main, actor `mirkoworz` e stringa esatta input `DEPLOY_BOOTSTRAP_TEST_OFF_ONLY`. Repository/actor/branch risultano coerenti nell'esecuzione; il contenuto dell'input non è disponibile nel run e **la causa esatta non è dimostrata**. Il campo compilato a mano potrebbe non aver superato il confronto; classificazione `INPUT_SUSPECTED_NOT_PROVEN`, non errore di Cloudflare né del token.
- [x] Corretto **solo il workflow su `main`** `.github/workflows/remura-tv-bootstrap-test-only-manual.yml` (commit `1892085aaab994bf27fcc77593f64c03580daabc`): input `confirmation` è ora `type: choice` con una sola opzione precompilata `DEPLOY_BOOTSTRAP_TEST_OFF_ONLY`. Rimangono invariati controllo manuale owner, `contents:read`, fonte pinned SHA `6f7ae923261ca1bc0d1099188b1edfbe5c333d4a`, test offline, GET-only preflight e **solo bootstrap inerte** del Worker TEST. Nessun altro job di rilascio è stato avviato.
- [ ] Occorre **un nuovo dispatch esplicito dell'utente** dalla pagina GitHub Actions selezionando `main` e l'unica opzione; non tentare di rilanciare il job skipped senza nuovo input. Dopo il run verificare sia i test sia il vero deploy e stato remoto `/health`, evitando la vecchia sonda GitHub 403 identica. **Non è stato autorizzato gateway completo, webhook, ingest ON né utilizzo D1**.
- [x] Secret GitHub `REMURA_CF_TEST_WORKER_EDITOR_TOKEN` già verificato tramite run GET-only #43493628453; non ricrearlo, non richiedere screenshot/token. PR #102 resta OPEN/DRAFT, main monitor budget invariato e Worker Production `remura-tv-ingest-lab` non toccato.

## CHECKPOINT v0.8.28 — TOKEN EDITOR WORKER TEST E METADATA LIVE CONFERMATI — 13/11/2026, ore 20:36 CET
- [x] L'utente ha configurato **Account API Token** `REMURA-TV-TEST-EDITOR`, scope `Specified Workers` → **esclusivamente `remura-tv-webhook-test`**, ruolo `Individual Workers → Editor`, `Admin` disattivato, come screenshot già verificati. Token registrato dall'utente in **GitHub Actions Secret `REMURA_CF_TEST_WORKER_EDITOR_TOKEN`**; nessun valore in chat, documenti o log. Non serve crearne altri né ripetere screenshot.
- [x] Per accertare il funzionamento senza concedere nuova autorità, creato il solo workflow read-only `.github/workflows/remura-tv-test-worker-editor-readonly.yml` su `main`, commit `87f496a4f3e729d96c89f43d5c4198bda1100b1f`: trigger automatico esclusivamente alla **creazione/modifica di questo stesso file** più `workflow_dispatch`, `contents:read`, checkout del **pin `6f7ae923261ca1bc0d1099188b1edfbe5c333d4a`**, test offline del guard, poi **un GET autenticato** `/accounts/{id}/workers/scripts/remura-tv-webhook-test/settings`. Nessun deploy, nessun POST, nessuna query D1, nessuna interazione con Production.
- [x] [GitHub run #43493628453](https://github.com/mirkoworz/remura/actions/runs/43493628453) **SUCCESS**: 9 test di sicurezza offline superati; `REMURA_TEST_TOKEN=SECRET_PRESENT_NOT_DISCLOSED`; risposta API sanitizzata `REMURA_BOOTSTRAP_PREFLIGHT=EXISTING_TEST_ONLY_NO_BINDINGS` e `WORKER=remura-tv-webhook-test; BINDINGS=NONE; DEPLOY=NOT_YET`. **LIVE metadata verificati**: Worker TEST esiste ed è privo di binding al momento della GET. Non equivale a prova del codice deployato (Hello World resta ultimo codice dichiarato dall'utente), del routing workers.dev, né a verifica che il token possa scrivere altri Worker; quest'ultima limitazione deriva dalla policy UI visibile.
- [x] Il workflow già preparato `.github/workflows/remura-tv-bootstrap-test-only-manual.yml` resta **non eseguito** e utilizzabile soltanto tramite `workflow_dispatch` su main con stringa esatta `DEPLOY_BOOTSTRAP_TEST_OFF_ONLY` e controllo owner. Conterrà un deploy del SOLO codice `bootstrap_test_worker.mjs` inerte, senza DB/secrets e con `GET /health.accepting=false`, ma richiede **ulteriore conferma esplicita dell'utente prima dell'esecuzione**. Nessun webhook TradingView ancora autorizzato.
- [ ] **Prossimo passo**: consenso distinta sostituzione Hello World con bootstrap inerte via workflow manuale owner-only, poi verificare codice effettivo e `/health` con canale affidabile (precedente sonda pubblica GitHub 403 inconcludente da non ripetere tale e quale). Nessuna attivazione ingest né collegamento al DB principale.
- [x] `main` monitor budget v0.8.14 non modificato, filoni A/B/C intatti, PR #102 DRAFT/OPEN senza merge, Worker Production `remura-tv-ingest-lab` non toccato, Free Workers $0 e D1 EU checkpoint acquisiti.

## CHECKPOINT v0.8.27 — CREAZIONE TEST OWNER E PREPARAZIONE GITHUB EDITOR SCOPED — 13/11/2026, ore 18:35 CET
- [x] L'utente ha confermato **«creato»** dopo la procedura `Start with Hello World → Deploy` per `remura-tv-webhook-test`. È una **dichiarazione del proprietario**; codice effettivamente deployato, nome finale, binding e Access **non ancora letti da API autorizzata**. Si presume solo Hello World innocuo, **non** il bootstrap sicuro già verificato in offline. Non richiedere di creare il Worker nuovamente.
- [x] Su documentazione Cloudflare del 13/11/2026 (ruoli aggiornati 15/09/2026), la policy API `Workers: Editor` limitata a **Specified Workers/Individual Workers → solo `remura-tv-webhook-test`** può aggiornare Worker esistente, ma non crearne/eliminarne altri. Percorso: **Manage Account → Account API Tokens → Create**. Fonte https://developers.cloudflare.com/workers/authorization/workers/ e https://developers.cloudflare.com/changelog/post/2026-09-15-granular-worker-permissions/ . Il token deve essere **account-owned** e non riutilizzare quelli D1/Analytics.
- [x] Nuovi `gateway-lab/bootstrap_settings_guard_v1.py` e 9 test `test_bootstrap_settings_guard_v1.py`: preflight esclusivamente `GET` API settings sul solo Worker TEST con nome fissato, richiede `bindings=[]`, errore fail-closed se sconosciuti/assenti, nessun valore o API response nei log. [CI #43473684646](https://github.com/mirkoworz/remura/actions/runs/43473684646) **SUCCESS** offline. Il preflight LIVE non è stato eseguito: **non esiste ancora il nuovo token in GitHub**.
- [x] Creato SU `main`, isolato dagli altri filoni, il workflow `.github/workflows/remura-tv-bootstrap-test-only-manual.yml`, commit `f89ce27`, **solo `workflow_dispatch` (NO cron, push o PR)**, permessi GitHub `contents:read`, consentito solo a owner `mirkoworz`, input esatto `DEPLOY_BOOTSTRAP_TEST_OFF_ONLY`. Checkout codice **PINNED SHA `6f7ae923261ca1bc0d1099188b1edfbe5c333d4a`**; prima esegue test Node e Python; poi GET-only metadata guard; compila il bootstrap inerte senza D1, Secrets o limiter ed esegue deploy soltanto dopo azione manuale owner. Nessun deploy avviato.
- [ ] **Unico setup manuale necessario prima della successiva esecuzione:** creare account-owned Cloudflare API Token `Workers: Editor` scope **Specified Workers/Individual Worker** con l'unico Worker `remura-tv-webhook-test`; nessun permission aggiuntivo product-wide o D1 Write, no Global API Key. Conservare token **esclusivamente** in GitHub Actions secret `REMURA_CF_TEST_WORKER_EDITOR_TOKEN`, mai in chat/screenshot; GitHub `REMURA_CF_ACCOUNT_ID` già presente e NON va rifatto. Se UI mostra solo **All Workers** o concede Admin → STOP, chiedere istruzioni senza scegliere scope eccessivi.
- [ ] Dopo token GitHub creato, verificare scope e invocare manualmente (su `main`) solo workflow bootstrap, con conferma esplicita del proprietario: prima `GET settings` e rifiuto dei binding inattesi, poi deploy codice inerte. Non autorizzare ancora gateway completo, ingest, webhook o SQL D1.
- [x] `main` daily budget v0.8.14 immutato, PR #102 OPEN/DRAFT senza merge, Worker Production `remura-tv-ingest-lab` con D1 principale non modificato, non introdotti costi Paid o ordini. Non dichiarare che il Worker TEST sia già isolato in runtime finché non arriva il preflight LIVE.

## CHECKPOINT v0.8.26 — AUTORIZZAZIONE CREAZIONE TEST, IN ATTESA DELLA UI OWNER — 13/11/2026, ore 17:27 CET
- [x] L'utente ha risposto **«Sì»** alla domanda esplicita di autorizzazione della **sola creazione iniziale** del Worker `remura-tv-webhook-test` con bootstrap inerte, senza D1/Secrets/limiter e senza webhook. Consenso limitato esattamente a questa fase, non al deploy del gateway completo, ingest ON, modifica di `remura-tv-ingest-lab`, trasferimento dati né creazione di token.
- [x] Ricontrollato stato PR #102 OPEN/DRAFT e codice bootstrap `gateway-lab/bootstrap_test_worker.mjs` già validato in precedenza. Documentazione Cloudflare dashboard conferma il percorso Workers & Pages → Create application → Create Worker: https://developers.cloudflare.com/learning-paths/workers/get-started/first-worker/ . L'interfaccia può creare prima un template di esempio; NON dichiarare che l'esempio iniziale sia il bootstrap approvato. Se non è possibile cambiare il codice prima del deploy, guidare l'owner a sostituirlo immediatamente e verificare che nessun POST sia accettato.
- [ ] **Azione proprietario da confermare**: creare solo `remura-tv-webhook-test` nella Dashboard Cloudflare, senza collegare GitHub, D1, Secrets, custom routes, ingest o altri servizi. Preferire il codice inerte al primo deploy se l'interfaccia lo consente; registrare screenshot dopo il salvataggio, senza credenziali. La creazione non è stata eseguita da questa sessione, che dispone di accesso GitHub ma non di scrittura Cloudflare.
- [ ] Solo dopo verifica dell'identità del nuovo Worker esistente: considerare token per-Worker Editor e rate limiter TEST con nuova autorizzazione specifica. **Non confondere il consenso di creazione col permesso di attivare webhook o dati live**.
- [x] Piano Workers Free e D1 distinti acquisiti, il monitor `main` v0.8.14 non modificato, PR #102 sempre DRAFT, nessun deploy/merge effettuato in questo aggiornamento.

## CHECKPOINT v0.8.25 — WORKER BOOTSTRAP INERTE E RUOLI GRANULARI — 13/11/2026, ore 16:34 CET
- [x] Partito solo dal checkpoint v0.8.24 già verificato e PR #102 **OPEN/DRAFT**; nessun vecchio audit o 403 ripetuto; `main` monitor giornaliero v0.8.14, Workers Free $0 e due D1 UE restano checkpoint acquisiti.
- [x] Verificata documentazione Cloudflare aggiornata 13/11/2026: il modello 2026 `Workers: Editor` consente deploy **solo Worker già esistente**; `Workers: Admin` a livello prodotto è necessario per **creare** un Worker via API/Wrangler e non può essere vincolato a un Worker inesistente. Ruoli per-Worker disponibili e applicabili a token/membri. **Cambiata la strategia**: preferire un bootstrap iniziale dell'unico Worker TEST tramite il proprietario in dashboard, dopo autorizzazione, evitando token product-wide Admin nella CI. Fonte https://developers.cloudflare.com/workers/authorization/workers/.
- [x] Creato `gateway-lab/bootstrap_test_worker.mjs` v0.8.25: codice ESM indipendente, **nessun binding D1, Secret, limiter, fetch esterno o log**, GET `/health` → `bootstrap_only/accepting:false`, tutti gli altri metodi/route → `503 disabled`. Anche se l'ambiente avesse flag ON o Secrets errati, non legge env né può ingestire. Il Worker non è stato creato su Cloudflare.
- [x] `gateway-lab/bootstrap_test_worker.test.mjs`: **6 test Node offline** verificano anti-ingest, no letture env/D1, no eco di credenziali, no-store e HTTP 503. Inseriti nel workflow esistente `.github/workflows/remura-tv-telemetry-lab.yml`; [Actions #43452920303](https://github.com/mirkoworz/remura/actions/runs/43452920303) **SUCCESS** e controlli sintattici verdi.
- [x] Esteso `.github/workflows/remura-tv-wrangler-dryrun.yml`: compila con **Wrangler 4.157 `deploy --dry-run`** anche il bootstrap con configurazione temporanea `workers_dev:false`, senza D1/Secrets/limiter né credenziali Cloudflare, oltre al già validato gateway di test sintetico; [Actions #43453466241](https://github.com/mirkoworz/remura/actions/runs/43453466241) **SUCCESS**. È una prova di packaging locale, NON un deploy e non dice nulla sul runtime, routing o billing reale.
- [x] Documenti `gateway-lab/BOOTSTRAP-TEST-WORKER-v0.8.25.md` e `gateway-lab/TEST-WEBHOOK-RELEASE-GATE-v0.8.22.md` (contenuto v0.8.25) spiegano creazione owner-only, eventuale **token Editor limitato al Worker TEST esistente**, gate successivi del gateway completo OFF e webhook reale, rollback e no-cost. Nessun nuovo token creato, nessun permesso aggiunto.
- [ ] Prossimo intervento **manuale e autorizzato**: **solo** creare Worker `remura-tv-webhook-test` con bootstrap inerte e senza D1/Secrets/route, dal dashboard del proprietario. Confermare solo identità e flag spento; **non** associare `remura-tv-lab`. Dopo creazione, preparare un token `Editor` limitato a questo singolo Worker, senza condividere valore in chat; prima chiarire se la UI supporta workers.dev disattivato e limitare il traffico di prova. **Non affermare che il Worker esista già**.
- [ ] Restano da verificare in modo reale: quota rate limiter nella specifica configurazione Free, CPU e fatturazione aggregata, secret dedicato, D1 TEST binding al gateway, endpoint workers.dev (precedente 403 inconcludente), primo POST veramente TradingView e qualità dati; successivi deploy/ingest richiedono consensi distinti, niente ordini.
- [x] Production `remura-tv-ingest-lab` v0.8.5 ancora invariato (binding `TELEMETRY_DB → remura-tv-lab` da screenshot utente); D1 MAIN e record sintetico TEST non modificati; PR #102 DRAFT, nessun merge, nessuna spesa/piano Paid, nessun webhook, filoni A/B/C intatti.

## CHECKPOINT v0.8.24 — PIANO WORKERS FREE REALE VERIFICATO — 13/11/2026, ore 15:54 CET
- [x] Acquisito screenshot utente Cloudflare → Compute → **Workers plans**: piano **Free $0**, pulsante **Current plan** disattivato sulla scheda Free, piano Paid **$5/month + usage** con opzione di upgrade; **Workers Free è il piano attuale dell'account alla data dello screenshot**, non una semplice pagina prezzi generica. Nessun clic su Upgrade o Change.
- [x] **Risolto blocco precedente "piano effettivo sconosciuto"** per Workers. Rimangono non accertati eventuali altri servizi/prodotti a pagamento, situazione delle fatture, disponibilità del Rate Limiting binding nell'account, contatori CPU reali per POST, numero di Worker e consumi condivisi. NON affermare "tutti i servizi Cloudflare sono gratis" né "fattura zero" sulla base della sola schermata Workers.
- [x] Limiti da documentazione ufficiale Cloudflare Workers Free verificata al 13/11/2026: **100.000 request/giorno/account**, **10 ms CPU/invocazione**, **100 Worker/account**; condizioni diverse per risorse esterne. Sforare quote Free può produrre errori/interruzioni e non deve essere presentato come capacità illimitata. Fonte: https://developers.cloudflare.com/workers/platform/limits/ e https://developers.cloudflare.com/workers/platform/pricing/
- [x] Rate Limiting API Cloudflare documentata con `namespace_id` univoco, `simple.limit` e `simple.period`, conteggi approssimativi per località e soggetti a overshoot; la documentazione non costituisce conferma di **binding attivo/reale sul Worker TEST**. https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/
- [x] Monitor GitHub `main` v0.8.14 con avvisi Free già attivo e verificato al checkpoint precedente; **nessuna modifica a main**, nessuna duplicazione dei monitor; la prossima esecuzione cron effettiva va verificata dopo 14/11 ore 08:37 CET.
- [ ] Prossimo gate: autorizzazione separata del primo **solo deploy TEST con ingest OFF**; prima preparare permesso Cloudflare minimo per **nuovo Worker TEST**, vero binding `TELEMETRY_DB → remura-tv-lab-test`, Rate Limiting e Secret TEST distinto, confermandoli senza usare l'URL Worker Production. Non eseguire deploy, POST reali o accendere TradingView da questa chat senza consenso separato. La compilazione `--dry-run` v0.8.23 era sintetica, non prova dei binding live.
- [x] D1 principale e record sintetico TEST immutati, Worker Production invariato, PR #102 DRAFT/OPEN, nessun segreto condiviso, nessun upgrade/servizio a pagamento, nessun trade, filoni A/B/C non toccati.

## CHECKPOINT v0.8.23 — REAL WRANGLER DRY-RUN, ZERO DEPLOY — 13/11/2026, ore 15:34 CET
- [x] Ripresa dal checkpoint v0.8.22 PR #102 DRAFT/OPEN; nessuna sonda pubblica 403 ripetuta, nessun altro test di lettura D1 reale eseguito (identità D1 TEST già verificata).
- [x] Riviste le fonti ufficiali Cloudflare aggiornate al 13/11/2026: Wrangler `deploy --dry-run` compila senza upload; Free Workers 100.000 richieste giornaliere su account e 10 ms CPU/invocazione, max 100 Workers; Rate Limiting binding `namespace_id` stringa intero univoco e `simple.period` solo 10/60, contatori approssimativi per località. **Documentazione dei limiti NON prova piano reale o costi account**. Fonti: https://developers.cloudflare.com/workers/wrangler/commands/workers/ ; https://developers.cloudflare.com/workers/platform/limits/ ; https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/
- [x] Creato `gateway-lab/build_test_worker_dryrun_v1.py`: legge esclusivamente il manifest di esempio con ingest OFF e placeholder, ne materializza in directory temporanea una copia con UUID D1 **fittizio** `00000000-0000-4000-8000-000000000002` e limiter namespace **fittizio** `987654321`; copia sorgente Worker senza credenziali e conferma nome Worker TEST e target `remura-tv-lab-test`. **Non usare mai il bundle temporaneo per un deploy reale**. No real database UUID, no token Cloudflare, no modifiche remote. Aggiunti 5 test sintetici `test_build_test_worker_dryrun_v1.py` (blocchi Production, flag ON, secrets inline, routes, placeholders risolti parzialmente).
- [x] Workflow dedicato `.github/workflows/remura-tv-wrangler-dryrun.yml`, solo PR #102 o push branch LAB e `contents:read`, senza secrets o deploy permissions. Esegue `npx wrangler@4.157.0 deploy --dry-run --config <temporanea> --outdir <temporanea>`, compilazione reale Wrangler con `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_API_KEY`, `CLOUDFLARE_ACCOUNT_ID` vuoti. Installazione via npm in runner GitHub, **non è una chiamata all'account Cloudflare**.
- [x] Un primo job dry-run [#43443229228](https://github.com/mirkoworz/remura/actions/runs/43443229228) è fallito per classe d'eccezione inattesa nel test sintetico dei placeholder; normalizzato in fail-closed con commit `1c6a783f`, senza intervento sull'ambiente remoto. **Esecuzione successiva [#43443677850](https://github.com/mirkoworz/remura/actions/runs/43443677850) SUCCESS**, 5 test nuovi PASS, manifest bloccato come esempio, Wrangler effettivamente compilato, dimensione package **11.76 KiB** (gzip **4.06 KiB**), `REMURA_WRANGLER_DRYRUN=COMPILED_SYNTHETIC_ONLY`. Il risultato è packaging locale, NON prova di runtime CPU o connettività webhook.
- [x] Stima volumetrica per **un solo pair M5**: 288 chiusure candela/24 h con heartbeat, 0,288% del limite teorico giornaliero 100k Workers Free, **esclusi** eventi aggiuntivi, ritrasmissioni, richieste anonime e altro consumo account. La richiesta regolare è sostenibile sul piano dei conteggi, ma non sono verificati CPU live, piano reale, rischi abuse e billing.
- [ ] Rimangono blocchi per il prossimo deploy: **approvazione esplicita distinta**, permesso Workers Write minimo limitato a `remura-tv-webhook-test`, namespace Rate Limiting reale, Secret separato, UUID DB TEST verificato in fase deploy, controllo dell'effettivo piano Cloudflare, rollback live non ancora eseguito. Il file `wrangler.webhook-test.EXAMPLE.json` **resta non distribuibile**, e nessuna configurazione Workers reale è stata letta/cambiata.
- [x] Worker Production `remura-tv-ingest-lab` e D1 principale non toccati, record sintetico D1 TEST preservato, main con budget v0.8.14, nessun ordine, nessun webhook reale né merge della PR #102; filoni A/B/C intatti.

## CHECKPOINT v0.8.22 — TARGET D1 TEST VERIFICATO E ROLLBACK DI LAB — 13/11/2026 ore 15:21 CET
- [x] Partito da `v0.8.21`, screenshot Worker Production già verificato `TELEMETRY_DB → remura-tv-lab`; NON ripetuti screenshot, vecchia sonda pubblica 403 o audit identici. PR #102 prima di operare DRAFT/OPEN e `main` monitor quotidiano v0.8.14 preservato.
- [x] Creato `gateway-lab/d1_test_target_preflight_v1.py`: preflight una tantum con token D1 READ e **soli 2 GET** (verify + inventario completo D1), controllo nomi, UUID distinti, giurisdizione UE e coerenza con il manifest TEST; **UUID mai scritti sul disco, nei file GitHub o nei log**. Nessuna SQL, nessuna modifica D1 o Worker, nessuna API Workers Settings ri-tentata con token D1 che aveva dato 403. Scopo nuovo: identificazione sicura del TARGET per il futuro Worker TEST, non ripetizione del budget.
- [x] `test_d1_test_target_preflight_v1.py` aggiunti **12 test sintetici** contro alias di UUID, filtro parziale/paginazione, giurisdizione errata, destinazione Production, token mancante, POST e log di dati sensibili. Workflow isolato `.github/workflows/remura-tv-test-target-preflight-readonly.yml`, con permessi `contents:read`, nessuno schedule/deploy. **Esecuzione LIVE [#43441281362](https://github.com/mirkoworz/remura/actions/runs/43441281362) SUCCESS**: `VERIFIED_TEST_DB_IDENTITY_ONLY`, `D1_MAIN_IDENTITY=VERIFIED_EU`, `D1_TEST_IDENTITY=VERIFIED_EU_DIFFERENT_FROM_MAIN`; `TEST_WORKER_MANIFEST=BLOCKED_UNRESOLVED_IDS`, `LIMITER_NAMESPACE=UNASSIGNED`, `WORKER_DEPLOY=NOT_AUTHORIZED`. Test 12/12.
- [x] Aggiunti 2 test Node a `gateway-lab/worker.test.mjs` per **simulare kill-switch**: stato ON memorizza evento **sintetico** in FakeD1, flag OFF produce `/health.accepting=false` e HTTP 503 senza altre scritture o cancellazioni; anche riattivazione flag senza limiter rimane fail-closed. **GitHub [#43441553706](https://github.com/mirkoworz/remura/actions/runs/43441553706) SUCCESS**: CI Python root 69, mock D1 11, test manifest 12 e gateway Node superati. Questa è **simulazione offline**, non rollback reale Cloudflare.
- [x] Nuovo documento `gateway-lab/TEST-WEBHOOK-RELEASE-GATE-v0.8.22.md`: separa due consensi espliciti (deploy nuovo Worker TEST inizialmente OFF, poi eventuale ON/test webhook TradingView), criteri di GO/NO-GO, monitor Free, procedure di emergenza e preservazione database TEST. **Nessun nuovo Worker è stato creato**, nessuna chiave/secret nuova, nessuna spesa e nessun ordine attivati.
- [x] Limiti ufficiali Workers Free 100.000 richieste/giorno/account e 10 ms CPU/invocazione; D1 Free 10 DB, 500 MB/DB, 5 GB/account. Disponibilità reale / stato fatturazione account **ancora non verificati**. Rate Limiting binding è **approssimativo per località**, non un tetto globale, e controlla gli eventi solo dopo l'invocazione Worker; namespace univoco e disponibilità effettiva **da verificare**. Fonti: https://developers.cloudflare.com/workers/platform/limits/ , https://developers.cloudflare.com/d1/platform/limits/ , https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/
- [ ] Prossimo intervento: confermare disponibilità reale del rate limiting/costo e permesso minimo Workers per il SOLO nuovo Worker TEST; poi sottoporre per autorizzazione la distribuzione `INGEST_ENABLED=false`. Il manifest in GitHub è SOLO esempio con placeholder, non pronto per il deploy. **NON distribuire o inviare webhook senza consenso distinto**.
- [x] Filoni A/B/C e monitor `main` intatti, PR #102 DRAFT, Worker Production vecchio v0.8.5 invariato, record sintetico D1 TEST conservato; nessun risultato di mercato reale o capacità predittiva dimostrata.

## CHECKPOINT v0.8.21 — TARGET D1 DEL WORKER PRODUCTION CERTIFICATO DA SCHERMATA — 13/11/2026 ore 15:11 CET
- [x] Screenshot utente iPhone ruotato in orizzontale: Worker `remura-tv-ingest-lab`, ambiente **Production**, sezione Settings → **Bindings**: riga completa **Type `D1 database` | Name `TELEMETRY_DB` | Value `remura-tv-lab`**. Confermata destinazione del binding sul **DB PRINCIPALE**, non quello TEST. Questo è un dato della **configurazione UI**, non un test del percorso webhook o della ricezione effettiva.
- [x] Chiuso il requisito manuale precedente sui nomi binding senza richiedere altri screenshot. Secret Production visto in precedente immagine come nome parziale `WEBHOOK_TOKE...`, valore encrypted; NON riesaminare/ricreare il secret, né affermare nome completo verificato da screenshot.
- [x] Il Worker Production NON va riutilizzato per il primo webhook di prova: mantenere separato un eventuale `remura-tv-webhook-test` legato **solo** al `remura-tv-lab-test`, con `INGEST_ENABLED=false` prima dell'autorizzazione. Manifest template e guard di v0.8.18 ancora non distribuibili, nessun UUID o token inserito.
- [x] Nella porzione di tabella Production è mostrato **un D1 binding** e **nessun Rate Limiting binding visibile**. Non affermare che rate limiter sia configurato né che la sua mancanza sia prova dell'intero runtime. Sorgente gateway GitHub v0.8.6 richiede `INGEST_RATE_LIMITER` in modalità ingest ON, altrimenti rimane fail-closed: non consentire tentativi senza verifica effettiva. La documentazione Cloudflare consente configurazione `ratelimits` con namespace_id stringa positiva, `simple.limit`, `simple.period=10|60`; limite approssimativo per location, non protezione assoluta dell'account. Fonte: https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/
- [ ] Prossimo passo: rendere pronto **in modo reversibile e senza deploy** il percorso del Worker TEST (binding D1 TEST, limiter, segreto separato, test isolato, costo Free, rollback) e chiedere consenso soltanto per distribuire/abilitare successivamente. Non modificare `main` o il Worker Production; non fare read/write sul database.
- [x] PR #102 sempre DRAFT OPEN all'ultima verifica, monitor daily main v0.8.14 intatto; nessuna modifica Cloudflare, nessuna spesa attivata, nessun alert TradingView, nessun ordine e filoni A/B/C non interferiti.

## CHECKPOINT v0.8.20 — SEGRETO PRODUCTION NOME PARZIALE — 13/11/2026 ore 15:09 CET
- [x] Acquisito nuovo screenshot iPhone in orizzontale, Worker `remura-tv-ingest-lab` → **Production** → Settings → Runtime variables and secrets. **Tipo `Secret`**, **nome visibile `WEBHOOK_TOKE...`**, **valore `Value encrypted`**. Nome visibile coerente col precedente `WEBHOOK_TOKEN_SHA256`, ma **troncato: NON conferma esattamente nome completo, contenuto, autenticazione o abilitazione dell'ingestione**.
- [x] Non esposti né richiesti valori segreti. Nessuna nuova operazione Cloudflare / GitHub da parte dell'utente, nessun token o costo nuovo.
- [ ] Informazione nuova indispensabile: schermata **Bindings** con colonne **Name / Type**, possibilmente nome D1 `TELEMETRY_DB` e database associato quando visibile, evitando qualsiasi valore sensibile; screenshot precedente mostrava solo tipo `D1 database`, non nome. Non richiedere nuovamente screenshot del Secret o Domains/Access.
- [ ] Binding `INGEST_RATE_LIMITER` e valore `INGEST_ENABLED` restano NON verificati nell'ultima configurazione runtime; screenshot parziale NON dimostra assenza di elementi oltre inquadratura. Nessun deploy, webhook o ingest finché preflight/consenso separato.
- [x] PR #102 DRAFT, nessun merge, ultimo monitor `main` v0.8.14 invariato, record sintetico D1 TEST preservato. Le prove full-chain attuali restano esclusivamente offline/sintetiche.

## CHECKPOINT v0.8.19 — WORKER PRODUCTION SETTINGS, SCREENSHOT UTENTE — 13/11/2026 ore 15:03 CET
- [x] Nuovo screenshot reale Cloudflare dashboard `remura-tv-ingest-lab` → **Settings** → tab **Production**. In `Runtime variables and secrets` visibile **un elemento di tipo Secret**; in `Bindings` visibile **un elemento di tipo D1 database**. In `Observability` spunta su `Include Invocation logs` nell'area visibile. Nessuna modifica effettuata.
- [x] **Non attribuire nomi che NON compaiono nell'immagine**: visualizzata soltanto colonna `Type` per Secret e D1. Non possiamo associare con certezza il Secret a `WEBHOOK_TOKEN_SHA256` né il binding D1 a `TELEMETRY_DB` o al database specifico. I checkpoint precedenti documentano la loro configurazione; **questa immagine non li riconferma nominalmente**. La colonna nome sembra fuori inquadratura sulla visualizzazione iPhone.
- [x] Nella porzione di schermata visibile **non risulta alcuna riga Rate Limiting** e non è visibile alcuna variabile plaintext `INGEST_ENABLED`; **non dire che siano assenti dall'intera configurazione** finché non si controllano nomi, ambienti e binding supportati dalla UI.
- [x] Confermata esistenza di impostazioni Production e binding D1/Secret dall'interfaccia proprietario **senza nuovi token**. Il workflow API Workers Settings aveva già prodotto `INCONCLUSIVE_HTTP_403` sul token D1 Read: non ripeterlo identico.
- [ ] **Unica informazione manuale residua per questa vista:** mostrare la colonna `Name` e `Type` nello stesso screenshot, senza aprire valori: modalità orizzontale/zoom-out Safari o scorrimento laterale tabella. Non richiedere screenshot Access/Domains già acquisiti, né segreti.
- [ ] Prima del webhook live serviranno verifica affidabile binding limiter/costo Free, ambiente TEST isolato (manifest v0.8.18 ancora INCOMPLETO/NO DEPLOY), flag ingest OFF fino al consenso per primo test e test end-to-end reale. Nessun ordine.
- [x] PR #102 ancora DRAFT OPEN all'ultimo controllo, Worker runtime non modificato, monitor main v0.8.14 invariato, nessuna modifica ai database, filoni A/B/C o configurazione Cloudflare.

## CHECKPOINT v0.8.18 — WORKER SETTINGS AUTH GET 403 E TEST WEBHOOK SICURO — 13/11/2026 ore 13:57 CET
- [x] Verificata documentazione **Cloudflare GET /accounts/{account}/workers/scripts/{script}/settings**, che richiede permessi Worker Scripts Read oppure Worker Metadata Read-Only; **NON** implica che il token D1 Read possieda tali permessi. Endpoint diverso da hostname pubblico `workers.dev`. [API Cloudflare](https://developers.cloudflare.com/api/resources/workers/subresources/scripts/subresources/script_and_version_settings/methods/get/).
- [x] Nuovo `gateway-lab/worker_metadata_probe_v1.py`: tenta **solo due GET autenticati** (verify token + metadata del solo Worker `remura-tv-ingest-lab`); valore segreti, bind D1 UUID, environment values, corpo risposte e token **mai pubblicati**. Schema sanitize: `INGEST_FLAG`, stato binding D1/secret/rate limiter, ma non simula stato del codice realmente deployato.
- [x] Nuova workflow `.github/workflows/remura-tv-worker-settings-readonly.yml` (branch DRAFT, nessuno schedule, permessi `contents:read`), con **11 test esclusivamente sintetici verdi**. [Run #43428754941](https://github.com/mirkoworz/remura/actions/runs/43428754941) SUCCESS come **esecuzione del controllo**, risultato **`REMURA_WORKER_SETTINGS=INCONCLUSIVE_HTTP_403`** dalla API autenticata: **NON** letti i metadata Worker. Non confondere verde della Actions con permesso ottenuto, configurazione verificata o ingest OFF. Il precedente 403 sulla URL pubblica resta un controllo distinto e inconcludente. Non ripetere identico con lo stesso token.
- [x] Preparato `gateway-lab/wrangler.webhook-test.EXAMPLE.json`, configurazione **non deployabile** per un nuovo Worker isolato `remura-tv-webhook-test`, D1 `remura-tv-lab-test`, `INGEST_ENABLED=false`, con UUID e namespace rate limiter lasciati intenzionalmente come placeholder. **No Secrets nel repo**, e nessun Worker nuovo creato su Cloudflare.
- [x] `predeploy_test_manifest_guard_v1.py` + `test_manifest_guard_v1.py`: blocca in offline qualsiasi destinazione al database principale, `INGEST_ENABLED=true`, variabili secret in chiaro, routes inattese, limiter assente/indebolito, IDs invalidi. [CI #43429329813](https://github.com/mirkoworz/remura/actions/runs/43429329813) **SUCCESS** (69 test laboratorio + 11 D1 reader + nuovi test manifest + Node simulato); stato manifest `EXAMPLE_BLOCKED_BY_UNRESOLVED_IDS`, non “ready for deploy”. Nessun deploy/webhook, nessuna scrittura D1.
- [ ] Per finire preflight configurazione: preferire **un'unica lettura manuale dalla UI delle sole righe Binding / Variables and Secrets, con valori segreti chiusi**, al posto di generare nuovi token. La disponibilità del binding Rate Limiting potrebbe non essere visibile da dashboard; stato limiter quindi da confermare separatamente prima del deploy. Il vecchio screenshot Domains & Routes è già acquisito, NON ripetere.
- [ ] Per primo webhook reale: preflight completo, verifica effettiva account Free e disponibilità rate limiter; eventuale Worker TEST isolato prima **OFF**, poi abilitazione per un test controllato SOLO dopo autorizzazione dell'utente; nessun dato nel DB principale durante il test.
- [x] PR #102 OPEN/DRAFT, Worker online v0.8.5 non aggiornato, main budget v0.8.14 invariato, record sintetico TEST conservato, filoni A/B/C non toccati. **Nessuna nuova credenziale o spesa**.

## CHECKPOINT v0.8.17 — CLOUDFARE DOMAINS / ROUTES DA SCHERMATE UTENTE — 13/11/2026 ore 13:44 CET
- [x] **Nuova verifica manuale, diversa dalla sonda pubblica GitHub**: screenshot Cloudflare Workers & Pages → `remura-tv-ingest-lab` → Settings → Domains & Routes, inviati il 13/11/2026 alle 13:44 CET. Vista `Worker URL` **Production**, hostname pubblico `remura-tv-ingest-lab.mirkoworz.workers.dev`, testo **`Anyone with this URL can visit`** e pulsante **`Enable Access`**. Questi elementi indicano **Access non attivato per quel collegamento Production nella vista corrente**, **non** garantiscono l'assenza di altre policy di accesso a livello account/hostname.
- [x] Sezione Custom Domains and Routes: **No custom domains**; nessuna custom route elencata. È presente anche una URL **Preview** distinta; NON utilizzare il percorso Preview per webhook senza valutare sicurezza e routing.
- [x] Non è stato cliccato alcun controllo mutativo: **no Enable Access, Add Route, Add Domain**, nessun cambio di infrastruttura, secrets, database o Worker.
- [x] Aggiornata diagnosi `INCONCLUSIVE_EDGE_403`: il precedente 403/403 GitHub è **ancora inconcludente**, ma non deve più essere attribuito senza prove al login di Cloudflare Access per l'URL Production. Cloudflare documenta un **Browser Integrity Check (BIC) obbligatorio sull'hostname workers.dev**, che può respingere client automatizzati prima che il Worker venga invocato; è **un'ipotesi tecnica, NON la diagnosi verificata del vecchio 403**. [Documentazione Workers.dev](https://developers.cloudflare.com/workers/configuration/routing/workers-dev/), [Access](https://developers.cloudflare.com/workers/configuration/cloudflare-access/).
- [ ] Prossima verifica necessaria **non duplicata**: binding/versione/settings Worker reali con canale autenticato read-only e permessi minimi. Evitare nuove richieste dal runner GitHub che replichino GET `/health` e `/` con lo stesso comportamento già classificato inconcludente.
- [ ] Il fatto che l'URL sia pubblico **non equivale ad ingest abilitato**; ultimo runtime noto v0.8.5, Pine alert OFF, primo webhook reale NON inviato. Prima di abilitarlo servono rate limiter, protezione anti-abuso e consenso distinto, idealmente primo test su D1 TEST.
- [x] PR #102 DRAFT/OPEN, main budget v0.8.14 invariato, Filoni A/B/C non coinvolti. **Nessuna operazione manuale ulteriore richiesta all'utente in questo checkpoint**.

## CHECKPOINT v0.8.16 — SIMULAZIONE FULL CHAIN E READER MAIN D1 OFFLINE — 13/11/2026, ore 13:11 CET
- [x] Nessun repeat dei vecchi audit Cloudflare: ripreso dal checkpoint v0.8.15 e PR #102 verificata OPEN/DRAFT. Esaminati esclusivamente Pine v0.8.1, gateway v0.8.6, bridge v0.8.15 e workflow CI pertinenti. `main` resta monitor giornaliero v0.8.14 con pinned commit precedente; Worker online non modificato, ingest OFF ultimo checkpoint.
- [x] Implementato `gateway-lab/offline_webhook_roundtrip.mjs`: **POST soltanto verso l'oggetto Worker in memoria Node**, con token sintetico e IP simulato, D1 FakeD1; prova 403 per IP/token errati, 200 accepted, duplicato idempotente, evento in ritardo non prospettico e heartbeat. Emette 3 sole righe completamente sintetiche e marcate `SYNTHETIC_LOCAL_NODE_WORKER_FAKE_D1`. Nessun accesso di rete o Cloudflare.
- [x] `test_offline_webhook_roundtrip_v1.py`: riceve tali righe, attraversa `remura_tv_bridge_preview_v1.py`, controlla coerenza contratto, classificazione eventi/heartbeat, etichetta LATE, rifiuti su campi D1 incoerenti, duplicati in conflitto quarantinati e nessun LONG/SHORT o ordine.
- [x] `gateway-lab/d1_preview_reader_v1.py`: predisposto lettore **SELECT esclusiva** su `remura-tv-lab` (solo PROSPETTICO, non TEST), account e giurisdizione UE obbligatori, finestra <= 24h, limite <= 100, sentinella `LIMIT+1` per rifiutare risposte troncate, schema D1 rigido e output analitico senza raw_json. Non possiede un CLI e **non viene chiamato con credenziali reali**; parametro `explicit_live_approval` è guardia tecnica supplementare, NON sostituisce approvazione utente.
- [x] `gateway-lab/test_d1_preview_reader_v1.py`: test di rete **interamente mocked**, verificano assenza di chiamate se non autorizzato, solo query SELECT, destinazione corretta, risposte Cloudflare incomplete e record invalidi. Non ha letto il DB principale reale.
- [x] [GitHub CI #43422541291](https://github.com/mirkoworz/remura/actions/runs/43422541291) **SUCCESS** (69 test Python laboratorio + 11 regressioni lettore, Node gateway test e controlli sintattici). CI non esegue alcuna connessione D1 principale né webhook. Workflow `.github/workflows/remura-tv-telemetry-lab.yml` ora v0.8.16, GitHub contents:read, solo branch PR.
- [x] Nuova guida `gateway-lab/WEBHOOK-LIVE-GATE-v0.8.16.md` con vincoli e gates: 403/403 GitHub inconcludente, possibile Cloudflare Access che richiede login (da verificare, NON accertato), read-only Worker settings richiede permesso Workers Metadata Read Only/Workers Scripts Read che gli attuali token non garantiscono; rate limiting approssimativo e costo reale sull'account Free sconosciuto. Non ripetere sonda pubblica identica, non richiedere segreti in chat.
- [ ] Prossimo passo sicuro: **configurazione autenticata read-only del solo Worker** (Access, routing, binding, versione) attraverso connettore/permessi minimi, solo quando possibile senza nuova esposizione segreti; nessun deploy, modifica Access o ingest. I quattro IP TradingView e la 2FA erano già verificati.
- [ ] Solo dopo preflight Worker + limite costo Free + consenso distinto: endpoint temporaneo isolato su D1 TEST, prova Webhook reale originato da TradingView, validazione 3 secondi/record, quindi eventuale passaggio al D1 prospettico. Nessun ordine automatico.
- [ ] Integrazione filoni B/C e notifiche richiedono validazione prospettica /out-of-sample e decisione architetturale separata. I volumi FXCM TradingView sono **proxy**, non esecuzioni istituzionali.
- [x] Filoni A/B/C, database principali, record sintetico TEST, secrets, Worker runtime e monitor quotidiano `main` intatti. **Zero servizio a pagamento attivato**.

## CHECKPOINT v0.8.15 — PRIMO ADATTATORE D1 → REMURA SOLO OFFLINE — 13/11/2026, ore 13:00 CET
- [x] Esaminato soltanto contratto Pine v0.8.1, ricevitore gateway v0.8.6, schema D1 e misuratore prospettico v0.8.3 gia presenti; **nessun test o configurazione Cloudflare precedente ripetuto**. Il Pine e il gateway hanno componenti di emissione/validazione ma **nessun webhook end-to-end LIVE ancora autorizzato**.
- [x] Nuovo `tradingview/delta-peaks/remura_tv_bridge_preview_v1.py` v0.8.15: accetta **solo un export JSONL preparato offline** con le 9 colonne dello schema `tv_flow_events`, usa `validate_telemetry_v1.validate_payload`, verifica coerenza tra metadati D1 e JSON originale, unicita chiave, timeliness sul timestamp **del gateway**, provenienza FXCM/proxy, flags ER/PEAK/RT/DAY, disponibilita footprint, ATR e POC, senza chiedere/leggere segreti.
- [x] Uscita JSON locale `remura.tv.observation.preview.v1` con etichette osservazionali, ragioni di dati mancanti e stato `OBSERVATION_ONLY | PARTIAL_OBSERVATION | LATE_NOT_PROSPECTIVE`. Il verdetto resta sempre `NESSUN_SEGNALE_OPERATIVO`, `orders_enabled:false`, `proof_of_institutional_activity:false`, `statistical_edge_validated:false`. **Non e il collegamento live REMURA app e non dimostra edge o profitti**.
- [x] Duplicati identici scartati; record con stessa chiave ma payload differente **interamente in quarantena**; record sintetici TEST, stime presentate come contratti CME, colonne incoerenti, timestamp falsi o payload JSON invalidi rifiutati. L'adattatore non scrive in D1, Cloudflare, Oracle, Firestore o altri filoni.
- [x] Test sintetici `test_remura_tv_bridge_preview_v1.py` e controllo di sintassi aggiunti al workflow **gia esistente** di PR #102. [Run GitHub #43421390844](https://github.com/mirkoworz/remura/actions/runs/43421390844) **SUCCESS** per test offline Python, simulazione gateway Node e syntax; **nessuna richiesta Cloudflare, nessun webhook**. Commit modulo `ba4cf512`, test `f0dda600`, gestione conflitti `70af2d3b`, regressioni `371645d3`, CI `4fdc9594`.
- [ ] Per primo **webhook reale**: preflight autenticato configurazione Worker e protezione edge (non rifare sonda GitHub 403 inconcludente); confermare disponibilita/costo limiter Free; test controllato su D1 TEST o canale isolato; solo con autorizzazione distinta deploy/abilitazione e TradingView `alert()` v0.8.1. Monitorare consegna TradingView e latenza 3s, nessun ordine.
- [ ] Per **analisi automatica REMURA**: implementare lettore D1 GET/SELECT a credenziali minime con politiche di accesso e quota, processo idempotente eventi → adattatore → validazione outcome/benchmark, UI filone C e notifiche solo dopo coordinamento esplicito con B/C. Nessuna scrittura verso B/C da questa PR.
- [ ] Per verdetti statisticamente utili: raccogliere campione prospettico completo (heartbeat M5 per misurare anche barre senza evento), false positive, esiti out-of-sample e risk/costi di negoziazione; **non trasformare etichette di osservazione in raccomandazioni di entrata**.
- [x] Rimane monitor giornaliero `main` v0.8.14 con run SUCCESS e pin SHA testato; PR #102 DRAFT OPEN, Worker online v0.8.5 ingest OFF ultimo checkpoint, sorgente v0.8.6 offline, record sintetico TEST immutato, altri filoni A/B/C intatti, nessun servizio a pagamento.

## CHECKPOINT v0.8.14 — INVENTARIO D1 LIVE E MONITOR GIORNALIERO VERDE — 13/11/2026, ore 12:52 CET
- [x] **Laboratorio PR #102:** GitHub Actions [#43414271846](https://github.com/mirkoworz/remura/actions/runs/43414271846), commit verificato `08ee9d8f5ba0b4655f4b0b84245afc7cb7a360c8`: job offline-safety SUCCESS con **85/85 test** (20 D1 Analytics, 17 Workers, 13 D1 TEST, 18 D1 account storage, 17 summary), job API LIVE **read-only SUCCESS**. `REMURA_D1_ACCOUNT_STORAGE=OK`: **2 database D1, 57.344 byte aggregati**, massimo **28.672 byte/DB**, D1 TEST **28.672 byte**; quota account 5GB di riferimento. Dati `file_size` **metadati reali**; consumi giornalieri Analytics **stime** (D1 1 read/0 write, Workers 123 requests/0 errors).
- [x] Sulla base della prova reale e dell'assenso a proseguire, aggiornato **solo** `.github/workflows/remura-cloudflare-budget-daily.yml` su `main` alla **v0.8.14**, con `permissions: contents: read`, ref codice immutabile `08ee9d8f...`, 85 test offline e quarta sonda GET-only account D1. Mai abilitati ingest, webhook, SQL write, Worker deploy, merge PR o ordini.
- [x] **Errore intercettato e corretto:** primo commit workflow `bd16c6fd` produsse YAML non valido; [run #43420321670](https://github.com/mirkoworz/remura/actions/runs/43420321670) FAILURE senza job avviati. Ricostruito il file dalla v0.8.13 funzionante, senza riusare il patching difettoso, e pubblicato fix su `main` [commit `f40da371`](https://github.com/mirkoworz/remura/commit/f40da371a0abe9cb007ec98fa3401904e23ac5a3).
- [x] **Run finale main** [#43420383076](https://github.com/mirkoworz/remura/actions/runs/43420383076) SUCCESS e log effettivo `REMURA_DAILY_BUDGET=READ_ONLY_COMPLETE`; 85/85 test, D1 account storage OK, **2 D1 / 57.344 byte**, Workers **133 richieste stimate**, 0 errori stimati, D1 **1 read/0 write stimate**, D1 TEST 28.672 byte. Nessun token stampato. Workflow prezzi e insights in main SUCCESS; [GitHub Pages #43420381151](https://github.com/mirkoworz/remura/actions/runs/43420381151) SUCCESS verificato. Rebuild Pages conseguente al push: **non equivale a Worker Cloudflare deploy**.
- [x] WARNING a 70% (annotazione Actions); CRITICAL a 90% o UNKNOWN causa failure, comprese nuove metriche D1 account. Le email/notifiche push **non sono verificate** e dipendono da preferenze GitHub. Non promettere avvisi telefonici.
- [ ] **Primo evento cron reale** atteso il **14/11/2026 verso le 08:37 CET**; prima esecuzione `push` non dimostra l'attivazione di `schedule`. Verificare evento e risultato domani senza ripetere oggi i test manuali.
- [ ] Ancora da verificare: Cloudflare billing/costi realmente maturati, piano effettivo, CPU totale Workers, Worker pubblicamente protetto oltre l'inconclusivo 403, rate limiting binding, e modalità affidabile di notifica warning/failure. Mai considerare metriche Analytics adaptive come billing esatto.
- [x] PR #102 sempre DRAFT/OPEN, due database UE non modificati, record sintetico TEST preservato, Worker runtime v0.8.5 e sorgente gateway v0.8.6 senza deploy, ingest OFF ultimo checkpoint, filoni A/B/C intatti.

## CHECKPOINT D1 ACCOUNT STORAGE READ-ONLY PREPARATO — 13/11/2026, ore 12:06 CET
- [x] Verificati solo PR #102 OPEN/DRAFT, roadmap v0.8.13 e scheduler in main v0.8.13; **nessun audit ripetuto, nessun deploy, merge o cambiamento su main**.
- [x] Nuovo `gateway-lab/cloudflare_d1_account_storage_guard.py` **v0.8.14** nel SOLO branch DRAFT: API GET di token verify, elenco D1 account con `page=1&per_page=100` e GET `file_size` di ogni database. Nessuna query SQL, POST, token in output, Cloudflare write o lettura delle tabelle. Riutilizza esclusivamente `REMURA_CF_D1_READ_TOKEN` e `REMURA_CF_ACCOUNT_ID` già presenti.
- [x] Controlli fail-closed contro elenco incompleto/paginazione mancante, UUID duplicati, metadata mancanti, assenza dei due D1 REMURA previsti o giurisdizione non UE per tali database. **UNKNOWN non è zero.** Inventario vincolato a max 100 elementi, senza assumere che il piano reale sia Free.
- [x] Soglie comparative Free su 10 DB/account, 500.000.000 byte/DB, 5.000.000.000 byte/account; WARNING a 70%, CRITICAL a 90%. `file_size` è metadata reale API ma **non contatore di fatturazione esatto**. Fonte: documentazione ufficiale D1 API e limits Cloudflare consultata il 13/11/2026.
- [x] Aggiunti test **esclusivamente sintetici/offline** `test_cloudflare_d1_account_storage_guard.py`, report esteso con campo D1 account e nuovi test summary. Workflow di LAB `.github/workflows/remura-tv-account-analytics-readonly.yml` modificato per tentare la quarta sonda **solo nel branch DRAFT**. Commit codice `b826817c`, test `c765ca63`, summary `54773f10`, test summary `5abeffb4`, workflow `119280ac`. Test e chiamata remota **da verificare su run GitHub Actions**, non dichiararli verdi prima del riscontro.
- [x] Raffinamento dello script per giurisdizione facoltativa dei **soli DB estranei a REMURA**, preservando il controllo EU obbligatorio sui due D1 REMURA; [commit `cb7f4663`](https://github.com/mirkoworz/remura/commit/cb7f4663bbce0e9e8ec8097d8682decae57ae34a). Aggiunto caso di test [commit `08ee9d8f`](https://github.com/mirkoworz/remura/commit/08ee9d8f5ba0b4655f4b0b84245afc7cb7a360c8). Esecuzione remota CI non ancora verificata da questa sessione. **Nessun nuovo dato live dichiarato.**
- [x] Verificata CI e nuovo inventario D1 LIVE nella run #43414271846: 85 test, lettura GET metadata 2 D1 e 57.344 byte. Casi incompleti restano UNKNOWN; nessuna nuova credenziale.
- [x] Aggiornato il solo workflow giornaliero su `main` dopo risultato positivo, commit `f40da371`, ref ora puntato in modo esplicito a `08ee9d8f` (85 test, live read-only); prima esecuzione `schedule` ancora attesa 14/11/2026 08:37 CET.
- [ ] Notifiche: in `main`, WARNING è attualmente annotazione GitHub; CRITICAL/UNKNOWN causa job failure. Le notifiche email/web dipendono dalle impostazioni GitHub dell'utente e NON sono state provate o attivate da REMURA; nessun canale a pagamento aggiunto.
- [x] Worker runtime v0.8.5 e `INGEST_ENABLED` non modificati; webhook TradingView/heartbeat OFF, PR DRAFT/OPEN, record sintetico TEST conservato; filoni A/B/C intatti.

## CHECKPOINT MONITOR GIORNALIERO ATTIVO IN MAIN — 13/11/2026, ore 11:15 CET
- [x] Utente ha autorizzato esplicitamente un **minimo workflow quotidiano di sola lettura** in `main`, isolato dalla PR #102; nessun merge della PR o deploy Cloudflare.
- [x] Creato solo `.github/workflows/remura-cloudflare-budget-daily.yml` su `main`, **REMURA v0.8.13**, [commit `3443c1e5`](https://github.com/mirkoworz/remura/commit/3443c1e521849c6e956d31d4028ce1ef06963db1). Esecuzione programmata **08:37 Europe/Rome ogni giorno**, con `workflow_dispatch` e `push` limitato alla modifica del solo file workflow. GitHub può ritardare o saltare esecuzioni sotto carico; non dichiarare consegna garantita.
- [x] Workflow con `permissions: contents:read`, checkout `persist-credentials:false` di codice read-only da **commit fisso e immutabile** `1e3c38b772df01b0e66679f0e727ffcdbf83c80a`, timeout 5 min. Nessun `git push`, SQL D1 Write, deploy Worker, webhook, merge o ordini; token GitHub Secrets mai stampati.
- [x] Esegue ogni volta **63 test offline**, poi metriche effettivamente interpellate via Account Analytics Read (Workers e D1 giornalieri) + D1 Read (metadati solo DB TEST); genera `GITHUB_STEP_SUMMARY` con valori disponibili/UNKNOWN. Mancanza secrets o stato non verificabile = job failure; `WARNING` a 70%, `CRITICAL` a 90% delle soglie calcolate. P99 CPU non fatturazione esatta.
- [x] [Prima esecuzione su `main` #43407561296](https://github.com/mirkoworz/remura/actions/runs/43407561296) SUCCESS, `REMURA_DAILY_BUDGET=READ_ONLY_COMPLETE`; stime 13/11/2026: **111 richieste Workers, 0 errori, D1 1 read/0 write**, dimensione reale D1 TEST **28.672 byte**. NON contatori billing esatti né prova di tutte le risorse account senza spese.
- [x] Il commit `main` ha attivato anche workflow esistenti (GitHub Pages build/deployment, price checks, insights checks); tutti osservati **SUCCESS**. Nessun file UI/applicativo modificato: il rebuild automatico di GitHub Pages è effetto collaterale del commit `main`, NON un deploy Worker o merge della PR #102.
- [ ] Prima esecuzione da `schedule` attesa **14/11/2026, verso le 08:37 Europe/Rome**; l'esito cron non è ancora verificabile. Il semplice risultato SUCCESS del push non prova che l'evento `schedule` venga attivato domani. Monitor consultabile tramite GitHub Actions; nessuna email/Telegram di allerta automaticamente configurata.
- [ ] Versioni future di script PR #102 **non entreranno** nel monitor schedulato senza un nuovo pin SHA testato e intervento deliberato su `main`.
- [ ] Restano non verificati: piano/costi billing esatti, Workers edge 403/403 da runner GitHub, protezione rate limiter reale, spazio aggregato tutti D1. Ingest OFF da ultimo checkpoint attendibile; non autorizzare webhook/ordini da stato monitor verde.
- [x] PR #102 resta OPEN/DRAFT, branch di ricerca indipendente, nessun tocco ai filoni A/B/C.

## CHECKPOINT MONITOR UNIFICATO FREE D1 + WORKERS — 13/11/2026 ore 10:12 CET
- [x] Fonti ufficiali Cloudflare: `workersInvocationsAdaptive` GraphQL con `sum.requests`, `sum.errors`, `quantiles.cpuTimeP99`, richiedendo solo il token **Account Analytics Read** esistente. Il dato è adattivo/stimato, non fatturazione esatta. Workers Free 100.000 req/die e 10ms CPU per singola invocazione.
- [x] Implementato `cloudflare_workers_usage_guard.py` v0.2: riepilogo account-wide da mezzanotte UTC, campione max 1.000 righe; risposta vuota/troncata non può essere presentata come zero/sicura; P99 mancante viene riportato come sconosciuto, non zero. Nessuna credenziale nei log.
- [x] **Prima prova reale Workers** [run #43398573498](https://github.com/mirkoworz/remura/actions/runs/43398573498): 100 richieste stimate, 0 errori stimati, 1 Worker rappresentato dai gruppi ritornati, massimo P99 osservato 3.080µs. **Non dimostra un consumo esatto/account completo né la conformità CPU di tutte le chiamate**.
- [x] **Monitor combinato** workflow `.github/workflows/remura-tv-account-analytics-readonly.yml` v0.4: query D1 Analytics + Workers Analytics + file_size D1 TEST; scrive resoconto sanitized nel `GITHUB_STEP_SUMMARY`. Protezione da valori assenti e nessun logging secret.
- [x] [Run #43399020915](https://github.com/mirkoworz/remura/actions/runs/43399020915): **63/63 test offline** (20 account D1 + 17 Workers + 13 D1 TEST storage + 13 report); job remoto SUCCESS: stime D1 `1 read, 0 write`, Workers `101 richieste, 0 errori`, DB TEST `28.672 byte`, `REMURA_BUDGET_REPORT=GENERATED_NO_SECRETS`.
- [x] Ulteriore prova verde dopo fix `cpuTimeP99=None` senza inventare zero: [run #43399187515](https://github.com/mirkoworz/remura/actions/runs/43399187515).
- [x] README `gateway-lab/README.md` aggiornato a v0.8.12-doc. Sorgente Worker v0.8.6 solo GitHub, runtime online v0.8.5, ingest non abilitato da noi.
- [ ] **Non schedulato giornalmente**: il workflow nel branch DRAFT funziona su push mirati e `workflow_dispatch`. GitHub `schedule` sul branch research non viene eseguito: serve un orchestratore minimo separato nel ramo default solo con permessi `contents:read` e senza deploy, da autorizzare esplicitamente, oppure una schedulazione esterna idonea.
- [ ] Rimangono non verificati: fatturazione e piano Cloudflare reali, protezione edge/403 del Worker, spazio complessivo D1 e disponibilità/costi rate limiting binding Free. Nessuna modifica a `main`, nessun webhook, ordine, SQL write, merge PR #102 o filoni A/B/C.

## CHECKPOINT ANALYTICS ACCOUNT-WIDE REALI RIUSCITE — 13/11/2026 ore 10:01 CET
- [x] Utente ha confermato inserimento nel GitHub Secret `REMURA_CF_ANALYTICS_READ_TOKEN` del token Cloudflare separato **Account Analytics → Read**. Non vengono richieste modifiche ai precedenti token D1 Read.
- [x] GitHub Action [run 43397743147](https://github.com/mirkoworz/remura/actions/runs/43397743147) rilanciata automaticamente tramite commit isolato alla workflow del branch DRAFT: offline-safety SUCCESS, `account-analytics-readonly` SUCCESS.
- [x] Output autentico GraphQL del **13/11/2026 UTC**: `REMURA_CF_ACCOUNT_QUOTA=OK`, `D1_ACCOUNT_ROWS_READ_ESTIMATE=1`, `D1_ACCOUNT_ROWS_WRITTEN_ESTIMATE=0`; limiti gratuiti di riferimento 5.000.000 read e 100.000 write/die. **Stime Analytics adattive, non contatori billing esatti** e potenzialmente incomplete/ritardate.
- [x] Token Analytics funzionante; nessuna query SQL di scrittura, mutazione API, deploy Worker, merce o ordine. README gateway aggiornato **v0.8.11-doc**, 13/11/2026 ore 10:01.
- [ ] Stato gateway pubblico dal runner GitHub resta `INCONCLUSIVE_EDGE_403`: 403/403 non prova disabilitazione né attivazione. Prima di ogni test webhook servono verifica da account, protezione edge e misure effettive Workers.
- [ ] Restano sconosciuti: consumo giornaliero Workers/CPU, dati billing esatti, spazio combinato dei due D1, disponibilità/costo Rate Limiting binding sul piano Free. Non dichiarare l'account completamente sicuro per i costi solo da D1 Analytics.
- [ ] Monitoring giornaliero vero **non ancora schedulato**. Workflow su branch research con `push` e `workflow_dispatch`; GitHub `schedule` userebbe main e va progettato separatamente con autorizzazione.
- [x] PR #102 verificata OPEN/DRAFT: mantenere no merge/no deploy/no activation; altri filoni A/B/C non modificati.

## CHECKPOINT PUBBLICO 403 + QUOTE GIORNALIERE PREPARATE — 13/11/2026 ore 06:57 CET
- [x] PR #102 ancora **OPEN/DRAFT**, commit isolati sul branch `research/tradingview-delta-peaks-20261111`; Worker pubblico runtime v0.8.5 non modificato, sorgente v0.8.6 solo GitHub, ingest OFF da ultimo stato confermato dall'utente (nuova verifica pubblica inconcludente).
- [x] `worker_public_failclosed_audit.py` v0.3 e [workflow GitHub](https://github.com/mirkoworz/remura/actions/runs/43374850790): esegue **solo GET** `/health` e `/`, mai POST o URL contenente token. 17 test offline verdi.
- [x] Esito reale dal runner GitHub: **HTTP 403/403**, `REMURA_TV_PUBLIC_FAILCLOSED=INCONCLUSIVE_EDGE_403`. Importante: il job verde indica che il caso 403 è stato classificato correttamente, NON che `accepting=false` sia stato verificato da GitHub. Senza nuovo controllo dall'account non dichiarare il Worker provato OFF.
- [x] Fonte Cloudflare GraphQL: il consumo D1 account-wide `rowsRead`/`rowsWritten` richiede **Account Analytics → Read**; il token D1 Read separato non basta. Metriche analytics adattive, non prove esatte della fatturazione. Non autorizzare scritture o nuovi privilegi.
- [x] `cloudflare_account_quota_guard.py` v0.1: query GraphQL **read-only**, giorno UTC, max 10 gruppi DB su Free, soglie 70% WARNING e 90% CRITICAL per 5.000.000 read / 100.000 write giornaliere. `NO_DATA` non equivale a 0.
- [x] [Workflow Account Analytics](https://github.com/mirkoworz/remura/actions/runs/43375218853): **20/20 test offline verdi**, job remoto `REMURA_CF_ACCOUNT_QUOTA=SKIPPED_MISSING_ANALYTICS_READ_TOKEN`, cioè nessun dato account-wide raccolto. Nessuna chiamata GraphQL remota.
- [ ] Per automatizzare il bilancio quotidiano serve un token **separato** e minimo Cloudflare Account Analytics Read salvato in GitHub Secret `REMURA_CF_ANALYTICS_READ_TOKEN`. Richiedere all'utente solo al momento opportuno; mai chiedere valore/screenshot token in chat. Non modificare `REMURA_CF_D1_READ_TOKEN`.
- [ ] In assenza di nuovo token, usare solo prova effettiva spazio D1 TEST (28.672 byte, 0,0057% del limite), non inventare utilizzo giornaliero Workers/D1 o costo realizzato.
- [ ] Se necessario controllare da sessione autenticata `/health` e `/` senza aprire `/ingest`, per chiarire 403 edge. Worker pubblico non testato end-to-end e webhook TradingView/heartbeat OFF.
- [x] `gateway-lab/README.md` aggiornato a v0.8.10-doc; nessun deploy, merge, ordine, o modifica ai filoni A/B/C. Nessun nuovo servizio a pagamento.

## CHECKPOINT D1 FREE STORAGE REALE AUTOMATIZZATO — 13/11/2026 ore 06:45 CET
- [x] Confermata fonte ufficiale Cloudflare per **GET metadati D1** con permesso D1 Read e campo `file_size`. Token GitHub esistente `REMURA_CF_D1_READ_TOKEN` riutilizzato, nessuna nuova credenziale.
- [x] Script `gateway-lab/cloudflare_d1_storage_guard.py` v0.1: solo D1 `remura-tv-lab-test` nella giurisdizione EU, 3 richieste **GET** (verify token, list DB TEST, get metadata TEST); nessun SQL sulla D1 prospettica e nessuna write.
- [x] Soglie automatiche storage sul singolo DB TEST: OK sotto 70%, WARNING da 70%, CRITICAL da 90% sul limite conservativo **500.000.000 byte** per DB Free. Le soglie sono guardie locali, non alert di notifica.
- [x] Workflow [run #43373867720](https://github.com/mirkoworz/remura/actions/runs/43373867720) **SUCCESS**: `REMURA_D1_READONLY_AUDIT=record_verified`, `REMURA_D1_TEST_STORAGE=OK`, `REMURA_D1_TEST_STORAGE_BYTES=28672`, quota TEST misurata **0,0057%**.
- [x] Test offline **47/47**: 21 read-only + 13 cleanup sintetico in SQLite memory + 13 storage metadata. GitHub Actions non fa merge/deploy.
- [x] README gateway aggiornato a v0.8.9-doc, 13/11/2026 ore 06:44.
- [ ] **Non ancora misurati:** consumo aggregato dei due database, quota D1 giornaliera letture/scritture, chiamate Worker/CPU e funzionalità/costo effettivo rate limiting binding sull'account Free. Non inventare `0%` o "tutto gratis" senza dashboard.
- [ ] Non aggiungere `schedule` nel branch DRAFT come se funzionasse: GitHub cron esegue workflow dal branch default; attuale audit parte solo su push selettivi/manuale.
- [ ] Il prossimo test pratico di ricezione richiederà preflight quota edge, rate-limiter binding e autorizzazione distinta. Ingest OFF, PR #102 DRAFT/OPEN, nessun alert/ordine.

## CHECKPOINT 2FA + LIMITER v0.8.6 OFFLINE — 13/11/2026, ore 06:38 CET
- [x] Utente conferma **2FA TradingView attiva** (13/11/2026); non ripetere richiesta né chiedere codici.
- [x] Verificata limitazione `workers.dev`: appartiene alla zona Cloudflare gestita, regole WAF del proprio dominio **non si applicano automaticamente**. Rate Limiting Workers disponibile a livello API binding, ma soglie **approssimative per Cloudflare location**, non garantiscono limite globale; costi/disponibilità account Free ancora da verificare.
- [x] Preparata SOLO nel branch PR #102 sorgente **gateway v0.8.6**, ancora NON distribuita: richiede `INGEST_RATE_LIMITER.limit()` presente prima di qualunque ingest; se assente, risponde 503, `/health.accepting=false` anche qualora INGEST_ENABLED=true.
- [x] Blocco rate limit applicato dopo controllo IP/token e prima di D1; oltre soglia 429, errore limiter 503; nessuna scrittura in Cloudflare, nessun deploy.
- [x] Aggiornati test Node con regressioni per missing binding, risposta health, rejection/throw, no write e IP non autorizzato. [CI](https://github.com/mirkoworz/remura/actions/runs/43373136227) verde sul commit del gateway+test, senza webhook live.
- [x] Guida gateway aggiornata a **v0.8.8-doc** con esempio NON attivo di binding e costi da verificare.
- [ ] Preflight prima del vero utilizzo: verifica effettiva tariffazione/rate-limit binding nel tuo account Free, identificatore namespace univoco, possibilità di configurazione sicura con risorse già in uso, test end-to-end autorizzati, protezione traffico anonimo su workers.dev, quote/latency/CPU reali.
- [ ] Non aggiungere `INGEST_ENABLED=true`, non distribuire il Worker v0.8.6, non toccare altri Worker, D1 principale, filoni A/B/C. PR #102 deve rimanere DRAFT.

## CHECKPOINT AUDIT IP TRADINGVIEW E QUOTE — 12/11/2026 ore 23:43 CET
- [x] Confrontate le quattro IPv4 allowlisted nel `worker.mjs` v0.8.5 con la [guida webhook TradingView](https://it.tradingview.com/support/solutions/43000529348/): corrispondono all'elenco ufficiale (12/11/2026).
- [x] Confermati da TradingView: webhook richiede 2FA, solo porte 80/443, timeout 3 secondi, IPv6 non supportato. Nessun webhook effettivo provato; tempo di risposta Worker+D1 ancora sconosciuto.
- [x] Confermate fonti [Workers Free](https://developers.cloudflare.com/workers/platform/limits/) (100k richieste/giorno, 10ms CPU/request) e [D1 Free](https://developers.cloudflare.com/d1/platform/limits/) (10 DB, 500MB/DB, 5GB/account, 5M read/100k write giornalieri).
- [ ] Verifiche **ancora necessarie**: 2FA TradingView effettivamente ON, rate limit edge/proxy, quote account aggiornate a due DB e CPU/latency reali. Non confondere riscontro documental con un test live.
- [x] Aggiornato il README gateway v0.8.7-doc. Worker runtime resta v0.8.5, ingest OFF, nessun deploy né merge PR #102.

## CHECKPOINT CLEANUP OFFLINE + D1 LIVE READ-ONLY — 12/11/2026 ore 23:41 CET
- [x] Sicurezza account e modalità: [PR #102](https://github.com/mirkoworz/remura/pull/102) verificata OPEN/DRAFT, nessun merge, nessun deploy dei Worker né modifica ai filoni A/B/C.
- [x] `cloudflare_d1_readonly_audit.py` v0.4: SELECT solo su D1 `remura-tv-lab-test` UE e verifica aggiuntiva del `raw_json` **esattamente sintetico**, timeframe e tipo evento. Nessuna API di scrittura.
- [x] `synthetic_cleanup_plan_v1.py`: genera soltanto un piano di eliminazione della singola chiave `REMURA_SYNTHETIC_WRITE_20261112` con guardie su simbolo, versione, timeframe, tipo evento, is_timely e JSON esatto. **Non esegue SQL né accede alla rete**.
- [x] `test_synthetic_cleanup_plan_v1.py`: **13 simulazioni su SQLite in memoria**. Insieme ai **21 test offline read-only** (totale **34**) eseguiti con successo nel workflow di verifica.
- [x] GitHub Actions [run #43321908263](https://github.com/mirkoworz/remura/actions/runs/43321908263): job offline-safety SUCCESS, job Cloudflare D1 Read SUCCESS; log `REMURA_D1_READONLY_AUDIT=record_verified` su `remura-tv-lab-test`, UE, SELECT. Nessuna scrittura remota.
- [x] Guida `gateway-lab/README.md` aggiornata con stato effettivo Cloudflare e separazione TEST/PROSPETTICO; sezione storica che sosteneva DB/Worker mai creati corretta.
- [ ] Cleanup reale del singolo record sintetico **non autorizzato né eseguito**; evitiamo di creare un token D1 Write ampio per cancellare una sola riga. Il record rimane esclusivamente nel DB TEST e non contamina `remura-tv-lab`. Potrà essere rimosso con un'unica DELETE manuale circoscritta o con procedura one-shot più avanti, dopo approvazione.
- [ ] Priorità successiva: verificare protezioni edge/IP TradingView, rate limit e quota Free, poi pianificare prova webhook end-to-end **solo con consenso esplicito** e tenendo `INGEST_ENABLED` OFF sino ad allora. Nessun alert o ordine live.

## CHECKPOINT TOKEN CORRETTO E AUDIT D1 REALE VERDE — 12/11/2026 ore 23:34 CET
- [x] Utente ha corretto una lettera nel GitHub Secret `REMURA_CF_D1_READ_TOKEN` senza pubblicare il valore in chat/repo.
- [x] Rilanciati solo i job falliti con GitHub Actions [run 43319409168, tentativo 2](https://github.com/mirkoworz/remura/actions/runs/43319409168): `offline-safety` SUCCESS e `cloudflare-readonly` SUCCESS.
- [x] Log reale del job Cloudflare `131541499082`: `REMURA_D1_READONLY_AUDIT=record_verified`; `DATABASE=remura-tv-lab-test; JURISDICTION=EU; HTTP=READ_ONLY; SQL=SELECT`. Confermata autenticazione API ed esistenza del record sintetico atteso; nessuna scrittura/cancellazione remota.
- [x] Token Account D1 READ funziona dalla GitHub Action. L'ID account verifica guardia hash attesa; il database principale `remura-tv-lab` **non è stato interrogato né modificato da questo workflow**.
- [ ] Pulizia del record sintetico richiede autorizzazione separata e un meccanismo con privilegio di scrittura limitato, oppure intervento manuale; non usare il token D1 Read per nuove funzioni scriventi.
- [ ] Eventuale successivo audit automatico periodico solo dopo scelta esplicita della frequenza. Worker ingress principale continua fail-closed; TradingView alerts/heartbeat OFF; PR #102 resta DRAFT/OPEN.

## CHECKPOINT AUTOMAZIONE CLOUDFLARE CON AUTENTICAZIONE 401 — 12/11/2026 ore 23:24 CET
- [x] Utente ha confermato aggiunta GitHub Actions Secrets `REMURA_CF_D1_READ_TOKEN` e `REMURA_CF_ACCOUNT_ID` (nessun valore segreto ricevuto in chat).
- [x] Avviato workflow D1 read-only su branch di ricerca: [run #43318523658](https://github.com/mirkoworz/remura/actions/runs/43318523658). I test offline verdi e il job API raggiunge Cloudflare, ma Cloudflare ha risposto HTTP **401** a GET /d1/database; nessuna SELECT D1 completata.
- [x] Aggiunto preflight GET /accounts/{account_id}/tokens/verify senza log sensibili; [run #43318951287](https://github.com/mirkoworz/remura/actions/runs/43318951287): **401 anche in verifica account token**.
- [x] Aggiunta protezione che blocca Account ID diversi da REMURA tramite digest SHA-256 e richiede il formato account-token `cfat_` introdotto nel 2026 (trim whitespace). Suite offline estesa a **18 test**.
- [x] [Run #43319409168](https://github.com/mirkoworz/remura/actions/runs/43319409168): offline-safety **SUCCESS**, live API bloccata prima della rete con `unexpected_account_api_token_format`. Ciò indica che il contenuto attuale del GitHub Secret non rispetta il formato previsto del token Account 2026; **non se ne conosce il valore e non va esposto**.
- [ ] Azione manuale minima: controllare e sostituire nel solo GitHub Secret `REMURA_CF_D1_READ_TOKEN` il valore **integrale** del token account Cloudflare (nuovo prefisso `cfat_`), senza includere nome, etichette, spazi o screenshot. Se smarrito, ruotarlo dal pannello Cloudflare senza condividere il nuovo valore. Non cambiare gli altri secrets.
- [ ] Alla conferma utente, riavviare audit con commit innocuo sul workflow; dichiarare successo solo dopo API attiva e SELECT D1 TEST verificata. Non cancellare dati né toccare Worker/filoni A/B/C o webhook.

## CHECKPOINT API D1 READ-ONLY — 12/11/2026, ore 17:48 CET
- [x] Integrazione automatizzabile via API D1 Cloudflare, senza nuovo deploy Worker né modifiche D1: script `gateway-lab/cloudflare_d1_readonly_audit.py` v0.1, limitato per codice a `remura-tv-lab-test` (EU) e SELECT sulla chiave sintetica.
- [x] Aggiunti **11 test offline** in `gateway-lab/test_cloudflare_d1_readonly_audit.py`, nessuna chiamata di rete nelle regressioni.
- [x] Creato workflow isolato `.github/workflows/remura-tv-cloudflare-d1-readonly.yml` limitato ai push del branch #102, più workflow_dispatch per uso futuro; GitHub permissions contents:read, senza deploy/cancellazioni, solo token `REMURA_CF_D1_READ_TOKEN` e account ID `REMURA_CF_ACCOUNT_ID` dai GitHub Secrets.
- [x] GitHub Actions [run 43262606971](https://github.com/mirkoworz/remura/actions/runs/43262606971) **SUCCESS**: job offline-safety verde. Job cloudflare-readonly terminato senza chiamate remote: **SKIPPED_MISSING_SECRETS**, non confondere il verde con un D1 live audit.
- [ ] One-time manuale: token API Cloudflare `Account > D1 > Read` sul solo account REMURA, salvato in **GitHub Actions Secrets** senza mostrarlo in chat, e ID account in secondo secret. NON creare D1 Edit né Workers Edit.
- [ ] Dopo secrets, nuovo commit al file di workflow su branch DRAFT per attivare il job remoto; verificare API read-only. Successivamente progettare cleanup con permessi di scrittura temporanei e autorizzazione separata.
- [ ] `remura-tv-write-test` deve mantenere Hello World come codice pubblicato; la diagnostica temporanea è stata abbandonata senza Deploy secondo l'utente. Nessun webhook, nessuna scrittura automatica aggiunta.

## CHECKPOINT WRITE PROBE SU D1 TEST — 12/11/2026, ore 17:38 CET
- [x] Worker temporaneo isolato `remura-tv-write-test` distribuito con Hello World, binding D1 Production `TELEMETRY_DB` → `remura-tv-lab-test` confermato da screenshot. Preview configurata per usare lo stesso database di test.
- [x] Editor Preview con codice sintetico di `INSERT OR IGNORE` su chiave `REMURA_SYNTHETIC_WRITE_20261112` e successivo `SELECT COUNT(*)`; secondo screenshot utente risposta `{"status":"d1_write_ok","record_found":1,"new_rows":0,"synthetic":true}`.
- [x] Confermata **lettura del record di test dal Worker Preview**, senza duplicazione nell'ultima richiesta. `new_rows:0` significa che l'ultima invocazione non ha creato una nuova riga; la presenza del record è coerente con precedente invocazione Preview. **Non attribuire con certezza il momento della prima scrittura** senza ulteriore verifica.
- [ ] Priorità: **rimuovere la modifica temporanea non autenticata dall'editor e uscire senza Deploy/Save**, mantenendo Hello World pubblico.
- [ ] Confermare nella console D1 TEST mediante SELECT sulla chiave la presenza e i metadati `LAB:TEST_ONLY`, poi eliminare solo tale riga di prova con consenso e verifica; controllare che D1 principale rimanga senza eventi.
- [ ] Non abilitare `INGEST_ENABLED=true`, heartbeat TradingView o ordini; non modificare altri Worker/filoni A/B/C. PR #102 resta DRAFT/OPEN senza merge.

## CHECKPOINT D1 TEST SCHEMA VERIFICATO — 12/11/2026, ore 15:51 CET
- [x] Creato manualmente dall'utente database D1 isolato `remura-tv-lab-test`, giurisdizione **The European Union**, region **Eastern Europe**, read replication Disabled (screenshot).
- [x] Esecuzione SQL su D1 Studio: una tabella `tv_flow_events` e due indici `idx_tv_flow_events_received`, `idx_tv_flow_events_symbol_close`, lanciando un comando per volta.
- [x] Controllo `sqlite_master` restituisce esattamente 3 righe: tabella + due indici (screenshot 12/11/2026).
- [x] Ultime quote D1 mostrate dall'utente prima della creazione: 1/10 database, 28,67 kB/5GB, 0/5M letture e 0/100k scritture (aggregati dashboard arrotondati). **Non è una misura dopo la creazione**.
- [ ] Test reale di scrittura dal Worker **non ancora svolto**; nessun evento prospettico TradingView confermato. Evitare endpoint diagnostici pubblici e garantire che il database di prova, non quello principale, sia l'unico target.
- [ ] Prossima azione: predisporre Worker di prova separato con binding D1 test e provare solo in preview controllata. Non modificare worker produttivo `remura-tv-ingest-lab`; ricezione `INGEST_ENABLED` resta disattivata. Nessuna PR merge, nessun ordine automatico.

## CHECKPOINT PROVA D1 IN PREVIEW — 12/11/2026, ore 13:22 CET
- [x] Utente ha creato localmente su iPhone un token forte e digest SHA-256; i valori NON sono stati condivisi in chat o nel repository. Dalla UI Cloudflare risulta un secret in Production. La correttezza del valore non è ancora verificata end-to-end.
- [x] Dopo aggiunta secret e deploy isolato del Worker, controlli LIVE: GET `/health` → `{"status":"lab_only","accepting":false}`; GET `/` → `{"status":"disabled"}`. Ingestion ancora OFF; nessun alert TradingView.
- [x] Console D1 `remura-tv-lab`: `SELECT COUNT(*) AS totale_eventi FROM tv_flow_events` → **0** eventi alle 13:01 CET del 12/11/2026 (screenshot utente). Questo prova lettura nella Console D1, non una scrittura Worker.
- [x] Editor Cloudflare: patch `ignoreBOM:false` presente; prova temporanea GET `/__lab_d1_probe` **solo in Preview** con `SELECT COUNT(*)` ha restituito `{"status":"d1_ok"}` secondo l'utente. Verifica accesso di lettura D1 dal Worker nella sessione Preview, **non conferma la scrittura né necessariamente l'identità dell'ambiente DB Production**.
- [x] Codice della diagnostica `/__lab_d1_probe` rimosso dall'editor e screenshot verificato; utente ha chiuso l'editor. Nessun deploy della diagnostica autorizzato o riferito.
- [x] PR #102 verificata DRAFT/OPEN tramite GitHub prima di questo aggiornamento, senza merge.
- [ ] **Prossimo passaggio**: prova scrittura D1 solo su database isolato di staging/Preview, oppure altra procedura esplicitamente approvata, senza contaminare `remura-tv-lab`. La documentazione Cloudflare segnala che Preview con binding D1 allo stesso database ID condivide i dati: non assumere isolamento automatico. Prima verificare quota Free reale e binding Previews Base.
- [ ] Non abilitare `INGEST_ENABLED=true`, webhook TradingView, heartbeat o ordini; non toccare filoni A/B/C o gli altri Worker.

## CHECKPOINT WORKER LIVE MA FAIL-CLOSED — 12/11/2026 10:55 CET
- [x] Due screenshot utente confermano Worker `remura-tv-ingest-lab.mirkoworz.workers.dev` con ricevitore REMURA v0.8.5 distribuito.
- [x] GET `/health` restituisce esattamente `{"status":"lab_only","accepting":false}`:
  Worker raggiungibile e flag ingestion OFF.
- [x] GET `/` restituisce `{"status":"disabled"}`: protezione predefinita fail-closed confermata live.
- [x] Binding Cloudflare D1 `TELEMETRY_DB` → `remura-tv-lab` confermato in precedenza dalla UI; schema tabella + due indici confermati con query di lettura, giurisdizione UE verificata.
- [ ] **Non ancora provata** una lettura/scrittura D1 effettuata DAL Worker, né una consegna webhook:
  `/health` e `/` non interrogano D1. Non dichiarare pipeline funzionante end-to-end.
- [ ] Prima di permettere acquisizione: predisporre segreto forte sul Worker senza inviarlo in chat/GitHub,
  controllo IP, test sintetico senza dati di mercato, riscontro D1 e quota CPU;
  fino ad allora `INGEST_ENABLED` deve restare assente/false.
- [ ] Alert Pine/TradingView e heartbeat restano disattivati, nessun dato prospettico reale.
- [ ] Filoni A/B/C intatti, nessun merge/deploy REMURA app né ordine di trading.


**PR #102 DRAFT/OPEN — NESSUN MERGE O WEBHOOK TRADINGVIEW.**

## CHECKPOINT PATCH EDITOR CLOUDFARE — 12/11/2026 10:52 CET
- [x] Utente ha copiato nell'editor Cloudflare il receiver del branch di ricerca.
  Screenshot del Worker `remura-tv-ingest-lab` mostra errore del
  typechecker `ts(2345)` in `new TextDecoder("utf-8", { fatal: true })`,
  perché il tipo `TextDecoderConstructorOptions` di Workers richiede
  la proprietà `ignoreBOM`.
- [x] [Receiver PATCH v0.8.5](gateway-lab/worker.mjs): sostituito con
  `new TextDecoder("utf-8", { fatal: true, ignoreBOM: false })`.
  Nessuna modifica al contratto JSON Pine `0.8.1-lab`,
  all'autenticazione o al fail-closed.
- [x] Utente ha aggiornato il decoder, confermato l'assenza di errori
  nell'editor e distribuito il Worker; health e disabled verificati con screenshot.
  La patch di tipo è quindi verificata nel codice distribuito.
- [x] Ricevitore v0.8.5 distribuito in produzione del SOLO Worker isolato,
  ma `INGEST_ENABLED` è OFF (risposte health e root). Segreti/config
  autenticazione e accesso reale D1 non ancora verificati: non attivare eventi.
- [ ] Risultato CI GitHub per commit patch da verificare.



**PR #102 DRAFT/OPEN — NO MERGE, NO ORDINI, NO WEBHOOK TRADINGVIEW.**

## CHECKPOINT WORKER CLOUDFARE — 12/11/2026 10:43 CET
- [x] L'utente ha creato e distribuito un Worker Cloudflare separato:
  `remura-tv-ingest-lab`, e ha aperto l'editor. Screenshot mostra soltanto
  il programma standard **Hello World**, non il receiver REMURA.
- [x] Nessun collegamento D1, secret, alert o invio dati è stato verificato;
  il Worker Hello World è pubblicato e non memorizza dati di mercato.
- [x] Confermate le istruzioni ufficiali Cloudflare per collegare un D1:
  pagina del Worker → tab `Bindings` → `Add binding` → `D1 database`.
- [x] **Binding D1 salvato e verificato dallo screenshot Cloudflare**:
  Worker `remura-tv-ingest-lab` → tipo D1 database → variabile
  `TELEMETRY_DB` → valore `remura-tv-lab`; confermato in Settings / Bindings.
  Non toccati `mirko-news-calendar` o `telegram-mirko-bridge`.
- [ ] **Prossimo step**: installare nell'editor SOLO il codice
  `tradingview/delta-peaks/gateway-lab/worker.mjs` dal branch della PR #102,
  con `INGEST_ENABLED` **assente** (runtime variables ancora vuote nello
  screenshot). Il ricevitore deve restare `fail-closed` e `/health` deve
  rispondere `{"status":"lab_only","accepting":false}`; il root endpoint
  dovrebbe restituire 503 (`disabled`). Codice Hello World attuale non
  memorizza dati; evitare webhook/segreti fino a test successivo.
- [ ] Eseguire test HTTP non distruttivi del Worker in isolamento e verificare
  le quote, poi affrontare autenticazione e attivazione controllata.
- [ ] Dopo binding verificato, sostituire Hello World con
  `gateway-lab/worker.mjs` SOLO in stato **INGEST_ENABLED assente/false**.
  Testare endpoint read-only /health, configurare sicurezza e
  secret in passaggi distinti; nessuna acquisizione reale senza autorizzazione.
- [ ] Ricontrollare limite Free dopo deployment del receiver, e test
  locali senza dataset reale.



**PR #102 DRAFT/OPEN — NO MERGE, NO DEPLOY, NO WEBHOOK, NO ORDINI.**

## CHECKPOINT D1 UE CONFERMATO — 11/11/2026 18:37 CET
- [x] Screenshot Cloudflare D1 Settings del database ricreato dall'utente:
  **Jurisdiction = The European Union**, **Region = Eastern Europe**,
  **Read replication = Disabled**. Verificata la giurisdizione europea dopo
  sostituzione del precedente DB senza giurisdizione.
- [x] **Nome D1 verificato nella foto della Console: `remura-tv-lab`.**
  Il suffisso `-eu` non è necessario: la giurisdizione UE è già confermata
  dalla schermata Settings. Nessuna nuova creazione/rinomina necessaria.
- [x] **SQL schema D1 eseguito dall'utente nel database `remura-tv-lab`**:
  screenshot Console mostra le tre istruzioni `CREATE TABLE IF NOT EXISTS`
  e `CREATE INDEX IF NOT EXISTS` e il messaggio
  `This query successfully executed` (11/11/2026).
- [x] **Schema D1 verificato mediante query readback in Cloudflare Console**:
  screenshot con risultato SQL di `sqlite_master` mostra esattamente
  la tabella `tv_flow_events` e gli indici `idx_tv_flow_events_received`
  e `idx_tv_flow_events_symbol_close` nel DB `remura-tv-lab`.
  La tabella è pronta, ma nessun invio dati TradingView è ancora attivo.
- [ ] Passaggio successivo: creare un Worker **dedicato e isolato**, senza
  toccare `mirko-news-calendar` o `telegram-mirko-bridge`; verificare
  la modalità di creazione nell'interfaccia prima di distribuirlo.
  Codice receiver `gateway-lab/worker.mjs` è fail-closed, richiede D1,
  secret hash e abilitazione esplicita; nessun webhook Live prima dei test.
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
