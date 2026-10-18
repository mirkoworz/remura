# REMURA — COT Index e Gap Index

Funzioni proposte sul ramo di sviluppo, **non distribuite su main**.

## Provenienza
Le schede `asset.html?symbol=...` interrogano i report CFTC ufficiali **TFF Futures Only** (`gpe5-46if`) per Forex/indici e **Disaggregated Futures Only** (`72hh-3qpy`) per metalli. Il browser richiede circa **5 anni** di report (più 21 giorni di margine) e conserva fino alle ultime **261 rilevazioni settimanali allineate**. Non è ancora implementato un archivio permanente sul server: una nuova apertura della pagina può comportare una nuova richiesta all'API CFTC.

## Calcoli
Per ogni categoria: `Net% = 100 * (long-short) / open_interest`.
Per le coppie FX: differenza dei Net% dei futures delle due valute contro USD; USD=0 è solo un riferimento matematico, non un future sul dollaro.

Selezionare 26, 52, 156 o 260 settimane:
- **COT Index**: `100 * (Net% attuale - minimo dei Net%) / (massimo dei Net% - minimo dei Net%)` nella finestra scelta.
- **Gap**: `Net% categoria 1 - Net% categoria 2`, espresso in punti percentuali con segno.
- **Gap Index**: la stessa normalizzazione 0–100 applicata **al Gap con segno**, non al valore assoluto.

Gli estremi 0/100 indicano solo estremi *relativi* al periodo, **non** probabilità di movimento del prezzo o la percentuale degli operatori long. In caso di dati insufficienti per la finestra richiesta, denominatore nullo o API offline, il risultato è **N/D**. Sui cross gli indici si riferiscono a un differenziale sintetico, non a un contratto COT diretto; gruppi istituzionali differenti non hanno necessariamente obiettivi opposti.

## Grafici
- Il pannello principale delle due categorie consente 26, 52, 156, 260 settimane.
- Gap storico collegato sui **soli** report disponibili; linea zero di riferimento.
- Anche il pannello dettagliato long, short e open interest accetta finestre fino a 260 settimane; i contratti di futures diversi non vengono sommati.

## Collaudo
```sh
node --check cot-indices-core.js
node --test tests/cot-indices.test.js
node --test tests/insights.test.js
```

Per un vero backtest occorrono prezzi storici con timestamp e un calendario di pubblicazione dei dati COT: il martedì è la data delle posizioni, **non** il momento in cui erano pubblicamente disponibili.
