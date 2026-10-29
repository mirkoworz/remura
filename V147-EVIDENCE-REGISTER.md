# REMURA v1.47 — Registro delle evidenze settimanali

## Perché esiste
La v1.46 ha mostrato 14 osservazioni abbinate su 14 mercati, ma solo
**1 settimana COT**. Il registro aggiunge la tracciabilità dei casi:
così i risultati positivi di una divergenza si possono ricondurre al
singolo mercato senza attribuire agli istituzionali ordini non osservati.

## Regole di integrità
- Utilizza `market_validation.paired_cases`: **la stessa selezione**
  della v1.46, nessuna re-interpretazione degli esiti già persistiti.
- Solo lo stadio `observation` iniziale e i **due esiti** calendar24/
  trading96 validati e conclusi. Un risultato singolo non viene
  artificialmente completato. Conferme ed eventi sovrapposti esclusi.
- Per ogni mercato e **data di riferimento COT**: direzione COT originaria
  (long/short), stato iniziale prezzo contro/a favore COT, movimento
  direzionale effettivamente registrato (bp), benchmark long sugli
  stessi intervalli e differenza tra i metodi. Non è un trade.
- La settimana COT è **data di riferimento**, non data di pubblicazione,
  non data di osservazione e non momento di ingresso. Nessuna
  retrodatazione all'accesso reale ai dati.
- Soltanto **ultime 12 settimane COT** a scorrimento per contenere
  risposta privata e interfaccia iPhone. Le settimane sono incluse
  in ordine temporale, **non** selezionate per rendimento favorevole.
  Nel frontend, massimo 24 schede alla volta, con filtri.
- Il riepilogo settimanale conta casi, esiti positivi e negativi di
  concordanze e divergenze, senza sommare i due orizzonti né le conferme.
- Nessuna stima di correlazione con 1 sola settimana: più simboli
  esposti al medesimo USD o evento macro possono essere dipendenti.
  Numero di mercati non significa numero di prove indipendenti.

## Sicurezza
- Endpoint privato `/private-api/signals/dual24/cases` è **solo GET**
  e legge SQLite in `mode=ro` con `PRAGMA query_only=ON`.
- Nessuna tabella, schema, backfill, calcolo vecchio, entry/exit OPEN,
  simbolo specifico del broker, account, password, token o endpoint
  operativo cambiato.
- API espone soltanto simboli canonici, COT week pubblica, etichette
  e movimenti percentuali in punti base. `Cache-Control: no-store`.
- Controllo as-of: esito incluso solo dopo chiusura della M15 d'uscita,
  e solo se era già stato valutato. Non si generano candele.
- UI usa solo `textContent` e rifiuta campioni/medie/direzioni
  matematicamente incoerenti, invece di mostrare risultati inventati.

## Validità e limiti
Ogni segno rappresenta **movimento lordo teorico**, non profitto.
Costi, spread e slippage sono assenti. L'intervallo Wilson, anche se
mostrato nella v1.46, non corregge la correlazione dei simboli.
Le conclusioni richiedono molte settimane indipendenti, nuove
osservazioni prospettiche e test fuori campione.

## Rilascio protetto
v1.47 contiene codice Python e quindi NON va installata sulla VPS
solo tramite i file web. Usare PR separata con test Python/Node verdi,
backup SQLite coerente e nuovo, installazione manuale protetta da lock,
controllo API e rollback codice. Fino ad allora v1.46 resta attiva.
