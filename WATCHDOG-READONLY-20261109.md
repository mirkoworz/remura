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


## 09/11/2026 — Rehearsal offline di integrazione, hash e rollback (SOLO PR #99)

L'audit GitHub del 9 novembre mostra che le PR [#89](https://github.com/mirkoworz/remura/pull/89) (B, HEAD osservato `9784fb1e`), [#98](https://github.com/mirkoworz/remura/pull/98) (v1.65, `69886bc1`) e [#99](https://github.com/mirkoworz/remura/pull/99) (watchdog, `1d60316e` prima di questa modifica) cambiano TUTTE `scripts/private_server.py`. Il fatto che GitHub mostri una PR come mergeable individualmente NON dimostra la compatibilità della combinazione delle tre. Questi HEAD sono un'istantanea, non pin immutabili per un futuro merge.

- `scripts/watchdog_staging_rehearsal.py:audit_shared_server` lavora su sorgenti fornite dal chiamante, identifica fork e possibili intervalli sovrapposti, ma obbliga **sempre** alla riconciliazione manuale di qualunque variazione. Non ottiene o unisce branch via rete e non firma la provenienza dei file. I test di conflitto usano file sintetici, NON una fusione vera delle tre PR.
- `verify_staged_bundle` verifica la corrispondenza esatta tra manifest, byte di tutti i file e digest SHA-256 dichiarati, oltre al contratto di import/watchdog. I PIN sono **forniti dal chiamante e non autenticati**: nessuna attestazione della VPS, dell'installer futuro, del codice installato o autorizzazione al merge. Lo storico installer v1.64 non include il modulo e resta NO-GO.
- `simulate_rollback` prova fallimento **prima** e **dopo** la sostituzione, più un caso completato, esclusivamente in una directory `TemporaryDirectory` appena creata e poi eliminata dal runner. Non accetta path di destinazione e non prova il backup/restore di SQLite, un rollback autoupdater o la ripartenza systemd reali.
- Workflow Watchdog già esistente, solo evento `pull_request`, nessun `workflow_dispatch`, nessuna API esterna o servizio nuovo. Test di protezione e regressioni sono offline. Lo stato CI dell'ultimo commit va letto dalle Actions GitHub prima di dichiarare verde.

**MANCANTE PER UN VERO GO:** acquisire i HEAD aggiornati delle tre PR, revisione e fusione serializzata del server, dipendenze/manifest e test end-to-end sul codice risultante, hash di origine autenticati, installer di nuova versione, preflight VPS, risorse e costi OCI, backup/restore-test off-host e rollback LIVE autorizzato, banner con numero/data/ora reali in alto in tutte le nove pagine, CI completa e consenso esplicito. PR #99 rimane OPEN/DRAFT; nessun merge, deploy, SSH, Oracle, Tailscale, modifica segreti, chiamata broker, Filone B o C.
