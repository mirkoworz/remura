# REMURA v1.48 — Qualità temporale COT e settimane indipendenti

## Decisione architetturale
Il COT ufficiale è un **report settimanale di riferimento**, non un
dato intraday, e il report-date non è la pubblicazione. REMURA v1.47
salvava solo i valori e la data di riferimento. La v1.48 memorizza per
**le sole nuove chiavi di contratto+report** il primo istante UTC
di cattura dal collector ufficiale in `cot_first_seen`.

Questa data è **prima acquisizione osservata da REMURA**, NON
timestamp certificato di pubblicazione CFTC. Non forzare orari
standard del venerdì (festività, ripubblicazioni e ritardi).
Gli archivi già esistenti non vengono retrodatati o etichettati
come provati, neppure se appaiono nelle prossime chiamate CFTC.

## Persistenza
`cot_first_seen(dataset,code,report_date,first_seen_at)`:
- Tabella piccola con PK univoca; nessuna nuova API esterna;
- `INSERT OR IGNORE` solo per una riga non presente in `cot_reports`
  all'inizio della transazione di raccolta;
- revisione/correzione di una riga già presente non cambia il
  primo timestamp; le acquisizioni vecchie rimangono sconosciute;
- non si cancellano le provenienze, i riferimenti statistici, le
  credenziali, i backup o le coorti esistenti.

## Audit, **non modifica al motore di segnali**
Endpoint privato, sola lettura e senza cache:
`/private-api/signals/weekly-quality`.
`mode=ro` e `PRAGMA query_only=ON`. Legge le **stesse coppie**
`calendar24`/`trading96` già verificate dalla v1.46/v1.47.
- Controlla per ogni coorte il timestamp di prima osservazione:
  il COT deve risultare acquisito prima di quell'istante.
- Per le variazioni COT serve il report corrente e il precedente.
  Per le valute incrociate occorrono **entrambe** le gambe e la
  settimana COT precedente comune.
- `recorded_before_observation`: prima acquisizione locale
  tracciata per tutti i report richiesti;
- `unknown_legacy`: prima acquisizione non tracciata, non inventata;
- `captured_after_observation`: discordanza temporale;
- `missing_cot_reference`: il report necessario non è più
  presente nell'archivio accessibile.
- Non cambia il conteggio, l'esito o il rendimento di alcun
  campione esistente: la provenienza è un controllo **separato**.

## Dipendenza fra mercati
L'endpoint conta **settimane COT con almeno un esito**
(distinte dai casi individuali) e, nelle settimane che contengono
entrambe le condizioni, riporta quale tra divergenze e concordanze
ha mostrato frequenza direzionale maggiore. Uno shock USD comune
può produrre molti casi nella stessa settimana.

Fattori qualitativi di esposizione condivisa: USD, metalli
preziosi, indici azionari USA e singole valute nei cross.
Questi sono **avvisi di sovrapposizione**; non presentano
coefficienti di correlazione calcolati.
Almeno 8 settimane sono una soglia minima descrittiva, **non** una
validazione predittiva. Non c'è ancora walk-forward affidabile
o costi di esecuzione.

## Installazione
Contiene una nuova tabella aggiunta dal collector ufficiale,
ma nessuna migrazione distruttiva. Non modificare né ricreare il DB.
Procedura obbligatoria: PR + CI completamente verdi, backup SQLite
**nuovo** e integro, verifica dello SHA, installazione server protetta
da lock con rollback, controllo delle tre API precedenti e della
nuova API prima di confermare l'aggiornamento.
La VPS v1.47 resta operativa finché non si completa il deploy protetto.
