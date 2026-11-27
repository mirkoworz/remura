# REMURA v0.8.136 LAB — runtime e riconciliazione v1.65
17/11/2026, sessione 14:22 CET — PR #102 DRAFT. Nessuna release.

## Entry point verificati nei sorgenti ancorati
- systemd: /opt/remura/.venv/bin/python /opt/remura/scripts/private_server.py --database /opt/remura/private/remura-prices.sqlite3; WorkingDirectory /opt/remura; EnvironmentFile privato.
- cTrader: private_server.collector_command usa sys.executable e scripts/ctrader_feed.py; SDK ctrader_open_api e Twisted importati nella funzione collect; find_spec in ctrader_preflight verifica la sola reperibilità, non il successo di import o autenticazione. Non installare SDK né eseguire collect nel LAB.
- COT: cot_monitor.collect_once importato nel server; libreria standard; nessun nuovo pacchetto.
- Myfxbook, IG, Capital: subprocess separati via sys.executable, rispettivamente update_myfxbook.py, update_ig.py, update_capital.py. Import di questi entrypoint non è esecuzione dei rispettivi main né prova di configurazione.
- MetaTrader5: solo ramo mt5_prices in price_feed, documentato per Windows; non aggiungere al venv Oracle ARM64.
- install.sh base installa python3, venv/pip, ca-certificates, git, rsync, curl da Ubuntu; SDK cTrader separato dopo OAuth. Non è una prova dei pacchetti realmente presenti.
- Riferimenti: base 30de2987fe28ee73044448817e66ac60391e3357 e candidato ABC SHA256 b70b82f6b2752536b5bbe8c6493072c4b5cff982da0f35124beb60779b92d4ab.

## Osservazione import-time
Il nuovo probe importa sette entrypoint in processi separati -I -S -B, HOME temporanea e ambiente senza credenziali. Audit hook blocca rete Python, subprocess, connessioni SQLite e principali scritture. Non è sandbox per codice ostile. Registra file locali realmente importati e differenze dal grafo statico; non chiama main o funzioni collector. Nessuna rimozione automatica: gli strumenti non raggiunti restano non classificati finché non si verificano invocazioni esterne e runbook.

## Riconciliazione updater / pacchetto
- autoupdate.py base classifica scripts/, deploy/oracle/ e .github/workflows/ manual_only; non utilizzare la sincronizzazione automatica per ABC.
- sync automatico non usa --delete e preserva private/, local/, data/prices/, .venv e credenziali. Il suo rollback del codice non è rollback del database.
- L'installer bootstrap rsync ampio e riavvia il servizio: non usarlo per v1.65.
- release_v164.py e backup_v156.py sono riferimenti, non installer compatibili: il backup usa SQLite backup API e restore isolato, ma va estesa la custodia cifrata indipendente e verificata la copertura di tutti i DB/stato.
- Manifesto futuro: separare asset UI, script runtime, componenti facoltativi, strumenti LAB, file deploy e stato mutabile; conservare i 90 cambiamenti già ancorati e registrare file invariati necessari, permessi, hash sorgente e destinazione, dipendenze installate, esclusioni e file nuovi. Non copiare data/ storici o credenziali come overlay generico.
- Gate aperti: inventario reale read-only redatto dei file installati e venv (senza env/token); mapping dei riferimenti esterni; manifesto completo e confronto con installedSha; backup coerente per DB e metadata, cifratura con chiave fuori VPS, prova ripristino isolata; rollback e decisione release. Nessuna attivazione o installazione.
