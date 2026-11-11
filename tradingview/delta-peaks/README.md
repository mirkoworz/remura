# REMURA — Order Flow Radar LAB v0.4
**Aggiornamento: 11/11/2026, ore 11:26 CET**

> Laboratorio nella PR **#102 DRAFT**. Nessun merge, deploy o impatto sui filoni A/B/C.

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

## DOPO IL TEST
Passare alla **misura 15, 30, 60 minuti post-ER**, con MFE/MAE in ATR, benchmark e registrazione anche dei falsi positivi. Va ancora confrontata la definizione dei livelli Week/Monthly col metodo originale del collaboratore.

**[Roadmap v0.4](ROADMAP.md)** · [Documentazione tabelle Pine](https://www.tradingview.com/pine-script-docs/visuals/tables/) · [Bar states](https://www.tradingview.com/pine-script-docs/concepts/bar-states/).
