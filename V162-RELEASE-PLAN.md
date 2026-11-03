# REMURA v1.62 — Piano di rilascio protetto (CANDIDATO, NON LIVE)

**Punto di partenza verificato:** applicazione LIVE v1.61, SHA codice/autoupdater `106e14a0b58c9e668b421a5982a9ffde22dc9243`. Main, al controllo del 03/11/2026, era `a32e8225c0291f10093518ea06655870aa6a7f9b`, **un solo commit figlio di dati Myfxbook**, non una release app. La differenza va riverificata prima di qualsiasi merge/installer.

**Dipendenze di ricerca:** PR #85 (comparatore offline UTC) → PR #86 (post-ingest opt-in e SQLite 256) → PR release v1.62. Le PR rimangono draft e impilate. Nessun merge a main fino a gate completi. Roadmap più recente candidata su PR #80: da integrare documentalmente, senza sovrascrivere lo stato storico con una riga datata.

## Modifiche di rilascio

- Esattamente **15 file**: backend `scripts/private_server.py`, `scripts/signals_monitor.py`; due **nuovi** moduli `scripts/h1_batch_comparison.py` e `scripts/h1_paired_store.py`; `nav.js`, `sw.js`; nove pagine HTML `index, asset, mercati, forex, catalogo, statistica-squali, stato-prezzi, fonti, impostazioni`.
- Tutte le pagine importano `nav.js?v=162`. Banner preparato `REMURA · Aggiornamento v1.62 · 03/11/2026 19:20 (Italia, preparazione)`, con **ora di installazione reale Europe/Rome** timbrata dall'installer, verificata nel manifest di rollback. Nuova shell PWA `remura-shell-v76-v1.62-h1-paired`, API private escluse dalla cache.
- `REMURA_H1_PAIRED_ENABLED=0` (o non presente) **obbligatorio nel primo deploy**. Installer rifiuta se è 1, non modifica l'ambiente e non crea chiamate broker, eventi o notifiche.
- Il nuovo monitor confronta solo 1–5 mercati salvati e già scansionati post-ingest, su un unico istante UTC, con H1 120 minuti/55 barre immutati. Gli aggregati non confrontabili restano N/D, non zero.

## Script preparati

- `deploy/oracle/release_v162.py`: SHA base v1.61 pinnato, 13 blob base certificati, nuovi file assenti obbligatori, tree/zip Git blob verificati, diff solo allowlist, due CI **push/main** verdi sullo SHA finale. `--check` legge solamente codice/SQLite e health. `--apply` separato usa lock autoupdater, backup SQLite tramite `backup_v156.py` (blob pinnato), restore-test isolato, rollback SHA256, installazione atomica 15 file, health e rollback dei 2 nuovi moduli in caso di errore. Non aggiorna stato autoupdater.
- `deploy/oracle/reconcile_v162.py`: script separato e indipendente, verifica SHA Git blob **immutabile** dell'installer, 15 file effettivi incluso nav timbrato, backup SQLite integro, manifesto rollback e due CI push/main; `--check` senza scritture, `--apply` aggiorna **solo** lo SHA nello stato autoupdater con backup dello stato. Non riavvia, non modifica SQL o config.
- I test `tests/test_release_v162.py` e `tests/test_reconcile_v162.py` sono offline, più test di comparazione e store. Prima di ogni deploy devono essere completati con success; test di vecchie versioni non vanno disabilitati per nascondere regressioni.

## Gate operativi (richiesti, NON ANCORA ESEGUITI)

1. **CI PR verdi** per Price e Insights, inclusi test dei due script release v1.62, file 9 pagine, privacy, flag off, backup/rollback, pin SHA e no nuovi fetch cTrader. Risolvere eventuali fallimenti senza aggirare i gate.
2. **Review e merge separati** #85, #86, poi rilascio candidato; ogni merge protetto e analisi diff completa. Se main contiene solo differenze dati Myfxbook, mantenere il vincolo separato codice/dati. Ogni nuova evoluzione non autorizzata arresta il rilascio.
3. **CI push/main verdi sullo SHA finale**; ottenere installer immutabile e controllarne SHA Git blob, non eseguire script da branch modificabili. Verificare prima che main non sia cambiato.
4. **Preflight VPS `--check`**, senza scritture, con health, file LIVE e stato autoupdater v1.61, H1 flag off, SQLite integrity, spazio e codice non alterato. Se fallisce, STOP.
5. **Installazione `--apply` solo dopo preflight**: backup SQLite e restore-test, lock, rollback, sostituzione esatta 15 file, health, verifica data/ora italiana visibile in alto sulle nove pagine e cache PWA.
6. **Riconciliazione autoupdater** `--check` poi `--apply` separati, dopo prova backup e SHA pinnato. Diagnostica privata su 38 prezzi, 34 Squalincome, 9 banner, zero eventi falsi.
7. **Attivazione reversibile** `REMURA_H1_PAIRED_ENABLED=1` con backup privato config e monitoraggio SQLite. Solo dopo almeno otto batch **reali**, misurare quanti confronti validi, H1 stale→ready e N/D. Non cambiare rotazione prima di valutare alternative su campione reale **a parità di budget API**.

## Vincoli sempre validi

Niente soglie più permissive, segnali fittizi, notifiche non validate, codice deploy senza backup o aumento broker calls. COT ufficiale e sentiment Myfxbook/Capital restano separati. CVD è proxy di tick-volume, non aggressor volume. Successive roadmap: qualità OHLC, rotazione, Squalincome/Radar, divergenze CVD, walk-forward con costi e rischio-rendimento, notifiche validate. Oracle Always Free, GitHub Actions, cTrader, Firestore: verificare periodicamente quote reali; basso uso RAM/disco **non prova** fatturazione zero.

**Questo documento NON autorizza il deploy: v1.61 resta LIVE fino alla certificazione di ogni gate.**
