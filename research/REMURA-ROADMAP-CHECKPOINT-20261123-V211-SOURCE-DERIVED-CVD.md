# REMURA V21.1 — Direzione CVD derivata dai numeri originali, non da dichiarazioni LONG/SHORT

**Aggiornamento LAB: 23 novembre 2026 — Europe/Rome.** Nessuna versione LIVE, nessuna modifica HTML.
**Filone A indipendente:** \`research/remura-v211-source-derived-cvd-20261123\`.
Base: \`research/remura-v210-forward-source-price-integrity-20261123\`, SHA \`4005c5ec5c6f4f561056062bed9be59910c5685b\`.

## Perché serve
La V21.0 riesamina la SHA256 dei byte originali ma, prima di V21.1, il lato LONG/SHORT del CVD poteva restare una *dichiarazione locale*. Un hash non rende automaticamente corretta una classificazione. V21.1 aggiunge una classificazione deterministica diretta dai numeri di un **NUOVO formato futuro**, da conservare prima dell'outcome.

L'audit reale V20.3 https://github.com/mirkoworz/remura/actions/runs/45121703188 contiene **12 ricevute TEST M5 OBSERVATION_ONLY**, senza payload raw per evento e senza direzione ammessa. Non possono essere convertite retroattivamente in trading signals. Il repository attualmente utilizzato per Filone A non contiene un protocollo originale TradingView che autorizzi a interpretare i suoi campi come due valori CVD. Non fingere compatibilità: è obbligatorio un futuro adapter verificato sul formato reale e la provenienza dell'evento.

## Nuovo protocollo strettamente LOCALE
File \`research/v211_raw_cvd_direction_admission.py\`.
Schema: \`remura-v211-closed-m5-cvd-pair-v1\`.
Esempio del solo CONTRATTO DI INPUT, con numeri fittizi (non ricevuta reale):

~~~json
{
  "schema": "remura-v211-closed-m5-cvd-pair-v1",
  "symbol": "FX:EURUSD",
  "timeframe": "M5",
  "source_family": "UNVERIFIED_CVD_PROXY_NOT_EXECUTED_VOLUME",
  "prior_close_utc": "2026-11-23T04:30:00Z",
  "event_close_utc": "2026-11-23T04:35:00Z",
  "prior_cvd": "100.125",
  "event_cvd": "105.125"
}
~~~

Lato CVD \`M5_CLOSED_CVD_DIFFERENCE_SIGN_ZERO_THRESHOLD_V1\`: differenza \`event_cvd-prior_cvd\` con Decimal esatto, senza arrotondamenti floating e soglia fissata **ZERO**. \`LONG\` se positiva, \`SHORT\` se negativa, \`FLAT\` se esattamente zero. Non è un segnale d'ingresso validato: la variazione può essere rumore, e la direzione è solo ipotesi di ricerca. **Questo CVD è un proxy, non misura del volume istituzionale o dei trade eseguiti.**

Regole: solo FX:EURUSD, timeframe M5, timestamp UTC espliciti, due M5 consecutive e chiuse, stringhe numeriche decimali canoniche fino a sei cifre dopo il punto e valore assoluto <= 999999999999.999999, niente schema extra, LONG/SHORT nel sorgente, duplicati JSON, NaN/Infinity, payload >64KB, evento futuro o presentato oltre 12 minuti dalla chiusura. La ricevuta timestamp è ancora una **asserzione locale NON verificata da un terzo**.

Il costruttore \`freeze_raw\` passa i byte originali al freezer V20.9, il quale richiede M15 cTrader chiuse e contigue e calcola anche la baseline prezzo-solo sullo stesso istante. Il ledger privato congela CVD-side ricalcolato, algoritmo, differenza numerica, SHA256 dei byte sorgente, timestamp dichiarati e i cinque OHLC chiusi; genera solo un hash-only manifest pubblico non contenente direzioni/prezzi/nonce.

L'auditor \`adjudicate_raw\` rilegge più tardi i **medesimi byte originali**, ricostruisce il segno e la differenza, richiede il match con il ledger immutabile e il manifest e ripete la verifica V21.0 di coerenza prezzo e tempo di congelamento. Se l'utente abilita separatamente \`github_readonly\`, anche il first-seen GitHub V20.8 viene verificato (solo due GET anonime, nessun push). L'output dichiara SEMPRE \`cvd_origin_independently_authenticated=false\`, \`raw_first_seen_timestamp_independently_authenticated=false\`, \`scientific_alpha_established=false\`.

In default \`python3 research/v211_raw_cvd_direction_admission.py\` non chiama rete, non apre database, non crea file e non produce un segnale. Tutti gli altri ingressi CLI richiedono separatamente file RAW locale fuori dal repository PUBBLICO, timestamp received dichiarato, DB SQLite preesistente ctrader read-only, directory privata fuori dal checkout; \`--write-private\` esplicito è necessario per scrivere la coppia privata 0600/0700. Nessun upload a GitHub viene eseguito.

## Stato e roadmap prima dei prezzi REALI
- CI dedicata: \`.github/workflows/remura-v211-raw-cvd-admission-tests.yml\`; 21 test NUOVI solo sintetici, senza ripetere suite di V20.4–V21.0.
- NON eseguire il programma in acquisizione reale, Mac, VPS, collector, D1, Workers, Oracle o Cloudflare senza autorizzazione esplicita e senza coordinamento Codex.
- Verificare con consenso specifico il formato e la provenienza autentici del segnale CVD TradingView (TV webhook non è automaticamente firmato). Il nuovo schema deve essere generato contemporaneamente e da un adattatore autenticato, non creato da un analista ex post.
- Verificare in sola lettura la copertura cTrader M15 delle quattro potenziali coorti V20.4. Non produrre performance direzionali dalle 12 osservazioni aggregate.
- Solo nuove decisioni pre-congelate e valori cTrader indipendenti permetteranno di stimare 60m/4h/24h, costi reali, baseline prezzo, intervalli di confidenza e coorti indipendenti.

## Free gate
Nessuna nuova API trading, Secret, conto, utente o spesa; solo nuovi file di ricerca e GitHub Actions già disponibile. **Quote GitHub Actions/billing non misurate in questo turno**, non dichiarare capacità Free illimitata.
**NO-GO** operativo: 0 nuovi eventi CVD reali ammessi da questa versione, 0 valutazioni di rendimento reali, 0 ordini/notifiche/merge/deploy.
