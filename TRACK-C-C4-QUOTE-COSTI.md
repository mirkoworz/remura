# REMURA — TRACK C4a: QUOTE, COSTI E CAPACITÀ (audit documentale, 08/11/2026)

**Decisione di sicurezza:** solo inventario statico e fonti ufficiali, nessuna interrogazione OCI/Firebase, modifica, nuovo servizio o costo autorizzato. La PR #97 resta DRAFT; i test C3c-c sono SOLO LAB. Questa pagina NON dimostra spesa zero né la continuità della raccolta.

## 1. Ambiti, evidenze e incognite

| Ambito | Limite/documentazione verificabile | Stato REMURA verificato | Da misurare senza alterare servizi |
| --- | --- | --- | --- |
| GitHub Actions | GitHub-hosted runner standard gratuiti nei repository **pubblici**. In GitHub Free, nei **privati** 2.000 minuti mensili e 500 MB di storage inclusi, soggetti a termini e piano effettivo. [Azioni / billing](https://docs.github.com/en/actions/concepts/billing-and-usage), [quote per piano](https://docs.github.com/en/billing/reference/product-usage-included). | Repo `mirkoworz/remura` **public** rilevato da metadata del repo il 08/11/2026; esistono run CI testati. Nessuna lettura dell'account Billing, dei minuti/artifacts effettivi o di altri repository privati. | Uso GitHub Actions e artifacts nel pannello Billing, eventuali budget di blocco per prodotti a consumo; retention e consumo storage. Non presumere zero per tutte le voci. |
| Oracle A1 Always Free | Il limite per tenancy **Always Free** è 1.500 OCPU-h e 9.000 GB-h/mese (≈2 OCPU / 12 GB stabili), fino a 200 GB block volume totale per boot/data, home region e shape eleggibile. [Oracle Always Free](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm). | Track infrastruttura ha riportato **Free Trial** ancora in corso, non prova operativa di 2 OCPU/12 GB già assegnati né configurazione post-trial. Non interrogato da C. Documenti Oracle su pagine diverse riportano anche tetti A1 più alti: **non usarli** come promessa per tenancy passata al solo Always Free. | Trial status, tipo tenancy, OCPU/RAM effettive, dischi boot+block allocati, home region, quote, eventuali risorse a pagamento, billing e alert. **Non** creare/upgradeare VM. |
| Firestore Standard | Un DB gratuito per progetto: fino a 1 GiB archiviato, 50.000 letture/di, 20.000 scritture/di, 20.000 cancellazioni/di, 10 GiB egress/mese. Backup/restore, PITR, TTL non inclusi. [Firebase pricing](https://firebase.google.com/docs/firestore/pricing). | Nessuna prova che il harness Track C scriva su Firestore e nessuna misura dell'utilizzo o piano Firestore. | Verificare eventuale progetto associato, piano, database, contatore richieste, storage e egress. **Non** abilitare fatturazione/backup a pagamento. |
| SQLite research | `scripts/track_c_c3b_durable_shadow.py`: limite applicativo pending 16, totale 4.500, main 1.048.576 byte, WAL 262.144 byte, busy timeout 25 ms; DB **solo directory temporanea**. | Guard e test sintetici, NON test di cap disco reale; quota filesystem non hard-limit. Per journal, schema e checkpoint misurare anche file `-shm`, `-wal` e filesystem. | DB corrente del collector, WAL+SHM per ogni DB, crescita per settimana, spazio libero, backup+temp, frequenza/checkpoint e capacità fs. |
| Worker isolato | `scripts/track_c_c3cc_isolated_worker.py` limita *solo il figlio offline Linux* a 2 s di CPU, 256 MiB di spazio virtuale, 1 MiB output file, 32 FD, genitore con timeout 0,2–5 s. | Crash, stall, saturazione, lock e core mock passati in Actions #42451905411. Nessun worker sul server, nessun utilizzo memoria/live misurato. | CPU%, RSS/PSS e swap, latenza/timeout nella VM reale, OOM killer, isolamento OS e riavvii; proteggere il collettore prima di qualunque attivazione. |
| Telemetria esistente | `scripts/resource_monitor.py` legge `/proc/meminfo`, `os.getloadavg`, `shutil.disk_usage('/')`, uptime e rete locale. `scripts/batch_timing.py` conserva 256 campioni aggregati opt-in. | Esempi e struttura nel repo; **nessun campione attuale** letto dalla VPS in C4a. Metriche OS non sostituiscono costi OCI né clock individuali dei commit per mercato. | Verificare preferibilmente report privati recenti già raccolti, senza credenziali, senza export di account/prezzi. |

## 2. Gate finanziario e operativo C4b → C5

Prima di raccogliere osservazioni reali, servono misure effettive e documentate: piano/quote residue e costi GitHub/OCI/Firestore; cap di disco e inode, RAM, CPU e swap durante i batch; backup esterno cifrato, restore-test e rollback; kill switch research; prova che un crash della ricerca non blocchi il collector in produzione; schema con clock sorgente, tentativi previsti, esclusi e UNKNOWN. Nulla in questa tabella autorizza nuovi servizi, cron o chiamate provider.

### Criteri conservativi proposti (NON configurati)

Usare avvisi all'**80%** di qualunque quota realmente applicabile e STOP research prima di superarla, preservando i collector. Il consumo stimato da dati del laboratorio non vale come costo o quote reale. Il budget email da **1 €** con alert **0,10 €** descritto nel filone infrastruttura è un avviso, non automaticamente una barriera di fatturazione. Nessuna garanzia di 0 € fino alla conferma della fatturazione e del piano effettivo.

**NO-GO invariato:** PR #97 e #89 DRAFT, `main`/LIVE non toccati da C, nessuna attivazione Track C5, nuova VM, provider polling, ordine, segnali o profitti.

## 3. C4b(a) — valutatore della capacità sulla telemetria esistente (solo LAB)

Nuovo codice `scripts/track_c_c4b_capacity_evidence.py`: accetta fino a otto campioni ridotti, già sanificati, dello schema `remura-resources-v1`. Verifica data UTC, età massima 5 minuti, ordinamento e uptime, RAM/disco/swap, proxy load1/logical, quote di coerenza; restituisce UNKNOWN su campioni assenti, vecchi o invalidi. **Non apre /proc, filesystem, HTTP, API OCI o provider** e non converte la simulazione in telemetria VPS reale.

- Limiti puramente esplorativi (NON attivati): RAM/disco >=80%, spazio libero <512 MiB, swap in uso o load1/logical >=0,8 segnalano possibile pressione. L'average load NON misura la percentuale CPU né il consumo OCPU OCI.
- Inventario opzionale solo **numerico** di core SQLite, WAL, SHM, research SQLite, WAL, SHM e backup. L'assenza di una sola misura genera UNKNOWN; anche valori numerici validi sono input NON attestato, NON prova di restore.
- 12 test con dati fittizi: episodi di saturazione, clock falsi, restart, input segreto rifiutato, single-sample bias e anti-GO. Il gate ritorna sempre `NO_GO_RESEARCH_AND_PROSPECTIVE_COLLECTION` senza alcun commit operativo. CI verificata sul commit `5d9aedbfb076c3a2bbfdd0501180aeeb9e5df3e1`: [Price Engine #42477019365](https://github.com/mirkoworz/remura/actions/runs/42477019365) **SUCCESS** e [Insights #42477019455](https://github.com/mirkoworz/remura/actions/runs/42477019455) **SUCCESS**. Solo laboratorio, non misurazione LIVE.

**Dai documenti privati già esistenti:** la telemetria batch del 3 novembre e i controlli Oracle del 7 novembre sono fotografie *storiche*, non misurazioni attuali. L'istanza E2.1.Micro (RAM 1 GB) è diversa da una futura A1; non usare 12 GB come RAM realmente disponibile. I dati di billing riportati pari a zero non provano la spesa finale, e il restore-test non è attestato da questa fase. **C4b(b) resta NO-GO** per mancanza di misurazioni correnti e autorizzazione a eventuale raccolta. Nessun nuovo GET, job schedulato, servizio o intervento VPS è stato richiesto.

## 4. C4b(b) — prova che il backup venga riaperto e ripristinato, kill gate di LAB

- Modulo dedicato: `scripts/track_c_c4bb_recovery_gate.py` (solo SQLite **sintetica** in una directory temporanea validata). L'inventario legge main/WAL/SHM e lascia file assente = NON PRESENTE, non 0 usato. Limiti TEST main 256 KiB, WAL 256 KiB, SHM 64 KiB, 32 ricevute fittizie.
- Backup via API SQLite su connessione readonly, controllo integrità del backup, successiva copia ripristinata in un secondo file e riapertura con integrità+digest+numero righe identico. Lavoro temporaneo e pulizia: nessun database LIVE o vero backup viene letto, sovrascritto, migrato o conservato.
- Spazio richiesto in test: euristica prudente `4×(main+WAL+SHM)+1MiB`. Per spazio simulato insufficiente, schema corrotto, backup manomesso, nomi occupati, symlink e percorsi remoti: UNKNOWN/rifiuto. Questo è SOLO budget fittizio locale e non una misura della VPS, costo OCI o garanzia di spazio reale.
- Kill switch simulato attivo di default. Anche disattivato durante la prova, non lancia un worker e non permette LIVE; l'esito di ogni percorso resta `NO_GO_RESEARCH_AND_PROSPECTIVE_COLLECTION`. Il futuro kill switch operativo, backup esterno cifrato, replica in un diverso host e restore/rollback LIVE necessitano architettura e consenso autonomi.
- **13 test** offline verificati sul commit `e89ff3b27b2d33bf0200ea26e983cc420d5a02ff`: [Price Engine #42478145437](https://github.com/mirkoworz/remura/actions/runs/42478145437) **SUCCESS**, [Insights #42478145434](https://github.com/mirkoworz/remura/actions/runs/42478145434) **SUCCESS**. Nessun polling, job programmato, intervento Oracle o operazione con Termius.

**Importante:** un verde GitHub significa che SQLite sintetica può essere salvata e ripristinata nell'harness CI, non che REMURA abbia un backup vero ripristinabile, l'account Always Free post-trial sia gratuito, o che il motore scientifico reale sia avviabile senza impatto.

## 5. C4b(c) — prova di COPERTURA, non di capacità

Nel nuovo `track_c_c4bc_evidence_coverage.py` un registro **solo metadata** mantiene aperti otto gate essenziali per C5: RAM/CPU/swap/disco corrente, SQLite/WAL/SHM corrente, restore cifrato fuori host, OCI piano/billing, GitHub quote, Firestore quote, isolazione di processo OS e prove FIRST-SEEN. Accetta rapporti storici o consegnati soltanto come **segnalazioni non autenticate**, non come autorizzazioni: la data/il tipo di fonte sono informazioni dichiarate, non proof of receipt. La provenienza del report non verifica che i dati all'interno siano corretti. Un registro vuoto produce otto MISSING; non produce "zero consumo".

**CI C4b(c) verificata**: commit `80825ac3fff6b021e8603a50efe79391d6cec0b7` — [Price Engine #42478844747](https://github.com/mirkoworz/remura/actions/runs/42478844747) **SUCCESS** e [Insights #42478844729](https://github.com/mirkoworz/remura/actions/runs/42478844729) **SUCCESS**. I 13 test sono **sintetici**, non autorizzano C5.

**Riconciliazione delle informazioni già disponibili senza nuovi servizi**:
- I report OCI privati del 7 novembre mostrano E2.1.Micro con 1 GB e boot 47 GB, trial probabile e analisi costi pari a 0 riportato fino al 7/11: **DOCUMENTI STORICI**, NON proof del piano post-trial né del carico del momento.
- Le prove private batch del 3 novembre verificano un singolo batch, ma **non** indicano commit per simbolo, throughput VPS di oggi o completezza delle scansioni.
- I 13 test C4b(b) del backup SQLite appartengono a una directory temporanea in GitHub: **non** verificano backup esistente e restore fuori dalla VPS.
- Non è disponibile in questo audit un inventario corrente **di tutte** le SQLite/WAL/SHM, una prova di restore off-host, limiti Firestore/GitHub realmente usati o attestazione del kill switch OS.

**Conclusione**: i report e la checklist sono utili per ridurre verifiche duplicate. Per procedere in C4b(d) servirà un controllo autorizzato strettamente read-only, preferibilmente usando dati diagnostici già ottenuti, con misure sanificate e identificatore del run originale. Nessuna nuova richiesta provider, modifica LIVE o riavvio.

## 6. C4b(d) — consultazione originale di report già acquisiti, nessun run nuovo

In GitHub PRIVATO remura-collector sono stati consultati senza rerun i log originali di due diagnostiche del 03/11/2026 ([#41649580706](https://github.com/mirkoworz/remura-collector/actions/runs/41649580706) e [#41653292319](https://github.com/mirkoworz/remura-collector/actions/runs/41653292319)). RAM e disco in entrambi i report erano sotto l'80%, ma erano osservazioni puntuali storiche e non un'attestazione delle risorse dell'08/11 o del consumo durante i picchi; le dimensioni SQLite/WAL/SHM e l'integrità di backup non erano misurate. La diagnostica riportava esplicitamente BACKUP_SQLITE non verificato. I valori numerici di VPS restano nei log privati.

Il costo OCI riportato dal run privato [#42305661998](https://github.com/mirkoworz/remura-collector/actions/runs/42305661998) era 0,0000 EUR nell'intervallo 02/10–05/11, con avvertimento ZERO_REPORTED_NOT_BILL_VERIFIED: non è una fattura né un limite di addebito. Non avviare un nuovo censimento. Il controllo piano Oracle post-trial è del filone Oracle dopo il 15/11.

Il workflow privato remura-vps-diagnostic.yml esistente ha già un preflight /private-api/resources; è schedulato ferialmente alle 06:37 UTC, ma il job privato è condizionato a REMURA_VPS_DIAG_ENABLED=1 (stato attuale sconosciuto). Non cambiare trigger, non azionarlo dal ramo C. Si tratta di GET alla VPS, non zero traffico; non contattano cTrader/Myfxbook/CFTC/OCI.

Il nuovo adapter OFFLINE scripts/track_c_c4bd_history_adapter.py accetta soltanto estratti sanitizzati delle percentuali RAM/disco e dell'esplicita mancanza di prova backup, senza aprire file né collegarsi a GitHub. I suoi test usano numeri fittizi, non i valori interni privati. Anche un estratto con clock recente viene classificato NON AUTENTICATO e non sostituisce la prova di backup, costo o headroom attuale. NO-GO per C4b(e)/C5 invariato.

**C4b(d) CI verificata:** commit 8e059c25a4aee05df320734254d3693a6a9822fa; [Price Engine #42479930569](https://github.com/mirkoworz/remura/actions/runs/42479930569) SUCCESS (15 test C4b-d inclusi), [Insights #42479930575](https://github.com/mirkoworz/remura/actions/runs/42479930575) SUCCESS. Solo codice offline, nessuna attestazione nuova da VPS.

## 7. C4b(e) — tre report schedulati reali già ottenuti, non misure correnti

Recuperati dal repository **privato** tre workflow automatici con job VPS diagnose SUCCESS: [4/11 #41851256335](https://github.com/mirkoworz/remura-collector/actions/runs/41851256335), [5/11 #42049427920](https://github.com/mirkoworz/remura-collector/actions/runs/42049427920), [6/11 #42234788299](https://github.com/mirkoworz/remura-collector/actions/runs/42234788299). I log riportavano RAM e disco ben sotto l'80% in quelle date, e il campo backup SQLite **non verificato**. Questi sono i report più recenti identificati nelle liste schedule/manual esaminate, non attestazione che non esistano altri run fuori da quelle liste né misura del 08/11. Lo storico aggregato della raccolta raggiunge 256 righe trattenute al 6/11: la finestra rolling non certifica gli eventi esclusi né otto slot univoci. I valori puntuali e i log completi restano nel repository privato.

Il nuovo confronto `scripts/track_c_c4be_historic_trend.py` non esegue GET e accetta SOLO riassunti pre-redatti consegnati dalla fonte; controlla clock UTC, duplicati, bounds, 256 come cap della finestra e consistenza aggregati. A parità di dati la conclusione resta SEMPRE `NO_GO_RESEARCH_AND_PROSPECTIVE_COLLECTION`. Test sintetici in CI, nessun numero reale inserito nel branch pubblico.

**Gate successivo C4b(f):** piano di misura **locale** dei file SQLite/WAL/SHM e prova di restore backup FUORI dalla VPS, con autorizzazione e limiti espliciti; il GET resources esistente da solo è insufficiente. Track Oracle verifica piano post-Trial in autonomia e con controllo delle quote; niente nuove chiamate mercato o servizi da Track C.

**C4b(e) test CI verificati**: commit `5d4ad1bd17289663ccd19ac7fb2cce5589d0e652`, [Price Engine #42480644071](https://github.com/mirkoworz/remura/actions/runs/42480644071) SUCCESS; [Insights #42480644044](https://github.com/mirkoworz/remura/actions/runs/42480644044) SUCCESS. Non certificano continuità, backup, costi o risorse VPS attuali.

## 8. C4b(f) — formato definitivo dell'inventario in sola lettura, SOLO CODICE

Dal codice LIVE attuale emerge un database noto `private/remura-prices.sqlite3` in WAL e un vecchio strumento di backup `deploy/oracle/backup_v156.py` che prevede snapshot con restore-test. Il comando `--backup` dello strumento di release **scrive file**: non eseguirlo come diagnostica di sola lettura. Il comando `--check` apre il database e fa integrity check, quindi è più invasivo di una misura di dimensione; non è stato eseguito.

Il nuovo `scripts/track_c_c4bf_metadata_inventory.py` è predisposto per misurare **solo metadati filesystem** dell'unico DB noto e dei suoi WAL/SHM, del filesystem e degli archivi locali nella cartella `predeploy-backups`. Distingue assenza, anomalie, limiti, file link e incompletezza. Non legge manifest, contenuto SQLite o altri documenti e non verifica checksum, restore, copia remota o durabilità. Il programma **non viene chiamato dalla LIVE, non è installato e non è una nuova Action**; le CI usano esclusivamente cartelle temporanee sintetiche. Richiede modalità specifica, autorizzazione ulteriore e path esatto per il futuro eventuale audit VPS.

Una copertura di una sola SQLite non equivale a un censimento di tutto lo storage. Per verificare il backup off-host occorrono luogo separato, hash verificato in ambiente protetto, data creazione, prova di recupero autorizzata, confini di costo e cancellazione controllata degli artefatti; nessun risultato può essere dedotto da `predeploy-backups` locale. **NO-GO C5**.

**Compatibilità release 1.64:** `release_v164.py` crea un bundle separato `rollback-v164-*` contenente copie del codice e `manifest.json`, mentre `backup_v156.py` genera `backup-v156-*` con snapshot SQLite. Il nuovo inventario distingue e somma i due gruppi separatamente, senza aprire i file; **rollback del codice non equivale a backup DB**, e nemmeno un archivio locale prova restore o copia fuori VPS. `reconcile_v164.py` include verifiche contenuto/manifest SOLO quando eseguito dalla procedura di rilascio. 19 test sintetici inclusi.

**C4b(f) CI verificata — LAB-only:** commit `1cdc90d57bed778cfc78b7cab399f5e1c375721f`; [Price Engine #42482561950](https://github.com/mirkoworz/remura/actions/runs/42482561950) **SUCCESS** (19 test inventario più suite esistenti), [Insights #42482561957](https://github.com/mirkoworz/remura/actions/runs/42482561957) **SUCCESS**. Prima CI del prototipo fallita (tipo `PosixPath`), corretta e mantenuta nella cronologia. Non è stata misurata la VPS.

## 9. C4b(g) — progetto del percorso NO-Termius, non nuova misura LIVE

Conferma statica dell'attuale `scripts/private_server.py`: `GET /private-api/resources` restituisce direttamente `resource_monitor.snapshot(counts)`, che contiene RAM/load/disco complessivo ma NON SQLite/WAL/SHM, predeploy-backups, inode o restore off-host. Il workflow privato può leggere la GET esistente, ma NON esegue comandi sulla VPS né dispone di accesso ai singoli file. Non basta rieseguire i medesimi endpoint per produrre dati assenti. Verificato che le vecchie diagnostiche consultate non hanno allegati utili. Niente numeri inventati.

**Alternativa preferita, senza Termius:** predisporre per futura release separata e approvata un campo `storageInventory` opzionale e default-OFF nella GET HTTPS privata già esistente, riusando il modulo di metadata C4b(f). Il campo deve escludere qualsiasi percorso, contenuto SQLite, manifest, credenziali o filename privato, e mantenere i vincoli di latenza/permessi. Il collaudo con rollback/backup per LIVE è un'altra decisione: non includerlo nella PR scientifica #97 per il merge.

Il contratto `scripts/track_c_c4bg_resource_transport_contract.py` e 15 test fittizi verificano il solo formato sanificato, l'età dichiarata, i bounds e l'impossibilità di promuovere una copia **locale** a restore **fuori host**. Fino a rilascio esplicito: `remoteEndpointCurrentlyImplemented=false`, tutti i gate LIVE/OCI/restore/first-seen non verificati e `NO_GO_RESEARCH_AND_PROSPECTIVE_COLLECTION`.

**Costo:** il codice e gli unit test nel branch non creano nuovi provider, servizi o fatture. Una futura GET aggiuntiva dalla diagnostica consumerebbe una chiamata HTTP della VPS e minuti GitHub Actions già applicabili; non dimostra di per sé un conto totale a 0 €.

**C4b(g) CI verificata (SOLO LAB):** commit `e834e74d680950b084bbe465b8dc4373a5b69577`; [Price Engine #42486731167](https://github.com/mirkoworz/remura/actions/runs/42486731167) **SUCCESS**, [Insights #42486731068](https://github.com/mirkoworz/remura/actions/runs/42486731068) **SUCCESS**. Il contratto non è installato sul server e non produce misure attuali.

## 10. C4b(h) — compatibility preview, non un endpoint operativo

Progettato `scripts/track_c_c4bh_resource_compat_preview.py` usando soltanto il contratto C4b(g). La simulazione conserva esattamente i nove campi `remura-resources-v1` e i loro valori se il feature flag è OFF (valore di default). Con flag LAB ON, richiede snapshot e metadati PRECALCOLATI e aggiunge solo `storageInventory` sanitizzato; non esegue `lstat/scandir/statvfs` e non ha I/O di rete o SQLite. Nessuna nuova GET, job o spesa verso la VPS.

La feature reale non può essere copiata direttamente dal prototipo: la futura integrazione deve **mai** fare scansioni nel thread che risponde alle GET e deve avere cache, timeout/limiti misurati esternamente, gestione errori, auth invariata e rollback. L'attuale `private_server.py` e `resource_monitor.py` NON importano il prototipo. L'eventuale nuova versione v1.65 con banner/versione/data su tutte le pagine, rilascio e rollback richiede decisione separata e non fa parte del Track C.

La validità di un payload non prova autenticità, stato attuale, costi, copie fuori host o recuperabilità. `NO_GO_RESEARCH_AND_PROSPECTIVE_COLLECTION` invariante. **18 test CI sintetici** associati alla PR #97.

## 11. C4b(i) — strategia off-host GRATIS-first, non backup operativo

Le quote ufficiali pubblicate OCI Object Storage indicano 20 GB combinati Always Free e 50.000 richieste/mese, con suddivisione 10 GB Standard + 10 GB Accesso non frequente + 10 GB Archive durante il trial; per la classe Standard finché il piano reale resta incerto usare **10 GB come limite prudente nel planner**, non come quota effettiva. Google Drive personale offre fino a 15 GB condivisi con Gmail/Foto. I GitHub Actions Artifacts hanno retention predefinita di 90 giorni e non sono destinazione permanente di backup. Vedi fonti nella roadmap C.

**Nota cruciale sui vecchi report:** il censimento privato OCI [#42305752464](https://github.com/mirkoworz/remura-collector/actions/runs/42305752464) indica 47 GB boot/200 GB allowance **block/boot**, non Object Storage. La Usage API [#42305661998](https://github.com/mirkoworz/remura-collector/actions/runs/42305661998) riportava 0 EUR aggregati storici ma non verificava fatture, trial o eleggibilità Always Free. Non confondere storage in GB con spazio DB locale né costo dichiarato con costo fatturato.

**Criteri di sicurezza:** cifratura autenticata con chiave di recovery che non dipenda dalla VPS, copia privata e identità cloud separata dal core, conservazione di più generazioni, test verificabile di recupero **FUORI host**, rotazione e alert. Un backup locale nella stessa `/opt/remura/private` non protegge dalla perdita del server; anche OCI Object Storage è off-VM ma nella stessa tenancy, quindi Google Drive (solo dopo controllo permessi, spazio e quote) può dare un secondo dominio di account. Per un primo gate più semplice, ci basta preparare il piano, senza accendere nuovi servizi prima della verifica dei costi.

Il codice `track_c_c4bi_offhost_recovery_plan.py` produce solo stime conservative su dimensioni dichiarate (non verificate) e ritorna sempre `NO_GO_RESEARCH_AND_PROSPECTIVE_COLLECTION`. Non genera cifratura, chiavi, archivi o upload. I suoi test sono completamente fittizi; nessuna prova di recupero reale.

**C4b(i) CI completata (NO-GO):** commit `0d442eb4a2399ee5a2ba064492c97b6ebdf5b33b` — [Price Engine #42488186932](https://github.com/mirkoworz/remura/actions/runs/42488186932) **SUCCESS**, [Insights #42488186927](https://github.com/mirkoworz/remura/actions/runs/42488186927) **SUCCESS**, 21 test sintetici. Nessun prezzo/consumo account e nessun restore esterno verificati.
