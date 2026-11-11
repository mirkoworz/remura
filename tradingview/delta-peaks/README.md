# REMURA TradingView — Delta Peaks LAB v0.3
**Aggiornamento documentazione v0.3: 11/11/2026, ore 09:39 CET**

> Solo laboratorio: PR #102 DRAFT. Nessun merge, deploy, ordine o collegamento automatico al motore REMURA live.

## CODICE DA COPIARE
Apri [REMURA-Delta-Peaks-LAB.pine](REMURA-Delta-Peaks-LAB.pine) → **Raw** → copia il testo integrale → incolla nel **Pine Editor** di TradingView.

Usa **FXCM:EURUSD — timeframe 5 minuti**; timeframe intrabar predefinito **1 minuto**. Salva, aggiungi al grafico, rimuovi le vecchie istanze v0.1/v0.2 e verifica il titolo **LAB v0.3**.

## NUOVI CALCOLI S/R (SFORZO / RISULTATO)
Il delta stimato e' il valore di uscita della libreria TradingView `ta/14`, `requestVolumeDelta("1", timeframe.period)`; non e' il tape completo CME.

A ogni candela chiusa:

1. **Sforzo relativo**: `effort = abs(delta) / SMA(abs(delta[1]), 30)`. Il denominatore comprende le 30 candele precedenti, non quella corrente.
2. **Risultato orientato al delta**: `signedResult = sign(delta) * (close - open) / ATR(14)`. E' positivo quando il corpo segue il segno del delta, negativo quando va in senso opposto.
3. **Efficienza S/R**: `efficiency = signedResult / effort`. Piccola o negativa significa movimento direzionale modesto/opposto rispetto alla pressione stimata. Non e' una misura dell'assorbimento reale, ne' la probabilita' di inversione.

**Regola di base di v0.3**: un evento `ER+` o `ER-` appare quando `effort >= 3.5`, `efficiency <= 0.07`, la candela e' confermata e sono passate piu' di **6 barre** dall'ultimo picco rilevato. I valori soglia sono **parametri sperimentali**, non ottimizzati sui dati o validati.

- **ER+ arancione sopra la candela**: pressione stimata positiva con basso risultato, non automaticamente SELL.
- **ER- azzurro sotto la candela**: pressione stimata negativa con basso risultato, non automaticamente BUY.
- **D+/D-** facoltativi, disattivati di default per mantenere il grafico pulito.
- Dashboard mostra Delta, Sforzo x, Risultato ATR, Efficienza ER, WEEK, CURRENT MONTH, PREVIOUS MONTH.
- Le tre linee dei livelli restano quelle originali: **massimo delta assoluto della singola candela** per periodo disegnato su **hl2**, non su prezzo di esecuzione istituzionale.

### Esempi numerici di controllo
Assumiamo media |delta| precedente = **500**, ATR = **10 pips**, soglia **0.07**, distanza minima rispettata.

| Delta | Corpo prezzo | Sforzo | Risultato | Efficienza | Evento |
| ---: | ---: | ---: | ---: | ---: | :--- |
| +2.400 | +2 pips | 4,8 | +0,20 | +0,0417 | ER+ |
| -2.400 | +2 pips | 4,8 | -0,20 | -0,0417 | ER- |
| +2.000 | +10 pips | 4,0 | +1,00 | +0,2500 | Picco, non ER |
| +100 | +1 pip | 0,2 | +0,10 | +0,5000 | Nessun picco |
| 0 (media 0) | 0 | N/D | 0 | N/D | Nessun picco |

Con **dati assenti**, ATR nullo o media del delta nulla, il calcolo ER produce **N/D**, non segnali inventati. Il filtro temporale può scartare eventi reali: per prove comparative impostare **Minimo barre tra picchi = 0**.

## STATO VERIFICHE
- **v0.1**: screenshot dell'11/11/2026 mostra che compila e visualizza marcatori e livelli su EURUSD FXCM M5, ma non dimostra alcun vantaggio statistico.
- **v0.2**: codice aggiornato su GitHub, **non ancora testato su TradingView**.
- **v0.3**: **test visivo/compilazione superato il 11/11/2026**. Due fotografie del grafico `FXCM:EURUSD` 5m mostrano indicatore v0.3 attivo, pannello Delta/Sforzo/Risultato/Efficienza, livelli Week/Monthly, marcatori ER+ e ER-. Nessun errore Pine visibile. Osservato ER- vicino all'11/11 sul grafico, senza inferire un risultato futuro.
- La metrica resta **NON VALIDATA** come previsione e i dati non sono feed istituzionali certificati. Gli screenshot non provano che l'evento preceda un'inversione.
- **Prossimo test**: bloccare ex ante soglie 3.5, 0.07 e gap 6, registrare ogni ER con timestamp/valore e misurare per 3, 6 e 12 barre successive distanza di chiusura, MFE/MAE in ATR e frequenza degli esiti avversi. Confrontare con un benchmark senza ER e senza attribuire una direzione automatica al marcatore; conservare anche gli insuccessi.
- Fonte tecnica: [libreria TradingView ta](https://www.tradingview.com/script/BICzyhq0-ta/), [riferimento Pine Script v6](https://www.tradingview.com/pine-script-reference/v6/).

## COSTI / LIMITI
La modifica non introduce nuove API, server, credenziali o abbonamenti. **GitHub: costo aggiuntivo nullo**. Limiti di storico intrabar, alert e indicatori dipendono dal piano TradingView. FXCM forex puo' offrire tick volume invece di volumi di contratti reali: mai spacciarlo per una misura istituzionale.

Prossime fasi: [ROADMAP.md](ROADMAP.md).
