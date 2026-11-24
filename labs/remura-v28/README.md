# REMURA v1.79 LAB · Convergenza V28

Aprire il LAB con un server locale. Dalla radice del repository:

```sh
python3 -m http.server 8079 --bind 127.0.0.1 --directory labs/remura-v28
```

La [Home locale](http://127.0.0.1:8079/) offre l’Experience originale, navigazione, Shark Cockpit, Mercati, Validazione e Fonti. I due archivi sono inclusi e il browser li carica dallo stesso indirizzo del LAB. La versione e l’ora Europe/Rome sono condivise da tutte le viste.

## Provenienza

| Cosa usa il LAB | Provenienza verificabile |
| --- | --- |
| COT CFTC, 7 fattori, 28 cross sintetici, 7 riferimenti futures | [Export B](https://github.com/mirkoworz/remura/commit/3ddf1f9308c9b371c448430c015634dae2af4073), blob Git `32a83a644f12c670f61247bfbc1d0c22e61356be`. Report del 10 e 17 novembre 2026, acquisizione del 24/11 alle 10:05:06 CET. Copertura originaria TFF 11/11, Disaggregated 3/3. |
| Myfxbook, 88 simboli del campione retail | [Snapshot pubblico già acquisito](https://github.com/mirkoworz/remura/commit/29a9493a777ea22421bb51b8df830b4a717b0125), blob Git `598adf1bdf2ef1f3a885068c30a9289f522cbf73`. Acquisizione del 24/11 alle 21:21:23 CET. |
| Experience, nove frame WebP e logo SMF | [Checkpoint Mac v0.22](https://github.com/mirkoworz/remura/commit/57b8612dc30015046f36936e7a9fbf8298f41c88), immagine per immagine dal blob HTML `ebab7141864302c442bd9bcd876faf6d40b731d8`. I dieci asset decodificati coincidono con i file LAB. |
| Regole di lettura del Cockpit | [Checkpoint D v1.78](https://github.com/mirkoworz/remura/commit/8bf2d229b16c5b6eefbdd65e1d2ec9f38680e8f1). Il LAB riprende l’archivio verificato e la divergenza per segno delle variazioni. |

## Prodotto e validazione

**Funzioni descrittive.** La navigazione e gli archivi consultabili funzionano in locale. Il pacchetto CFTC copre due settimane. Storico a 52 settimane, parità privata e attestazione della prima disponibilità restano da acquisire. Squalincome e Ampere attendono archivi utilizzabili. Un passaggio verso una release condivisa richiede l’integrazione autorizzata del filone C, il collaudo dei ruoli sul server previsto e la prova di questa integrazione su Safari iPhone fisico.

**Ricerca prospettica.** Il [protocollo A](https://github.com/mirkoworz/remura/blob/600c36434ed88d051c3dab61cef11f6b86789bb2/research/REMURA-A-V223-COT-CVD-PROSPECTIVE-PROTOCOL.md) documenta zero decisioni ammesse. Il [run TEST](https://github.com/mirkoworz/remura/actions/runs/45121703188/job/137516719502) conferma 12/12 ricevute di trasporto. Il [checkpoint RAW](https://github.com/mirkoworz/remura/blob/600c36434ed88d051c3dab61cef11f6b86789bb2/research/REMURA-ROADMAP-CHECKPOINT-20261124-V221-CVD-RAW-OWNER-PROOF.md) riporta 13 record osservati dall’OWNER. Il [report prezzi](https://github.com/mirkoworz/remura/blob/600c36434ed88d051c3dab61cef11f6b86789bb2/research/real-proofs/REMURA-A-PRIVATE-PRICE-COVERAGE-OWNER-REPORT-20261123.json) attesta 4/4 coperture M15 ipotetiche a 60m e 4h. L’ultimo termine teorico a 24h è passato il 24/11 alle 06:30 CET. La continuità M15 a 24h resta da attestare. Confronti prospettici maturi a 60m, 4h e 24h: 0/0/0. Alpha N/D.

## Verifica della consegna

```sh
git hash-object labs/remura-v28/data/cot-b223.json labs/remura-v28/data/myfxbook-latest.json
git diff --name-only 29a9493a777ea22421bb51b8df830b4a717b0125...HEAD
```

Il riepilogo delle modifiche contiene solo `labs/remura-v28/`. Il collaudo della nuova integrazione ha superato 33/33 controlli in Chrome a 390 px, inclusi navigazione, lettura locale degli archivi, versione e ora, riproduzione, salto e movimento ridotto. Il controllo DOM separato ha verificato 42 righe COT, 88 righe Myfxbook, ricerca e isolamento di un archivio in errore. Il precedente checkpoint Mac conserva la prova Safari dell’Experience originale.
