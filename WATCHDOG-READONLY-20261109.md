# REMURA — Watchdog passivo della raccolta (Filone A)

**Data preparazione:** 9 novembre 2026 (Europe/Rome). **Stato:** branch di sviluppo offline, non rilasciato.

## Problema osservato nel codice

Il servizio systemd controlla il processo HTTP, non la vita del thread interno collector_loop: un arresto non gestito del thread può quindi lasciare il sito online con i prezzi non più raccolti.

## Soluzione proposta

Il GET privato già esistente /private-api/health aggiunge il campo collectorWatchdog senza cambiare i campi esistenti. Distingue threadState (running, stopped, disabled, unknown) dall'età informativa dell'ultimo batch con successo (recent, old_or_market_closed, unknown).

- Solo consultazione in-process, senza chiamate aggiuntive a cTrader, OCI, GitHub o Tailscale.
- Nessun thread/timer aggiuntivo, autospegnimento, autoripristino, notifica o riavvio automatico.
- Nessuna credenziale, OHLC, ID account o endpoint esterno nel risultato.
- Una candela vecchia non prova un malfunzionamento (weekend, festività, sessioni CFD, mercato chiuso).
- La vita del thread non dimostra che non sia bloccato, né la qualità di tutti e 38 i mercati.
- Soglia di 45 minuti descrittiva, non uno SLA e non un allarme automatico.

## Sicurezza del rilascio

Le PR B #89 e v1.65 #98 modificano anch'esse scripts/private_server.py: occorrerà risolvere l'integrazione in futuro prima di qualsiasi merge. Non toccare PR #89, #97, #98 o la versione LIVE v1.64. La numerazione e la data/ora in alto su tutte le pagine vanno aggiornate solo con un rilascio effettivo e dopo autorizzazione specifica.

## Test

- python -m unittest discover -s tests -p 'test_collector_watchdog.py' -v
- python -m unittest discover -s tests -p 'test_collector_watchdog_http.py' -v
- python -m unittest discover -s tests -p 'test_private_server.py' -v

Nessun test deve avviare broker o workflow manuali; test HTTP solo localhost e SQLite temporaneo. I test di integrazione HTTP devono essere eseguiti dentro un checkout completo del repository (non nel prototipo ZIP isolato).

## 09/11/2026 — Gate aggiuntivo sul bundle di rilascio

Il vecchio script v1.64 usa un elenco immutabile di 15 file, **senza** `scripts/collector_watchdog.py`. Non deve essere riutilizzato per questa PR: un server aggiornato con import del modulo mancante non può funzionare. L'autoupdater riconosce le modifiche sotto `scripts/` come `manual_required` e non le installa automaticamente. 

`watchdog_release_gate.check_bundle()` è un controllo statico **solo offline**, che esige entrambi i moduli nella lista futura e verifica sintassi/import/campo HTTP. **NON** certifica al momento hash, stato Oracle, backup, restore, costi o possibilità di deploy. Il rilascio rimane NO-GO finché non esisterà un installer/versione coordinata con rollback, controlli LIVE e autorizzazione esplicita. 

Test: `python -m unittest discover -s tests -p 'test_watchdog_release_gate.py' -v` su CI della PR. Nessuna modifica a `deploy/oracle/release_v164.py`, PR B, C, v1.65 o macchina LIVE.
