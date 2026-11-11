# REMURA TradingView — ROADMAP Delta Peaks LAB v0.3
**Aggiornamento: 11/11/2026, ore 09:03 CET**

## Stato attuale
- [x] Cartella indipendente `tradingview/delta-peaks/`, PR #102 **DRAFT**, senza modifiche a main/produzione e ai filoni A/B/C.
- [x] **v0.1**: screenshot EURUSD FXCM M5 del 11/11/2026 mostra corretta visualizzazione di marcatori e livelli.
- [x] **v0.2**: riduzione del rumore visivo, delta / media precedenti, distanza minima fra picchi.
- [x] **v0.3**: metrica numerica dell'efficienza Sforzo/Risultato con Delta, Sforzo relativo, Risultato orientato (ATR), Efficienza ER e alert dedicati.
- [ ] **Prova compilazione v0.3** in Pine Editor TradingView e screenshot.
- [ ] Verificare comportamento con delta 0/N/D, ATR assente, storia intrabar incompleta, grafici con o senza volume.
- [ ] Confrontare **WEEK / CURRENT MONTH / PREVIOUS MONTH** con esempi e regole specifiche del metodo del collaboratore.
- [ ] Confrontare i segnali filtrati vs senza gap, soglie 0.07 e 3.5 su campioni *prospective* senza selezione a posteriori.

## Formula v0.3 (nessuna ottimizzazione retrospettiva)
```
Sforzo = abs(delta) / SMA(abs(delta delle 30 barre precedenti))
Risultato = sign(delta) * (close - open) / ATR(14)
Efficienza = Risultato / Sforzo
ER = barra confermata AND Sforzo >= 3.5 AND Efficienza <= 0.07
     AND rispetto del gap minimo (6 barre intermedie)
```
Il risultato dell'ultima barra appare in dashboard: non è storico statistico di efficacia, non è un segnale direzionale e non identifica specifici istituzionali.

## Sviluppi successivi
1. **v0.4 — livelli del metodo**: validare posizione e tipologia di livelli Week/Monthly con esempi, considerare range e valore del delta di periodo.
2. **v0.5 — registrazione prospettica**: definire evento, timeframe di osservazione, target/stop solo per misurare esiti e falsi positivi, nessuna promessa di profitto.
3. **v0.6 — filtri robustezza**: sessioni, volatilita', feed mancanti, gap, forme di volume, almeno due condizioni indipendenti.
4. **v0.7 — eventuale integrazione REMURA**: verificare webhook, limiti del piano e termini di uso; preferire opzioni gratuite.
5. **Futures reali**: confronto con CME soltanto quando dati utilizzabili e validi sono disponibili.

## Regole permanenti
- Intestazione con versione e data/ora CET/CEST a ogni modifica.
- Niente merge/deploy della PR #102, niente interferenza coi filoni A/B/C.
- Separare compilazione Pine, verifica dati e validazione scientifica.
- Evitare leak di credenziali, servizi a pagamento o chiamate non necessarie.
- Documentare falsi positivi e negativi, non scegliere solo i successi.

## Registro
- **v0.1 — 11/11/2026 08:41 CET**: prototipo iniziale.
- **v0.1 screenshot — 11/11/2026 08:54 CET**: compilazione e visualizzazione osservate.
- **v0.2 — 11/11/2026 08:54 CET**: soglie e pulizia grafica, in attesa di test Pine.
- **v0.3 — 11/11/2026 09:03 CET**: calcolo normalizzato numerico Effort/Result/Efficiency, pannello e avvisi ER per segno delta. Test Pine non ancora svolto.
