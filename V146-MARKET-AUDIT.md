# REMURA v1.46 — audit statistico per mercato (candidato)

## Scopo
Rendere leggibili i risultati dei due studi 24h già presenti in REMURA
v1.45 senza trasformare pochi campioni correlati in segnali operativi.

## Regola fondamentale: stessi casi, stesso periodo

- Il confronto usa **esclusivamente** lo stadio `observation` della
  prima coorte autentica per **simbolo e settimana COT**.
- Due risultati si confrontano soltanto quando `calendar24` e
  `trading96` sono entrambi registrati per la medesima chiave
  `(symbol,report_date,observation)`.
- Un campione presente soltanto in un metodo non entra nei calcoli di
  nessuno dei due. È mostrato come **non abbinato**.
- Conferme tecniche ed eventi qualificati possono sovrapporsi alle
  osservazioni e NON sono aggiunti come prove indipendenti.
- Concordanze e divergenze sono attribuite usando la classificazione
  registrata nell'osservazione iniziale, non quella aggiornata in seguito.
- Le statistiche per mercato sono alfabetiche; nessun ranking operativo.

## Misure
Numero di coorti potenzialmente mature, coppie completate, casi non
confrontabili, settimane COT distinte, frequenza nella direzione COT,
intervallo Wilson descrittivo, movimento medio verso il COT, benchmark
long sullo stesso sottocampione, differenza trading96 meno calendar24.
Intervallo Wilson NON corregge la dipendenza per settimana e tra mercati.
Nessuna metrica di esecuzione include spread, commissioni o slippage.

## Salvaguardie
- Il nuovo endpoint `/private-api/signals/dual24/markets` apre SQLite
  in `mode=ro` + `PRAGMA query_only=ON`. Nessuna migrazione, INSERT,
  UPDATE, DELETE, token, simbolo del broker o prezzo OHLC è esposto.
- Esiti successivi alla richiesta o non ancora confermati da una candela
  chiusa NON sono inclusi. Le coorti che non hanno superato il minimo
  di 24h + 15 minuti non sono considerate mature.
- Il frontend verifica schema, tipologia, coerenza dei conteggi e
  corrispondenza tra percentuali e campioni. In caso di risposta
  anomala mostra «Non disponibile», non dati finti.
- Selezione del singolo mercato solo nella pagina 24h; le statistiche
  precedenti rimangono inalterate.
- Test con due settimane COT, gruppi concordi e divergenti, coorti
  parzialmente mature, stadi sovrapposti, dati futuri e permessi SQLite.

## Rilascio
La nuova versione comprende codice Python: non installare sulla VPS
tramite semplice aggiornamento frontend. Usare PR con CI verdi, backup
SQLite *nuovo* verificato, aggiornatore con lock e rollback. Conservare
la v1.45 in produzione fino all'installazione autorizzata e verificata.

Nessun ordine, nessun dato aggiuntivo a pagamento. Una condizione
non è validata per il trading solo perché supera 30 campioni: sono
necessarie più settimane **indipendenti**, test fuori campione e
valutazione del rischio/spread.
