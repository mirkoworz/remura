# REMURA — TRACK A: Qualità H1 e raccolta prezzi

**Ultimo stato attestato:** 04/11/2026 ore 10:47 Italia (3/3 H1 stale = 3/3 H4 stale = 3/3 prices_stale: AUDCAD/AUDCHF/AUDJPY; H1 avanzate di 2h tra 2 full-scan). **Roadmap coordinatrice:** [ROADMAP.md](ROADMAP.md). **Track parallelo:** [B — Shark Science](ROADMAP-B-SHARK-SCIENCE.md).

## 04/11/2026 ore 07:15 Italia — verifica A1 GitHub e replay offline (NON misura LIVE nuova)

**Controlli eseguiti sul branch A, senza accesso SSH, senza broker/API nuovi e senza deploy:**
- Branch `research/track-a-h1-20261104` e GitHub `main` sullo SHA `43829313b41813776017e4a43a20204052a360bd` alla verifica; il ramo B lavora separatamente. Lo SHA corrente GitHub non sostituisce lo SHA LIVE `1568edefabc7bbdb7d06485d2b863b196a4e6155`.
- `remura-collector` PR [#22](https://github.com/mirkoworz/remura-collector/pull/22) e [#23](https://github.com/mirkoworz/remura-collector/pull/23) **merged**, controlli offline di PR **success**. La diagnostica programmata è su `main` con `37 6 * * 1-5` UTC (07:37 Italia il 04/11), condizionata a `REMURA_VPS_DIAG_ENABLED=1`. **Al controllo delle 07:15 non era ancora presente un run `schedule` della diagnostica dopo il merge**; i run CI PR non interrogano la VPS. Il primo run automatico effettivo e il suo risultato vanno verificati, non presunti.
- Il **solo campione LIVE H1 paired attestato** resta quello delle 20:54 del 03/11: `samples=1`, `comparableSamples=1`, `unverifiableSamples=0`, `5→5`, `staleToReady=0`, `h1Advanced=0`, `h1Unchanged=5`. **NON si afferma che oggi i campioni siano ancora uno**: non è stato ancora letto un nuovo snapshot della VPS. A1 e A2 **non completati**.
- Revisionati `scripts/private_server.py`, `scripts/price_feed.py`, `scripts/price_store.py`, `scripts/h1_batch_comparison.py` e il vecchio report privato [#31](https://github.com/mirkoworz/remura-collector/actions/runs/41611353786). Il codice ricostruisce H1 da 4 M15 UTC contigue e complete, H4 da 16. Nel #31 tutti gli 8 H1 stale erano coerenti con l'ora teorica ricavabile dall'ultima M15; questo **non esclude** gap H4 o cause nuove, da verificare con campioni recenti.
- La pianificazione prioritaria attuale ha 8 batch × 5 = **40 acquisizioni programmate/2 ore** (38 strumenti unici; EURUSD/XAUUSD 2 volte), non 40 GET effettivi garantiti. Il post-ingest riusa SQLite e la full-scan resta distinta. Una nuova rotazione **non è giustificata** dai soli aggregati storici.

**Replay locale di sola matematica, 04/11 (dati sintetici, non mercato reale):**
- 38 strumenti teorici, 8 gruppi da 5 con due priorità ripetute, 96 scansioni ogni 15 minuti in 24h = **3648 valutazioni sintetiche**; soglie invariate M15=180m, H1=120m, H4=300m, tutte le M15 disponibili in modo ideale al batch. Nessuna chiamata API e nessun accesso Oracle.
- Scansione teorica sul minuto esatto `:00`: `H1 stale=360/3648`, `H4 stale=90/3648`, `M15 stale=0`. Scansione quattro minuti dopo: `H1 stale=720/3648`, `H4 stale=180/3648`, `M15 stale=0`. **Queste cifre NON sono osservazioni dei 34 mercati LIVE** e mostrano quanto il conteggio cambi vicino alle soglie con l'ora di lettura, senza recuperare una sola candela.
- Permutando soltanto i 36 strumenti non prioritari fra i medesimi slot, mantenendo esattamente 40 acquisizioni programmate/2h, i **totali sintetici restano invariati** nelle fasi 0, 4 e 14 minuti: cambiano i nomi dei mercati penalizzati, non il numero complessivo. Spostare la scansione per far risultare "verde" un contatore **non è una correzione della freschezza**; serve prova LIVE prima di cambiare pianificazione.

**Prossima verifica A1 obbligatoria:** leggere tramite la diagnostica privata schedulata (quando realmente eseguita) o una singola GET locale read-only `/private-api/signals/status` gli aggregati `h1Paired` (totali, validi, N/D, last UTC, readyBefore/After, staleToReady, h1Advanced, h1Unchanged); leggere la full-scan dei 34 al suo timestamp e l'ultimo stato batch. Confrontare età di ogni H1 con M15/H4, fasi UTC e mercati precedentemente problematici. Se >=8 record totali ma validi insufficienti, **proseguire l'osservazione**. Non modificare codice operativo, quote, soglie, cron o produzione sulla base del replay.

## 04/11/2026 ore 10:47 Italia — A3 finale: coincidono esattamente i tre insiemi stale

**Fonte:** screenshot dell'utente dal comando GET locale read-only `/private-api/signals/status`, eseguito alle 10:47 italiane e riferito alla medesima *full-scan* salvata delle `2026-11-04T09:38:17.703163+00:00` (10:38:17 Italia). Nessuna nuova chiamata cTrader.

- `M15_STALE = NESSUNO`.
- `H1_STALE = AUDCAD, AUDCHF, AUDJPY`.
- `H4_STALE = AUDCAD, AUDCHF, AUDJPY`.
- `PREZZI_STALE = AUDCAD, AUDCHF, AUDJPY`.
- Intersezione H1∩H4 = **3/3**, ed è identica alle esclusioni `prices_stale`; non sono 9 strumenti distinti. **La coincidenza mancava nell'A6 e ora è verificata**.
- Per ciascuno: `M15_age≈113,3m` (**entro** soglia 180m), `H1_age≈158,3m` (**oltre** 120m), `H4_age≈338,3m` (**oltre** 300m). Tutti i timestamp sono relativi alla stessa full-scan UTC.
- Le chiusure corrispondono a M15 **07:45 UTC**, H1 **07:00 UTC**, H4 **04:00 UTC**. La H1/H4 successiva chiuderebbe alle **08:00 UTC**, ma la M15 più recente disponibile alla scansione chiude alle **07:45 UTC**: manca almeno il quarto d'ora finale necessario per completare il bucket orario/quadrorario, senza imputare automaticamente un *gap anomalo*. Non creare né anticipare artificiosamente la 08:00.
- **Confronto longitudinale utile per gli stessi tre mercati**: alla precedente full-scan `2026-11-04T07:22:50 UTC` la H1 era vecchia di ≈142,8m (chiusura ≈**05:00 UTC**); alla nuova full-scan `09:38:17 UTC` la H1 ha chiusura ≈**07:00 UTC**. La chiusura reale H1 è dunque **avanzata di due ore** fra le due fotografie, pur risultando ancora temporaneamente stale al secondo controllo. Questo dimostra che non è una H1 definitivamente bloccata per questi tre strumenti; **non certifica** esattamente a che secondo il batch sia arrivato.
- L'osservazione rafforza la causa principale **rotazione dei batch ~120m + chiusure UTC + soglie genuine**. Non dimostra un bug nel rollup né un'API rotta; test precedenti della coorte GBP/EUR delle 09:23→09:48 avevano già mostrato 8/8 H1 avanzate/fresche dopo il batch, senza anomalie di rollup sul controllo mirato.
- **Limite residuo:** questo audit riguarda mercati/fotografie di una sessione aperta, non ogni futura chiusura di mercato, weekend o incongruenza H4; casi futuri anomali devono tornare `N/D` o `stale` fino a prova, senza presunzione di innocuità.

**Decisione di uscita TRACK A per le cause H1 osservate:** A3 completato per i casi attuali; A4 simulazione a pari budget già documentata, A5 = **nessun fix necessario e nessuna release**, A6 rapporto con metriche LIVE completato. L'ottimizzazione del **solo numero mostrato nella full-scan** sarebbe cosmetica; i dati post-ingest reali vengono già verificati dal monitor esistente. Lasciare la PR A #88 **draft e isolata** finché non si coordina il merge documentale con TRACK B #89, senza toccare la VPS o i banner v1.62. Continuare a sorvegliare disponibilità e quote nel normale monitor, senza nuovo cron o richieste broker. La fatturazione Oracle/GitHub/Firestore rimane **non verificata** dai soli contatori tecnici.

## 04/11/2026 ore 10:43 Italia — A6: audit multisistema LIVE M15/H1/H4 + risorse

**Fonte reale:** screenshot Termius utente, 4 novembre 2026 ore 10:43 italiane, 2 GET *locali* in sola lettura `/private-api/signals/status` e `/private-api/resources`. Data **dello snapshot full-scan**: `2026-11-04T09:38:17.703163+00:00` (**10:38:17 Italia**); non confondere con l'ora della successiva lettura o con altri snapshot del mattino.

| Metrica reale dello snapshot | Dato attestato |
| --- | ---: |
| Strumenti Squalincome | 34 |
| M15 pronte / stale / N/D (soglia 180m) | **34 / 0 / 0** |
| H1 pronte / stale / N/D (soglia 120m) | **31 / 3 / 0** |
| H4 pronte / stale / N/D (soglia 300m) | **31 / 3 / 0** |
| `prices_stale` (dalle `exclusionReasons`) | **3** |
| `cot_group_conflict` / `cot_no_direction` / `price_no_direction` | **14 / 9 / 16** |
| Batch registrati in finestra telemetrica | **79** |
| Acquisizioni nominali pianificate / salvate | **395 / 395** |
| Post-ingest successi / errori | **79 / 0** |
| RAM usata / totale | **0,28 / 0,93 GiB** |
| Disco usato / totale | **3,54 / 44,07 GiB** |
| Nuove chiamate cTrader dovute a questo audit | **0** |

**Interpretazione:** 395/395 sono **salvataggi nominali per strumenti pianificati**, NON conteggio effettivo di richieste a cTrader (paginazione, retry, sorgenti di backup), né garanzia per futuri batch. `79` è il numero dei campioni nella finestra corrente, non una misura di uptime permanente. I tre `prices_stale` e le tre H1/H4 stale **non sono ancora abbinati per simbolo**, pertanto non sostenere che si tratti precisamente degli stessi tre mercati. I contatori `exclusionReasons` sono **motivi potenzialmente multipli per mercato**: non sommare `14+9+16+3` per dichiarare 42 mercati esclusi. Esclusioni legate a COT o direzione non sono difetti di raccolta prezzi.

**Confronto temporale reale:** il precedente controllo full-scan delle 09:23 italiane aveva **8 H1 stale**; gli stessi otto risultavano **8/8 H1 avanzate e fresche** dopo il loro giro di raccolta alle 09:48 (test su SQLite read-only, 0 anomalie M15→H1 nel controllo). Il nuovo snapshot delle 10:38 italiane ha **3 H1 stale**, ma **non dimostra** che si tratti delle stesse coorti né un progresso permanente o causato da modifiche, perché **nessuna ottimizzazione LIVE è stata distribuita**. Il monitor post-ingest era già attivo prima dell'audit; non attribuire `8→3` a un fix inesistente.

**Capacità/costi:** RAM e disco mostrano margine ma non certificano affatto fatturazione **Oracle Always Free**, quote cTrader, quota Actions condivisa, Firestore o traffico mensile OCI; tali dati richiedono i pannelli dei provider. Non creare ulteriori workflow/cron per colmare questa lacuna, non dichiarare costo zero certificato. Nel repository privato `remura-collector` PR #22/#23 sono integrate ma al controllo GitHub di oggi **non risulta ancora un run diagnostico `event=schedule`**: la raccolta batch LIVE non equivale alla riuscita del workflow schedulato GitHub.

**Esito A6:** rapporto multidimensionale **completato per la fotografia documentata**, senza miglioramento operativo attribuibile e senza bug persistente dimostrato. Restano **due limiti da chiudere in A3**, se vogliamo classificazione diagnostica affidabile delle residuali: (i) individuare tramite **una sola GET già esistente** i simboli di M15/H1/H4 stale e se coincidono con `prices_stale`; (ii) correlare alle sessioni, ultime M15 contigue, esito e turno del batch. A5 = **nessuna correzione backend giustificata**; non cambiare soglie, rotazione, API, versione o VPS. Un'eventuale presentazione "H1 stale / probabile attesa batch" va studiata offline senza convertire stale in READY.

## 04/11/2026 — A4 confronto offline a budget invariato: nessun fix operativo giustificato

**Benchmark già disponibile, non ripetere codice:** [PR privata collector #19](https://github.com/mirkoworz/remura-collector/pull/19), simulazione al secondo del collector **8×5=40 acquisizioni nominali ogni 120 min** contro le stesse 40 nella disposizione alternativa; **34 mercati monitorati**. Le 40 acquisizioni nominali sono del modello prioritario/rotazione esistente, NON una misura delle richieste API reali (bootstrap, paginazione e backup possono richiederne di più).

| Scenario sintetico PR #19 | Acquisizioni pianificate / 2h | H1 escluse medie teoriche su 34 in una scansione |
| --- | ---: | ---: |
| Lettura appena prima dell'ingest (+104 sec dal quarto, durata fittizia 18s) | 40 | 10,5 |
| Lettura dopo l'ingest (+150 sec dal quarto, durata fittizia 18s) | 40 | 6,5 |
| Lettura dopo l'ingest, durata fittizia 29s | 40 | 6,5 |
| Dopo ingest, ordine gruppi alternativo | 40 | 6,0 |

**Limiti decisivi:** tutti gli esiti della tabella sono sintetici, assumono M15 ideali contigue e durate ipotetiche; `10,5→6,5` riflette soprattutto **il momento della fotografia**, non maggiori informazioni fornite dal broker o minor latenza effettiva del primo segnale. `6,5→6,0` trasferisce il rischio fra mercati; non rappresenta vantaggio dimostrato. **Mai usare questi numeri come impatto LIVE o P&L.** La raccolta di riferimento senza doppie priorità sarebbe 38 strumenti/2h; cambiare da 40 a 38 non è un test a budget pari e potrebbe penalizzare EURUSD/XAUUSD.

**Confronto con prova LIVE attuale:** `50/50` paired comparabili, `185/226` transizioni stale→ready fra foto precedente e post-ingest (sulla stessa UTC); 8/8 strumenti stale alle 09:23 con nuove H1 fresche dopo la successiva raccolta alle 09:48, 0 anomalie del controllo H1. Dunque il monitor post-ingest già implementato agisce sulla disponibilità reale delle candele salvate; non è provato che cambiare ordine o fase migliori la **prima disponibilità** dei dati. Non mettere in produzione alcuna modifica alla schedulazione.

**Decisione A4:** valutazione offline completata per questo scenario; conservare ritmo e soglie, **nessun fix backend H1 identificato**. Un futuro miglioramento può essere solo sulla **chiarezza degli stati visualizzati** (freschezza live vs vecchio snapshot full-scan vs possibile attesa proprio batch), inizialmente come progetto offline, senza trasformare `stale` in `ready` e senza cambiare strategie. A5 allo stato = `NON NECESSARIO`; v1.62 LIVE invariata, nessun costo aggiuntivo o nuova chiamata autorizzati. A6 rimane aperto per risorse, API e M15/H1/H4 nella stessa nuova fotografia e valutazione delle esclusioni.

## 04/11/2026 ore 09:48 Italia — A3: recupero degli 8 mercati verificato nel ciclo successivo

**Evidenza di follow-up LIVE (screenshot Termius utente, lettura SQLite `mode=ro`):** controllo alle `2026-11-04T08:48:16.619986+00:00`, 09:48:16 Italia, sugli **stessi 8 mercati** che alle 09:23 italiane risultavano H1 stale. Il controllo interroga soltanto la SQLite locale, senza nuove richieste cTrader né modifiche:
- `TENTATIVI=8`: per tutti gli otto è stato registrato un **nuovo tentativo** rispetto alla full-scan `2026-11-04T08:23:02 UTC`. Negli output per mercato visibili, `ESITO=ok` per tutti.
- `AVANZATE=8`: l'ultima chiusura H1 registrata per ciascuno è **successiva alle 06:00 UTC** pre-controllo. La loro età alla lettura risulta circa **48,3 minuti**, coerente con chiusura UTC circa 08:00. `FRESCHE=8`: tutte entro la soglia **immutata di 120 minuti**, con almeno 55 H1 secondo il gate usato dal comando.
- `ANOMALIE=0`: il test mirato non trova alcuna H1 più arretrata rispetto all'ultima ora completa ricavabile da quattro M15 contigue presenti negli ultimi 32 record. Non è audit retroattivo di tutte le H4 né prova di assenza di ogni possibile gap storico.
- Le due coorti viste alle 09:30 (tentativi `06:31/06:46 UTC`, H1 stale all'atto della full-scan `08:23 UTC`) vengono dunque **recuperate dopo un nuovo tentativo di raccolta** nella successiva finestra osservata. Questo dimostra concretamente che la condizione stale di quegli 8 era **transitoria**, non permanentemente bloccata. Non attribuisce con precisione al secondo il momento del salvataggio, né dimostra automaticamente che tutte le future esclusioni abbiano la stessa causa.

**Decisione tecnica A3:** causa prioritaria per questa coorte è la **fase delle acquisizioni a gruppi (rotazione ~120 minuti) rispetto alla full-scan di tutti i 34** e alla soglia H1 rigida di 120 minuti. Confronti paired LIVE precedenti: 50/50 campioni validi, 185 transizioni stale→ready su 226 confronti ripetuti; nessun N/D. La contiguità M15 e assenza anomalia sono verificate limitatamente al test di follow-up; nessun bug UTC/DST o rollup H1 dimostrato. **A3 completato per gli 8 mercati di questa verifica; monitoraggio di altre sessioni/market closures/H4 rimane distinto.**

**Decisione A4/A5 per ora:**
1. **Non serve correggere il rollup né innalzare le soglie.** Il sistema recupera da sé i gruppi osservati; un fix senza un difetto dimostrato introdurrebbe rischio inutile.
2. Non spostare soltanto la full-scan per rendere più gradevole il conteggio H1. La full-scan deve restare una fotografia *as-of* con soglie genuine; l'osservatore post-ingest esistente ha già mostrato 50 confronti validi.
3. Studiare **solo offline** una presentazione più leggibile dei due stati separati: `H1 attualmente non idonea` (vero) e `compatibile con attesa del prossimo batch` (ipotesi condizionata a timestamp, fonte primaria e ultima riuscita). Non mostrare mai `READY` a chi è sopra 120 minuti, né promettere l'ora del prossimo tentativo; le sessioni chiuse hanno un trattamento separato.
4. Prima di ogni eventuale rilascio chiedere ulteriori prove sulla freschezza dei 34 mercati, sulle H4, sugli errori di provider e sui consumi. Il beneficio misurato di una diversa UI/stato deve essere reale. Nessun aumento cTrader oltre gli 8 batch già previsti, nessuna nuova API/cron, nessun deploy in parallelo al TRACK B.
5. **Criterio A5:** senza problema operativo dimostrato, chiudere il fix come `NON NECESSARIO` anziché generare artificialmente una release. Il TRACK A può proseguire con rapporto A6 e verifiche di budget senza modifiche LIVE.

## 04/11/2026 ore 09:30 Italia — A3: otto H1 stale in due coorti, tentativi OK

**Fonte reale:** screenshot lettura privata `/private-api/signals/status` e `/private-api/prices/status`, senza chiamate broker aggiuntive, eseguita dall'utente 04/11 ore 09:30 Italia. La scansione full-scan `2026-11-04T08:23:02.710633+00:00` (= **09:23:02 Italia**) aveva **8/34 H1 oltre soglia**:
`EURJPY`, `EURNZD`, `GBPAUD`, `GBPCAD`, `GBPCHF`, `GBPJPY`, `GBPNZD`, `GBPUSD`.

- Tutti e otto: **fonte `primary`, ultimo esito `ok`, ultimo tentativo registrato prima della scansione**. Cinque (`EURJPY,EURNZD,GBPAUD,GBPCAD,GBPCHF`) con `lastAttempt≈06:31:30 UTC`; tre (`GBPJPY,GBPNZD,GBPUSD`) con `lastAttempt≈06:46:30 UTC`. Questi sono timestamp dell'ultimo *tentativo* riportato dallo status letto dopo la full-scan, non timestamp esatti di commit candela o prova definitiva dello stato alle 08:23. Il test conferma che a lettura 09:30 non compariva un tentativo successivo per questi otto.
- A `08:23:02 UTC`, **H1 ≈143 minuti**, **M15 ≈98–113 minuti**, **H4 ≈263 minuti**. Soglie inalterate: H1 120m (**stale**), M15 180m (**entro**), H4 300m (**entro**). Chiusura ultima H1 coerente con le **06:00 UTC**, timestamp M15 coerente con ultime chiusure **06:15** o **06:30 UTC**; questo spiega la divergenza tra età M15 e H1 senza postulare bug UTC/DST.
- I valori `lastComplete` stampati da `prices/status` rappresentano **l'apertura dell'ultima M15**, e sono stati letti *dopo* la scansione. Non scambiarli per la sua chiusura né per un campione storico perfettamente simultaneo alla full-scan.
- Il ciclo di raccolta attuale è nominalmente **120 minuti per gli strumenti non duplicati**. Se il gruppo delle 06:31:30/06:46:30 si ripete puntualmente, i **prossimi tentativi previsti** sarebbero intorno alle **08:31:30 e 08:46:30 UTC** (09:31 e 09:46 Italia), **dopo la scansione** delle 08:23. Questa è una previsione di *schedule*, NON una prova che il batch sia effettivamente riuscito o che la prossima H1 divenga eligible. Non aggiungere timer/polling per verificarla.
- Gli otto simboli sono coerenti con **due gruppi consecutivi** di aggiornamento, uno di cinque e uno di tre osservati da Squalincome, ma lo slot/market mapping effettivo non è qui verificato. Un ultimo esito `ok` non prova continuità di ogni candela M15, integrità completa H4 o assenza di errori futuri.
- Evidenza ora **fortemente favorevole al disallineamento temporale fra full-scan, batch e rollup H1** come causa principale dei gruppi stale che ruotano; **nessun errore UTC, corruzione OHLC o sorgente primaria difettosa dimostrato**. Il comportamento non giustifica modifiche di soglia, API, scheduling o banner.

**Gate A3 successivo (una lettura, no polling):** confrontare per questi otto strumenti le coppie `lastAttempt`/`lastOutcome` e la reale ultima H1 chiusa **dopo il successivo slot** attraverso SQLite read-only o le GET private esistenti. Contare `nuovo tentativo`, `ingest riuscito`, `H1 avanzata`, `H1 ancora stale` all'istante del nuovo controllo; non confrontare timestamp da scansioni diverse come se fossero simultanei. Se il giro successivo conferma tutti gli 8 aggiornati con H1 genuina, A3 può concludersi per questa coorte, quindi A4 deve verificare offline una migliore **informazione sullo stato di attesa del batch** e il tempo fino al post-ingest, non spostare le letture per rendere verdi dati vecchi.

## 04/11/2026 ore 09:08 Italia — A3: 50 campioni paired ripartiti sui veri 8 slot

**Fonte osservata:** comando locale read-only dell'utente su SQLite privata `remura_h1_paired` LEFT JOIN `remura_batch_timing` sulla stessa `ingest_returned_utc`, massimo 64 record; output terminale delle 09:08 italiane. Il codice ha attestato `SOLO_LETTURA=OK` e `CHIAMATE_BROKER_AGGIUNTIVE=0`. Campioni effettivamente presenti: **50**, ultimo `2026-11-04T08:01:47.071618+00:00` (**09:01:47 Italia**); **50 validi, 0 N/D, 0 senza slot**. Il JOIN individua un batch corrispondente per tutti i campioni letti; non attribuire automaticamente un singolo batch come unica causa di tutte le variazioni.

| Slot batch | Validati | N/D | H1 pronte prima | H1 pronte dopo | Stale→ready | Mediana distanza full-scan→paired (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 7 | 0 | 17 | 35 | 18 | 580 |
| 2 | 7 | 0 | 5 | 35 | 30 | 601 |
| 3 | 6 | 0 | 0 | 24 | 24 | 621 |
| 4 | 6 | 0 | 5 | 30 | 25 | 607 |
| 5 | 6 | 0 | 14 | 30 | 16 | 604 |
| 6 | 6 | 0 | 0 | 24 | 24 | 600 |
| 7 | 6 | 0 | 0 | 24 | 24 | 598 |
| 8 | 6 | 0 | 0 | 24 | 24 | 606 |
| **Totale** | **50** | **0** | **41** | **226** | **185** | — |

**Interpretazione prudente, senza falsi positivi:**
- `226` rappresenta **osservazioni ripetute di mercato**, non 226 mercati unici o operazioni; alcuni mercati possono essere raccolti due volte per giro. `185` sono transizioni *stale→ready* a parità di orologio di valutazione UTC, cioè **81,9% delle 226 comparazioni**, non una percentuale di profitto. I conteggi sono internamente coerenti `41+185=226`.
- L'età `full_scan_age_seconds` di circa **580–621 secondi** è la **distanza fra il full-scan salvato e il momento del confronto**, NON l'età della candela H1. Una scansione generale può essere distante ~10 minuti dall'analisi post-ingest: la coorte raccolta nel frattempo presenta H1 autenticamente nuove, mentre la vecchia fotografia generale resta ancorata alla situazione precedente.
- Recuperi osservati in **tutti gli otto slot**; in tutti i 50 confronti validi gli H1 dei gruppi confrontati erano ready *dopo*. Questo **non** dimostra che 34/34 H1 siano ready contemporaneamente nella full-scan, né misura la disponibilità continua del prezzo. L'ultima full-scan attestata precedentemente era 27/34 ready alle 08:22:50 italiane; i due dati misurano popolazioni e tempi differenti.
- L'associazione esatta `post_utc`/batch, il numero di slot ripetuti e la coerenza di timestamp H1/M15 rendono la **fase di raccolta vs fotografia periodica** l'ipotesi di lavoro principale. Senza un controllo temporale per mercato e presenza delle 4 M15 contigue, nessuna affermazione definitiva sulla causa esclusiva di ogni H1 stale. Non allentare soglia 120 minuti, non ritardare artificialmente il full scan per ottenere più verdi.
- Riusare il replay in PR collector [#19](https://github.com/mirkoworz/remura-collector/pull/19) e i test UTC/DST in PR app [#84](https://github.com/mirkoworz/remura/pull/84), **non fare deploy dei branch datati**. Nessun bisogno dimostrato di nuove richieste cTrader, provider o Firebase.

**Prossimo gate mirato A3:** confrontare, usando la GET privata `/private-api/prices/status` **già esistente** e il medesimo timestamp UTC di lettura, `lastAttempt`, `lastOutcome`, `lastComplete` e stato H1/M15/H4 per i **7 stale identificati alle 08:22:50**; verificare se l'ultimo `lastAttempt` è antecedente al proprio slot e se provider, sessione o errori spiegano un dato rimasto vecchio. I sette possono essere già cambiati: NON trattarli come stale attuali senza una nuova fotografia. Se coerenti e senza errori, passare A4 a modellare offline il *tempo di effettiva analisi post-ingest*, non ridisegnare le 40 acquisizioni programmate per rendere verde la full-scan. A5 fix **non autorizzato né giustificato** dai soli 50 campioni; LIVE resta v1.62.

## 04/11/2026 ore 08:32 Italia — A1/A2: RISULTATI LIVE CONFERMATI DALLA VPS

**Fonte:** comando `python3` in sola lettura dell'utente sulla VPS (1 GET locale `/private-api/signals/status`), screenshot terminale 04/11 ore 08:32 italiane. Valori osservati, non sintetici.

**H1 paired, ultimo post-scan 2026-11-04T07:31:58.224658+00:00 (08:31:58 Italia):**
- `state=ready`, `samples=48`, `comparableSamples=48`, `unverifiableSamples=0`, `lastState=COMPARABLE`. **Traguardo >=8 confronti reali e validi: RAGGIUNTO**. Registro bounded di campioni; le righe possono riguardare più volte gli stessi mercati e non sono 48 cicli indipendenti né 48 trade.
- In 48 confronti paired: `marketsCompared=216`, `readyBefore=39`, `readyAfter=216`, `staleToReady=177`, `h1Advanced=210`, `h1Unchanged=6`. I 177 sono **passaggi da stale a ready nel confronto alla stessa UTC** tra precedente full-scan e successivo post-ingest, non 177 mercati unici, e NON dimostrano da soli causalità esclusiva del batch, opportunità profittevoli o anticipo istituzionale.
- **Fotografia distinta full-scan** alle `2026-11-04T07:22:50.199499+00:00` (08:22:50 Italia): **27/34 H1 ready**, **7/34 H1 stale**, **0 H1 non verificabili**. I 7 stale: `AUDCAD`, `AUDCHF`, `AUDJPY`, `USDCHF`, `USDJPY`, `USOIL`, `XAGUSD`. Ognuno ha `H1_age≈142.8 min` e `lag_vs_M15_teorico_min=0`: chiusura H1 allineata all'ora UTC teorica dell'ultima M15. L'allineamento dell'ultimo timestamp NON certifica la contiguità di tutte le barre storiche H4.
- I sette simboli di questa fotografia non coincidono con gli otto simboli stale del 03/11 ore 20:46: **compatibile con coorti rotanti e fase dei batch**, ma richiede correlazione con orari di raccolta effettivi. Non confrontare 26/34 e 27/34 come prova di miglioramento di un mercato sempre uguale; sono istanti e strumenti diversi.
- I **48 campioni provano che la telemetria paired è operativa** e che nei post-ingest osservati il frame H1 dei gruppi confrontati risultava sempre pronto dopo il controllo, mentre il full-scan anteriore poteva essere stale alla stessa UTC. Resta da verificare per mercati e fasi se il post-ingest sta riducendo la *latenza del primo controllo utile*, non semplicemente la posizione della scansione. Niente cambio gate 120m, niente prezzi interpolati.

**A3 — diagnosi in corso:** verificare con una nuova lettura *read-only* della stessa API già presente `collectorTiming` (8 slot, successo ingest, durata), `scanTiming` (fase, esiti), e `diagnostics.markets[].timeframes` H1/M15/H4, con timestamp UTC di misura. Distinguere `M15 presente ma H1 necessariamente più vecchia` da `4 M15 mancanti`, condizioni di chiusura/sessione del broker e strumento in attesa del proprio slot. **Non incrementare il polling**. Confronto offline già disponibile su PR app [#84](https://github.com/mirkoworz/remura/pull/84) (UTC/DST) e PR collector [#19](https://github.com/mirkoworz/remura-collector/pull/19) (fase al secondo / 40 acquisizioni); riusare e validare prima di scrivere un nuovo algoritmo.

**A4 — decisione attuale:** 48/48 comparabili consentono di avanzare alla diagnosi temporale; **non giustificano da soli modifiche a rotazione o scansioni**. La priorità è identificare se la full-scan possa essere distinta chiaramente dalla freschezza *post-ingest* già osservata, senza aumentare chiamate cTrader, senza false H1 verdi e senza toccare lo Shark Science B.

**Automazione:** PR collector #23 è integrata, ma alle verifiche GitHub della mattina del 04/11 non risultava ancora una esecuzione `event=schedule` del workflow diagnostico; i test `event=pull_request` non leggono lo stato LIVE. Per questa rilevazione è stato usato il comando locale; la schedulazione resta da verificare separatamente senza aggiungere nuovi cron.

## Scopo
Assicurare che REMURA ragioni su prezzi **realmente verificati** e non su H1 vecchie, incomplete o con orologi incoerenti. Priorità alla causa dei problemi, non a rendere artificialmente verdi gli indicatori. Questo track NON introduce nuovi segnali né modifica il modello trading.

## Baseline attendibile
- Applicazione **LIVE v1.62** installata il 03/11/2026 ore **20:31 Italia**, nove pagine e banner verificati, SQLite backup+restore-test, rollback e SHA autoupdater riconciliati su `1568edefabc7bbdb7d06485d2b863b196a4e6155`. GitHub `main` può avere nuovi commit di **soli dati Myfxbook**: SHA main NON è prova di nuovo codice LIVE.
- Collector ON, Squalincome 34 mercati, monitor post-ingest ON, COT sync ON, batch timing ON e rotazione prioritaria ON. A 20:46 8/8 ultimi batch salvati, 8/8 post-scan riusciti e nessun errore.
- Diagnostica 20:39: **26/34 H1 pronte**, **8/34 stale oltre 120 minuti**, almeno 55 barre, 0 insufficienti/anomale. Otto simboli osservati a 20:46: `NAS100`, `NZDCAD`, `NZDCHF`, `NZDJPY`, `NZDUSD`, `US30`, `US500`, `USDCAD`.
- `REMURA_H1_PAIRED_ENABLED=1` attivato reversibilmente alle 20:50 Italia, riavvio e health OK. Primo campione reale letto alle 20:54: `samples=1`, `comparableSamples=1`, `unverifiableSamples=0`; 5 mercati, H1 ready **5→5**, **0 stale→ready**, **0 barre avanzate**, 5 invariate. Questo NON dimostra nulla sugli altri 29 mercati né un trading edge.
- L'algoritmo H1 paired esegue il confronto **alla stessa UTC**: 1–5 mercati del batch vs full-scan di 34; campione N/D se non confrontabile. Soglia H1 120 min, almeno 55 barre, snapshot full-scan entro 30 min. Registro solo aggregati, max 256 campioni, senza nomi/prezzi/token. Un avanzamento NON prova causalità del batch.
- Diagnostica privata sul repository `mirkoworz/remura-collector`: PR **#22** aggiunge campioni/validi/N/D/recuperi usando la **GET già esistente**; PR **#23** aggiunge **una** schedulazione lun–ven 06:37 UTC, condizionata a `REMURA_VPS_DIAG_ENABLED=1`. Le PR erano integrate al 03/11; l'esito del primo run schedulato **non era attestato**.

## Passi e criteri di completamento (A)
- [x] **A1 — audit aggiornato (04/11 08:32):** leggere lo stato LIVE **prima** di qualsiasi modifica (health, SHA installato, auto-update, flag nel processo, snapshot e campioni). Non confondere raccolte pre-attivazione con record `remura_h1_paired`; confrontare timestamp/slot. Preferire diagnostica privata read-only già presente, altrimenti un solo comando Termius quando davvero necessario. Verificare se il workflow schedulato è stato eseguito, non assumerlo.
- [x] **A2 — campione sufficiente (48/48 validi, 216 confronti):** raccogliere **almeno 8 record paired nuovi, reali**, successivi all'attivazione; distinguere `samples`, `comparableSamples`, `unverifiableSamples`, `lastState`, `readyBefore`, `readyAfter`, `staleToReady`, `h1Advanced`, `h1Unchanged`. Se 8 totali ma troppi N/D, prolungare la misura anziché inventare conclusioni.
- [x] **A3 — indagine per causa (chiusa per le coorti osservate il 04/11; restano monitoraggi ordinari per sessioni e anomalie future):** correlare gli 8 mercati stale con sessioni/chiusure H1 UTC, momento del full-scan, slot effettivi, finestra M15→H1 (4 barre), sorgente primaria/backup, età all'istante della decisione e weekend. Testare localmente le ipotesi UTC/DST prima di intervenire. Non confondere 26/34 osservati a 20:39 con stato attuale.
- [x] **A4 — proposte senza costi (solo valutazione offline, nessuna modifica LIVE):** simulare offline alternative sulla **stessa quantità di chiamate**: prioritaria 8×5=40 acquisizioni programmate/2h (EURUSD e XAUUSD ripetuti) contro 38 standard. Confrontare disponibilità realmente valida e N/D, non soltanto conteggi cosmetici. Rivedere [PR collector #19](https://github.com/mirkoworz/remura-collector/pull/19) (replay sintetico, non effetto LIVE certificato).
- [x] **A5 — valutazione fix: NON NECESSARIO (nessun bug H1 dimostrato; nessuna modifica LIVE):** solo se supportato da campioni e test, preparare PR focalizzata su raccolta/telemetria; CI verdi e review diff. Un solo track per volta può effettuare merge, version bump e deploy VPS. Ogni rilascio applicativo richiede **v nuova + data/ora italiana effettiva in alto sulle nove pagine**, backup SQLite, restore-test, rollback e riconciliazione autoupdater.
- [x] **A6 — conclusione (report sullo snapshot 04/11 ore 10:38, con limiti espliciti):** report con prima/dopo su campioni reali, impatto M15/H1/H4, differenza sulle esclusioni Squalincome, latenza e uso API/disco. Se non c'è miglioramento dimostrabile, dichiararlo.

## Limiti, costi e coordinamento
- **Gratis prima di tutto**: zero nuove richieste a cTrader/Capital/Myfxbook per questo audit; non aggiungere polling o cron senza stimare quota/costi e consenso. Oracle Always Free, GitHub Actions e Firestore devono restare nei limiti: le fatture vere non sono verificabili dai soli dati RAM/disco.
- Lavorare su ramo dedicato `research/track-a-h1-20261104`, nato da SHA attuale di `main`, e PR separata. **Non modificare** file del track B, modello segnali/CVD, notifiche o `ROADMAP-B-SHARK-SCIENCE.md`.
- **Durante le due chat:** aggiornare principalmente questo file per il progresso del track A; sincronizzare `ROADMAP.md` soltanto quando si integra la PR, dopo aver ricontrollato il nuovo `main`. Non fare merge o deploy sulla fiducia: fermarsi e riconciliare se l'altra chat ha aggiornato `main`.
- Nessun trade automatico o pretesa di anticipare con certezza gli istituzionali; l'idoneità delle H1 è prerequisito per test statistici, non una strategia profittevole.
