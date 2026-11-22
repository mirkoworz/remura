# REMURA COT v0.6 LAB — forward-only sidecar / Mac handoff
22 novembre 2026 (Europe/Rome) · NO-GO live.

## Differenza sostanziale dalla v0.5
La v0.5 testava esclusivamente lo schema additivo vuoto e il rollback DDL. La nuova v0.6 scrive **solo future acquisizioni sintetiche** nella sidecar in memoria e interroga il dato conosciuto alla decisione; NON importa righe legacy, non ricostruisce revisioni storiche e non altera cot_reports.

- Modulo: research/cot/cot_forward_only_v06_lab.py
- Test nuovi: research/cot/test_cot_forward_only_v06_lab.py (17 casi).
- Usa esattamente SyntheticCutover(synthetic=True) v0.5, che vieta database reali; nessun percorso file configurabile.
- Un capture event contenente fonte **dichiarata**, ricevuta **locale** e rows viene scritto in una transazione BEGIN IMMEDIATE assieme alle eventuali nuove versioni e al puntatore current_head.
- Versione immutabile distinta da current_head aggiornabile. Nessuna UPDATE della versione COT, trigger SQLite v0.5 ancora attivi.
- Duplicate byte-identical idempotente, campione invariato con evento aggiunto ma nessuna nuova versione, conflitto alla stessa ricevuta e backdating locale respinti, failpoint rollback dopo evento e dopo righe.
- Un as-of restituisce la versione locale precedente o UNKNOWN; non interroga la tabella legacy per riempire i vuoti. Audit verifica i hash, eventi-versioni, clock, trigger, FK, current_head e immutabilità logica.
- Risultati soltanto LOCAL_VERSION_UNATTESTED; le fonti CFTC e i timestamp non sono ricevute indipendenti. Il ledger non è un servizio live e non certifica il vero first-seen.

## Gate Mac e sicurezza
La vulnerabilità potenziale del codice attuale scripts/cot_monitor.py con ON CONFLICT DO UPDATE rimane senza modifica su Oracle. Non è stato verificato alcun danno ai dati reali.
La v0.6 è un **prototipo di comportamento**, non uno script di migrazione da eseguire. Prima di un cutover occorrono autorizzazione specifica, backup DB+WAL consistente e ripristinato, analisi schema reale, gestione legacy e retention, test compatibilità reader, capacità server e attivazione controllata del nuovo writer. Nessuna prova del backup Oracle qui.
**Alpha reale NO-GO. Collector Oracle, Mac e v1.65 preservati.**
