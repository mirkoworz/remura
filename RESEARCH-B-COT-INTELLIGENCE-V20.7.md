# REMURA — FILONE B / Intelligence CFTC v20.7 LAB

**Checkpoint:** 23 novembre 2026, Europe/Rome.  
**Base:** V20.6, repo `mirkoworz/remura`, ramo di ricerca `research/filone-b-cot-intelligence-v206-20261123`.  
**Stato:** ricerca isolata, **non installata / non pubblicata**, nessun deploy, merge, query addizionale, variazione di collector, database o motore prezzi.

## Obiettivo realizzato

Un motore COT puro, indipendente dai prezzi, che distingue:
1. **Posizionamento CFTC autentico** del contratto futures, suddiviso nelle categorie ufficiali TFF o Disaggregated Futures Only;
2. **Variazione della settimana** nei netti normalizzati per open interest, soltanto quando esistono due report comparabili adiacenti (intervallo di 5–9 giorni per festività);
3. **Posizionamento relativo** tramite min–max COT Index 0–100 e rango percentile empirico su 26/52/156/260 settimane, senza inventare indici per range costanti, storia insufficiente o settimane mancanti;
4. **Contrasto fra categorie** (netti con segno concordi/opposti), non prova che siano hedge contro speculazione o ordine futuro;
5. **Mappatura futures/Forex controllata**, vietando i surrogati per simboli non verificati;
6. **Gate temporale as-of**, basato sul primo timestamp effettivo di acquisizione locale CFTC, non sulla data del martedì.

File:
- `cot-intelligence-core.js` — libreria JavaScript riutilizzabile, pura, senza fetch, accesso file, segreti, scritture o ordini;
- `scripts/cot_intelligence_snapshot.py` — esportatore **in sola lettura di una COPIA OFFLINE** dell'archivio COT SQLite esistente; nessun uso obbligatorio del collector;
- `tests/cot-intelligence.test.js` — 12 test con fixture sintetiche per mappatura, variazioni, date, indici, inconsistenze e non-lookahead;
- `tests/test_cot_intelligence_snapshot.py` — 3 test offline per esportazione limitata, provenienza, elenco contratti e assenza di mutazioni.

## Contratti e semantica

Rispettano la mappatura già in `nav.js` e la whitelist di `scripts/cot_monitor.py`:

| Famiglia | Dataset ufficiale | Sottogruppi confrontati | Futures / codici |
|---|---|---|---|
| 28 coppie Forex | TFF Futures Only `gpe5-46if` | Asset Manager / Leveraged Funds | EUR 099741, GBP 096742, JPY 097741, AUD 232741, CAD 090741, CHF 092741, NZD 112741 |
| Indici / DXY | TFF Futures Only | Asset Manager / Leveraged Funds | US500 13874A, NAS100 209742, US30 124603, DXY 098662 |
| Oro / argento / WTI | Disaggregated Futures Only `72hh-3qpy` | Managed Money / Producer Merchant | XAUUSD 088691, XAGUSD 084691, USOIL 067651 |
| GER30, VIX, UKOIL | — | — | **Non mappati**, N/D: vietata sostituzione con altro future |

I report si riferiscono a **future**, non alle posizioni spot Forex, ai CFD cTrader o al volume intraday.

### Formule

- `netPercentOI = 100 * (long - short) / openInterest` per ciascuna **categoria dello stesso future**.
- `weeklyChange.aPp = netPercentOI.a(t) - netPercentOI.a(t-1)` in **punti percentuali**.
- `categoryGapPp = netPercentOI.a - netPercentOI.b`; segni diversi = categorie in opposizione di *netti*, non automaticamente trader avversari.
- `COT Index = 100 * (ultimo - minimo) / (massimo - minimo)`, sulla finestra coerente e completa, senza predizioni.
- `FX(base/quote) = netPercentOI(base future USD) - netPercentOI(quote future USD)`; per USD si pone 0 **solo come riferimento matematico**. Non si sommano contratti o open interest di valute diverse.
- `USDCAD = -netPercentOI(CAD)` e `CADJPY = netPercentOI(CAD) - netPercentOI(JPY)`.
- `openInterestContracts=null` per tutti i cross e le coppie FX sintetiche: non esiste un open interest direttamente sommabile delle due gambe.

Le due gambe non devono avere report correnti disallineati: `misaligned_latest` blocca il calcolo. Il record precedente è usato per la variazione settimanale solo con intervallo 5–9 giorni. Gli intervalli storici non contigui producono `gapped_history` o `insufficient`, non valori riempiti.

## Provenienza e prevenzione lookahead

La CFTC tipicamente pubblica venerdì i riferimenti di martedì, ma festività e ritardi sono possibili. **Non convertire `reportDate` in `publishedAt`**.

- Senza `observedAt` il motore calcola soltanto una descrizione ex-post: `mode=descriptive_only`. Non è prova di conoscibilità all'epoca.
- Con `observedAt` (timestamp UTC con fuso esplicito), sono accettate soltanto le righe `firstSeenAt <= observedAt` già effettivamente acquisite da REMURA. Un report nuovo visto dopo l'osservazione è escluso, anche se ha un martedì anteriore.
- Un record COT storico senza `firstSeenAt` rimane **non attestato**. Non retrodatare né usare una data fittizia; se serve una gamba mancante il verdetto è `unverified_or_unavailable`.
- `firstSeenAt` prova la **prima acquisizione locale**, non l'ora ufficiale di pubblicazione né l'assenza di revisioni.
- La qualità dell'analisi non dimostra profitto, tempismo degli ordini, dati di singoli fondi o precisione predittiva.

## Utilizzo OFFLINE senza costi API

Eseguire unicamente su **una copia locale** dell'archivio, non sulla produzione:

```bash
python3 scripts/cot_intelligence_snapshot.py --db /percorso/copia-offline.sqlite3 --limit 5000 > /tmp/remura-cot-offline.json
node -e 'const s=require("/tmp/remura-cot-offline.json");const c=require("./cot-intelligence-core.js");console.log(c.evaluate(s.rows,"CADJPY",{window:52}))'
```

Per un'analisi **as-of** appendere `observedAt:"2026-11-21T12:00:00Z"` e assicurarsi che esista una prima acquisizione locale reale. Le output vanno trattate come ricerca privata. Non caricare copie del DB, prezzi, token o dettagli di account su GitHub.

L'archivio del collector attuale mantiene circa **420 giorni**: 26/52 settimane sono potenzialmente verificabili, 156/260 richiedono una storia ufficiale più lunga **e una provenienza temporale adeguata**. Non chiamare nuove API o inventare la prima acquisizione per colmare il vuoto.

## Verifiche locali

```bash
node --check cot-intelligence-core.js
node --test tests/cot-intelligence.test.js
python3 -m unittest discover -s tests -p 'test_cot_intelligence_snapshot.py'
```

Le fixture sono costruite per controllare il codice, **non** sono risultati di mercato. Le verifiche senza accesso a una copia dell'archivio reale non attestano aggiornamento CFTC, copertura o redditività.

## Fonti ufficiali

- CFTC, informazioni, tempi di pubblicazione e categorie: https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm
- TFF Futures Only: https://publicreporting.cftc.gov/Commitments-of-Traders/TFF-Futures-Only/gpe5-46if
- Disaggregated Futures Only: https://publicreporting.cftc.gov/Commitments-of-Traders/Disaggregated-Futures-Only/72hh-3qpy
- Archivio CFTC: https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm

## Confine con Filone A e prossimi gate

Non implementare trade entry, prezzi futuri, costi/slippage, metriche di payoff, walk-forward o baseline price-only in questo ramo: **sono del Filone A**. Prima di collegare questa intelligence a Squalincome/Ampere servono una struttura versionata di osservazioni settimanali e un contratto as-of compatibile con il motore scientifico, oltre alla prova sui dati reali. Non convertire in segnali BUY/SELL basandosi sui soli COT.

**Versioning:** questo è `v20.7-B LAB`, **non una release REMURA LIVE**. In caso di futura integrazione autorizzata, aggiornare il numero e la data/ora italiana visibile in alto su **ogni pagina**, con release unificata e verifica regressioni. Non alterare `nav.js` o i banner di produzione ora.

**Costi:** trasformazione offline, Python standard library, Node integrato. Zero nuovi provider, zero nuove chiamate CFTC, zero storage remoto aggiuntivo per i dati; repository pubblico e GitHub Actions standard su GitHub Free non consumano minuti fatturabili secondo la documentazione GitHub (verificare le impostazioni di fatturazione prima di eventuali nuovi workflow).
