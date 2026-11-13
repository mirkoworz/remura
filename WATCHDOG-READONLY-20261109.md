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


## 09/11/2026 — Reconciler strutturale incrociato, senza fusione (solo DRAFT #99)

**Fonte verificata prima del commit:** diff reali delle tre PR su `scripts/private_server.py`:
- **B #89** (HEAD osservato `9784fb1e`) modifica `collect_once` per il parent read del file JSON, `retail_once` per ricevute originali e `squalincome_loop` per il percorso periodico di ricerca disattivato per default. Non riattivare le opzioni scientifiche.
- **v1.65 #98** (HEAD osservato `69886bc1`) aggiunge `StorageMetadataCache`, `storageInventory` sulla rotta risorse se flag OFF-by-default è esplicitamente ON, e avvio della cache in `main()`.
- **Watchdog #99** modifica l'import del modulo, `http_handler(db_path, collector_thread=None)`, il payload HEALTH e il passaggio del thread da `main()`. **#98 e #99 modificano entrambe `main()` nella zona di avvio thread/stop; l'unione non può essere presunta sicura**. L'integrazione futura deve conservare sia `_STORAGE_CACHE.start(db_path,stop)` condizionata, sia `thread=None` e `collector_thread=thread` nell'handler.

Nuovo `scripts/watchdog_crosspr_contract.py:inspect_candidate(source,pin)`:
1. Verifica che il codice candidato sia Python parsabile e che il suo SHA-256 uguagli il pin fornito dall'operatore. Il pin **non è autenticato** dal modulo, e non dimostra identità del codice LIVE.
2. Verifica **solo strutturalmente** il mantenimento delle opzioni B disattivate per default, la cache v1.65 e la diagnostica watchdog con binding del thread.
3. Se manca una dipendenza restituisce `BLOCKED_MISSING_CONTRACTS`; in presenza delle forme attese restituisce solo `STRUCTURAL_REVIEW_REQUIRED`, **mai** `release_authorized=true`. Un codice che soddisfa AST può comunque essere errato, regressivo o insicuro; non è un validatore semantico.
4. Le prove `tests/test_watchdog_crosspr_contract.py` usano sorgenti Python sintetici per simulare un'integrazione e casi di omissione/attivazione accidentale. Il test sul `private_server.py` reale della #99 deve restituire BLOCKED per B e v1.65, con la parte watchdog presente. Questo è un test POSITIVO di fail-closed, non un fallimento della PR.

**Piano successivo, senza eseguirlo:** prima di un futuro merge preparare in UN SOLO ramo di integrazione serializzato un candidato con gli HEAD aggiornati e verificati; audit funzionale, CI completa, diff allowlist, prove su flag spenti e invocazioni effettive, installer/manifest e rollback con DB off-host, verifica SHA LIVE, quote e autorizzazione specifica. Non copiare alla cieca i vecchi HEAD: cambiano quando B o C prosegue. Non riusare `release_v164.py`. Il nuovo strumento NON unisce branch, NON tocca main, B, C, Oracle, Tailscale, VPS, API o segreti. Stato sempre OPEN/DRAFT/NO-GO.


## 09/11/2026 — Blueprint installer a 16 file e rollback transazionale sintetico, NO-GO LIVE

**Codice su sola PR #99:** `scripts/watchdog_release_blueprint.py` e `tests/test_watchdog_release_blueprint.py`, eseguiti dentro il workflow PR-only Watchdog già esistente. Nessuna modifica a `deploy/oracle/release_v164.py`: quell'installer serve esclusivamente v1.64, contiene una base v1.63 immutabile e **non** sa creare `scripts/collector_watchdog.py`; non riusarlo per distribuire la nuova funzionalità.

**Prova aggiunta:**
- Legge tramite `ast.literal_eval` la vera lista statica `FILES` di v1.64 senza importare né eseguire l'installer: deve contenere esattamente 15 file, incluse le nove pagine HTML, e `NEW_FILES=()`. Una modifica inattesa del contratto è `INVALID_LEGACY_INSTALLER`.
- Prepara in memoria il modello candidato **15 vecchi file + 1 nuovo modulo**, legge i **byte veri del checkout GitHub della PR #99** (inclusi CSS/JS/HTML e asset binario splash), calcola impronte SHA256 e verifica presenza/import/sintassi del Watchdog tramite il gate offline esistente. Queste impronte sono calcolate sui byte dello stesso candidato, **non sono PIN di fonte autenticata o prove di identità del commit LIVE**.
- Segnala esplicitamente `V164_REFERENCE_NOT_A_NEW_RELEASE` per le pagine/banner/cache ancora v1.64. **Nessun nuovo numero di versione o timestamp di deploy viene inventato**: il futuro rilascio approvato deve timbrare data/ora Europe/Rome reale nelle nove pagine, aggiornare cache e verifica dell'installer/autoupdater.
- Su `TemporaryDirectory` creata solo dal test, con **15 predecessori artificiali** e modulo Watchdog inizialmente assente, effettua una simulazione della sostituzione di tutti i 16 file. Ripete la procedura iniettando un guasto dopo ciascuno dei 16 file: controlla il ripristino di tutti e 15 i predecessori sintetici e la rimozione dell'eventuale nuovo modulo. La prova resta confinata alla cartella temporanea del runner, non legge né modifica la VPS.
- Rifiuta il file mancante o aggiuntivo, manifest v1.64 alterato, source Python con sintassi errata, rollback con indice non valido, e non espone alcuna funzione `apply`/CLI di deployment. L'esito positivo è sempre `OFFLINE_BLUEPRINT_ONLY_NO_DEPLOY` / `release_authorized=false`.

**CI verificata sul codice commit `23d87039fb54dd5efa9b73c540375f9ea4a5b476`:** Watchdog [#42702707277](https://github.com/mirkoworz/remura/actions/runs/42702707277), Price [#42702707657](https://github.com/mirkoworz/remura/actions/runs/42702707657), Insights [#42702707222](https://github.com/mirkoworz/remura/actions/runs/42702707222) **tutte SUCCESS**. Incluso nello step Watchdog `Sixteen-file candidate blueprint and full-bundle rollback (offline)`. Se questo aggiornamento documentale genera nuove Actions, verificarle separatamente sul suo SHA prima di attribuirgli nuovi verdi.

**Limiti da non nascondere:** il test non misura fsync/durabilità reale dopo SIGKILL o blackout, permessi e ownership host, symlink nei path installati, lock autoupdater, servizi e riavvio systemd, rollback con database LIVE, copie SQLite coerenti e restore off-host, né quote/costi Oracle o disponibilità post trial. Il modello a 16 file copre **solo il Watchdog** su base storica v1.64: NON include automaticamente dipendenze/protezioni delle PR #89 e #98. Prima di qualunque installer reale occorre risolvere conflitti tra PR, nuova versione, diff allowlist, file Git verificati esternamente, preflight, backup/restore/rollback, quota/costi e consenso esplicito. Per il momento backup rimandato su decisione dell'operatore.

**Stato obbligatorio:** #99 OPEN/DRAFT, NO MERGE, NO DEPLOY. LIVE v1.64 soltanto documentata; Oracle, Tailscale, chiavi, filoni B/C, broker e repository privato intoccati.


## 10/11/2026 — Watchdog v1: testimone passivo di avanzamento del ciclo

**Problema reale individuato:** `thread.is_alive() == True` non distingue un collector che completa cicli da uno vivo ma bloccato per lungo tempo. La vecchia età di `last_success` non certifica un blocco (mercati chiusi, assenza di nuove candele, feed non aggiornato).

**Nuovo contratto SOLO sulla PR #99 (non LIVE):**
- `scripts/collector_watchdog.py:CycleProgress` conserva **solo in RAM** il tempo monotono di creazione e il tempo dell'ultima iterazione completata. Il loop principale lo segna **dopo** l'elaborazione già esistente e **prima** della sua normale attesa. Un ciclo completato non significa che siano stati raccolti prezzi validi; il campo `latestBatch` rimane indipendente.
- La stessa `/private-api/health` già protetta aggiunge `progressState` e `progressAgeMinutes`. Il server non aggiunge endpoint, GET esterne, thread, timer, scritture SQLite, log, chiamate broker, accessi Oracle, richieste GitHub o riavvii.
- Stati: `disabled` (raccolta spenta), `stopped` (thread terminato), `unknown` (nessuna misura affidabile), `awaiting_first_cycle`, `first_cycle_overdue`, `recent_cycle` e `no_recent_cycle`. La soglia **60 minuti** è esclusivamente indicativa, non SLA né allarme certo. Per un thread vivo che non completa iterazioni per oltre un'ora, il dato segnala un **problema da investigare**, non prova un guasto broker e non attiva autocorrezione. L'orologio è `time.monotonic()` in-process; nessuna timestamp UTC della pubblicazione provider.
- `collector_loop` conserva i suoi parametri esistenti, aggiungendo un parametro keyword-only `progress=None` opzionale. Il normale flusso di raccolta e la schedulazione restano invariati; eventuali errori dell'osservabilità non interrompono il collector. `main` crea l'oggetto solo quando `REMURA_COLLECTOR_ENABLED=1`, lo passa al thread e all'handler già esistente.
- Test unitari e HTTP localhost verificano prima iterazione non completata, thread vivo senza progressi, ciclo con zero prezzi salvati, thread terminato, raccolta disabilitata, orologio monotono anomalo e assenza di nuove chiamate broker durante la GET. `watchdog_crosspr_contract.py` esige che l'import `CycleProgress` e la sua propagazione fino all'endpoint sopravvivano alla futura riconciliazione #89/#98/#99.

**Separare segnali e prove:** liveness del thread, avanzamento dei cicli e freschezza dei dati rimangono tre misure diverse. Un thread può ancora completare cicli con risposte vuote o errori, e il nuovo testimone non certifica la qualità del feed, la continuità H1/M15, né l'uptime post trial. Se il processo termina, l'endpoint non sarà raggiungibile e servirà un controllo esterno già autorizzato; il watchdog in-process non può auto-segnalare un intero server spento.

**Requisiti per LIVE invariati:** PR OPEN/DRAFT, nessun merge/deploy, release installer v1.64 non idoneo a includere il modulo; servono un rilascio serializzato, version/date Europe/Rome visibili nelle nove pagine, rollback e backup/restore autorizzati e verifica diretta della VPS. Oracle Always Free da controllare dopo il 15 novembre, nessun provisioning, nessuna modifica alla diagnostica privata/Tailscale.


## 10/11/2026 — Gate statico anti-spreco broker / conservazione della cadenza

Dopo l'introduzione del testimone passivo dei cicli, è stato aggiunto `scripts/watchdog_cadence_guard.py` con `tests/test_watchdog_cadence_guard.py`, eseguiti nell'**unico workflow PR-only Watchdog già presente**. È un controllo offline sul parser AST: **non** importa né esegue `private_server.py`, non apre reti, non crea timer/thread, non interroga cTrader, Oracle o Tailscale e non modifica il database.

Il gate controlla che il codice candidato conservi **due soli call-site sintattici** nel ciclo `collector_loop`: primaria e fallback `source="backup"`; esattamente una attesa `stop.wait(seconds_to_next_quarter())`; selezione batch standard/priority già esistente sotto `REMURA_PRIORITY_COLLECTOR_ENABLED`; una sola creazione del thread collector in `main`; un solo `CycleProgress`; l'unico testimone `progress.mark_completed()` prima dell'attesa; **nessuna** chiamata a collector da `http_handler` e nessun timer `time.sleep` aggiunto al ciclo.

I test di regressione modificano **solo stringhe Python simulate in memoria** per tentare un terzo call-site cTrader, un secondo thread, attesa diversa, timer extra, assenza del testimone e chiamate broker da HTTP: il gate restituisce `BLOCKED_CADENCE_DRIFT`. Il codice reale della PR deve restituire soltanto `STATIC_REVIEW_REQUIRED` con `violations=[]` e `release_authorized=False`.

**Limiti importanti:** un AST statico non misura chiamate broker effettive, traffico, prezzi, quote, costi, né può escludere call-site creati dinamicamente o un cambio semantico del numero di richieste per batch. Nessuna garanzia di spendibilità gratuita di Oracle o GitHub Actions deriva dal semaforo verde. Se la logica di raccolta cambierà intenzionalmente, servirà una revisione esplicita dei gate e una misurazione futura autorizzata.

**Controllo della diagnostica VPS:** al 10/11 alle 11:40 italiane, il repository privato non riportava ancora un run diagnostico del 10/11; l'ultimo run riuscito resta il 09/11 17:47 Italia (38/38 recenti). Ritardi delle schedulazioni GitHub sono documentati; non scambiarli per guasti Oracle e non forzare workflow manuali. L'errore 403 OIDC del run manuale 09/11 è distinto in issue privata remura-collector #48. Non ripetere audit OCI già completati.

**Divieti invariati:** PR #99 OPEN/DRAFT; nessun merge, deploy, restart, SSH/Termius, chiamata API broker, nuovo cron, modifica IAM, budget o altre PR, backup rinviato per decisione del titolare.
