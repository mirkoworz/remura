# REMURA v1.45 — confronto fra 24 ore trascorse e 96 M15 negoziate

## Stato
Release **candidata, non installata**. La VPS resta v1.44 fino al nuovo
backup coerente del SQLite privato, test e installazione protetta manuale.
Nessun ordine, nessun invio di trading, nessun accesso aggiuntivo al broker.

## Due esperimenti genuinamente distinti

1. **calendar24**: un'osservazione autentica parte dall'apertura M15
   successiva alla prima rilevazione REMURA già salvata nella coorte.
   Si confronta il prezzo **open** della M15 che inizia esattamente
   24 ore di calendario dopo. Per oro/argento, se il target ricade
   nella pausa **21–22 UTC** verificata tramite screenshot cTrader
   FP Markets, è ammessa **solo** la prima riapertura successiva
   entro 60 minuti (ritardo tracciato). Non si usa un quote fittizio.
   Una chiusura weekend o gap non verificato rende il caso non valutabile.
2. **trading96**: partendo dalla stessa entry, si leggono **96 M15 realmente
   negoziate e chiuse**. Uscita teorica al prezzo open della 97ª M15.
   Una pausa verificata di un'ora sui metalli può allungare la durata
   di calendario a 25 ore o più. Altri gap, inclusi weekend per cui
   REMURA non dispone ancora di calendario autenticato, non vengono
   inseriti nell'analisi.

In entrambi i metodi sono ammesse esclusivamente candele M15 complete e
precedenti al momento della valutazione. L'open d'uscita viene letto solo
dopo la chiusura della relativa M15. Escursione favorevole/contraria
usano esclusivamente le candele reali antecedenti all'uscita, non
quella dell'uscita (che rappresenterebbe futuro rispetto al prezzo open).

## Persistenza e metodo

- **Nuova tabella add-only** `squalincome_dual24_outcomes`, primaria
  `(symbol,report_date,stage,metric)`. Nessuna modifica alla tabella
  `squalincome_validation_outcomes`, ai risultati v1.40, ai COT o al
  collector.
- Coorte già esistente per mercato/settimana COT e stadio; conferme,
  osservazioni ed eventi sono correlati e **non si sommano**.
- Nessun cambio broker: provider e simbolo originario devono
  corrispondere. Nessuna barra sintetica. Pausa accettata solo se
  consiste esattamente in **quattro M15 assenti dalle 21:00 alle 22:00
  UTC** nei metalli XAUUSD/XAGUSD, da ottobre 2026, nei giorni feriali.
- Gli esiti vengono salvati una sola volta e non sovrascritti, anche
  quando i dati storici M15 vengono eliminati dalla retention.
- Percentuale nella direzione COT, intervallo Wilson 95% descrittivo,
  benchmark long, MFE/MAE teorici in bp; **nessun costo incluso**.
- Sotto 30 osservazioni o 8 settimane COT: «Campione insufficiente».
  Superata la soglia non equivale a predittività fuori campione.
- `potentiallyMatureCohorts` è solo il numero di coorti che hanno
  superato il **minimo** di 24h+15min; le finestre senza le 96 barre
  autentiche possono non essere ancora pronte e sono esplicite.
  Non significa che sia trascorsa necessariamente la durata effettiva
  di trading, né misura accuratezza di previsione.

## Output e implementazione

La nuova API privata `/private-api/signals/dual24` restituisce solo
aggregati e rimane `no-store`. Il Radar iPhone v1.45 visualizza
questo confronto solo quando si selezionano le 24 ore, conservando
separatamente il risultato **storico 24h** di REMURA v1.40.
Se il backend nuovo non è ancora installato, lo stato è «non disponibile»
anziché percentuali inventate.

## Attività prerelease

1. CI GitHub (backend, frontend e regressioni) completamente verdi.
2. Backup coerente di `/opt/remura/private/remura-prices.sqlite3`
   effettuato **dopo** le ultime raccolte, validato con `PRAGMA quick_check`.
3. Installazione manual-only della modifica Python con updater di REMURA,
   lock, backup codice, verifica endpoint + rollback documentato.
4. Nessuna modifica alle soglie di freschezza, retention, motore dei
   segnali o configurazioni trading.
5. Verifica visiva su iPhone e coerenza dei numeri dopo installazione.
