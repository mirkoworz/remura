# REMURA — Filone A V21.4 LAB: ponte diagnostico nativo TradingView CVD → coerenza M5

**Aggiornamento V21.4, 23/11/26, 21:21:02 Europe/Rome.** Ramo `research/remura-v211-source-derived-cvd-20261123`. PR #112 ancora Draft. Nessun merge, deploy, D1, broker o intervento sul collector.

## Costruito: verifica locale della coppia originale, senza segnali

`research/v214_native_tv_cvd_pair_probe.py` è un modulo **offline e di sola lettura**, per due file RAW originali privati prodotti in seguito da una coorte diversa dai 12 TEST aggregati precedenti. Non richiede API, Cloudflare, GitHub, dati futuri, Secrets o scritture.

Il riferimento di contratto verificato è il ricevitore storico, non la conferma di ricezione reale: `tradingview/delta-peaks/gateway-lab/worker_cvd_candidate.mjs` al commit [58dc84e0](https://github.com/mirkoworz/remura/blob/58dc84e0de93b48eb5a6c596664d4d338548754a/tradingview/delta-peaks/gateway-lab/worker_cvd_candidate.mjs). Lo schema `remura.tv.flow.cvd.preview.v1` distingue `snapshot`, `configuration`, `cvd` e marca il CVD come **proxy da volume classificato, non esecuzioni CME o ordini istituzionali**.

Il nuovo controllo verifica in modo **parziale, deliberatamente conservativo**:
- JSON originale UTF-8 max 20 KB per file, chiavi duplicate/non-finite rifiutate, schema/versione `0.9.1-cvd-lab` e coppia `FX:EURUSD` M5 già chiusa;
- identità e qualità proxy, configurazione essenziale del modello `D08_SEGMENT_PORT_V091`, due chiusure M5 contigue di 300.000 ms;
- stessa giornata CVD/identico segmento e contatore barre consecutivo, `complete,continuous,eligible,day_valid` veri, continuità numerica `delta segmento ≈ trusted_delta corrente` con tolleranza solo di 0,000001;
- compatibilità **senza arrotondamenti** con le stringhe decimali fino a sei cifre del futuro contratto V21.1;
- SHA256 dei **due byte stream originali**, senza riesportare o modificare il sorgente.

La funzione pura `audit_native_pair()` calcola un **segno di variazione proxy per sola diagnosi privata**, e lo marca `prospective_decision_admitted=false` e `frozen_for_outcomes=false`. Il comando CLI **non mostra** direzioni, valori, hash o orari. Riferisce solo compatibilità e stato non operativo. **Non chiama mai il freezer V21.2**.

## Uso, solo dove esistono due nuovi file autentici fuori dal repository

~~~bash
python3 research/v214_native_tv_cvd_pair_probe.py

python3 research/v214_native_tv_cvd_pair_probe.py \
  --prior-native-raw /percorso/privato/prima.original.json \
  --event-native-raw /percorso/privato/dopo.original.json
~~~

Il secondo comando è soltanto un esempio di utilizzo futuro, **non avviato** qui. I file originali non vanno copiati su GitHub. La funzione diagnostica non può convalidare la firma del mittente o il timestamp del primo arrivo. Il controllo è un **sottoinsieme** della validazione JS del gateway storico, NON ne sostituisce l'esecuzione completa: eventuali incongruenze delle altre sezioni della busta nativa richiedono il validator originale e un'infrastruttura autenticata. La continuità numerica controllata è conservativa e può rifiutare payload legittimi con modelli numerici diversi; non correggere manualmente le misure per forzarne l'ammissione.

## Nessuna scorciatoia sul blocco dati

- Le 12 ricevute V20.3 TEST (run 45121703188) restano **OBSERVATION_ONLY**, quattro potenziali finestre M15, **zero trade**.
- Esempi usati da `research/test_v214_native_tv_cvd_pair_probe.py`: dati **sintetici**, sei nuovi controlli, non attestano feed reali.
- Prezzi cTrader M15 privati del 23/11: **N/D**. Due payload RAW nativi nuovi originali: **N/D**. Primo timestamp autenticato/precommit esterno: **N/D**. Campione esiti 60m/4h/24h: **0**; costi osservati: **N/D**.
- Nessun passaggio a V21.1 diretto/automatico: prima serve una verifica completa del contratto nativo, dei timestamp e del congelamento pre-outcome e della fonte indipendente cTrader.

**Prossima prova concreta:** sul DB cTrader già esistente, **copia offline autorizzata** più `research/v204_private_cvd_price_coverage.py` di sola lettura. Per la direzione serve acquisizione ex ante di due **nuovi** eventi con ricevuta indipendente. Non si cambia il gateway TEST e non si chiama Cloudflare.

**Costo incrementale:** €0 per codice offline/CI esistente; consumo e quote effettive GitHub Actions non misurati in questa sessione.
