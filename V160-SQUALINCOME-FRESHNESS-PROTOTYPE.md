# REMURA — Prototipo offline degli stati di freschezza Squalincome

**03/11/2026 · ricerca, NON installata.** REMURA live resta **v1.59** con SHA `e924f4cf6f1a384fd84a3cef66c89a16e35de3fd`. Nessuna modifica a backend, Oracle VPS, autoupdater, notifiche o servizi broker.

## Diagnosi alla base

La diagnostica privata #31 (`41611353786`) ha osservato alle 09:19:07 UTC **8 H1 sopra 120 minuti, 8 H4 sopra 300, M15 zero sopra 180**, pur con H1 coerenti con l'ora teorica consentita dalla M15. Il simulatore privato PR #17 (`remura-collector`) ha riprodotto il fenomeno matematicamente con una rotazione **ideale** di otto gruppi in due ore, senza chiamate broker. **Non significa che sappiamo già quali batch successivi si completeranno realmente.**

## Tre stati leggibili, distinti da un segnale

| Stato | Condizioni | Cosa può fare REMURA |
| --- | --- | --- |
| `price_live_ready` · **Dati prezzo idonei alla verifica live** | Integrità verificata, sorgente recente, almeno 55 candele per M15/H1/H4; tutte le rispettive chiusure UTC coerenti e entro 180/120/300 minuti; metadata qualità dello stesso snapshot e scansione recentissima | Un eventuale backend può **solo proseguire** con gli ulteriori gate COT e struttura. **Non è** un segnale BUY/SELL |
| `waiting_verified_batch` · **In attesa del batch verificato** | Prezzi storici corretti ma almeno un timeframe oltre soglia e prova dal collector di un successivo batch atteso, non ancora scaduto. È **sempre non live** | Mostrare spiegazione, storico e prossima occasione di aggiornamento se **attestata dal server**. Mai promuovere eventi nuovi |
| `price_stale` · **Dati fuori soglia** | Integrità verificata ma H1/H4/M15 superano le soglie e **non** è provata una schedulazione prossima valida | Conservare storico, escludere nuove conferme live |
| `unverified` · **Dati non verificabili** (stato di sicurezza aggiuntivo) | Qualità o timestamps non dimostrabili, storico insufficiente, weekend, snapshot troppo vecchio o fonti non sincronizzate | Nessuna conferma live e nessuna etichetta ingannevole "in attesa" |

La prima implementazione pura `squalincome-freshness-core.js` è **non importata** dalle nove pagine o da `private_server.py`. I test `tests/squalincome-freshness.test.js` verificano anche che **ogni** uscita riporti `signalAuthorized:false`, perché questo modulo *non* analizza COT, non genera eventi, non inferisce posizioni istituzionali e non deve autorizzare ordini.

## Contratto obbligatorio per una eventuale UI live futura

Il classificatore richiede:
- `scanAt`, `observedAt`: tempi UTC/offset espliciti; `observedAt-scanAt` non può superare **20 minuti**;
- `frames.M15/H1/H4.lastClosedAt`, `.bars`: derivati dalle candele realmente verificate dalla VPS, non dal dispositivo; richiede almeno **55** per timeframe; è controllata la sequenza dei timeframe e il timestamp di chiusura;
- `priceQuality.integrity === verified`, `priceQuality.freshness === recent`, `priceQuality.ready === true`, con `checkedAt` coincidente col full scan (entro **1 secondo precedente**): questo evita di unire erroneamente GET che descrivono momenti diversi;
- opzionale `batch` con `provenance:server_collector_schedule`, `state:running`, `lastOutcome:ok`, `lastSuccessfulCollectionAt` non precedente all'ultima M15 e `nextExpectedAt` in futuro, entro 120 minuti dal precedente successo. **Non** è un orario stimato dallo storico.

**Vincolo fondamentale:** la v1.59 espone `/private-api/signals/status` e `/private-api/prices/status` da due letture **non atomiche** e non espone un `nextExpectedAt` verificato per ogni mercato. Quindi **con i soli endpoint attuali non è lecito accendere automaticamente un badge verde o giallo affidabile**. Il prototipo fa `unverified` senza metadata coerenti, non prova a dedurli. Questo è un prerequisito di backend per qualsiasi futura UI e richiederà una release protetta, non un aggiornamento silenzioso.

## Sicurezza e rollout

- Soglie originali **M15 180, H1 120, H4 300 minuti**, senza rilassamenti.
- Non inventare `nextExpectedAt` da `lastAttempt + 120 min`: l'orario è variabile e il tentativo può fallire.
- Non usare questo classificatore per riemettere vecchi eventi o spostare `price_time` delle osservazioni.
- Validare eventuale implementazione server con snapshot atomico, test di chiusure H1/H4 contigue, gestione weekend/festivi/rollover, assenza di leak, quote API invarianti, controllo dei costi.
- Solo dopo CI e validazione, creare una release esplicitamente numerata con **versione/data/ora italiane in alto sulle nove pagine**, backup SQLite, restore-test, rollback e SHA autoupdater riconciliato. La PR #77 CVD rimane **separata** e non va unita automaticamente con questo prototipo.

**Per eseguire i test offline:** `node --test tests/squalincome-freshness.test.js`. GitHub CI li esegue nella PR con Insights checks e Private price engine checks.
