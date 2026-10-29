# REMURA v1.49 — Controllo acquisizione dei report COT

## Perché
La v1.48 conserva l'istante UTC in cui REMURA incontra per la prima
volta una **nuova** riga CFTC. La v1.49 controlla la qualità di quelle
acquisizioni, separatamente dalle statistiche di previsione e dai prezzi.

## Rete e costi
- **Nessuna nuova API.** Il collector CFTC ufficiale già attivo sulla
  VPS interroga gli archivi TFF e Disaggregated ogni **6 ore** quando
  `REMURA_COT_SYNC_ENABLED` è attivo.
- La v1.49 **non fa chiamate esterne aggiuntive**: legge il database
  locale con `mode=ro` e `PRAGMA query_only=ON`.
- Nuova API privata `GET /private-api/cot/week-watch` con
  `Cache-Control: no-store`. Non espone account, token, password,
  prezzi o posizioni.
- Il frontend è leggibile anche da iPhone con Tailscale, senza
  notifiche Telegram e senza ordini automatici.

## Cosa controlla
- Copertura **11/11 TFF** e **3/3 Disaggregated** per ogni settimana
  COT di riferimento; codici ufficiali mancanti espliciti.
- Distinzione tra *settimana completa più recente* e *precedente*
  (occorrono due periodi per la variazione COT). Nessun riempimento.
- Prima acquisizione locale per ogni contratto e settimana, dai dati
  autentici salvati in v1.48; record legacy senza first-seen rimangono
  «non tracciabili». Un timestamp futuro o invalido non viene accettato.
- Righe della settimana COT più recente catturate **nelle ultime
  48 ore**, solo quando entrambi gli archivi hanno la stessa
  settimana completa e presentano acquisizioni locali recenti.
  Non significa prova della data ufficiale di pubblicazione.
- Ultimo tentativo, successo, errore separato per fonte. Un errore
  nella raccolta non cancella record precedenti.
- Se la data del report più recente supera **14 giorni**, la UI
  richiede controllo, **non dichiara che un report è perso**:
  orari di pubblicazione, festività, posticipi, revisioni e latenze
  possono legittimamente cambiare. Non si inventano i dati.
- Un ciclo di candele cTrader / aggiornamento sentiment NON è
  identificato come nuovo COT.

## Limiti onesti
«Report completo» significa copertura dei contratti osservati,
non che i numeri siano garantiti corretti o pubblicati alla data
standard. Non si finge di conoscere timestamp di pubblicazione CFTC.
Il monitor non calcola coefficienti di correlazione, segnali, rendimento
netto o probabilità operative.

## Rilascio
Modifica il backend Python: l'aggiornamento automatico della VPS
**non installa questa versione da solo**. Dopo PR e test verdi,
eseguire backup SQLite **nuovo e verificato**, controllo SHA esatto,
installazione protetta da lock, health-check e test della nuova API,
con rollback codice se fallisce. Non eliminare dati o credenziali.
La v1.48 VPS resta attiva fino all'installazione protetta v1.49.
