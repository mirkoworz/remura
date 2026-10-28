# REMURA v1.43 — diagnostica pause di sessione (candidata)

## Dato osservato in produzione, 28 ottobre 2026

Lo storico privato cTrader di XAUUSD e XAGUSD presenta 4 candele M15
assenti nello stesso intervallo di ogni sessione:
- 21/22 ottobre: 23:00–00:00 orario Italia (CEST)
- 26/27 ottobre: 22:00–23:00 orario Italia (CET)
- Entrambe le fasce sono 21:00–22:00 UTC.

La ripetizione in due strumenti e attraverso il passaggio all'ora solare
è **compatibile** con una chiusura quotidiana del broker, ma non prova
l'orario ufficiale del contratto. Verificarlo sul server di trading prima
di trattarlo come dato accertato.

## Cosa fa questa PR

- Legge solo M15 reali dei due metalli da SQLite privato.
- Raggruppa interruzioni brevi per ora UTC e numero di candele assenti.
- Una pausa si considera solo *ricorrente candidata* con almeno 3 giorni
  distinti, senza includere il weekend o osservazioni future.
- Endpoint privato GET /private-api/signals/session-gaps con stato
  diagnostico aggregato, senza OHLC, broker, credenziali o account.
- Nella pagina statistica una sezione chiudibile spiega i dati senza
  modificarli. Nessun risultato viene simulato.
- Versione/data/ora italiana e cache PWA aggiornate su tutte le pagine.

## Cosa NON fa

- Non cambia le soglie di freschezza né il collector.
- Non costruisce M15 sintetiche.
- Non ricalcola i vecchi risultati, non cambia il significato di "24 ore".
- Non converte una giornata con 23 ore negoziate in 24 ore negoziate.
- Non esegue ordini o automatismi di trading.
- Non considera una pausa del broker certificata dalla sola ripetizione.

## Importante per la prossima evoluzione

La metrica esistente misura 24 ore di calendario/tempo trascorso con un
vincolo restrittivo di 96 M15 consecutive. Gli esiti non disponibili per
pause di sessione **rimangono non disponibili**. Per implementare una nuova
metrica dovremo separare esplicitamente:
1) rendimento dopo 24 ore di calendario usando solo prezzi di mercato
   realmente osservati e un prezzo finale valido, con pausa segnalata;
2) rendimento dopo 24 ore di negoziazione (96 candele effettive), dove
   il tempo di calendario può superare 24 ore.

Sono due esperimenti distinti. Non mescolare né sovrascrivere i loro dati
senza un benchmark coerente, una nuova definizione e test di non-lookahead.

## Prima di installare sulla VPS

Il cambiamento importa un nuovo script Python nel server privato:
l'autoupdater correttamente richiede installazione manuale. Verificare
entrambi i CI verdi, nuovo backup SQLite, installazione protetta e rollback;
non unire in main mentre questi prerequisiti mancano.
