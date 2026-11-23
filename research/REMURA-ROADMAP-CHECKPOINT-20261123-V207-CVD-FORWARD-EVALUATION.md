# REMURA V20.7 — CVD forward-only, prezzi futuri reali, confronto price-only
**Aggiornamento LAB: 2026-11-23 13:35 CET — Europe/Rome.** Nessuna release LIVE.

## Provenienza e perimetro
Ramo separato `research/remura-v207-cvd-forward-price-validation-20261123`, base immutabile V20.6 `8e841ceaabbaee4959c151883418310f9a7ac3fb`. Non modifica main, collector Mac, Oracle, Cloudflare/D1, Workers, API broker, app pubblica, Secret o pagamenti. GitHub repository e' PUBBLICO: nessun prezzo personale, log broker o decisione privata devono essere committati qui.

Il precedente run reale [45121703188](https://github.com/mirkoworz/remura/actions/runs/45121703188) certifica 12/12 ricevute CVD TEST M5 nella sola finestra 04:30–05:25 UTC del 23/11, ma **12 OBSERVATION_ONLY, 0 trade e 0 outcome**. V20.4 ha dimostrato che sono solo **4 coorti temporali M15** (04:45, 05:00, 05:15, 05:30 UTC) correlate, non 12 decisioni indipendenti. Il run V20.4 e' gia' GREEN: **non ripeterlo**. Non risultano ancora acquisiti in questo filone i prezzi privati cTrader EURUSD del 23/11: completezza e ritorni 60m/4h/24h **non misurati**. Ne' 29 confronti retail V20.6 ne' il benchmark BCE daily costituiscono esiti futuri M15.

## Nuovo sviluppo V20.7
- `research/v207_forward_cvd_evaluation.py`: modulo **solo lettura**, solo EURUSD cTrader M15, riusa adapter gia' esistente `v204_private_cvd_price_coverage.py`; non invoca Internet, broker, D1, Cloudflare o collector. Accetta un ledger di **decisioni future scritte prima dell'esito**, non deriva decisioni dalle 12 ricevute aggregate.
- Contratto decisione: ID univoco, M5 chiusa, ricezione reale, registrazione, freeze, decisione `LONG/SHORT/FLAT` CVD, decisione baseline `LONG/SHORT/FLAT` basata solo su prezzo gia' noto, orario di conoscenza baseline, conteggio osservazioni, riferimento a SHA Git immutabile e orario di commit. Sequenza temporale obbligatoria, nessun anchor riusato, al massimo 30 minuti tra chiusura M5 e commit, una sola decisione per possibile ingresso M15.
- Ingresso **ipotetico** all'open della PRIMA candela M15 che inizi strettamente DOPO il commit, non all'open passato o alla chiusura CVD. Uscita sul close della quarta/sedicesima/novantaseiesima M15 **chiusa e consecutiva**: orizzonti 60m/4h/24h in tempo di calendario con barre vere; gap/weekend censurati, non ricostruiti; finestre ancora aperte non possono essere valutate.
- Il benchmark **price-only e' congelato nello stesso ledger, alla stessa entrata e sullo stesso set di orizzonti**. Nessuna scelta retrospettiva della direzione; `FLAT` e' ammesso come astensione e non paga costi. Osservazioni aggregate per decisione non vengono spacciate per campioni indipendenti.
- Pips ipotetici per direzione: `side * (close_future - open_ingresso) / 0.0001`. Net = gross meno spread pips ipotizzato **una volta** e slippage per lato **due volte**. NON equivale a PnL effettivamente eseguibile o a costi realmente osservati. In mancanza di entrambe le assunzioni di costo il software non pubblica metriche nette.
- **Soppressione di risultati prematuri:** mostra solo conteggi e maturazione fino a **30 confronti direzionali completi + almeno 10 finestre non sovrapposte** per ciascun orizzonte. Anche sopra soglia produce statistiche descrittive provvisorie, mai dichiarazioni di alfa o indipendenza.
- **Verifica esterna ancora mancante per definizione:** il software verifica il *formato* di SHA/orario Git ma non interroga GitHub per dimostrare che il commit esista o contenga davvero la decisione congelata; inoltre `provider=ctrader` nello SQLite non autentica da solo il broker o i prezzi. Il report espone esplicitamente `anchor_sha_and_time_claims_externally_verified=false`, `independent_price_feed_authenticity_externally_verified=false` e `scientific_alpha_established=false`. Richiedera' un passaggio di verifica esterna prima di qualsiasi statistica validata.
- `research/test_v207_forward_cvd_evaluation.py`: **12 test solo nuovi**, con prezzi/decisioni interamente SINTETICI, inclusi lookahead, commit tardivo, hash riusato, baseline retroattiva, M15 non matura, gap, costi di andata/ritorno, soppressione campione piccolo e confronto appaiato su 30 giornate fittizie.
- `.github/workflows/remura-v207-cvd-forward-validation.yml`: job dedicato solo a questi 12 test e gate senza ingressi, senza Secret e senza dati reali.

## Comandi SOLO LOCALI a futura autorizzazione Mac/VPS
```bash
# Solo i 12 nuovi test (non le suite gia' superate)
python3 -m unittest discover -s research -p 'test_v207_forward_cvd_evaluation.py' -v

# Audit di readiness: senza ledger e DB nessun rendimento
python3 research/v207_forward_cvd_evaluation.py

# Solo quando esistono prezzi e decisioni REALI congelate in anticipo, e accesso esplicito:
python3 research/v207_forward_cvd_evaluation.py \
  --decision-ledger /PERCORSO_LOCALE_PRIVATO/forward_decisions.json \
  --private-sqlite /PERCORSO_LOCALE_PRIVATO/prices.sqlite \
  --spread-pips VALORE_VERIFICABILE \
  --slippage-pips-per-side VALORE_VERIFICABILE
```
Gli ultimi due valori sono obbligatori per simulazioni nette; non abbiamo ancora misure storiche di spread/slippage: **non impostare valori inventati come fossero reali**. Lo SQLite viene aperto in `mode=ro` e `query_only=ON` dal lettore V20.4. Il report esclude prezzi, ticker broker, SHA/ID evento individuali, file privati e credenziali.

## Verifica nuova CI realmente conclusa
- Workflow dedicato: https://github.com/mirkoworz/remura/actions/runs/45175591389 — SUCCESS, HEAD testato `50bfa407dac8fad627e62e86834c5b4bf62b5c25`.
- Log ufficiale del job `causal-validation`: **Ran 12 tests in 0.053s — OK**; inoltre `REMURA_V207_NO_REAL_PRICE_OR_DIRECTIONAL_ALPHA=PASS`.
- Nessuna vecchia suite V20/V20.4/V20.6 rieseguita. Tutti i 12 test sono SINTETICI, e la seconda asserzione della CI verifica che senza ledger e prezzo il motore NON produce rendimento.
- Il commit successivo di questo documento non altera il codice gia' testato. Nessun test di outcome REALE, spread effettivo o identificazione istituzionale e' incluso.

## Risultato scientifico verificabile AL CHECKPOINT
- Trasporto CVD TEST: 12/12 ricevute vere gia' certificate, nessuna nuova richiesta o ri-esecuzione.
- Segnali direzionali forward realmente congelati: **0 attestati**.
- Prezzi futuri autentici M15 EURUSD consultati in questo filone: **0**.
- Outcome 60m / 4h / 24h e benchmark price-only netto realmente validati: **N/D**, non zero rendimento.
- Profitto, win rate e alfa istituzionale: **NON DIMOSTRATI**.
- Consumati: nessun nuovo servizio, richiesta API dati, deploy o traffico cloud; unicamente GitHub repository e CI di progetto separata (controllare eventuali quote account, non presupporre che siano illimitate).

## Prossima barriera prima di risultati con prezzi veri
1. Accesso espressamente autorizzato al DB cTrader privato **solo in lettura**, dopo coordinamento col Mac/Codex; utilizzare **V20.4** per contare le 4 coorti e i gap senza esporre OHLC.
2. Per i NUOVI eventi CVD, registrare e attestare una direzione prospettica realmente prodotta dal sistema, con timestamp di conoscenza verificato, snapshot immutabile PRIMA dell'ingresso, e baseline prezzo-solo definita senza vedere il futuro. Non trasformare le 12 ricevute old OBSERVATION_ONLY in segnali.
3. Validare esternamente SHA e commit time del freeze, identita' fonte prezzi, spread/slippage reali, latenza e sessioni. Eseguire le metriche paired per orizzonte, separando regimi/periodi e controllando l'overlap. Eventuali soglie/modelli da tarare su train, poi congelare prima del test temporale out-of-sample.
4. Solo dopo numerosita' e provenienza credibili valutare intervalli di confidenza, drawdown simulato, regime e valore incrementale rispetto a price-only; **nessun trading automatico o avviso operativo**.

**NB:** non confondere questo sviluppo con le prove preesistenti del trasporto CVD o della ricezione retail. E' nuova infrastruttura metodologica per misurare una futura ipotesi; senza campione forward genuino resta scientificamente NO-GO.
