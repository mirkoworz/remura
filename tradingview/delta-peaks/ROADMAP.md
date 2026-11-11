# REMURA TradingView — ROADMAP Delta Peaks LAB v0.2
**Aggiornamento: 11/11/2026, ore 08:54 CET**

## Stato attuale
- [x] Sezione autonoma `tradingview/delta-peaks/` e PR **#102 DRAFT**, separata da main e dai filoni A/B/C.
- [x] **v0.1** — compilazione e visualizzazione viste nello screenshot TradingView dell'11/11/2026 su `FXCM:EURUSD` 5m. Non e' una validazione scientifica.
- [x] **v0.2** — riduzione rumore visivo, picchi separati da ER, soglia basata su 30 barre precedenti, intervallo minimo configurabile.
- [ ] Prova di compilazione **v0.2** in Pine Editor, screenshot di confronto con v0.1.
- [ ] Controllare feed senza volume, disponibilita' storico intrabar e coerenza colori/valori.
- [ ] Confrontare con il metodo di riferimento dei picchi delta Week, Current Monthly e Previous Monthly.

## Step successivi (non ancora implementati)
1. **v0.3 — livelli fedeli al metodo:** distinguere massimo della barra, livello di prezzo effettivo, range/estremi e metrica di delta per Week/Current/Previous.
2. **v0.4 — robustezza & falsi positivi:** analisi dei filtri sui dataset disponibili, nessun ottimismo retrospettivo.
3. **v0.5 — prova prospettica:** registrare eventi prima della reazione, misurare casi positivi e negativi, volatilita', orari, eventi news.
4. **v0.6 — eventuale integrazione REMURA:** flusso alert consentito, a costo zero se possibile, senza segreti in Pine e senza ricondurre dati FXCM a CME.
5. **Confronto futures:** solo su dati autentici e utilizzabili legalmente quando disponibili.

## Regole permanenti
- Ogni modifica con versione e **data/ora CET/CEST nell'intestazione** di Pine, README e roadmap.
- Nessuna promessa di profitti, segnali anticipatori o identita' istituzionale prima di test seri.
- Nessun merge, deploy o modifica automatica alle PR dei filoni A/B/C.
- Priorita' al gratuito, monitorando i limiti di piani e servizi.
- Separare sempre **verifica compilazione/UI** da **validazione scientifica**.

## Registro modifiche
- **v0.1 — 11/11/2026 08:41 CET:** script iniziale con picchi, ER e livelli WEEK/MONTH, condizioni di alert.
- **Verifica v0.1 — 11/11/2026 08:54 CET:** screenshot FXCM:EURUSD 5m conferma esecuzione e visualizzazione, segnali molto affollati.
- **v0.2 — 11/11/2026 08:54 CET:** soglia 3.5 su media delle barre precedenti, gap minimo di 6 barre, visualizzazione ER per default, D+/D- opzionale. In attesa della prova sul grafico.
