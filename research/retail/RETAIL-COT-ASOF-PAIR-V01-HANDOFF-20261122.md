# REMURA Retail × COT — pairing causale v0.1 LAB
**22 novembre 2026 — Europe/Rome.** Offline, dati sintetici, NO-GO reale.

## Nuovo codice ed evidenza
- Branch `research/retail-cot-asof-pair-v01-lab-20261122`.
- `research/retail/retail_cot_asof_pair_v01_lab.py` implementa un selettore
  `as-of` per decisione con sorgenti non intercambiabili: Myfxbook RETAIL
  e CFTC FUTURES. Richiede un'identità esplicita, payload archiviato,
  timestamp di ricezione locale e hash dei byte.
- Nessun dato registrato dopo la decisione può essere usato per simulare la
  stessa decisione, neppure se è una revisione di un rapporto vecchio.
- Se mancano dati => UNKNOWN; mappatura non dichiarata => NON_COMPARABLE;
  payload alterato, clock incoerente, contenuti discordanti allo stesso
  momento, regressione di versione => QUARANTINE.
- Anche quando produce una coppia, lo stato è
  `LOCAL_PAIR_UNATTESTED_FIXTURE_ONLY`: una stringa di mapping **non prova**
  che futures e spot siano davvero comparabili.
- CI run **44999167732**:
  https://github.com/mirkoworz/remura/actions/runs/44999167732
  — **20/20 PASS**, job e log verificati, marker
  `REMURA_RETAIL_COT_ASOF_V01=20_20_PASS`.
- Non sono stati ripetuti l'audit Myfxbook 34 file / 3.984 osservazioni
  né le suite esistenti di COT v0.1/v0.2, TradingView o Contributors.

## Non dichiarare ancora
- Nessuna ammissione di dati Myfxbook o COT reali per una data decisione.
- Nessuna attestazione indipendente di primo arrivo dei dati.
- Nessuna mapping proof effettiva tra futures CFTC e spot FX.
- Nessuna prova di attività istituzionale contemporanea, flusso aggressore,
  vantaggio predittivo o profitto.
- Non è un motore di trade, non genera segnali o raccomandazioni.

## Gate successivi
1. Recuperare la **versione originale archiviata** di ogni osservazione
   retail e COT e i clock di ricezione (non sostituire `latest.json`
   a un valore non catturato in passato).
2. Verificare pubblicazione CFTC, eventuali revisioni e tempo di acquisizione
   contro evidenze indipendenti; se manca, etichettare non attestato.
3. Costruire mappatura firmata/revisionata per contract code, simbolo spot,
   orientamento di valuta e intervallo; non inferire dall'etichetta testuale.
4. Collegare solo dati ammissibili a identità singole decisioni TradingView
   secondo il protocollo V2 congelato, con controllo sulle finestre UTC.
5. Valutare prestazioni solo su dati autentici prospectively admitted e
   fuori campione. Prima di tutto, misurare copertura e missingness.

**Decisione:** motore di selezione temporale sintetico GREEN; analisi
causale con dati reali ancora NO-GO.
