# REMURA — ROADMAP CHECKPOINT V07 — 22 novembre 2026, Europe/Rome

**Checkpoint incrementale, SOLO LAB. V01–V06 conservati senza sovrascrivere la loro storia.**
La fonte completa precedente è research/REMURA-ROADMAP-CHECKPOINT-20261122-V06.md sul branch research/contributors-free-evidence-gate-v093-20261122, commit V06 daacb5af8058853f3fe2f96f52946cea3ad68389. Il checkpoint V05 è su research/tv-no-signal-without-proof-v0188-20261122. La V07 aggiorna SOLO i nuovi fatti qui verificati e mantiene tutti i vincoli V06.

## Stato GitHub dopo il checkpoint V06
- Main verificato invariato: bd19918f457809f0568aee5c674b1b36a254971e (aggiornamento Myfxbook automatico del 22/11, non merge LAB).
- PR #105 Contributors v0.92: OPEN/DRAFT, merged=false, head 59bd2e57a6a0e9adad211e0f33907bc8ae1ee5f8.
- PR #106 TradingView v0.8.186: OPEN/DRAFT, merged=false, head c467cbafa5348a1507c9bd49cedb9e73fc43bc5a.
- Nessun merge o deploy eseguito.

## Nuovi sviluppi REALI: 2 filoni indipendenti
### TRACK 1 — Retail / Myfxbook v0.6 PROSPECTIVE PROVENANCE RECEIPTS
Branch: research/retail-provenance-receipts-v06-lab-20261122.
HEAD di codice, test, handoff e CI: 458c57dcfd9c27ad5229059eae8d461b83efc815.
File nuovi:
- research/retail/provenance_receipt_ledger_v06_lab.py
- research/retail/test_provenance_receipt_ledger_v06_lab.py
- research/retail/MYFXBOOK-PROSPECTIVE-PROVENANCE-RECEIPTS-V06-20261122.md
- .github/workflows/remura-retail-receipts-v06-only.yml
GitHub Actions: https://github.com/mirkoworz/remura/actions/runs/45029051564
**SUCCESS, 14/14 PASS**, log esaminato: Ran 14 tests, OK, REMURA_RETAIL_RECEIPTS_V06=14_14_PASS.

Nuovo valore scientifico: schema di eventi prospettici con distinzioni fra evento e registrazione, orario locale e GitHub riportato, completamento Pages e pubblicazione originale Myfxbook, identità contenuto, non-mutazione del ledger, controllo duplicazioni, catena hash SHA-256, e indicazione esplicita delle dichiarazioni di ricevuta indipendente. L'autodichiarazione di un witness NON certifica il primo accesso al dato: firme, risposta server e digest originali NON verificati. La catena non è tamperproof senza head ancorata esternamente. Nessuna esecuzione retroattiva del replay v0.5 e nessun test ripetuto. **NO_GO_SCIENTIFIC_ADMISSION**.

### TRACK 2 — TradingView v0.8.189 PER-DECISION EVIDENCE JUNCTION
Branch: research/tv-per-decision-junction-v0189-lab-20261122.
HEAD finale: 1426e9e61128744ce65331e6f2517198ba9fa8fb.
File nuovi:
- tradingview/delta-peaks/decision_evidence_junction_v0189_lab.py
- tradingview/delta-peaks/test_decision_evidence_junction_v0189_lab.py
- tradingview/delta-peaks/TV-V0189-PER-DECISION-JUNCTION-HANDOFF-20261122.md
- .github/workflows/remura-tv-junction-v0189-only.yml
GitHub Actions iniziale: https://github.com/mirkoworz/remura/actions/runs/45029054931 — 17 test PASS e 1 errore nella fixture: il test di scambio pointer usava erroneamente lo stesso ID prova in due slot e il codice rifiutava correttamente i pointer duplicati. Corretto SOLO il test, commit 1426e9e61128744ce65331e6f2517198ba9fa8fb, senza cambiare protocollo né comportamento produttivo.
CI finale: https://github.com/mirkoworz/remura/actions/runs/45029099045
**SUCCESS, 18/18 PASS**, log esaminato: Ran 18 tests, OK, REMURA_TV_JUNCTION_V0189=18_18_PASS.

Nuovo valore scientifico: join dichiarativo esatto di CVD M5, price-only, retail e COT per singolo decision_id; rifiuto di associazioni incrociate, duplicate o ambigue; validazione dell'ordine temporale e finestra ricezione M5; confronto esattamente sulla stessa barra M5; as-of/pubblicazione COT separati; mapping spot/futures NON verificato; missingness mai convertita in zero. Tutti gli ID, orari e SHA di input restano mere dichiarazioni, non primo-seen verificato. Nessuna misura di PnL, nessun segnale, nessuna promessa di alpha.
**ABSTAIN_RESEARCH_ONLY**. Protocollo V2 NON modificato.

## Protocollo TradingView V2 (congelato)
- Development dal 16/11/2026 00:00 UTC al 23/11/2026 00:00 UTC (escluso).
- Holdout 1 dal 23/11/2026 00:00 UTC al 30/11/2026 00:00 UTC (escluso).
- Holdout 2 dal 30/11/2026 00:00 UTC al 07/12/2026 00:00 UTC (escluso).
- Holdout 1 apre il 23 novembre alle 01:00 italiane. L'orologio NON prova che siano stati acquisiti dati autenticati e ammissibili.
- Primario CVD vs price-only a 60 min; secondari 4h/24h, FIFO M5, entro 120 s e prima del successivo close M5; costi ipotetici 0/1/2 pip; no tuning/backfill.
- Mai attribuire un edge istituzionale senza comparazione prospettica vera, mapping verificato, timeliness, corretta copertura M5 e esiti fuori campione.

## Altri filoni PRESERVATI INVARIATI
A — COT / Shark Science: revision lineage v0.1 20/20, atomic ingest v0.2 16/16, WAL reopen v0.3 15/15, global integrity v0.4 12/12. Rischio ON CONFLICT DO UPDATE in scripts/cot_monitor.py in fixture, NON corruzione Oracle confermata; migrazione additiva reale solo via Mac, con backup e consenso.
C — Contributors: Access+D1 15/15; revoca 12/12; routing/ownership 18/18; manual gate 18/18; hardcap Access 22/22; v0.93 free evidence 16/16. PR #105 DRAFT, pilot 1–2 amici ancora NO-GO. Serve lettura quote/piano/seats/Actions reali con consenso, Safari iPhone fisico, login/logout/revoca e isolamento utenti; OWNER approva soltanto, collaboratori modificano solo i propri livelli.
D — Retail: esistono dati Myfxbook reali e audit storico; as-of v0.1, EURUSD replay v0.2, Git provenance v0.3, Pages association v0.4, Actions bracket v0.5 (16/16 su tre catene di commit reali). Myfxbook indica retail, NON istituzionali. Run Pages iniziata NON significa contenuto pubblicato al medesimo istante.
E — FREE: workflow remura-cloudflare-budget-daily.yml già esistente, non attivato né duplicato. Run 44919682812 riporta Workers OK, D1 test/account storage OK, D1 quota UNKNOWN_NO_GRAPHQL_DATA; budget INCOMPLETE_OR_CRITICAL. Cloudflare Free, Access seat headroom, billing e GitHub Actions margin NON completamente provati. Nessuna nuova query GraphQL: le 2 precedenti sono già consumate. Nuove CI LAB brevi non certificano quote residue.
F — Mac/Oracle/Experience: remura-collector branch codex/mac-custody-checkpoint-20261120 SHA 7a23f61b2cb1e520bff623348366231ee093bb3f noto nel V06, non rivalidato ora. v1.65 root-owned predisposta, NON installata; autoupdater inibito; collector preservato. Experience v0.30 LAB: toro e orso 3D in collisione, loading, esplosione, logo REMURA/pinna, SMF e ringraziamento; foto personale da rimuovere in futura release, NON pubblicata. Private Capture v0.15 LAB, zero nuove acquisizioni.
G — Ampere Radar Oracle Milano + Telegram: esistente, NON duplicato o riattivato, repo mirkoworz/remura-ampere-radar, SHA V06 3cdd6b8ba6cd7601db29e3b8d6a092f96ce72e0a non rivalidato.
H — Squalincome, Shark Science, scoring, forza relativa, Delta, Telegram Contributors, UI pubblica: roadmap aperta, no produzione né promessa di rendimento.

## Gate e priorità V08
1. Integrare per prova singola un controller di VERIFICA realmente indipendente (firme, byte, prima disponibilità, versioni) soltanto dopo verifica margine FREE e consenso specifico per eventuale servizio; nel frattempo solo simulatori e verifica offline.
2. TV: preregistrare un inventario non modificabile delle decisioni reali; mancanze e orari attestati, nessun fold postumo; nessun segnale senza prove.
3. COT: da iPhone solo piano di migrazione additiva e schema anti-rollback; su Mac prove backup/cutover prima di qualunque collector.
4. Contributors: offline minimizzazione dei permessi e matrice OWNER/CONTRIBUTOR; quote reali e pilot richiedono nuova autorizzazione specifica.
5. Verificare quote Free correnti usando dati già disponibili, segnalando sempre UNKNOWN. Non lanciare monitor già esistenti senza richiesta.
6. Preservare lavoro Mac, PR #105/#106 DRAFT e main. Per ogni vera pagina REMURA modificata, intestazione con versione pubblica e data/ora Europe/Rome in alto su TUTTE le pagine.

**Riassunto:** due componenti indipendenti realmente implementati, 32/32 nuovi test GREEN nelle CI finali; nessun test storico ripetuto. Nuova roadmap V07 SOLO documentale. Stato alpha istituzionale NO-GO, pilot Contributors NO-GO, produzione INVARIATA.
