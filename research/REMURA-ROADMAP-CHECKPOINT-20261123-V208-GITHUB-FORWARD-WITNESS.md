# REMURA V20.8 — prova server GitHub delle decisioni forward (hash-only)
**Aggiornamento LAB: 23 novembre 2026, ore 15:14 CET — Europe/Rome.** Nessuna versione LIVE, deploy o modifica HTML.

## Stato confermato
Base V20.7 su SHA `331141709b6ff46b3ba86af6d1d245b042d2d8eb`. Ramo isolato: `research/remura-v208-github-decision-witness-20261123`. V20.7 e PR #107 restano Draft e intatti. Non sono stati modificati collector Mac, Oracle, Cloudflare, D1, accessi, broker, Secrets, prezzi privati o app di produzione; **nessuna chiamata a provider di mercato**.

La prova reale V20.3 [run 45121703188](https://github.com/mirkoworz/remura/actions/runs/45121703188) conserva 12/12 ricevute CVD M5 TEST del 23/11, **12 OBSERVATION_ONLY**, zero decisioni direzionali/successi. V20.4 certifica soltanto quattro potenziali coorti M15 correlate. Non trasformarle retrospettivamente in segnali. Il materiale GitHub NON fornisce prezzi futuri cTrader autentici del 23 novembre: 60m/4h/24h, PnL ed edge restano **N/D**.

## Nuovo sviluppo
- `research/v208_github_decision_witness.py`: lettore di prova che, soltanto se avviato ESPLICITAMENTE con `--github-readonly` e un ledger privato, compie **max 10 GET anonimi e non autenticati** alla **sola GitHub REST API** (max 5 decisioni per invocazione, due GET ciascuna, **nessun retry**).
- Ogni decisione privata possiede una nonce segreta casuale >=128 bit. La serializzazione canonica SHA-256 **esclude** i campi ancora mutabili dell'anchor; l'hash comprende direzione CVD, benchmark price-only, timestamp, ID e nonce. Un file pubblico di manifest contiene SOLO `schema` e `commitment_sha256`, nel path `research/forward-anchors/<hash>.json`. Non mandare a GitHub il ledger privato, la nonce, prezzi o decisioni reali.
- Il verificatore confronta: run `push` di GitHub Actions **SUCCESS** su branch+workflow dedicati e repository ID, `head_sha` autenticato dal server, `created_at` del server, e il manifest effettivamente servito dal medesimo commit SHA immutabile. Rigetta hash alterato, filename errato, SHA contraffatto, workflow/repo/branch diversi, timestamp futuro, duplicati e mancato rispetto del gate causale V20.7. Usa come tempo di conoscenza il **run.created_at server**, **MAI** la data del commit indicata dall'utente.
- Non si attiva nessuna raccolta o ricezione live di CVD; i timestamp e la provenienza del feed CVD non sono autenticati da questo hash: `underlying_cvd_receipt_provenance_independently_verified=false`.
- `.github/workflows/remura-v208-anchor-witness.yml`: solo sul ramo di ricerca e solo se qualcuno pubblica volontariamente un NUOVO hash manifest; verifica che i file non contengano altri campi. Non carica dati o Secrets. `.github/workflows/remura-v208-github-auditor-tests.yml`: verifica separatamente il codice con soli mock sintetici.
- `research/test_v208_github_decision_witness.py`: **13 NUOVI test**, no riesecuzione dei vecchi. Fallimento iniziale dovuto a un'aspettativa troppo specifica sull'ordine del rifiuto hash, corretto nel solo test; produzione e v20.7 invariati.

## Prove attestabili
**Nuovi 13 test sintetici:** [Actions run 45191409820](https://github.com/mirkoworz/remura/actions/runs/45191409820) **SUCCESS**, log ufficiale `Ran 13 tests ... OK`, marker `REMURA_V208_NO_REAL_LEDGER_NO_GITHUB_CALLS_NO_ALPHA=PASS`. Le risposte GitHub di questi test erano MOCK, non una prova di runtime LIVE.

**Vero test di custodia temporale GitHub con impegno SINTETICO, NON dato di mercato:**
- Hash pubblico (senza direzione o nonce): `b6929ad503806a0d706e270ff0803fdaab784495705930a8997958ddbb6804ca`.
- [Commit fissato 3fe1a28](https://github.com/mirkoworz/remura/commit/3fe1a28acc27f046cd4d367093982b9fa9f9cd42) contiene esclusivamente un manifest hash-only nel nuovo path `research/forward-anchors/`; non è stato pubblicato alcun ledger.
- [GitHub Actions run 45191640343](https://github.com/mirkoworz/remura/actions/runs/45191640343) **SUCCESS**, path del workflow `.github/workflows/remura-v208-anchor-witness.yml`, `event=push`, `head_sha=3fe1a28acc27f046cd4d367093982b9fa9f9cd42`, repository `mirkoworz/remura` ID `1422235455`; `created_at=2026-11-23T14:12:07Z` (**15:12:07 CET**). Log `REMURA_V208_HASH_ONLY_WITNESS=SUCCESS`.
- Verifica indipendente col connettore GitHub della URL pinned alla SHA: manifest con lo STESSO hash, blob `ab8e6cae2296a43d53e99c7def209d6b57f7b897`.
- Il ledger **sintetico** temporaneo, mantenuto solo localmente e NON caricato, è stato serializzato in modo canonico e la sua SHA-256 coincide. Il fittizio M5 event-close era `2026-11-23T14:10:00Z`, perciò dopo il witness GitHub delle 14:12:07Z l'**unica entrata teorica** ammissibile sarebbe l'open M15 `2026-11-23T14:15:00Z`. Questa è una dimostrazione di restrizione cronologica, **non** un ordine e non una previsione di mercato.
- Direzione sintetica `FLAT`, nessuna reale lettura CVD o prezzi cTrader, nessun risultato statistico.

## Come funzionerà in futuro — NON avviare ancora
1. Per ogni FUTURA decisione, il processo legittimo che genera segnali deve congelare un ledger privato PRIMA dell'esito con evidenze autentiche di fonte, contemporaneamente al benchmark prezzo-solo e nonce casuale; la nonce non deve comparire su GitHub.
2. Pubblicare in ramo di ricerca SOLO il manifest hash-only e attendere che GitHub registri `created_at` di un run `push` effettivamente SUCCESS. Il record privato assocerà `anchor.workflow_run_id` a quell'esatto run. L'entrata si determina SOLO dalla prima M15 successiva al witness del server, non dal precedente timestamp dichiarato.
3. Con un accesso **nuovamente autorizzato** al DB cTrader locale e senza conflitti Mac/Codex, verificare M15 future reali in sola lettura tramite V20.4/V20.7 e confrontare lo stesso prezzo su 60m/4h/24h, baseline, gap e costi realmente documentati. V20.8 non prova autenticità della fonte CVD o del broker.
4. Non confondere 5 decisioni per esecuzione con 5 trade indipendenti; occorre un campione molto più lungo, regimi, embargo/overlap, intervalli di confidenza e out-of-sample prima di affermare vantaggio.

## Come interrogare solo in ambiente privato, quando esplicitamente autorizzato
```bash
python3 research/v208_github_decision_witness.py
# Senza input: nessun network, nessuna decisione e nessun alpha.

# Solo dopo pubblicazione di hash veramente prospettici e consenso separato:
python3 research/v208_github_decision_witness.py \
  --private-decision-ledger /PERCORSO_PRIVATO/forward_decisions.json \
  --github-readonly \
  --private-sqlite /PERCORSO_PRIVATO/prices.sqlite \
  --spread-pips VALORE_DOCUMENTATO \
  --slippage-pips-per-side VALORE_DOCUMENTATO
```

**GATE scientifico V20.8: NO-GO per qualunque indicazione di entrata reale.** La vera prova è della **custodia temporale dell'hash** e dei controlli anti-lookahead; nessuna misura di efficacia predittiva o di capitale in questa fase. Costi: zero nuovi servizi, zero acquisti e nessuna API broker; due CI nuove e una prova GitHub Actions hanno usato soltanto risorse GitHub, quote account non dichiarate come illimitate.
