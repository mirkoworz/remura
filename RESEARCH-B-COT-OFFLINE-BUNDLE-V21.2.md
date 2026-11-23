# REMURA — Filone B V21.2: parità CFTC → 7 fattori FX con un solo comando offline

**Checkpoint LAB:** 23/11/26, 21:11:39 Europe/Rome. Branch `research/filone-b-cot-intelligence-v206-20261123`, PR #108 Draft. Nessun merge/deploy, nessun intervento Cloudflare/Oracle/Mac.

## Nuova connessione concreta

`scripts/cot_offline_parity_fx_bundle.py` riunisce i **due moduli esistenti** di v21.0 (`cot_intelligence_parity.py`) e v21.1 (`cot_fx_dashboard_export.js`), in esecuzione offline solo dopo la disponibilità autorizzata di **due copie JSON locali**. Un'unica esecuzione:

1. controlla digest SHA256 del file CFTC pubblico, esatta struttura, 14 contratti (TFF e Disaggregated) per due report consecutivi, 5 valori per contratto, data di prima acquisizione locale e mancanti/discrepanze;
2. se la parità manca **non avvia** Node e restituisce `BLOCKED_PUBLIC_PRIVATE_PARITY_NOT_CLEAN` con `dashboard=null`;
3. se la parità è pulita usa il file **pubblico** per calcolare con Node un output descrittivo di 7 fattori FX TFF + 28 cross sintetici, bloccato se report/campi/periodo non coincidono; aggiunge solo **conteggi aggregati** di copertura first-seen privata, non righe prezzi/copie private;
4. dichiara sempre `historicalDataAvailabilityIndependentlyVerified=false`, `futurePricesOrPerformanceVerified=false`: confrontare valori attuali non prova che fossero noti alla data storica.

~~~bash
python3 scripts/cot_offline_parity_fx_bundle.py \\
  --public /percorso/offline/cftc-public.json \\
  --private /percorso/offline/remura-cot-copy.json \\
  --report-dates 2026-11-10,2026-11-17 \\
  --now-utc 2026-11-23T20:00:00Z
~~~

L'esecuzione non effettua **HTTP, richieste CFTC, scritture, nuove API, depositi GitHub, trading, lettura del DB produttivo o nuove spese**. I due snapshot devono già esistere nella stessa macchina, copiati tramite procedura separata autorizzata. Nessun batch automatico sulle quote gratuite.

## Prove e limiti

- `tests/test_cot_offline_parity_fx_bundle.py`: **sei test nuovi** su fixture sintetiche (28 chiavi su 2 settimane, 7 fattori/28 cross, errore di valore bloccante, first-seen mancante, digest contraffatto, file privato mancante, date/cadenza incoerenti).
- Ultima verifica CI della precedente V21.1: [45255236881](https://github.com/mirkoworz/remura/actions/runs/45255236881) SUCCESS. Nuova CI V21.2 da registrare separatamente.
- Le 980 righe CFTC ufficiali del run [45206837974](https://github.com/mirkoworz/remura/actions/runs/45206837974) erano nel filesystem temporaneo; **nessun artifact** disponibile per quella esecuzione. Non ricostruire snapshot da statistiche aggregate. Nessun nuovo audit CFTC in questo turno.
- Finché manca una copia pubblica verificabile + privata offline: **parità REALE N/D, 7 numeri autentici N/D, first-seen N/D**. I mock nei test non sono dati di mercato.
- Restano categorie separate: TFF Asset Managers/Leveraged Funds contro Disaggregated Managed Money/Producer-Merchant. Nessun flusso live, nessun segnale prezzo, nessun calcolo del Filone A.
