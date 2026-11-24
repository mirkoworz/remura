# REMURA v1.80 LAB · Convergenza V28

Aprire il LAB con un server locale. Dalla radice del repository:

```sh
python3 -m http.server 8079 --bind 127.0.0.1 --directory labs/remura-v28
```

La [Home locale](http://127.0.0.1:8079/) offre l’Experience originale, navigazione, Shark Cockpit, Mercati, Validazione e Fonti. Il browser carica i dati dallo stesso indirizzo del LAB. La versione e l’ora Europe/Rome sono condivise da tutte le viste.

Il manifest e il service worker preparano l’app e gli archivi per la consultazione offline. In **Fonti → App e consultazione offline**, attendere «Copia offline disponibile su questo dispositivo». L’installazione sulla schermata Home di iPhone richiede Safari e un’origine HTTPS raggiungibile dal dispositivo. Il server di prova qui sopra è sul Mac e il collaudo su iPhone fisico resta da eseguire.

## Provenienza

| Cosa usa il LAB | Provenienza verificabile |
| --- | --- |
| COT CFTC, 7 fattori, 28 cross sintetici, 7 riferimenti futures | [Export B](https://github.com/mirkoworz/remura/commit/3ddf1f9308c9b371c448430c015634dae2af4073), blob Git `32a83a644f12c670f61247bfbc1d0c22e61356be`. Report del 10 e 17 novembre 2026, acquisizione del 24/11 alle 10:05:06 CET. Copertura originaria TFF 11/11, Disaggregated 3/3. |
| Myfxbook, 88 simboli del campione retail | [Snapshot pubblico già acquisito](https://github.com/mirkoworz/remura/commit/29a9493a777ea22421bb51b8df830b4a717b0125), blob Git `598adf1bdf2ef1f3a885068c30a9289f522cbf73`. Acquisizione del 24/11 alle 21:21:23 CET. |
| Storico Myfxbook, 34 serie e 3.684 rilevazioni | [Serie pubbliche nello stesso commit](https://github.com/mirkoworz/remura/tree/29a9493a777ea22421bb51b8df830b4a717b0125/data/myfxbook/history). Proiezione esatta di timestamp, percentuale long e percentuale short. Blob LAB `2a4395c0fd0cd4e500f5ac49a154348bf925931e`, 129.034 byte. |
| Experience, nove frame WebP e logo SMF | [Checkpoint Mac v0.22](https://github.com/mirkoworz/remura/commit/57b8612dc30015046f36936e7a9fbf8298f41c88), immagine per immagine dal blob HTML `ebab7141864302c442bd9bcd876faf6d40b731d8`. I dieci asset decodificati coincidono con i file LAB. |
| Regole di lettura del Cockpit | [Checkpoint D v1.78](https://github.com/mirkoworz/remura/commit/8bf2d229b16c5b6eefbdd65e1d2ec9f38680e8f1). Il LAB riprende l’archivio verificato e la divergenza per segno delle variazioni. |

## Prodotto e validazione

**Funzioni descrittive.** La navigazione e gli archivi consultabili funzionano in locale. Il pacchetto CFTC copre due settimane. Storico a 52 settimane, parità privata e attestazione della prima disponibilità restano da acquisire. Squalincome e Ampere attendono archivi utilizzabili.

**Funzioni operative.** Il [checkpoint Contributor v1.10](https://github.com/mirkoworz/remura/commit/f2c1bda8cae7a6fb9e8c342b8995027690f29014) documenta 15 test SQLite, 4 test HTTP, un collaudo browser sul bundle e 103 controlli di regressione superati. Proposte, ricevute e approvazione OWNER restano nel pacchetto con protezione Access e D1. Per la release condivisa servono un collaudo sul Worker dedicato dopo autorizzazione e la prova di entrambe le parti su Safari iPhone fisico.

Lo storico Myfxbook mantiene gli orari osservati. Per 30 simboli il periodo copre il 25 ottobre–24 novembre 2026. Per NAS100, US2000, US30 e US500 copre il 16–22 ottobre. Il selettore a sette giorni usa l’ultima rilevazione di ciascun simbolo come riferimento. Il [run CFTC da 70 settimane](https://github.com/mirkoworz/remura/actions/runs/45206837974) non conserva artefatti scaricabili per ricostruire le serie.

**Ricerca prospettica.** Il [protocollo A](https://github.com/mirkoworz/remura/blob/600c36434ed88d051c3dab61cef11f6b86789bb2/research/REMURA-A-V223-COT-CVD-PROSPECTIVE-PROTOCOL.md) documenta zero decisioni ammesse. Il [run TEST](https://github.com/mirkoworz/remura/actions/runs/45121703188/job/137516719502) conferma 12/12 ricevute di trasporto. Il [checkpoint RAW](https://github.com/mirkoworz/remura/blob/600c36434ed88d051c3dab61cef11f6b86789bb2/research/REMURA-ROADMAP-CHECKPOINT-20261124-V221-CVD-RAW-OWNER-PROOF.md) riporta 13 record osservati dall’OWNER. Il [report prezzi](https://github.com/mirkoworz/remura/blob/600c36434ed88d051c3dab61cef11f6b86789bb2/research/real-proofs/REMURA-A-PRIVATE-PRICE-COVERAGE-OWNER-REPORT-20261123.json) attesta 4/4 coperture M15 ipotetiche a 60m e 4h. L’ultimo termine teorico a 24h è passato il 24/11 alle 06:30 CET. La continuità M15 a 24h resta da attestare. Confronti prospettici maturi a 60m, 4h e 24h: 0/0/0. Alpha N/D.

## Verifica della consegna

```sh
git hash-object labs/remura-v28/data/cot-b223.json labs/remura-v28/data/myfxbook-latest.json labs/remura-v28/data/myfxbook-history.json
git diff --name-only 29a9493a777ea22421bb51b8df830b4a717b0125...HEAD
```

Il riepilogo delle modifiche contiene solo `labs/remura-v28/`. La v1.80 ha superato 32/32 verifiche mirate in Chrome a 390 px. Con rete e risposte del server di prova disattivate, l’app ha riaperto Mercati, letto tutti e tre gli archivi e mostrato l’introduzione con movimento ridotto. Sono stati verificati i 34 simboli storici, le date degli indici, i selettori, la registrazione limitata al percorso LAB e le icone. Il checkpoint Mac conserva la prova Safari dell’Experience originale.

Per ogni nuova versione dell’app o degli archivi, aggiornare insieme il numero e la data nell’intestazione e la versione della cache in `sw.js`. La copia nuova diventa attiva dopo la chiusura delle schede che usano la versione precedente.
