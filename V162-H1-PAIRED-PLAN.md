# REMURA v1.62 — Integrazione H1 comparata post-ingest (candidata, NON LIVE)

**Data:** 03/11/2026. **Stato:** ricerca opt-in separata, non installata.
**Base:** PR #85, commit `d8a79ebc31de741994997cead74a67cf671ca86d`.
**LIVE attestata al passaggio di consegne:** v1.61 applicazione/autoupdater
`106e14a0b58c9e668b421a5982a9ffde22dc9243`.
**Main GitHub:** `a32e8225c0291f10093518ea06655870aa6a7f9b`, commit
figlio della LIVE che aggiorna esclusivamente campioni dati Myfxbook.
Il branch `ROADMAP.md` della PR #80 può contenere aggiornamenti non confluiti:
la versione della roadmap su main non è fonte di stato LIVE senza verifica.

## Obiettivo e interpretazione

Misurare per i soli mercati effettivamente acquisiti in un batch da 1–5
quante H1 risultavano pronte nell'ultima scansione completa e quante H1
risultano pronte dopo l'ingest, **entrambe valutate al medesimo istante UTC**.
Il test non confronta due conteggi globali effettuati in momenti diversi.
`staleToReady` conta mercati effettivamente recuperati; `N/D` significa
informazione incomparabile, non zero e non perdita reale.
Un avanzamento H1 **non dimostra** causalità del batch, abilità previsionale,
movimento istituzionale o opportunità di trading.

## Implementazione

- `REMURA_H1_PAIRED_ENABLED=1` **opt-in e OFF per default**. Richiede già
  `REMURA_SQUALINCOME_AFTER_INGEST_ENABLED=1`, monitor Squalincome attivo,
  collector attivo e sync COT attivo. Nessuna nuova richiesta cTrader,
  nessun nuovo endpoint, nessuna scansione aggiuntiva.
- `scripts/signals_monitor.py`: cattura, soltanto su richiesta interna, i
  metadati H1 presenti nella scansione mirata originaria; UTC identico.
  Comportamento e risposta preesistenti immutati a flag spento.
- `scripts/private_server.py`: sotto il lock della scansione già attiva
  legge l'ultimo snapshot full-scan dal DB in sola lettura, cattura i
  metadati delle stesse 1–5 H1 della scansione post-ingest, applica
  `compare_paired_h1`, poi tenta la registrazione di soli aggregati.
  Se la registrazione non riesce, l'osservazione originaria non fallisce.
- `scripts/h1_paired_store.py`: SQLite privato su DB preesistente, tabella
  `remura_h1_paired`, massimo 256 righe. Registra solo orari UTC e
  `state`, conteggi aggregati pronte prima/dopo, recuperate, avanzate,
  invariate ed età della full-scan. Nessun simbolo, prezzo, broker ID,
  credenziale, segnale o evento. Nella `/private-api/signals/status`
  già esistente compare `h1Paired` soltanto con flag attivo; il riepilogo
  espone solo conteggi, mai righe dettagliate.
- Comparatore immutato della PR #85: massimo 5 target, full-scan esattamente
  34 mercati, distanze UTC valide, H1 almeno 55 barre, soglia 120 minuti.
  Ritardi, future-bar, H1 regredite o snapshot incompleti -> **N/D**.
- Nessuna modifica alle soglie M15/H1/H4, alla rotazione broker, al COT,
  al modello Squalincome, a Radar, alle notifiche o ai permessi web.
- Test automatici: flag OFF, test UTC, 1 solo observer/batch, API broker 0,
  N/D, DB mancante, errori SQLite, limite 256, assenza segreti e regressioni.

## Gate di rilascio PROTETTO v1.62 — NON eseguiti

1. CI Price e Insights su commit candidato; ispezione dei risultati e
   confronto puntuale con PR #85, #83 e #80. Niente merge alla cieca.
2. Conservare SHA codice e dati distinti: main può avanzare solo per dati
   Myfxbook; certificare che nessun codice/app LIVE sia variato prima del
   rilascio. Vietato aggiornare main/deploy/autoupdater durante la ricerca.
3. Preparare installer `release_v162.py` con **lista esatta** dei nuovi
   file, pin Git SHA immutabile e SHA256/blob per tutti i file installati.
   `--check` deve rifiutare qualunque divergenza LIVE/SQLite, permessi
   insufficienti, o CI non verde. Test isolati di copia, ripristino e rollback.
4. Nella release visibile, mostrare **v1.62 e la data/ora effettiva italiana**
   in alto su tutte e nove le pagine; aggiornare cache PWA e verificare
   test release-consistency. Non scrivere ora fittizia di installazione.
5. Prima dell'applicazione LIVE: backup SQLite consistente e restore-test
   verificato, lock autoupdater, preflight read-only, rollback pronto.
   Solo dopo un OK esplicito eseguire installazione controllata e
   riconciliare l'autoupdater al nuovo SHA, senza riattivare un vecchio SHA.
6. Al primo rilascio mantenere `REMURA_H1_PAIRED_ENABLED=0`; attivare solo
   con modifica reversibile e diagnostica privata. Nessun ordine trading.
7. Solo dopo 8+ batch reali verificati, misurare percentuale di confronti
   validi, recuperi H1, N/D e contesto di freschezza. Prima di modificare
   la rotazione provare alternative **a budget API invariato** su campione
   reale e senza alterare soglie.

## Roadmap attiva

P1: risolvere la divergenza freschezza M15/H1/H4 sui 38 mercati.
P2: preservare COT ufficiale e sentiment retail Myfxbook/Capital distinti.
P3: migliorare Radar Squali/Squalincome con qualità dati e storia verificabile.
P4: divergence CVD proxy dichiarando che non è aggressor volume;
backtesting walk-forward purgato, falsi positivi, rischio/rendimento e costi.
P5: notifiche solo dopo evidenza statistica, monitoraggio infrastrutturale
e verifica delle quote **gratis** su Oracle, GitHub, cTrader, Firestore.
