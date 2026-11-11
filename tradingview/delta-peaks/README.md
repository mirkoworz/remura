# REMURA — Order Flow Radar & Footprint Premium LAB v0.5
**Aggiornamento documentazione v0.5: 11/11/2026, ore 12:48 CET**

> Laboratorio nella PR **#102 DRAFT**. Nessun merge, deploy o impatto sui filoni A/B/C.

## CHECKPOINT VISIVO v0.5 — 11/11/2026, ore 12:48 CET

**Prova FOOTPRINT su FXCM:EURUSD a 5 minuti: superata per caricamento/UI e dati visibili.**
La fotografia dell'utente mostra il nome `REMURA Order Flow Radar Premium LAB v0.5` sul grafico e il pannello `REMURA PREMIUM FLOW v0.5` con `DATI FOOTPRINT = PRESENTI`. Il grafico stesso e' configurato come **Footprint volume nativo di TradingView**: le celle bid/ask colorate vengono da quella visualizzazione, non sono disegnate dal nostro Pine. Il nostro Pine mostra invece il pannello.

Campione **LIVE/PROVVISORIO** osservato: BUY stimato **92**, SELL stimato **109**, delta **-17**, Delta/Vol circa **-8,5%**, conteggio imbalance BUY=**0**, SELL=**0** e ER stimato **NORMALE**. POC e Value Area sono valorizzati. Sono valori transitori: NON sono un risultato della sessione, non equivalgono a contratti CME e non dimostrano vantaggio statistico.

**Da verificare separatamente:** selezione della vista `RADAR` dallo stesso indicatore v0.5, ricalcolo dopo chiusura candela e differenza tra delta della libreria intrabar e footprint nativo. Non modificare ancora i segnali ER per includere POC/imbalance.

Prossima fase: definire il protocollo di misurazione ER **15/30/60 minuti** senza lookahead, su barre confermate e con benchmark; non confondere test visivo con misurazione di predittivita'.

## COPIA SU TRADINGVIEW
**[Codice Pine v0.4](REMURA-Delta-Peaks-LAB.pine)**: aprilo su GitHub, premi **Raw**, copia tutto da `//@version=6` e sostituisci il codice nel **Pine Editor** su **FXCM:EURUSD, 5 minuti**. Salva e Aggiungi al grafico; togli le vecchie istanze per non sovrapporre gli indicatori. Il titolo corretto sara' **REMURA Order Flow Radar LAB v0.4**.

## NOVITA' RADAR
| Colore | Significato |
| --- | --- |
| Verde | Delta stimato positivo, pressione classificata positiva |
| Rosso | Delta stimato negativo, pressione classificata negativa |
| Giallo | Sforzo relativo alto (fascia intensita' 3/5) |
| Arancione | Picco relativo di delta, sopra la soglia e fuori dal gap |
| Viola | Bassa efficienza Sforzo/Risultato su un picco (ER+/ER-) |
| Grigio | Dati insufficienti, non classificabili |

L'intensita' **1/5 — 5/5** dipende dal rapporto tra delta corrente e media dei delta assoluti precedenti. Soglie: **1x, 2x, 3.5x, 5x**. Non e' una probabilita' di successo ne' la quota di reali contratti acquistati/venduti.

### Due stati fondamentali
- **LIVE / PROVVISORIO**: candela ancora aperta. Delta, colori, sforzo, efficienza e una possibile ER cambiano finche' arrivano nuovi dati. Non sono segnali confermati.
- **CHIUSA / OK** oppure **STORICO / CHIUSO**: candela terminata. Solo allora il codice genera i marcatori ER+/ER-/D+/D-, aggiorna il registro eventi e soddisfa le condizioni degli alert. Se vuoi creare un alert TradingView, preferisci **una volta per chiusura candela**.
- La riga **ANOMALIA** e' **provvisoria mentre il grafico segnala LIVE**.
- Il registro **Ultimo #1, #2, #3** conserva solo i tre **picchi confermati**, etichettati D+/D-/ER+/ER-, ora di **apertura** della candela nel fuso **Europe/Rome** e Sforzo x. Include anche picchi normali, non soltanto ER.

### Impostazioni
- **Mostra radar colorato**: mostra/nasconde il pannello.
- **Mostra gli ultimi 3 eventi**: mostra/nasconde lo storico nella tabella.
- **Colora candele anomale (anche LIVE)**: disattivato per default per non sovrascrivere i colori di altri indicatori. Se attivato, la candela aperta puo' cambiare colore e tornare normale alla chiusura.
- **Mostra anche D+/D-**: disattivato per default per mantenere il grafico pulito.

## FORMULE PRESERVATE
1. Sforzo = `|deltaBar| / SMA(|deltaBar| delle 30 barre precedenti)`.
2. Risultato = `sign(deltaBar) * (close - open) / ATR(14)`.
3. Efficienza = `Risultato / Sforzo`.
4. ER = picco sopra `3.5x`, efficienza minore o uguale a `0.07`, separazione minima di **6 barre**, barra **confermata**.
5. WEEK / CURRENT MONTH / PREVIOUS MONTH: ancora massima candela per delta assoluto nel periodo disponibile al prezzo `hl2`. Non equivale al prezzo di esecuzione istituzionale.

## STATO VERIFICHE
- **v0.3**: screenshot dell'utente mostra grafico funzionante EURUSD FXCM M5.
- **v0.4**: codice aggiornato su GitHub, controlli statici interni superati. **Non ancora compilata o osservata LIVE sul Pine Editor**. Per il prossimo passo mandare due schermate, una durante la candela e una alla sua chiusura.
- Il feed FXCM Forex puo' usare tick volume. Il delta da `TradingView/ta/14` e' una stima intrabar, **non un footprint bid/ask del CME**, e gli ER non sono ordini BUY/SELL validati.
- Nessuna nuova API, server o abbonamento; nuovi costi REMURA **zero**. Disponibilita' di dati intrabar/alert soggetta al piano TradingView.

## NUOVO: RADAR + FOOTPRINT UNIFICATI — v0.5 PREMIUM (11/11/2026, 12:40 CET)

**Test Premium sulla foto del 11/11/2026: SUPERATO lato compilazione e dati.** Sul grafico `FXCM:EURUSD` 5m la PROBE mostra `DATI PRESENTI`, buy **16**, sell **23**, delta **-7**, POC circa **1.11335**, VAH **1.11340**, VAL **1.11330**, 0 righe BUY imbalance e 1 riga SELL imbalance. I dati sono della candela LIVE, pertanto provvisori.

A questo checkpoint e' stato aggiunto **[REMURA-Order-Flow-Radar-Premium-v0.5.pine](REMURA-Order-Flow-Radar-Premium-v0.5.pine)**, SENZA sovrascrivere il Radar v0.4 o la PROBE. E' un file alternativo che conserva i calcoli ER e permette di scegliere nel suo unico pannello:

- `Vista pannello = FOOTPRINT` (default): BUY/SELL classificati, delta e delta/volume %, POC (centro riga), VAH/VAL, numero di righe BUY/SELL imbalance, indicazione ER e rapporto Sforzo/Efficienza.
- `Vista pannello = RADAR`: pannello v0.4 originale con pressione verde/rossa, intensita', anomalie ER e ultimi tre eventi.
- `Mostra POC come punti` default **OFF**: se acceso disegna solo il POC delle candele chiuse. Non e' un punto di entrata automatica.

### Come testare la v0.5
1. Apri il nuovo file, premi **Raw**, copia tutto e incolla in un nuovo indicatore Pine su FXCM:EURUSD M5.
2. Per evitare due pannelli sovrapposti sul grafico, rimuovi temporaneamente le istanze separate di Radar v0.4 e Premium Probe.
3. Controlla che **FOOTPRINT** visualizzi dati e che scegliendo **RADAR** nelle impostazioni compaia il vecchio pannello.
4. Invia uno screenshot delle due viste, con eventuali messaggi di compilazione o runtime.

La v0.5 ha superato solo controlli statici di integrita' su GitHub; **non risulta ancora compilata sul Pine Editor**. I tre `alertcondition` esistenti si basano **solo** su delta stimato e ER, NON sul footprint. Nessun ordine, webhook, merge o deploy.

Il footprint FXCM proviene dalla classificazione direzionale di dati intrabar, **non** dall'identificazione delle controparti istituzionali e neppure dal book completo CME. Una differenza tra delta `requestVolumeDelta()` e delta `request.footprint()` non e' di per se' un errore: aggregazione e granularita' possono differire.

Il piano Premium e' gia' posseduto dall'utente: nessun nuovo abbonamento necessario per questa prova. Le eventuali quotazioni real-time CME restano una questione separata.

## ESPERIMENTO NUOVO: FOOTPRINT NATIVO CON PREMIUM (11/11/2026, 11:58 CET)

Ora che il piano dell'utente e' **TradingView Premium**, e' disponibile anche [REMURA-Footprint-Premium-Probe.pine](REMURA-Footprint-Premium-Probe.pine), test autonomo su `request.footprint()` (non modifica il Radar v0.4).

Il file mostra **BUY/SELL categorizzati, delta footprint, POC (centro della riga), VAH, VAL e numero di righe con imbalance BUY/SELL**. Usa un'unica richiesta footprint come da limiti Pine, con 10 tick per riga e sbilanciamento 300% predefiniti. Nessun alert/ordine/trasmissione a REMURA.

Per provarlo: su `FXCM:EURUSD` 5m aprire il nuovo file GitHub → **Raw** → copia nel Pine Editor e Aggiungi al grafico. Il radar v0.4 puo' restare installato, ma inizialmente e' meglio provarlo da solo per non confondere i pannelli. Il nuovo pannello e' in alto a sinistra.

**Verifica critica:** se il footprint restituisce N/D, non attribuire BUY/SELL inesistenti; verificarne disponibilita' sul simbolo, sul timeframe e sul piano. Il dato FXCM puo' essere tick volume e la distinzione BUY/SELL si basa sulla direzione intrabar, non su contratti CME/identita' dei trader.

**Stato:** file caricato, **compilazione Pine e presenza di dati FXCM ancora da verificare sul grafico**. Non sostituiamo la v0.4 finche' questa prova non passa.

Fonti: [Footprint Pine](https://www.tradingview.com/pine-script-docs/concepts/other-timeframes-and-data/#requestfootprint), [Guida Footprint](https://it.tradingview.com/support/solutions/43000726164/).

## DOPO IL TEST
Passare alla **misura 15, 30, 60 minuti post-ER**, con MFE/MAE in ATR, benchmark e registrazione anche dei falsi positivi. Va ancora confrontata la definizione dei livelli Week/Monthly col metodo originale del collaboratore.

**[Roadmap v0.4](ROADMAP.md)** · [Documentazione tabelle Pine](https://www.tradingview.com/pine-script-docs/visuals/tables/) · [Bar states](https://www.tradingview.com/pine-script-docs/concepts/bar-states/).
