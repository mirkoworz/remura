# REMURA v1.50 — Attestazione prima acquisizione COT (solo frontend)

## Obiettivo
Alla comparsa della prossima settimana ufficiale, riconoscere automaticamente
se **tutte e 14** le righe permesse CFTC hanno una **prima acquisizione locale
registrata**, oppure se la settimana è parziale/non tracciabile.

## Come funziona
- La v1.49 già registra in SQLite `cot_first_seen` per le **nuove** righe,
  una sola volta per contratto e data report.
- Usa esclusivamente la risposta privata già disponibile
  `/private-api/cot/week-watch`. Non è stato aggiunto alcun accesso esterno,
  lavoro programmato aggiuntivo, prezzo o costo API.
- Per la data COT più recente, mostra righe tracciate / 14 e distintamente
  TFF / 11, Disaggregated / 3.
- Stato `fully_tracked` solo se il report più recente è completo in
  entrambi i dataset e **tutti i 14** timestamp esistono e sono validi.
- Se arriva prima TFF e poi Disaggregated, mostra `partial` e non
  certifica la settimana a metà.
- I vecchi 14 report COT già acquisiti prima della v1.48 rimangono
  `legacy`: non inventa timestamp, non ricalcola statistiche.
- Un guasto corrente della fonte è mostrato a parte dalla certificazione
  storica. Il passare delle 48h non cancella la registrazione della prova.
- Interfaccia aggiornata automaticamente solo quando il controllo frontend
  su GitHub è verde, senza cambiare il backend né la struttura del database.
- **Limite:** tracciabilità della cattura locale ≠ data ufficiale di
  pubblicazione ≠ segnale ≠ prova statistica di profitto.

## Deploy
Variazione frontend (`*.html`, `*.js`, test, PWA). Il backend v1.49
è compatibile e **non deve essere reinstallato manualmente**. L'aggiornatore
sulla VPS opera solo quando i test GitHub del commit finale sono tutti verdi.
