# REMURA v1.65 — ponte verso verifiche reali, senza Termius

**Checkpoint documentale: 08/11/2026 | Filone C C4b(k) → C4b(l) | Stato: NO-GO.**

Questo documento è un **inventario delle automazioni di diagnostica già esistenti** nel repository *privato* `mirkoworz/remura-collector`, verificato direttamente dai file sorgenti. **Non sono stati avviati workflow, consultate credenziali, letti log di produzione, contattata la VPS o interrogate API Oracle** durante questo checkpoint. Non è un certificato dei risultati delle automazioni.

## 1. Non duplicare: i controlli disponibili nel repository privato

| Automazione già presente | Avvio e protezioni verificate nel codice | Che cosa può attestare se eseguita | Che cosa NON può attestare |
| --- | --- | --- | --- |
| `remura-vps-diagnostic.yml` | Job `diagnose` su `main`, repository privato, `workflow_dispatch`/cron feriale, **solo se** `REMURA_VPS_DIAG_ENABLED == '1'`; Tailscale OAuth con identità effimera, test offline prima della connessione | GET HTTPS MagicDNS da endpoint privati esistenti, health, stato autoupdater e **SHA stampato nei log solo per le prime 12 cifre**, stato/tempi dei feed e percentuale RAM/disco | Hash completi dei file, SHA effettivo da filesystem indipendente, inode, fatture Oracle, sicurezza ACL verificata in modo indipendente, backup/restore |
| `remura-oracle-cost-readonly.yml` | Solo `workflow_dispatch` su `main` privato; test prima dell'SDK OCI; sola query COST aggregata; credenziali GitHub Secrets, nessuna nuova risorsa | Consumo/costo Oracle rendicontato dalla Usage API per gli **ultimi 35 giorni UTC completi**, a livello tenancy | Costi pendenti e giornata corrente, fattura definitiva, idoneità Always Free o scadenza trial; la query SDK è semanticamente read-only anche se l'API usa HTTP POST |
| `remura-oracle-storage-readonly.yml` | Solo dispatch su `main` privato; test offline prima dell'SDK OCI; inventario limitato e sanitizzato | Capacità provisioned boot/block/backup **regione home** su compartimenti accessibili; riferimento indicativo 200 GB/5 backup | Byte **liberi all'interno della VM**, inode, quota totale altre regioni, costi o idoneità Always Free |
| `remura-oracle-other-regions-readonly.yml` | Solo dispatch su `main` privato; OCI SDK read-only, massimi di paginazione | Inventario sanitario aggregato di risorse anche nelle regioni sottoscritte **non home** | Capienza filesystem della VPS, costi finali, copertura di regioni non autorizzate all'identità |
| `remura-oracle-compute-census-readonly.yml` | Solo dispatch su `main` privato; OCI Compute list operations | Censimento Compute ARM e confronti **nominali** con riferimenti Always Free | Capacità libera effettivamente disponibile nell'host, fatture, possibilità garantita di creare VM ARM |

Le cinque definizioni sono state lette dal repository privato, **senza modificarlo**. Ogni workflow è già stato predisposto come task di sola lettura sul piano infrastrutturale, ma invocarlo comporta richieste e minuti di esecuzione: **non considerare zero il costo finché non è verificato**.

Per evitare doppioni con il Filone A, riutilizzare l'ultima esecuzione reale già verificata se conserva freschezza, scope e head corretti. **Non ripetere test conclusi** senza necessità né attivare il cron se la variabile è disabilitata. Non inventare una data di ultima esecuzione: la cronologia dei run e la variabile non sono state interrogate in questa fase.

### Link diretti per futura consultazione privata

- [VPS — diagnostica privata sola lettura](https://github.com/mirkoworz/remura-collector/actions/workflows/remura-vps-diagnostic.yml)
- [Oracle — costi Usage API sola lettura](https://github.com/mirkoworz/remura-collector/actions/workflows/remura-oracle-cost-readonly.yml)
- [Oracle — storage home region sola lettura](https://github.com/mirkoworz/remura-collector/actions/workflows/remura-oracle-storage-readonly.yml)
- [Oracle — storage e Compute altre regioni](https://github.com/mirkoworz/remura-collector/actions/workflows/remura-oracle-other-regions-readonly.yml)
- [Oracle — censimento Compute ARM](https://github.com/mirkoworz/remura-collector/actions/workflows/remura-oracle-compute-census-readonly.yml)

Lanciare eventuali workflow manuali **solo dopo una decisione esplicita** e soltanto dal branch `main` del repository privato. Non inserire token o secret in screenshot, issue, PR o log.

## 2. Regole di equivalenza: cosa prova davvero ciascun dato

1. `SHA_INSTALLATO=xxxxxxxxxxxx` nei log diagnostici è un **prefisso del campo** `installedSha` restituito dall'API: non dimostra l'hash byte-per-byte del codice attualmente sul filesystem. Non sostituisce verifica indipendente di versione, autoupdater e 12 file preesistenti.
2. `VPS_DISCO_USATO_PERCENTO` è la percentuale di `disk.used / disk.total` riferita al **filesystem radice** come esposto da `resource_monitor.py`, non una verifica degli inode né dello spazio libero specifico per il database/backup. L'endpoint non fornisce `statvfs`/inode nel codice LIVE attuale.
3. Il censimento dei volumi OCI è provisioned cloud storage; **non equivale** a `df`, capacità residua per snapshot SQLite, numero di inode o libertà da costi extra.
4. `OCI_COST_AMOUNT=0` (se mai ottenuto) è riferito a una finestra di 35 giorni UTC chiusi, non alla tariffazione in tempo reale; la console Billing, idoneità Always Free, stato trial e quote devono essere valutati separatamente.
5. Il passaggio via MagicDNS Tailscale, il controllo base HTTPS e l'assenza di redirect aiutano a preservare la privacy della diagnostica ma **non certificano da soli** l'effettiva ACL, policy proxy e assenza di ingress pubblici. Richiedono una verifica dedicata.
6. GitHub Actions verdi sulla PR #98 dimostrano test **offline** del codice in branch. Le due CI reali `push/main` sul futuro **esatto SHA target** sono una prova diversa, ancora non acquisita.
7. L'esistenza di archivi e file di backup da metadati non prova integrità dei contenuti, test di restore **off-host**, rientro del collector in salute o rollback codice di produzione.
8. L'attestazione della barra versione v1.65 e timestamp Italia su nove pagine, SW/PWA e health **può avvenire solo dopo un rilascio separatamente approvato**, non nel preflight della LIVE v1.64.

## 3. Prossima sequenza operativa, senza SSH e senza scorciatoie

**A — Revisione fonti (nessuna mutazione).** Controllare le più recenti prove già esistenti dei Filoni A e C; annotare **solo** classificazione, data UTC e scope, non dati personali. Da GitHub confrontare branch `main`, PR #89/#97/#98 e SHA del codice. Questo checkpoint ha verificato `main = 5ec7d73247b7ec074ce3640d7cafecaa7b3f1c74`; non è l'identità del codice installato sulla VPS.

**B — Eventuale nuova lettura reale (autorizzazione separata).** Solo se le prove pregresse sono incomplete o scadute, decidere **quale workflow privato già presente** avviare manualmente. Per un controllo della VPS usare il job GET privato solo se già abilitato e con Tailscale funzionante; non accendere la variabile `REMURA_VPS_DIAG_ENABLED` per forzare l'esecuzione. Per i costi usare `remura-oracle-cost-readonly.yml`, per i volumi `remura-oracle-storage-readonly.yml`, eventualmente regioni non-home. Niente nuovi workflow, bucket, volumi o trial upgrade. Prima confrontare le quote GitHub Actions e stato di fatturazione reali.

**C — Colmare i buchi effettivi (solo design per ora).** Gli strumenti attuali non forniscono: checksum completo del codice installato, inode liberi, prova independente ACL/ingress, snapshot SQLite coerente con restore isolato e recupero off-host. Predisporre un futuro probe **sola lettura autorizzato e limitato** per i primi due elementi, con privacy e nofollow/FD pinned; backup/restore restano **azioni scriventi** sotto un'altra autorizzazione. Non aggiungere endpoint LIVE tramite questa PR.

**D — GO/NO-GO.** La v1.65 non può essere installata finché mancano SHA LIVE attendibile, ACL, fatturazione e quote, spazio + inode + headroom, backup/restore verificato, rollback, doppia CI push/main del target, continuità raccolta e consenso dedicato. Il Track C/C5 prospettico resta separatamente bloccato. La diagnostica storage proposta per v1.65 resta OFF.

## 4. Privacy, costi, promozione versione

- Tutti gli output operativi veri rimangono nel repository **privato**; mai copiarvi dentro PII, PEM, API key, OCID completi, database o prezzi grezzi. Nella PR pubblica si salva **solo l'inventario dei percorsi di verifica** e stati generici.
- Non avviare la diagnostica, non fare dispatch, non modificare job scheduler, non utilizzare Termius, non cambiare Tailscale/OCI/collector, non aggiornare `main` dal Filone C.
- Non modificare il banner v1.64 corrente; la regola “numero aggiornamento + data/ora reale in alto su tutte le pagine” sarà applicata solo al futuro rilascio v1.65 autorizzato.
- Nessun fornitore a pagamento richiesto. Gratuità **non attestata** dai workflow/simulazioni; serve verifica quote/costi da account vero.

**Decisione finale del documento: `NO_GO_RELEASE_AND_PROSPECTIVE_COLLECTION`.**
