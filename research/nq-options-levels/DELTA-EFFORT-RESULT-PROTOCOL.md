# REMURA — DELTA PROFILE / EFFORT vs RESULT
**Checkpoint ricerca v0.5 — 10 novembre 2026, sera italiana.** NO LIVE · NO costi · PR #101 DRAFT.

## Evidenza diretta del trader (riferita dall'utente, chat 10/11/2026 ore 21:15–21:18)
- "Noi guardiamo i picchi di delta".
- "Tipo il delta week in base allo sforzo e risultato".
- Profili menzionati: "Current montly", "Previus montly", "Week", "Montly".
- "Ma di base tutti i delta current / Li usiamo in base allo sforzo che c e".

**Priorita' aggiornata:** Delta per livello di prezzo su profili temporali, con interpretazione price response; le precedenti GEX/OI/Expected Move sono **ipotesi declassate**, non da escludere come possibili filtri. Evitare di affermare che tutte e sei le zone derivino necessariamente da un solo tipo di picco o che siano segnali long/short.

## Terminologia e calcolo
- `Delta(p,periodo) = AskVolumeAggressivo(p) - BidVolumeAggressivo(p)` se il provider definisce Ask/Bid come aggressione correttamente etichettata. Non dedurre dal semplice OHLCV o da tick-volume forex.
- Delta per prezzo differisce da CVD temporale. Cerca massimo **positivo**, minimo **negativo** e massimo **assoluto**, etichettandoli separatamente; `argmax(Delta)` e `argmax(|Delta|)` non sono la stessa cosa.
- **Current week e current month** mutano durante il periodo. **Previous month** resta chiuso, salvo correzioni del provider. Il generico `Monthly` necessita conferma della selezione/ancora. ATAS documenta ufficialmente `FixedProfilePeriods` tra cui CurrentWeek, LastWeek, CurrentMonth, LastMonth, Contract: https://docs.atas.net/api/ATAS.Indicators.FixedProfilePeriods.html
- ATAS `Volume Profile & TPO` permette `Profile=Delta` / `Delta V2` / `Bid and Ask` e `Max Level Type=Delta`, `Positive Delta`, `Negative Delta`. **Non** assumere dalla foto una selezione effettiva senza preset. https://help.atas.net/it/support/solutions/articles/72000602305-volume-profile-tpo

## Sforzo vs risultato (definizione sperimentale, non formula del trader)
- **Sforzo**: Delta firmato e volume aggressivo eseguito presso un prezzo/intervallo in una finestra temporale definita ex-ante; misurare sia intensita' sia segno.
- **Risultato**: variazione del prezzo *successiva o simultanea* riferita alla stessa finestra osservata, mai con quote future per assegnare il livello di prima.
- Delta molto negativo e prezzo che non riesce a scendere (o molto positivo e prezzo che non riesce a salire) e' **compatibile con assorbimento**, ma puo' riflettere anche altri processi; richiede osservazioni successive e criteri falsificabili. Delta alto con forte avanzamento e' scenario differente.
- Non utilizzare un rapporto spurio |Delta|/|move| in presenza di movimento nullo senza gestione robusta e preregistrazione. Evitare ottimizzazione post-hoc delle soglie sul 10/11.
- Non attribuire le aggressioni osservate a soggetti "istituzionali" nominati: nei trade prints standard manca l'identita' dell'esecutore.

## Dataset richiesto per una riproduzione autentica
- Contratto/roll esplicito NQ, exchange-time, ID della sorgente, timestamp trade e timestamp locale di prima ricezione, `price`, `volume`, `aggressorSide` o due campi bid/ask trade volume attestati.
- Period boundaries dell'Exchange (CME/Chicago e sessione specificata), per evitare che `week` o `month` in UTC non corrispondano ad ATAS. Servono informazioni su session template, timezone e profilazione/deduplicazione, correzioni e tick size (NQ: 0.25).
- Per ogni snapshot: `as_of` prima delle zone mattutine, SHA immutabile e prova di first-seen. **Non** backfill delle correnti usando delta di fine seduta.
- Per Effort vs Result: sequenza temporale intraperiodo, percorso prezzo, volume aggressivo. Un solo istogramma finale non prova assorbimento quando la zona fu segnata.
- Prezzi broker FXCM M5, tick volume e CVD stimati non sostituiscono il tape futures NQ bid/ask.

## Protocollo esecutivo futuro, senza spesa
1. **Catalogare indicatori/settings ATAS**: Screenshot soltanto delle configurazioni `Profile Type`, `Max Level Type`, timeframe/periodo CurrentWeek, CurrentMonth, PreviousMonth, ore/sessione e CVD Multi; evitare dati account.
2. **Raccogliere accesso lecito ai dati**: priorita' a fonte futures NQ aggressor-classified a basso costo/gratuita; non promettere tape storico free o CME dati veri senza verificare licensing/delay/quote.
3. **Calcolo offline e reversibile**: costruire `delta_by_price` per periodo e salvare picchi positivi/negativi con timestamp di disponibilita', nessuna decisione o segnale automatico.
4. **Studio prospettico**: fissare prima distanza, finestre e definizione di "reazione" (e prezzo di invalidazione), confrontare su sessioni indipendenti contro baseline price-profile/round levels/casuale e segnali senza Delta. Stop-lookahead, survivorship e cherry-picking; costi/esecuzione veri prima di qualsiasi net PnL.
5. Confronto GEX/OI solo come **ipotesi secondaria separata**; non etichettare una zona Delta come Gamma Wall senza evidenza.

## Stato sicurezza / costi
- **Non abbiamo ancora dati tick NQ con lato aggressore**, quindi il modello non puo' produrre livelli nuovi verificabili. Nessuna richiesta di feed, job, scraping, deploy, ordinazione o abbonamento.
- Nessuna prova di vantaggio statistico, predizione di movimenti istituzionali o riproduzione esatta della logica privata del trader.
- Ramo `research/nq-options-levels-20261110`, PR #101 DRAFT, nessun merge; Track B #89 e A/C intatti, REMURA LIVE invariata.
