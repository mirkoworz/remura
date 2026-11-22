# REMURA COT v0.5 LAB — schema additivo sidecar, RAM soltanto
22 novembre 2026, Europe/Rome.

## Contesto e limite
Nel codice operativo scripts/cot_monitor.py, cot_reports usa ON CONFLICT DO UPDATE mentre cot_first_seen e' conservato al primo inserimento. Cosi' una revisione sopravvenuta rischia di contaminare gli as-of storici. Il pruning legacy non consente di ricostruire versioni perse. Il rischio e' verificato nel codice, NON e' corruzione Oracle verificata.

## Nuova consegna
- research/cot/cot_sidecar_cutover_v05_lab.py: SyntheticCutover(synthetic=True) usa solo SQLite :memory:; nessun path o database da passare.
- research/cot/test_cot_sidecar_cutover_v05_lab.py: 13 nuovi test mirati sullo schema, rollback, quarantena e compatibilita'.
- Crea tre nuove tabelle append-only vuote e quattro trigger di blocco UPDATE/DELETE, senza modificare cot_reports e cot_first_seen.
- DDL eseguito con execute per statement in SAVEPOINT; usare executescript qui avrebbe fatto commit implicito e compromesso il rollback.
- Failpoint sintetici dopo creazione tabelle e dopo trigger; rollback deve lasciare zero oggetti sidecar.
- Hash locale e conteggi delle tabelle legacy prima/dopo, e controlli FK e trigger.
- Niente inserimento di vecchi dati nel versionamento nuovo: legacy_asof restituisce quarantena e mai posizioni per una decisione.
- Nessun recupero storico, nessuna attestazione first-seen e nessuna migrazione operativa.

## Mac - gate operativo non autorizzato
1. Il collector reale, v1.65 e autoupdater rimangono riservati al Mac. Nessuna attivazione remota.
2. Backup consistente database+WAL, prova ripristino isolato, verifica spazio e schema reale, solo con nuovo permesso.
3. Cutover additivo reale e compatibilita' del reader da studiare in staging separato, senza attribuire un timestamp di pubblicazione CFTC ai vecchi dati.
4. Eventuale dual-write del nuovo acquisito e rollback soltanto dopo permesso; mantenere provenance indipendente e blocco retrodatazioni.

NO-GO per migrazione Oracle e alpha istituzionale; zero dati live toccati.