# REMURA TradingView — Delta Peaks LAB v0.2
**Aggiornamento: 11/11/2026, ore 08:54 CET**

> Laboratorio indipendente: non modifica la web app REMURA, i filoni A/B/C, i deploy o i servizi cloud.

## COPIA IL CODICE AGGIORNATO
**Apri [REMURA-Delta-Peaks-LAB.pine](REMURA-Delta-Peaks-LAB.pine)** e premi **Raw** per copiare l'intero testo, a partire da `//@version=6`.

1. Apri **TradingView** sul simbolo **FXCM:EURUSD** a **5 minuti**.
2. Apri **Pine Editor**, sostituisci tutto il vecchio codice v0.1 con quello v0.2 e clicca **Salva / Aggiungi al grafico**.
3. Elimina dal grafico la vecchia istanza v0.1, se presente: evita marcatori doppi.
4. Controlla sul grafico: titolo **v0.2**, linee **WEEK azzurra, CURRENT MONTH gialla, PREVIOUS MONTH grigia tratteggiata** e **ER**.
5. Se serve vedere anche ogni picco, nelle impostazioni attiva **Mostra anche D+/D- (diagnostica)**.

## MODIFICHE v0.2 PER RENDERE LEGGIBILE IL GRAFICO
- **ER** (ipotesi sforzo/risultato) visibile per impostazione predefinita; **D+/D-** nascosti, attivabili dalla diagnostica. Un ER non e' una conferma di assorbimento istituzionale.
- Soglia di selezione alzata da **2,5** a **3,5** volte la media dei **30 delta assoluti precedenti** (nella v0.1 la barra entrava nella propria media).
- Filtro di distanza fra due picchi: **6 barre** complete senza nuovi eventi dopo un picco, cioe' circa 30 minuti su M5; parametro modificabile anche a 0.
- Marcatori D+/D- evitano di sovrapporsi a ER quando entrambe le visualizzazioni sono attivate.
- I tre **livelli storici non cambiano formula** in questa versione: massimo |delta| della singola barra in ciascun periodo, disegnato al suo `hl2`. Questa scelta va confrontata con il metodo di riferimento.
- Gli alert restano presenti ma **non vengono inviati automaticamente a REMURA**.

## RISULTATO OSSERVATO
- **v0.1 compilata e visibile** sul grafico FXCM:EURUSD 5m nella foto condivisa **11/11/2026**: marcatori e tre livelli visibili, nessun errore di compilazione mostrato.
- **v0.2 non ancora compilata su TradingView**. Prossima prova: confrontare screenshot prima/dopo e verificare che i segnali restino sensati.
- Non e' stata verificata alcuna capacita' predittiva o prova di posizionamento istituzionale.

## LIMITI
- `TradingView/ta/14` e `requestVolumeDelta()` stimano il delta usando dati intrabar disponibili. **FXCM Forex non equivale al flusso di contratti CME**; il volume puo' rappresentare attivita' del feed/tick volume.
- I massimi WEEK e MONTH sono parziali se la profondita' dei dati intrabar e' insufficiente; il valore puo' essere N/D.
- Un picco isolato puo' essere rumore, news o evento del feed; ER e' una regola euristica (delta grande e corpo piccolo o movimento opposto).
- Il filtro anti-affollamento puo' omettere anche eventi validi: **per studio rigoroso** confrontare v0.1 e v0.2 e provare `Minimo barre tra picchi = 0`.
- Costo aggiuntivo da questa modifica GitHub: **zero**; disponibilita' degli indicatori/alert dipende dai limiti TradingView del piano.

**Prossimi passi:** [ROADMAP.md](ROADMAP.md). Non fare merge o deploy dal laboratorio senza verifica separata.

**Fonti tecniche:** [libreria ufficiale TradingView ta](https://www.tradingview.com/script/BICzyhq0-ta/), [Pine Script v6](https://www.tradingview.com/pine-script-docs/).
