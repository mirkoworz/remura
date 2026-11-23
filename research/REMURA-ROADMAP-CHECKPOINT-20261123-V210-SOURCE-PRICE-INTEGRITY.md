# REMURA V21.0 — Integrità prospettica del sorgente CVD e baseline M15

**Checkpoint LAB: 23 novembre 2026, ore 20:21 CET (run CI 19:21:49 UTC).**
Solo ricerca, nessuna release LIVE, nessun aggiornamento HTML. Ramo \`research/remura-v210-forward-source-price-integrity-20261123\`, base V20.9 SHA \`803b3a65a54e3f0493bc4a12162ff9b009b12b7b\`. PR #107/#109/#110 restano Draft, nessun merge. Non modificati Mac/Codex, collector privato, Oracle, Cloudflare/D1, Workers, Secret, API mercato o produzione.

## Punto scientifico centrale

I 12 CVD TEST M5 autenticamente raccolti nella finestra limitata del 23/11 ([run 45121703188](https://github.com/mirkoworz/remura/actions/runs/45121703188)) sono SOLO aggregati **OBSERVATION_ONLY**. Il file \`research/real-proofs/REMURA-V203-CVD-TEST-RECEIPTS-20261123.json\` dichiara esplicitamente \`without_raw_event_payloads: true\`, \`valid_unique_bars: 12\`, \`scientific_admission: false\`, \`outcomes_computed: false\`, \`independent_provenance: false\`, \`verdict: NO_OPERATIONAL_SIGNAL\`. Non è legittimo derivare da questi aggregati 12 nuove direzioni di trading. V20.4 riconduce le ricevute a quattro possibili coorti M15 correlate.

Il nuovo modulo **NON falsifica** payload individuali mancanti o timestamp retroattivi. Attende file originali **FUTURI**, loro ledger privati prespecificati con V20.9, prova di hash GitHub V20.8, e prezzi ctrader disponibili nel DB locale già esistente.

## Nuovo sviluppo REALIZZATO: \`research/v210_forward_integrity_gate.py\`

- Validatore privato **solo lettura**, nessuna rete salvo l'esplicito flag \`--github-readonly\` (max 2 GET GitHub REST anonime per UNA decisione; nessun retry; nessun push), nessuna creazione di file, nessuna acquisizione cTrader o TV, nessun ordine.
- Per UNA nuova decisione V20.9 prende: ledger congelato privato, manifest locale solo SHA256, **byte ORIGINALI del file sorgente** dell'evento CVD, e prezzi dal DB cTrader SQLite in lettura. Richiede che \`sha256(raw_source_bytes)\` corrisponda a \`source_event_sha256\` congelato; altrimenti **rifiuta**. Controlla che il manifest corrisponda all'intera decisione sigillata (salvo anchor).
- Valida la catena temporale evento M5 chiuso → ricevuto → registrato/congelato → dato baseline già noto. Rifiuta evento vecchio oltre 12 minuti, futuro o ricezioni incoerenti. Applica esattamente la policy V20.9 e **una** osservazione per decisione, non 12 trade fasulli.
- Ricostruisce le ultime **cinque** M15 chiuse **al timestamp originale di freeze**, non cinque M15 più recenti del giorno in cui si analizza. Richiede cinque barre contigue, età massima 20 minuti al freeze, corrispondenza integrale di timestamp + OHLC con lo snapshot M15 sigillato nel ledger; **non usa prezzi futuri per ricostruire il benchmark**.
- Ricalcola il benchmark deterministico \`M15_FIVE_CLOSED_CONTIGUOUS_CLOSE_MOMENTUM_SIGN_V1\`: LONG se ultimo close > primo, SHORT se minore, FLAT se uguale. Rifiuta direzione precompilata diversa anche se si prova a ricalcolare un nuovo hash con quel dato falso.
- Se \`--github-readonly\` è attivato separatamente, riutilizza il verificatore V20.8 per il run GitHub \`push\` successo, SHA e first-seen UTC, senza inviare payload o prezzi; poi usa V20.7 esclusivamente per **conteggiare** finestre M15 future e applicare gli esistenti gate di campione/costi. In V21.0 una finestra completa è classificata come **copertura del prezzo**, NON profitto autenticato. Mantiene \`actual_forward_outcomes_evaluated=false\` e \`scientific_alpha_established=false\`.
- Output aggregato, senza quote, simboli broker, ID evento, raw bytes, nonce o percorsi privati. Dichiara sempre che: digest originale coerente **non è una firma autentica TradingView**; il lato CVD può essere ancora una dichiarazione; i timestamp ricevuta provengono dal file locale; la semplice uguaglianza col DB corrente **non prova che quel dato fosse presente nel DB al freeze**. Prezzi broker e spread/slippage non sono verificati esternamente.

## Verifica nuova, senza ripetere suite superate

\`research/test_v210_forward_integrity_gate.py\`: **17 test completamente sintetici** con mock GitHub; includono fonte raw modificata, riaggregazione 12 ricevute rifiutata, prezzo futuro escluso dal vecchio snapshot, manipolazione benchmark anche dopo nuovo hash, manomissione OHLC congelate, correzione dello storico DB, receive-time tardivo, flags di autenticazione falsi, provider scorretto, hash GitHub con conclusion=failure e costi ipotetici non scambiati per osservati.

\`.github/workflows/remura-v210-forward-integrity-tests.yml\`: esclusivamente 17 nuovi test, nessun Secret, nessun input di mercato vero e seconda barriera CLI a input vuoto.

GitHub Actions [run 45248148888](https://github.com/mirkoworz/remura/actions/runs/45248148888) — SUCCESS HEAD \`21b3e209bc4fb335742d02ef3bba74d25f0cbbc2\`, log \`Ran 17 tests ... OK\` e \`REMURA_V210_NO_REAL_SOURCE_OR_PRICE_NO_CLAIM=PASS\`. **Verifica finale del nuovo codice aggiornato**: [GitHub Actions run 45248293673](https://github.com/mirkoworz/remura/actions/runs/45248293673) — SUCCESS su SHA \`731d5599c4d56c2743252da0952bac6f6e5ff96c\`, log ufficiale \`Ran 17 tests ... OK\` e \`REMURA_V210_NO_REAL_SOURCE_OR_PRICE_NO_CLAIM=PASS\`. Qui viene testata anche la nuova condizione \`actual_forward_outcomes_evaluated=false\` quando una finestra M15 è completa ma non vi è performance autentica.

## CLI per un futuro collaudo LOCALE, solo con autorizzazione separata

~~~bash
# Privo di effetti: nessun input o API
python3 research/v210_forward_integrity_gate.py

# SOLO con file reali privati disponibili e autorizzazione di accesso:
python3 research/v210_forward_integrity_gate.py \
  --private-decision-ledger /PRIVATO/decisione.private.json \
  --private-manifest /PRIVATO/decisione.hash-only.json \
  --original-event-bytes /PRIVATO/evento_cvd_originale.raw \
  --private-sqlite /PRIVATO/ctrader_prices.sqlite

# Il flag --github-readonly aggiungerebbe al massimo due GET anonime
# per verificare un run di push hash-only già esistente.
~~~

Nessun comando è stato eseguito sul Mac/Oracle o sui file dati privati oggi da questo filone. Nessuna nuova credenziale o attivazione Cloudflare.

## Prossimo gate non aggirabile

1. Ottenere in autorizzazione separata dati PRIVATI cTrader M15 in SOLA lettura per controllo copertura delle quattro coorti preesistenti senza dedurre direzioni; sincronizzare con Codex e non ripetere test di sistema già superati.
2. Abilitare, dopo consenso specifico, la raccolta di NUOVI eventi M5 originali con evento e digest fissati nello stesso momento, timestamp first-seen e direzione definita in modo esplicito e verificabile. Senza prova reale di provenienza non chiamarli segnali autentici.
3. Pubblicare eventualmente **solo** SHA256 nonce-salted su GitHub, in un workflow autorizzato; archiviare i ledger privati fuori dal repository pubblico. V20.7/V20.8/V20.9/V21.0 costituiscono la catena logica di verifica, ma il pilota non è stato attivato.
4. Assumere e verificare costi reali, sessioni, overlap e benchmark price-only identico per 60m/4h/24h. Necessari almeno 30 confronti e 10 non sovrapposti per orizzonte prima di mostrare **statistiche descrittive provvisorie**; questo non è di per sé significatività o alfa.

**Stato scientifico: NO-GO per ingressi reali, notifiche operative, tassi di successo e prestazioni istituzionali.** Nessun prezzo reale indipendente consultato dal DB; esiti N/D, non 0. Nuovi servizi a pagamento ZERO; zero richieste broker/Cloudflare; una nuova CI GitHub Actions su risorse già presenti, quote account non verificate come illimitate.
