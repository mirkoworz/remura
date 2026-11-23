# REMURA — Filone B v20.9 LAB: audit pubblico CFTC, prova sui dati autentici

**Data:** 23 novembre 2026, Europe/Rome. **Ramo:** `research/filone-b-cot-intelligence-v206-20261123`; **PR:** #108 Draft.  
**Permessi:** codice di ricerca isolato, senza merge/deploy, niente collector Mac, DB produzione, D1, Oracle, trading, cloud storage o nuove credenziali.

## Scopo

Ottenere un singolo audit **read-only** dei report ufficiali CFTC TFF Futures Only e Disaggregated Futures Only, senza scambiare la lettura corrente per una prova di acquisizione storica della VPS.

- `scripts/cot_public_official_audit.py`: due richieste HTTPS a `publicreporting.cftc.gov` `/resource/gpe5-46if.json` e `/resource/72hh-3qpy.json`; solo 14 contratti allowlisted (11+3), campi di posizione aggregati, fino a 70 settimane, risposta max 5MB ciascuna, 20 s per richiesta, **nessun retry/fallback**, nessuna API key.
- Serializzazione `source: official_public_cftc_socrata`, `captureClock: public_api_read_at_not_official_publication`, `readAtUtc`, `dataSha256`, `first_seen_at: null` per tutti i record. La lettura pubblica NON dimostra quando il report fosse pubblico nel passato.
- `cot-intelligence-watchlist.js` accetta questa nuova classe **solo** come `descriptive_only`. Rifiuta `observedAt` e qualsiasi timestamp di cattura privata inventato.
- Le classifiche descrittive restano separate per cross Forex, future finanziari TFF e fisici Disaggregated. Stati insufficienti o settimane anomale bloccano ranking; nessuna previsione.
- Due prove indipendenti: test Python mock e test JavaScript per schema, campi, orologi e separazione dati. Le fixture non sono dati di mercato reali.

## Prova automatica isolata

Il workflow `.github/workflows/cot-intelligence-lab-checks.yml` ha eseguito un **singolo audit pubblico sulla PR #108**, successivamente **ritirato** con commit `221d6c65a138de01c3a169af0692056af5e193fd`. Rimangono esclusivamente i test offline, senza job di raccolta automatica. Nel job le risposte temporanee sono scritte nel filesystem effimero del runner e **non** vengono commit-tate, caricate su storage cloud o distribuite. I log ospitano soltanto contatori, stato e una breve classifica descrittiva più checksum; non contengono token o dati personali.

L'audit pubblico può fallire se la CFTC è momentaneamente indisponibile, limita l'accesso o modifica i campi. In tal caso riportare l'errore senza sostituire dati fittizi o usare una fonte non verificata.

## Fonti e orari

- [TFF Futures Only ufficiale](https://publicreporting.cftc.gov/Commitments-of-Traders/TFF-Futures-Only/gpe5-46if)
- [Disaggregated Futures Only ufficiale](https://publicreporting.cftc.gov/Commitments-of-Traders/Disaggregated-Futures-Only/72hh-3qpy)
- [Calendario CFTC 2026](https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm): rilascio 20 novembre, prossimo 30 novembre festivo
- [Annuncio CFTC del 27/10/2026](https://www.cftc.gov/PressRoom/PressReleases/9316-26): cambiamento pianificato a due report settimanali. Il gate `cadence_review` impedirà confronti settimanali inesatti prima di una revisione esplicita.

## Come distingueremo le prove

- **CFTC ufficiale ora:** possibilità di descrivere **autentici posizionamenti aggregati** alla data letta, non posizioni individuali o flusso eseguito;
- **Cache privata REMURA:** verifica indipendente della presenza/assenza del report nella VPS e del timestamp `cot_first_seen`, non verificata qui;
- **Filone A:** eventuale verifica scientifica della capacità predittiva con prezzi futuri, split temporali e costi. **Non è il lavoro di questo filone.**

Non presentare i risultati del job come prova di acquisizione del collector o promessa di guadagno. Nessun dato pubblico viene etichettato come `first_local_capture_asof`.

## Test attesi

```bash
node --test tests/cot-intelligence.test.js tests/cot-intelligence-watchlist.test.js tests/cot-intelligence-public.test.js
python3 -m unittest discover -s tests -p 'test_cot_*audit.py'
python3 -m unittest discover -s tests -p 'test_cot_intelligence_snapshot.py'
```

**Gate rilascio:** non aggiornare automaticamente l'etichetta versione delle pagine LIVE: v20.9 è solo LAB; la prossima release unificata deve includere versione e data/ora Europe/Rome visibili in ogni pagina pubblicata.

## Risorse gratuite

Lettura HTTPS pubblica con massimo due GET e runner standard GitHub Actions su repository pubblico. Nessuna nuova tabella, Worker, D1, chiamata a broker o storage persistente. Verificare i limiti GitHub prima di automazioni ricorrenti: questo audit è non schedulato.

## Evidenza autentica acquisita e registrata

**Audit pubblico una tantum GitHub Actions:** [run #45206837974](https://github.com/mirkoworz/remura/actions/runs/45206837974), job `One-off CFTC official read (2 HTTPS GETs max, no secrets)`, **SUCCESS** il 23/11/2026.

- `readAtUtc = 2026-11-23T15:35:17.664069Z` (16:35:17 ora italiana);
- `source = official_public_cftc_socrata` e `watchlist_mode = descriptive_only`;
- **980 righe ufficiali**: 70 settimane x 14 contratti allowlisted, incluse entrambe le settimane comparabili `2026-11-10` e `2026-11-17`;
- copertura **TFF 11/11** e **Disaggregated 3/3**, latest e previous completi, `state = descriptive_ready`;
- **SHA-256 delle righe NORMALIZZATE** (non dell'intera risposta HTTP): `a2d58c5a3347c121b491c5f495f7ee01ed83b6a282cc11fb2e5f49b1688ffb23`;
- output suddiviso in **28 cross Forex sintetici, 4 futures TFF diretti, 3 futures Disaggregated**;
- **nessuna prova della disponibilità storica dei dati su VPS**. Questo audit pubblico non usa il DB privato REMURA, né inserisce `cot_first_seen`.

### Primo confronto reale 17/11 vs 10/11

**Unità:** differenza tra (Long - Short)/Open Interest x 100 in *punti percentuali*, prima categoria ufficiale di ciascun dataset. Non è una variazione di prezzo, ordine, intensità live o possibilità di guadagno.

| Gruppo | Riferimento | Variazione net%/OI categoria A, pp |
|---|---|---:|
| TFF diretto — Asset Manager | US30 | -11,7403 |
| TFF diretto — Asset Manager | NAS100 | +2,7570 |
| TFF diretto — Asset Manager | US500 | -2,6226 |
| TFF diretto — Asset Manager | DXY | +1,7897 |
| Disaggregated — Managed Money | XAUUSD | -2,5162 |
| Disaggregated — Managed Money | XAGUSD | -2,0846 |
| Disaggregated — Managed Money | USOIL | -0,4953 |
| FX **sintetico** — Asset Manager | GBPAUD | +7,6571 |
| FX **sintetico** — Asset Manager | GBPNZD | +6,9413 |
| FX **sintetico** — Asset Manager | GBPCAD | +6,1169 |
| FX **sintetico** — Asset Manager | AUDCHF | -5,8250 |
| FX **sintetico** — Asset Manager | EURGBP | -5,7489 |

I 28 cross Forex riutilizzano 7 futures sottostanti e sono fortemente sovrapposti. Il ranking è solo per ampiezza della variazione **entro la stessa famiglia**; **non è una classifica di probabilità future**. Sono state riportate nei log le prime cinque coppie Forex e tutti i sette futures diretti; le altre coppie non sono persistite né inventate.

**Doppia CI al momento del rilievo:** `REMURA insights checks` run [#45206838259](https://github.com/mirkoworz/remura/actions/runs/45206838259) **SUCCESS** e test Filone B run [#45206837974](https://github.com/mirkoworz/remura/actions/runs/45206837974) **SUCCESS**. Conservare la PR Draft e **non** attivare nuovamente la prova pubblica senza nuova valutazione.

### Gate successivo

Confronto con una **copia offline autorizzata** della cache COT privata REMURA: verificherà davvero `cot_first_seen`, settimane disponibili nel collector e tempi di acquisizione. Non collegare ancora questo audit alla previsione dei prezzi del Filone A o a un verdetto BUY/SELL nella UI.
