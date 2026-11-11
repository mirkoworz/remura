# REMURA TradingView — ROADMAP Delta Peaks LAB v0.1
**Aggiornamento: 11/11/2026, ore 08:41 CET**

## Stato verificato
- [x] Sezione separata `tradingview/delta-peaks/` predisposta nel ramo di ricerca.
- [x] Prima implementazione Pine v6, libreria ufficiale `TradingView/ta/14`.
- [ ] Test di compilazione dentro TradingView su `FXCM:EURUSD` 5m.
- [ ] Screenshot leggibile di picchi e livelli; test con feed privo di volume.
- [ ] Confronto qualitativo con video/esempi del metodo del collaboratore.

## Sequenza prevista
1. **v0.1 — base:** delta intrabar, picchi, sforzo/risultato, WEEK, CURRENT MONTH, PREVIOUS MONTH (prototipo).
2. **v0.2 — definizione precisa dei livelli:** scegliere se tracciare prezzo della candela, range, extreme, barra selezionata, eventuale delta week e metrica mensile.
3. **v0.3 — robustezza:** gestione storico parziale, valori assenti, soglie e falsi positivi, allarmi su barra confermata.
4. **v0.4 — verifica prospettica:** salvare esempi prima della reazione del prezzo; confrontare risultati e fallimenti.
5. **v0.5 — integrazione REMURA (solo dopo test):** valutare una trasmissione lecita e sostenibile degli alert; preferire soluzione gratuita, proteggere segreti e limiti dei piani.
6. **Fase futura — futures CME:** confronto con dati reali su sedi/contratti autorizzati, se disponibili; mai equiparare automaticamente FXCM a CME.

## Regole
- Sempre aggiornare versione e **data/ora in CET/CEST** nell'intestazione di ogni file modificato.
- Nessuna promessa di profitto, predittivita' o identificazione certa degli istituzionali.
- Separare ricerca e produzione; non toccare filoni A/B/C.
- Controllare prima opzioni gratuite, quote TradingView e costi ricorrenti.
- Registrare per ogni modifica: cosa cambia, come riprodurre e quale risultato e' stato osservato.

## Registro modifiche
- **v0.1 — 11/11/2026 08:41 CET**: importato prototipo Pine per delta stimato, picchi, ipotesi sforzo/risultato, livelli settimanali/mensili, dashboard e condizioni di alert. **Test TradingView ancora da eseguire**.
