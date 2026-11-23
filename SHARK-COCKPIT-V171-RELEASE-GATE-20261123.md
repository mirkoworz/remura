# REMURA D — Shark Cockpit v1.71 LAB · Gate release iPhone
**23 novembre 2026 · Europe/Rome · NON PUBBLICATA · NO MERGE**

## Evidenza integrata nuova
- Ramo `feature/shark-cockpit-v171-my-sharks-iphone-20261123` basato su v1.70.
- La CI della v1.70 (run 45190807376) **FAILED** su test di allineamento HTML/versione. Non convertire il run storico in verde.
- Nuovo workflow **v1.71 integrato** `.github/workflows/remura-shark-cockpit-v171-focus.yml`, commit `4023a6b29b73127b0d05cfd0b825f55ede6157a4`, GitHub Actions run **45254668270 SUCCESS (77/77)**. Include storico, evidence, anatomia, movers, preferiti, core e release-consistency. Nessuna chiamata dati live, Secret, API privata, deploy o merge nel test.
- Preview `preview/REMURA-Shark-Focus-v171-iPhone-STANDALONE-LAB.html` NON ancora verificata su Safari iPhone in questa versione; la v1.69 era stata verificata. Evitare dichiarazioni “v1.71 provata su iPhone”.

## Perimetro reale v1.71
- Storico e radiografia settimanale sui record CFTC pubblici con data martedì e gap espliciti; nessuna interpolazione.
- Sentiment retail trattato a parte; preferiti `localStorage` soltanto nel Safari corrente, nessun account, nessuna sincronizzazione iCloud promessa.
- Stati informativi verificabili / non disponibili; COT **non** è CVD, ordine live, prezzo futuro o singola istituzione.
- **Non** incorporare ancora 7 fattori di Filone B o risultati predittivi A finché l'altro ramo non fornisce un contratto versionato con provenienza, time-of-availability e test.

## Contratto di collegamento previsto per A+B, non ancora attivo
Il successivo adapter UI deve accettare soltanto input **versionati** e originati dal sistema B/A autorizzato. L'assenza del feed deve restituire N/D, mai zeri sintetici.

**B → D**: `schema_version`, `market_id`, `cftc_contract_market_code`, `dataset` (TFF/Disaggregated), `report_date`, `first_seen_at`, `source_url`, `source_revision`, `factor_definitions_version` e array dei **sette fattori definiti da B**, ciascuno con ID noto, valore, unità, qualità e provenance. Rifiutare: identificatore sconosciuto, mismatch futures/spot, timestamp assente, revisione in conflitto e valori non validati. Le sette definizioni tecniche **non sono ancora nominate o inventate in questo filone**.

**A → D**: `experiment_id`, `evaluation_cutoff`, `outcome_horizon`, `n_decisions`, `benchmark_price_only`, `net_cost_model`, `metric_definition`, `result_quality`, `source_run_id`. Visualizzare risultati solo se l'esperimento dichiara misurazioni genuine e gate lookahead/costi superati. Non creare segnali, punteggi o precisione inesistenti.

Nessun nuovo fetch implementato finché non esistono endpoint e policy con proprietà di accesso verificate.

## Release minima coordinata
1. **Congelare componenti D v1.71**, usare run 45254668270 come evidence; non rilanciare vecchie suite senza diff applicativi.
2. **Safari iPhone**: apertura preview v1.71, CFTC quando presente, stato N/D quando assente, 2 martedì consecutivi, gap, stella ON/OFF, reload preferiti, navigazione diretta radiografia/storico, filtri, prova in condizioni di rete assente.
3. **Integrare selettivamente** da ramo UI a un futuro candidato release derivato da `main`, previo consenso. Inventariare file JS/CSS/HTML/preview/manifest/SW/nav, collisioni con A+B, Mac e Contributors. Proibito portare accidentalmente preview in produzione o sovrascrivere Splash Mac.
4. **PWA**: audit cache `sw.js`, invalidazione della vecchia shell, fallback offline solo asset pubblici e mai API private. Verificare cache e versione anche dopo aggiornamento Safari; preparare una strategia di ritorno al vecchio service worker in caso di guasto.
5. **Stamp globale**: al futuro aggiornamento applicativo, versione progressiva e data/ora reale Europe/Rome in alto su OGNI pagina HTML effettivamente aggiornata; per release produzione i timbri coerenti di tutte le pagine richieste. Conservare rollback e backup previsti dalla roadmap Mac/VPS.
6. **Gate release**: SHA main e CI integrata riscontrati, prova iPhone, firma/backup/rollback di competenza Mac, quote Free verificate, consenso esplicito per merge/deploy. Pilot Contributors è **un gate separato** e non può essere dichiarato attivo insieme alla sola release UI.

## Conflitto da non ignorare
Con main `4f8d8a707789eec29686a1568c4b8441e4c7d684`, confronto GitHub 23/11: ramo D **91 commit avanti e 4 indietro**, **49 file** nel diff. Serve integrazione **allowlisted** e audit di dipendenze, non merge diretto. I file HTML legacy e `nav.js` sono presenti nel diff: interazione possibile con i lavori Mac. PR #105 e #106 rimangono Draft e indipendenti.

**Tutto LAB. Nessun deploy, merge, attivazione, acquisizione di dati o nuovo costo cloud autorizzato da questo documento.**
