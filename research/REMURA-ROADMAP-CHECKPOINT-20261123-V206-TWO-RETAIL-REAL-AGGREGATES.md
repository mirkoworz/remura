# REMURA — CHECKPOINT V20.6: real cross-provider RETAIL sentiment
**Aggiornamento: 23 novembre 2026, ore 08:34 CET — Europe/Rome.**

**Ambito:** ricerca isolata in branch research/remura-v206-two-retail-independent-snapshot-audit-20261123, creata da V20.5. Nessun merge in main, deploy, variazione Oracle/Mac/cTrader/collector o intervista a Cloudflare, D1, Workers, Capital API, Myfxbook API o Secrets. Eredita integralmente roadmap V01–V20.5.

## Progressi reali verificati in questo turno
### 1. Compatibilita' col database prezzi cTrader privato (codice, NON dato)
- Il repository pubblico MAIN contiene i moduli reali scripts/price_feed.py e scripts/price_store.py: il database SQLite conserva il payload EURUSD con campi symbol, provider=ctrader, providerSymbol, timeframes.M15, timestamp t in UTC con Z e OHLC o,h,l,c.
- Il lettore di ricerca V20.4 research/v204_private_cvd_price_coverage.py richiede esattamente questi campi: **compatibilita' a livello di schema confermata**. Non c'e' necessita' di modificare il collector Mac. Le 12 ricevute M5 CVD TEST del 23/11 equivalgono a 4 potenziali istanti M15, che restano non direzionali.
- L'ultima reale diagnostica VPS pubblicata su GitHub repo privato e' workflow run 44765941152 il **20/11/2026**; mostrava PREZZI_COLLECTOR=running e ultimo open EURUSD M15 20/11 14:45Z, ma **NON dimostra lo stato del 23/11**. Non sono stati avviati workflow di diagnostica o chiamati endpoint VPS in questo turno.

### 2. Primo confronto incrociato di DUE POPOLAZIONI RETAIL, realmente osservate
Due file letti in RAM dal connettore GitHub, **nessun ulteriore fetch verso i provider**:
- Myfxbook Community Outlook PUBBLICO, commit main fissato a1188f8af77951b9c59b7bb1facbfa6fe2f820e7, snapshot 2026-11-23T02:55:17Z, 89 simboli.
- Capital.com Client Sentiment DEMO PRIVATO, metrica client_positions, commit main fissato a4fd286439007fc9620904f7f20c3c018425f29c, snapshot 2026-11-23T02:53:02Z, 31 simboli.
- Differenza oraria snapshot **135 secondi**, analisi dei soli ticker identici presenti in entrambe le fonti (29); 2 simboli Capital non avevano controparte Myfxbook.
- **24/29** coppie condividono la stessa PREVALENZA long/short, **5/29 prevalenze contrarie**: 20 entrambi maggioranza long, 4 entrambi maggioranza short, 2 Myfxbook long/Capital short, 3 Myfxbook short/Capital long; zero esatti 50%.
- Differenza assoluta della percentuale long tra provider: media **16.20** punti percentuali, mediana **19.20**. Almeno 10pp in 18 mercati, almeno 20pp in 10, almeno 30pp in 4, almeno 40pp in 1. Entrambi estremo >=70% long o <=30% long in 7; estremi contrari 0.
- Le popolazioni, i denominatori e le metriche NON sono equivalenti; una divergenza retail non prova passaggio di denaro istituzionale, ne' una operazione contraria utile. Non dedurre 82,8% di successo da 24 prevalenze concordi.
- **Privacy:** NON pubblicati ticker Capital, righe Capital originali, % individuali private, log di broker, account, token o credenziali. Il report salvato nel repository pubblico contiene SOLO aggregati.

### 3. Codice replicabile pronto e nuovi test completati
- Script di ricerca research/v206_two_retail_snapshot_audit.py, versione aggregata: accetta due file JSON LOCALMENTE (Myfxbook PUBBLICO + Capital PRIVATO) e restituisce soltanto i conteggi, distribuzioni e intervalli di divergenza. Rigetta identita' provider false, metriche non client_positions, demo/live mix, orari non sincronizzati entro 10 minuti, symbol illegali, valori NaN/fuori 0..100, percentuali non complementari e timestamp individuali non coincidenti con i rispettivi snapshot. Nessuna chiamata a broker o reti.
- Nuovi test SOLO di questo script research/test_v206_two_retail_snapshot_audit.py: **6 nuovi test**.
- Workflow CI soltanto sul ramo di ricerca: .github/workflows/remura-v206-two-retail-private-safe.yml. NON scarica file Capital, nessun Secret. GitHub Actions https://github.com/mirkoworz/remura/actions/runs/45131720078 : SUCCESS per **6 test sintetici del programma**. **Non dichiarare che questo CI pubblico abbia letto i dati Capital:** l'analisi REALE dei due snapshot e' stata fatta separatamente dal connettore GitHub autorizzato, mentre il CI prova il nuovo codice con fixture sintetiche.
- Il risultato REALE e' stato conservato come JSON su research/real-proofs/REMURA-V206-TWO-RETAIL-SNAPSHOT-20261123-AGGREGATES-ONLY.json; source commit e timestamp documentati. Non contiene valori privati per simbolo.

## Situazione scientifica: non attribuire successo inesistente
- La fonte CFTC TFF istituzionale V20 del 17/11 (pubblicata 20/11) resta distinta dai dati retail, e ha gruppi Asset Managers e Leveraged Funds spesso divergenti. Nessuna ipotesi su chi anticipa il prezzo e' stata confermata dai 29 confronti.
- CVD D1 TEST 12/12 ricevute nell'unica finestra interrogata con autorizzazione proprietario, ma radar 12 OBSERVATION_ONLY, 0 segnali operativi e 0 esiti futuri. Non fare altre query Cloudflare con la precedente autorizzazione consumata.
- Prezzi M15 cTrader reali del 23/11 non ancora visti: non sappiamo la completezza del 60m/H4/24h. Il dataset BCE quotidiano del 20/11 non sostituisce prezzi intraday.
- I campioni dei due fornitori sono concentrati nello stesso istante e su mercati FX collegati, quindi NON 29 esperimenti indipendenti. Non suggerire operazioni e non dichiarare alpha.

## Roadmap prossima priorita'
1. Appena un accesso Mac/VPS e' esplicitamente disponibile e non interferisce con Codex, localizzare il percorso del DB prezzi privato e invocare il lettore V20.4 **in sola lettura** con l'aggregato delle 12 ricevute, senza token, nuove scansioni, import o upload dei prezzi. Riportare solo 4 possibili finestre M15 e completezza a 60m/H4/24h.
2. Prima di eseguire nuovi test prospettici di rendimento, definire decisioni CVD per barra, prima conoscenza, prezzo indipendente, benchmark price-only allineato, controlli per sessione e spread/slippage. L'aggregato 29 retail e' una baseline descrittiva, non una entry strategy.
3. Conservare archivio Myfxbook reale V20.5 5.334 record (+1.410 ex-rolling) su ramo ricerca, gia' attestato GitHub run 45124731092. Retention automatica append-only richiede variazione produzione autorizzata; niente nuovi workflow API.
4. Contributors: Workers e D1 dashboard Free verificati 23/11; Access seats, Billing e JWT/ownership/revoca reali ancora NO-GO. Non registrare amici o assegnare permessi senza autorizzazione distinta.
5. Rilascio controllato Cockpit v1.68 LAB/TradingView LAB/Contributors LAB, Splash Toro-Orso, Mac v1.65; NON sovrapporsi a Codex. Se si aggiornano pagine HTML per una reale release, versione incrementata e timestamp Europe/Rome in alto.
6. Controllare periodicamente consumi GitHub Actions/Cloudflare Free, senza interrogazioni remote nuove a meno di consenso.

## Custodia e costi
Nessun nuovo abbonamento, database, Secret, deploy, merge, modifica Mac o Oracle. GitHub Actions ha eseguito una breve CI pubblica su un ramo research; Capital personale e' rimasto nel repo PRIVATO. Non pubblicare file Capital per rendere il CI piu' comodo.

**Verdetto V20.6:** abbiamo ora una prima misura incrociata su 29 mercati di due feed retail realmente presenti, oltre alle 12 ricevute CVD autentiche e ai 5.334 record storici Myfxbook salvati. Le metriche di previsione futura istituzionale non sono ancora validate.
