# REMURA — Candidato backend + vista iPhone stati di freschezza Squalincome (NON LIVE)

**03/11/2026 · PR #78 in ricerca, NON installata.** REMURA live resta **v1.59** con SHA `e924f4cf6f1a384fd84a3cef66c89a16e35de3fd`. Il backend nel **ramo candidato** ora contiene nuove letture di metadata, mentre il backend LIVE, Oracle VPS, autoupdater, notifiche e servizi broker non sono stati modificati.

## Diagnosi alla base

La diagnostica privata #31 (`41611353786`) ha osservato alle 09:19:07 UTC **8 H1 sopra 120 minuti, 8 H4 sopra 300, M15 zero sopra 180**, pur con H1 coerenti con l'ora teorica consentita dalla M15. Il simulatore privato PR #17 (`remura-collector`) ha riprodotto il fenomeno matematicamente con una rotazione **ideale** di otto gruppi in due ore, senza chiamate broker. **Non significa che sappiamo già quali batch successivi si completeranno realmente.**

## Tre stati leggibili, distinti da un segnale

| Stato | Condizioni | Cosa può fare REMURA |
| --- | --- | --- |
| `price_live_ready` · **Dati prezzo idonei alla verifica live** | Integrità verificata, sorgente recente, almeno 55 candele per M15/H1/H4; tutte le rispettive chiusure UTC coerenti e entro 180/120/300 minuti; metadata qualità dello stesso snapshot e scansione recentissima | Un eventuale backend può **solo proseguire** con gli ulteriori gate COT e struttura. **Non è** un segnale BUY/SELL |
| `waiting_verified_batch` · **In attesa del batch verificato** | Prezzi storici corretti ma almeno un timeframe oltre soglia e prova dal collector di un successivo batch atteso, non ancora scaduto. È **sempre non live** | Mostrare spiegazione, storico e prossima occasione di aggiornamento se **attestata dal server**. Mai promuovere eventi nuovi |
| `price_stale` · **Dati fuori soglia** | Integrità verificata ma H1/H4/M15 superano le soglie e **non** è provata una schedulazione prossima valida | Conservare storico, escludere nuove conferme live |
| `unverified` · **Dati non verificabili** (stato di sicurezza aggiuntivo) | Qualità o timestamps non dimostrabili, storico insufficiente, weekend, snapshot troppo vecchio o fonti non sincronizzate | Nessuna conferma live e nessuna etichetta ingannevole "in attesa" |

`squalincome-freshness-core.js` è ora **caricato solo da `mercati.html` nel ramo candidato**; la sua risorsa è inserita nell'allowlist privata e nel precache PWA del ramo. Non è ancora distribuito sulla VPS v1.59. I test `tests/squalincome-freshness.test.js` verificano anche che **ogni** uscita riporti `signalAuthorized:false`, perché questo modulo *non* analizza COT, non genera eventi, non inferisce posizioni istituzionali e non deve autorizzare ordini.

## Contratto obbligatorio per una eventuale UI live futura

Il classificatore richiede:
- `scanAt`, `observedAt`: tempi UTC/offset espliciti; `observedAt-scanAt` non può superare **20 minuti**;
- `frames.M15/H1/H4.lastClosedAt`, `.bars`: derivati dalle candele realmente verificate dalla VPS, non dal dispositivo; richiede almeno **55** per timeframe; è controllata la sequenza dei timeframe e il timestamp di chiusura;
- `priceQuality.integrity === verified`, `priceQuality.freshness === recent`, `priceQuality.ready === true`, con `checkedAt` coincidente col full scan (entro **1 secondo precedente**): questo evita di unire erroneamente GET che descrivono momenti diversi;
- opzionale `batch` con `provenance:server_collector_schedule`, `state:running`, `lastOutcome:ok`, `lastSuccessfulCollectionAt` non precedente all'ultima M15 e `nextExpectedAt` in futuro, entro 120 minuti dal precedente successo. **Non** è un orario stimato dallo storico.

**Stato del collegamento nel candidato PR #78:** `scripts/signals_monitor.py` salva `priceQuality` (solo `integrity`, `freshness`, `ready`, `checkedAt`) **insieme** ai `timeframes` e al `lastScanAt` della stessa scansione completa. `serverTime` arriva dal medesimo GET `/private-api/signals/status`: la UI legge così lo stesso snapshot, non unisce le due API con orari diversi. I controlli originali sono riutilizzati durante la scansione, senza chiamate broker in più. Lo scan mirato post-ingest **non sovrascrive** lo snapshot completo. La UI mostra i contatori di prezzo separati dagli idonei COT/prezzo e i singoli stati nelle righe M15/H1/H4. **La VPS v1.59 non espone ancora questi campi**: senza installazione della release proposta o con un GET di oltre 20 minuti, l'interfaccia deve mostrare `unverified`. 

**Limite intenzionale:** nessun `nextExpectedAt` per singolo mercato è ancora attestato dal collector nella v1.59, né aggiunto da questa PR. Il classificatore conserva il supporto `waiting_verified_batch` per il futuro, ma **nella schermata attuale di candidatura la sua conta sarà zero**. Non inventare questa informazione usando il ritmo medio dei batch. Dopo test separati della schedulazione si potrà integrare, se il server saprà garantirne la provenienza.

## Sicurezza e rollout

- Soglie originali **M15 180, H1 120, H4 300 minuti**, senza rilassamenti.
- Non inventare `nextExpectedAt` da `lastAttempt + 120 min`: l'orario è variabile e il tentativo può fallire.
- Non usare questo classificatore per riemettere vecchi eventi o spostare `price_time` delle osservazioni.
- Prima della release, verificare con snapshot e test di integrazione che la qualità per mercato e il timestamp provengano dallo stesso record e dalla stessa scansione. La continuità H1/H4 è già oggetto dei controlli `audit_market`, ma le date future, le sessioni speciali e i fallimenti del collector devono restare fail-closed. Monitorare overhead della scansione VPS, quote API invarianti e controllo costi.
- Solo dopo CI e validazione, creare una release esplicitamente numerata con **versione/data/ora italiane in alto sulle nove pagine**, backup SQLite, restore-test, rollback e SHA autoupdater riconciliato. La PR #77 CVD rimane **separata** e non va unita automaticamente con questo prototipo.

**Test offline:** `node --test tests/squalincome-freshness.test.js tests/squalincome-diagnostics.test.js` e `python -m unittest discover -s tests -p 'test_signals_monitor.py' -v`. Le due CI GitHub Insights e Private Price Engine hanno superato i test del collegamento su PR #78. Non esiste ancora un risultato LIVE di questa versione; non promuovere il candidato automaticamente.
