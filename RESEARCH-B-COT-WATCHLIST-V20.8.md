# REMURA — Filone B v20.8 LAB · Classifica COT verificabile

**Aggiornamento ricerca:** 23 novembre 2026, Europe/Rome.  
**Eredita:** `RESEARCH-B-COT-INTELLIGENCE-V20.7.md`, checkpoint V20.6.  
**Ramo:** `research/filone-b-cot-intelligence-v206-20261123` · PR #108 **Draft**.  
**Stato:** offline / sviluppo isolato, **nessun merge, deploy, collector, Mac, segnale BUY/SELL o modifica produzione**.

## Implementazione

`cot-intelligence-watchlist.js` e `scripts/cot_intelligence_watchlist.js` leggono soltanto l'export di `scripts/cot_intelligence_snapshot.py` da una **copia offline** SQLite esistente. Nessuna nuova interrogazione CFTC, nessuna modifica ai conti, prezzi, cloud o API.

### Tre classifiche separate

1. `fx_relative` — 28 coppie, differenziale sintetico tra futures valutari contro USD. Sono 28 *viste* che riutilizzano 7 futures, **non 28 misure istituzionali indipendenti**. Non è il posizionamento spot Forex.
2. `tff_futures` — US500, NAS100, US30, DXY. Variazione Asset Manager/Institutional, contrapposta soltanto nella rappresentazione a Leveraged Funds.
3. `disagg_futures` — XAUUSD, XAGUSD, USOIL. Variazione Managed Money con Producer/Merchant come categoria distinta, **non** come opposizione speculativa certa.

Ordinamento deterministico **all'interno di ciascuna categoria** per valore assoluto della variazione settimanale in **punti percentuali** del netto/OI del primo gruppo. Pareggi: ordine alfabetico. Non è uno score predittivo, non confronta i contratti grezzi dei cross, non stima guadagni, prezzi futuri o probabilità di inversione.

Per ogni candidato: simbolo, codice CFTC, categoria A/B, report date, netto%/OI, variazione A/B e gap, eventuale COT Index storico 52 settimane, timestamp locale di prima acquisizione, tipo synthetic/direct e fattori di esposizione sovrapposti.

## Gate per dati affidabili

- `INVALID_OR_TRUNCATED_SNAPSHOT`: accetta solo formato dell'esportatore REMURA e richiede `truncated=false`; non classifica dati parzialmente esportati.
- `INVALID_CFTC_ROWS` e `CFTC_FUTURE_CLOCK`: input invalidi o timestamp futuri rifiutati.
- `incomplete_latest`/`incomplete_previous`: per ogni dataset servono **tutti i contratti attesi** sia nell'ultimo che nel precedente report. L'assenza blocca solo il dataset interessato.
- `cadence_review`: intervallo non compreso fra **5 e 9 giorni**; differenze tra report non chiamate ingannevolmente *settimanali*.
- `stale`: il riferimento più recente oltre 14 giorni fa blocca la classifica relativa.
- `first_local_capture_asof`: con `--as-of`, usa solo le righe con prova di acquisizione locale al tempo richiesto. Una settimana legacy non tracciata non viene retrodattata.
- Senza `--as-of`, `descriptive_only`: dati autentici consultabili soltanto ex-post; **nessuna conferma della disponibilità storica**.
- `GER30`, `VIX`, `UKOIL` restano non mappati. Una mappatura futura richiede verifica del contratto, della categoria e del simbolo del broker.

La mancanza di una sola riga in Disaggregated non deve falsare il monitor TFF: i gate sono separati e spiegano gli esclusi. Non si pretende che `first_seen_at` coincida con la pubblicazione CFTC.

### Fonte CFTC e possibile cambio cadenza

Il programma ufficiale del 2026 indica pubblicazione 20 novembre (report con riferimento 17 novembre), e per il calendario tradizionale la successiva pubblicazione prevista è **30 novembre** a causa della festività negli USA: https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm .

Il **27 ottobre 2026** CFTC ha annunciato il **piano** di passare a due report settimanali entro fine anno, con riferimento lunedì/mercoledì e rilascio mercoledì/venerdì. Questo non va interpretato come già attivo: https://www.cftc.gov/PressRoom/PressReleases/9316-26 .

**Conseguenza tecnica:** finché la frequenza effettiva non viene certificata, qualsiasi intervallo fuori 5–9 giorni resta `cadence_review`. In futuro serviranno serie omogenee separate, cambio della semantica `weeklyChange`, gate di pubblicazione e suite di test dedicata; **non** rietichettare automaticamente due report in una settimana come uno solo.

## Esecuzione deterministica — SOLO SU COPIA OFFLINE

```bash
python3 scripts/cot_intelligence_snapshot.py \
  --db /percorso/copia-offline.sqlite3 --limit 5000 \
  > /tmp/remura-cot-offline.json

node scripts/cot_intelligence_watchlist.js \
  --input /tmp/remura-cot-offline.json \
  --now 2026-11-23T14:00:00Z
```

Per l'audit di un istante storicamente osservabile:

```bash
node scripts/cot_intelligence_watchlist.js \
  --input /tmp/remura-cot-offline.json \
  --now 2026-11-23T14:00:00Z \
  --as-of 2026-11-21T12:00:00Z \
  --window 52
```

L'output su stdout contiene **solo aggregati**; non copiarvi segreti né dump completi di produzione. La fonte SQLite privata non è stata letta in questo sviluppo: classifiche numeriche effettive restano **non verificate** fino a input autentici disponibili da copia autorizzata.

### Test

```bash
node --check cot-intelligence-core.js
node --check cot-intelligence-watchlist.js
node --check scripts/cot_intelligence_watchlist.js
node --test tests/cot-intelligence.test.js tests/cot-intelligence-watchlist.test.js
python3 -m unittest discover -s tests -p 'test_cot_intelligence_snapshot.py' -v
```

Fixture deterministiche sintetiche: testano guardie, mapping, ranking, non lookahead, ma non dimostrano risultati statistici sul prezzo.

### Costi & filoni

Solo JavaScript e Python standard library + GitHub Actions su PR pubblica, no nuovi endpoint né server. Nessuna spesa incrementale di rete o storage mercato. Ramo Filone B non modifica `nav.js`, `asset.html`, splash, UI Filone D, Contributors Filone C, collector locale Mac, backend Filone A o Cloudflare. Una futura integrazione autorizzata aggiornerà versione **e ora Italia** in alto su ogni pagina effettivamente rilasciata.

## Roadmap successiva

1. Eseguire la classifica su dati **autentici** da copia offline e certificare le 14 righe CFTC per le ultime due settimane; altrimenti mostrare i motivi del gate.
2. Verificare gli eventuali cambiamenti di frequenza e l'interpretazione dei nuovi report.
3. Passare al Filone D solo il contratto di output **descrittivo**, non il motore dei prezzi.
4. Filone A continua indipendente per validazione su prezzi futuri e causalità, senza importare scorciatoie COT.
