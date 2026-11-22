# REMURA V20 — MISURAZIONI REALI | aggiornamento 22/11/2026, 23:37:38 Europe/Rome

**Stato:** RESEARCH / NON DISTRIBUITO · **Main invariato** · **Nessuna attivazione né accesso ai Secret**.

## Fonti e integrità

- **Retail Myfxbook pubblico:** `mirkoworz/remura` main `cce37d0bcf55d8b1c02d56304e7e2c29d1319c59`, `data/myfxbook/latest.json` e i 34 file in `data/myfxbook/history/`. Snapshot del **2026-11-22 22:23:40 UTC**, **89 strumenti**. Non è flusso istituzionale.
- **Capital.com DEMO privato:** `mirkoworz/remura-collector` main `a8f8cedf2ff1960f6bee3f8ed7dd24f864656844`, `private/capital/latest.json` e 31 file in `private/capital/history/`. Snapshot del **2026-11-22 20:45:11 UTC**, **31 strumenti**, metrica `client_positions`; posizioni clienti broker, **non CVD né flusso istituzionale**. Qui sono pubblicati **solo conteggi aggregati**, non record/percentuali per singolo simbolo privato.
- I record appartengono a popolazioni e metodi diversi. `t` è il timestamp del record salvato, non una prova indipendente di first-seen/receipting prima della decisione. Non ricostruire il first-seen.
- Fonte dei numeri: lettura diretta dei 65 JSON individuali tramite connettore GitHub, non fixture. Aggregati calcolati sulle strutture `records`. Il vecchio `data/myfxbook/history.json` non è considerato una serie temporale aggiornata.

## MISURAZIONI REALI — fase descrittiva

| Misura | Myfxbook retail | Capital.com DEMO |
|---|---:|---:|
| Serie lette | **34** | **31** |
| Osservazioni timestamped salvate | **3.924** | **3.791** |
| Intervallo storico recente per la maggior parte delle serie | 24/10–22/11/2026 UTC | 19/10–22/11/2026 UTC |
| Mediana intervallo fra due snapshot nelle serie attive | **5,91 h** | **6,85–6,87 h** |
| Coppie di snapshot consecutivi | **3.890** | **3.760** |
| Coppie consecutive con identica % long | **2.244 (57,7%)** | **1.229 (32,7%)** |
| Gap interni superiori a 12 ore | **0** | **32** |
| Gap interni superiori a 24 ore | **0** | **0** |
| Long + short non coerenti (tolleranza 1,01 pp) | **0** | **0** |
| Timestamp duplicati all'interno di una serie | **0** | **0** |

**Totale:** **7.715 righe di osservazione** su **65 serie**, NON 7.715 segnali indipendenti, operazioni, transazioni o outcomes.
La frequenza osservata è di diverse ore, **non** 20 minuti certi né 2 ore certe. I gap includono ritardi di scheduling e chiusure; un intervallo regolare non prova di per sé che il provider abbia modificato i dati.

### Eccezione: 4 indici Myfxbook STALE
`NAS100`, `US2000`, `US30`, `US500`: ciascuna serie contiene **36 record**, dal 16 ottobre 19:50:39 UTC al **22 ottobre 01:38:06 UTC**. Sono **144** delle 3.924 osservazioni ma NON fresche. In quei 36 record la percentuale long di ciascun indice è costante. Le altre **30 serie Myfxbook** hanno **126 record ciascuna** dal 24 ottobre 00:02:18 UTC al 22 novembre 22:23:40 UTC, cioè 3.780 osservazioni aggiornate. Non indicare gli indici archiviati come correnti.

### Quattro esempi PUBBLICI Myfxbook, basati su dati reali

| Strumento | N | Long iniziale | Long finale 22/11 | Variazione | Min–Max nel periodo |
|---|---:|---:|---:|---:|---:|
| EURUSD | 126 | 84% | **85%** | +1 pp | 64–89% |
| USDJPY | 126 | 70% | **59%** | −11 pp | 30–71% |
| CADJPY | 126 | 71% | **79%** | +8 pp | 61–80% |
| XAUUSD | 126 | 64% | **62%** | −2 pp | 39–73% |

La variazione del sentiment è una statistica descrittiva; non è rendimento del prezzo né prova di anticipazione. `avgL` e `avgS` di Myfxbook sono valori medi delle posizioni retail, **non** una serie di quotazioni spot indipendenti.

## Capital DEMO / Firestore — qualità della raccolta

- 23 file storici con **122** record, 7 con **123**, uno (`XAGUSD`) con **124**: **3.791** in totale.
- Le 31 serie arrivano al 22 novembre 20:45:11 UTC. La maggioranza parte il 19 ottobre 2026, con XAGUSD dal 18 ottobre.
- L'ultimo ledger privato letto per il giorno UTC 22/11 aveva `used: 6` chiamate prenotate e `lastCycle: 20:45:08Z`; è uno **snapshot storico**, non il budget disponibile al momento futuro. Non dedurre margine operativo da questo solo campo.
- Le ultime run già verificate `45068187711` (Capital) e `45068217134` (Firestore) sono SUCCESS. I **32 documenti Firestore** provano sincronizzazione del feed, non 32 previsioni, trades, barre CVD o rendimenti.
- La schedulazione Capital ha intenzione di lavorare ogni 2 ore e di rispettare 36 richieste prenotate al giorno, ma negli archivi la mediana effettiva è 6,85–6,87 ore. Distinguere cron configurato dalla frequenza realmente ottenuta.

## Cloudflare Free — nuova evidenza dai LOG PREESISTENTI (senza nuove query)

La run giornaliera **45039172579** del 22/11 alle 15:35 UTC ha **FAILED** nello step analytics, mentre il test offline è GREEN. I log della run esistente registrano:

- `REMURA_CF_ACCOUNT_QUOTA=UNKNOWN_NO_GRAPHQL_DATA`: **non è attestato il consumo giornaliero righe D1**.
- `REMURA_CF_WORKERS_USAGE=OK`: stima analytics adattiva, **non billing esatto**.
- `REMURA_D1_TEST_STORAGE=OK`: **6.266.880 byte**, **1,2534%** del limite indicato 500.000.000 byte del singolo DB TEST.
- `REMURA_D1_ACCOUNT_STORAGE=OK`: **6.557.696 byte** totali indicati, su cap 5.000.000.000 byte Free.
- `REMURA_DAILY_BUDGET=INCOMPLETE_OR_CRITICAL`: il workflow ha correttamente rifiutato il verde complessivo quando una dimensione resta sconosciuta.

**Interpretazione:** non emerge una saturazione dello storage letto; NON è provata la riserva giornaliera di letture/scritture D1, né i seats Access o la fatturazione personale. Non chiamare Cloudflare GraphQL senza nuova autorizzazione. Per pilot Contributors il gate rimane **NO-GO**.

## FILONE B — HOLDOUT TradingView CVD

- La finestra V2 comincia **23 novembre 2026 ore 00:00 UTC / 01:00 CET**, senza retrodatazioni.
- Dal codice GitHub e dai run CI verdi è verificabile la preparazione del sistema TEST; **non è dimostrato** il suo stato runtime attuale, un alert TradingView consegnato, una ricevuta first-seen forward-only o un prezzo indipendente accoppiato.
- Richiedere prova runtime TEST senza mutare configurazioni; se mancante, il risultato corretto è **NO EVENTI CONFERMATI / RUNTIME UNKNOWN**, non 0 trade o 0 alpha.
- Prima di misurare 60m/H4/24h servono feed prezzo indipendente, `observed_at` e `first_seen` attendibili, qualità dati, confronto price-only sulle stesse finestre e politiche ex-ante per ritardi/missing, spread, costi, censura. Nessun PnL/edge positivo inferibile dai 7.715 snapshot.

## FILONE C — Gate pilot 1–2 collaboratori

- v0.95 Safari verificata, v0.96 contratto server e portale protetto LAB, v0.97 Free gate no-network 21/21 GREEN; non ripetere suite precedenti senza modifiche.
- **Access seats effettivi, Billing e consumi D1 giornalieri: UNKNOWN**; il monitor budget risulta incompleto. Servono policy Access corretta, JWT server-side, ownership D1, owner review, ricevuta durevole, prove Safari e blocco con revoca identità D1 + policy Access + sessioni.
- NON attivare utenti o Worker senza approvazione esplicita. L'interfaccia pronta in LAB **non** equivale a login reale disponibile.

## Ordine successivo — misurazione prima dei prototipi
1. Congelare e osservare esclusivamente eventi forward-only dal 23/11 00:00 UTC; attestare alert, ricevitore, timestamp e qualità. Non ricostruire orari da log storici.
2. Collegare prezzi indipendenti cronologicamente corretti al solo campione futuro, con label 60m/H4/24h dopo maturazione, e confrontare con price-only e no-signal.
3. Risolvere Free gate da dashboard account in sola lettura; poi collaudo pilota protetto **solo con autorizzazione mirata**.
4. Separatamente verificare COT CFTC martedì confrontabile e pubblicazione ufficiale; non presentare sentiment retail come movimento degli istituzionali.
5. Integrare in release controllata Cockpit v1.68/Contributors soltanto dopo revisione, consenso e coordinamento Mac; main e PR #105/#106 invariati.

**Costo nuovo:** zero servizi attivati; la presente commit consiste solo in un documento di ricerca su branch isolato. Roadmap V01–V19 ereditata e conservata.
