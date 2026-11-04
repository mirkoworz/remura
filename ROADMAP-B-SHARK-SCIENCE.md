# REMURA — TRACK B: Shark Science, CVD e validazione istituzionale

**Data di separazione:** 04/11/2026 Italia. **Roadmap coordinatrice:** [ROADMAP.md](ROADMAP.md). **Track parallelo:** [A — Qualità H1](ROADMAP-A-H1.md).

## Diario operativo — 04/11/2026, TRACK B (offline, senza deploy)

**Audit PR #77 e codice LIVE completato a livello statico.** PR #77 è draft su una base vecchia (v1.59) e non integrabile direttamente contro `main` v1.62: 17 commit/11 file; NON fare merge diretto. `main` all'avvio del lavoro: `43829313b41813776017e4a43a20204052a360bd`, branch B inizialmente identico. Identificato che:
- `price-core.js` calcola CLV × tick volume, con reset a mezzanotte UTC; il detector PR #77 conferma i pivot solo dopo 2 barre M15 a destra e scarta campioni mancanti/stale/gap. `confirmedAt` è **teorico**, non certifica `collectedAt` o `detectedAt`.
- `scripts/cvd_benchmark.py` confronta pivot prezzo+ATR con sottoinsieme filtrato dal CVD e tre rotazioni deterministiche; gli esiti dopo quattro M15 sono movimenti di prezzo **lordi**, non PnL. Rotazioni ≠ test di significatività; gli eventi sono correlati e il filtro CVD è meccanicamente legato al prezzo attraverso CLV.
- `scripts/cvd_session_replay.py` esegue sessioni UTC storiche, non oltre 45, con esclusioni di gap e volumi; **non prova** rendimento, successo out-of-sample o volume degli istituzionali.
- `scripts/statistical_validation.py` su main mantiene coorti forward-only, entry dopo osservazione e conteggi Wilson, **senza** spread/slippage; i campioni COT osservati realmente sono differenti da un backfill ex-post. Per ogni replay futuro occorre una data pubblicazione CFTC verificata; `reportDate <= observedAt` non è sufficiente.
- `insights-core.js` separa già COT, prezzi, sentiment Myfxbook/Capital e macro con narrative descrittive; il nuovo gate NON cambia l'UI.

**Codice realizzato su branch B (ricerca, non deploy):**
- Portati dalla PR #77 come **blob identici** soltanto `cvd-divergence-core.js`, tre `scripts/cvd_*.py` e quattro test relativi: nessuna vecchia `ROADMAP.md`, nessuna modifica al workflow generale.
- Nuovo `scripts/shark_science_gate.py` e `tests/test_shark_science_gate.py`: contratto UTC con timestamp di pubblicazione, raccolta/rilevamento, provenienza, mercato COT mappato, H1/M15/H4 ready, esclusione delle prove future/stale e separazione dei quattro canali COT/retail/prezzo/CVD. Output solo spiegazioni e stato `CONFERMA PARZIALE`, `DA OSSERVARE`, `NESSUN SEGNALE VALIDATO`; nessuna probabilità inventata, ordine, notifica o attribuzione istituzionale.
- Workflow **separato** `.github/workflows/shark-science-offline.yml` (runner Ubuntu standard di repository pubblico; timeout 5 min; nessuna connessione broker). Test sintetici e parità JS/Python. I test verranno verificati tramite CI della PR B, non dichiarati verdi in anticipo.

**Gate rimasti APERTI, prossimi passi:**
1. Verificare CI della PR B; correggere eventuali regressioni senza tocchi al TRACK A.
2. Audit data lineage completo: contratti `publishedAt` CFTC autentici, `sampledAt/availableAt` retail, `closedAt/collectedAt/detectedAt` OHLC/CVD e disponibilità di archivi genuini. Non simulare una pubblicazione o chiamare validi i dati non attestati.
3. Replay offline su OHLC archiviati reali tramite strumenti privati già autorizzati e **senza** nuovi broker GET; registrare universo iniziale, sessioni escluse, coverage, `N/D` e rischi di survivorship. Non mettere prezzi o account-ID in repo pubblico.
4. Solo su dati reali sufficienti: comparazione prezzo/ATR contro CVD proxy, contro controllo negativo **fuori campione**; entry dopo effettiva disponibilità, spread/slippage/commissioni stimate e stress test; train/validation/test cronologici con purging/embargo. Non presentare `favorableFraction` come win-rate netto.
5. Successivamente progettare Radar spiegabile con supporti/mancanze e notifica iPhone **disabilitata** finché un vantaggio statistico non è confermato in più periodi.

**Costi e release:** 0 nuove chiamate cTrader, 0 modifiche Oracle/collector, 0 servizi acquistati. Runner standard GitHub Actions nel repository `remura` pubblico ha utilizzo compute gratuito secondo documentazione GitHub; costi/quote di altre risorse, storage e il repo privato non sono qui attestati. LIVE resta v1.62: nessun banner cambiato perché nessuna release eseguita.

## Missione
Evolvere Radar Squali / Squalincome da presentazione di numeri a **ipotesi misurabili** su movimenti rilevanti, divergenze prezzo/CVD, conferme e condizioni di rischio. **Obiettivo: probabilità empiriche, non promesse di guadagno, né segnali attribuiti con certezza alle istituzioni.** Non aspettare che il track A finisca per lavorare **offline**; non utilizzare come conferma dati H1 vecchi o N/D.

## Base tecnica verificata
- REMURA applicazione LIVE **v1.62**, installata 03/11/2026 20:31 Italia, codice/autoupdater SHA `1568edefabc7bbdb7d06485d2b863b196a4e6155`; nove banner/health/backup/restore-test collaudati. Nel frattempo GitHub `main` può avanzare per soli dati Myfxbook: distinguere SHA codice LIVE e `main`.
- Dati già connessi: COT CFTC settimanale ufficiale (TFF e Disaggregated, segmenti distinti), sentiment retail Myfxbook/Capital separato, OHLC cTrader M15/H1/H4, cronologia e analisi Squalincome 34 mercati, indici/macro DXY/VIX, metalli e petrolio. Disponibilità e qualità vanno riverificate a ogni test.
- Track A sta misurando H1 paired; baseline 03/11 20:39 **26/34 H1 ready e 8 stale**, con 1 solo campione paired attestato alle 20:54 (**5 H1 ready prima/dopo, nessun recupero**). Non imporre attesa di A per esperimenti offline, ma **escludere dati stale** dai test operativi e non presentare risultati come LIVE con validazione incompleta.
- [PR applicativa #77](https://github.com/mirkoworz/remura/pull/77) draft, branch `feature/cvd-divergence-v160-offline-20261103`: già contiene laboratorio offline `scripts/cvd_divergence.py`, `scripts/cvd_benchmark.py`, `scripts/cvd_session_replay.py`, `cvd-divergence-core.js`, test e documentazione. **Non riscrivere tutto da zero**: audit del codice, degli input e dei test, confrontare con `main`, conservando il principio causale. Non unire tutta la PR #77 automaticamente: include anche un vecchio `ROADMAP.md` e workflow da valutare singolarmente.
- Il CVD ricostruito dalle candele cTrader con CLV×tick volume è **un proxy**, non vero delta bid/ask aggressore né volume eseguito istituzionale. La divergenza prezzo/CVD proxy è un'indicazione da sottoporre a prova, non prova che uno squalo stia acquistando/vendendo.
- COT arriva con ritardo settimanale e va confrontato con il suo **orario di pubblicazione realmente conoscibile**: proibito utilizzare nel backtest dati futuri o revisione ex-post senza rispettare tempi di disponibilità.

## Passi e criteri di completamento (B)
- [ ] **B1 — inventario fonti e qualità:** leggere il codice attuale, i campioni già disponibili e la PR #77; definire per ogni fonte timestamp effettivo di disponibilità, frequenza, ritardo, copertura e bias. Distinguere rigorosamente istituzionali, retail e proxy.
- [ ] **B2 — laboratorio divergenze prezzo/CVD offline:** testare swing prezzo e proxy CVD con barre chiuse, finestre sessione UTC coerenti, conferme di struttura/assorbimento Wyckoff/VSA solo come ipotesi etichettate; segnali causali senza look-ahead, no repaint, qualità volume/tempo e condizioni di esclusione chiare. Confrontare anche una baseline semplice senza CVD.
- [ ] **B3 — modello multistrato:** separare **contesto settimanale COT** (chi compra/vende sul mercato futures pertinente), **sentiment retail** (posizionamento contrarian quando verificabile), **contesto macro** DXY/VIX e **trigger intraday prezzo+volume**. Nessun peso magico o indicatore dichiarato migliore senza evidenza. Evitare falsi proxy COT per indici/broker e simboli privi di corrispondenza affidabile.
- [ ] **B4 — test scientifici:** walk-forward cronologico con train/validation/test, embargo/purge attorno alle finestre, costi spread/slippage, gap, sessioni e ritardo osservazione, metriche precision/recall, falsi positivi, payoff, drawdown, profit factor e robustezza per simbolo/regime. Non adattare le soglie usando lo stesso campione del test; nessuna garanzia di rendimento.
- [ ] **B5 — Radar e spiegazioni:** progettare verdetti trasparenti, per esempio `DA OSSERVARE`, `CONFERMA PARZIALE`, `NESSUN SEGNALE VALIDATO`, accompagnati da evidenze/assenze e motivi; non usare `BUY/SELL` come certezza. Qualità H1 dal track A deve essere un gate, non una scorciatoia.
- [ ] **B6 — notifiche solo dopo validazione:** progettare avvisi iPhone privati senza dati sensibili, duplicazioni o sovraccarico, attivabili solo in presenza di statistiche credibili e consenso. Prima non inviare notifiche operative.
- [ ] **B7 — rilascio futuro controllato:** CI offline, controllo regressioni, privacy, no segreti, nessuna nuova richiesta broker per algoritmo; eventuale implementazione LIVE solo dopo gate con unico merge/deploy coordinato. Ogni versione LIVE nuova: numero di aggiornamento e **data/ora effettiva italiana visibili in alto su tutte le nove pagine**, backup SQLite/restore-test, rollback, riconciliazione SHA.

## Vincoli condivisi e coordinamento
- Preferire componenti già presenti, calcolo locale e campioni gratuiti; **niente nuovi servizi a pagamento, nessun aumento API né scrape non autorizzato** senza un gate prezzi/quote e consenso dell'utente. Il rischio di fattura non si presume nullo solo perché c'è una quota gratuita.
- Lavorare sul ramo dedicato `research/track-b-shark-science-20261104`, creato dall'attuale `main`, e utilizzare PR **draft** per esperimenti; NON cambiare scheduler, collector, flag H1, server VPS, `ROADMAP-A-H1.md`, né installare una nuova versione mentre A è attivo.
- Per evitare conflitti: usare soprattutto `ROADMAP-B-SHARK-SCIENCE.md` per gli aggiornamenti B. Prima di merge/deploy rileggere HEAD GitHub e verificare PR/branch di A e B; integrazione e versione LIVE **serializzate**, due chat parallele solo nel lavoro preparatorio.
- Primo output utile: audit tecnico della PR #77 + piano di test scientifici implementabile **ora**, senza Termius e senza attendere gli otto campioni H1.
