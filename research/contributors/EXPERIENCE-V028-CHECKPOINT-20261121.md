# REMURA Experience v0.28 LAB — checkpoint operativo e gate v0.29
**21 novembre 2026, ore 08:18 CET (Europe/Rome). Solo laboratorio, nessun deploy.**

## Provenienza ed integrità
- Base esatta: Experience v0.27 su research/experience-custody-recovery-v027-20261121 @ d9c57782fd4f0d2f0b8edd59275b1ceaf384c4f8.
- Nuovo branch: research/experience-offline-custody-audit-v028-20261121.
- Nuovi file:
  - offline_source_audit_v028_lab.mjs — blob 598e1191772bda01deac1fc36a7741a601eb60dc, commit 663692473598e790442dc4d55ffc06b814aa185c.
  - test_offline_source_audit_v028_lab.mjs — blob 4eb4326dc3d5d6a63eb855c08770099e695abdf0, commit 9be5745977ae77044881b8b04ef2ad8287399e63.
  - offline_audit_cli_v028_lab.mjs — blob 4cc92a880cec47133e6313eb2ade3392211a8655, commit dabe6e072b536832b19176a2c065ac5e3075d913.
  - test_offline_audit_cli_v028_lab.mjs — blob e58af2470e2f592ed8257a501d1504fad656b414, commit 83f60d424440852038ac00b03be7ead72a424366.
- Tutti e quattro i blob GitHub sono identici alle impronte git hash-object degli stessi file collaudati localmente.
- Dipendenze precedenti immutate: anchor_proof_v026_lab.mjs e custody_recovery_v027_lab.mjs. Non riscritti i registri precedenti, i test acquisiti e gli asset grafici.

## Risultato implementato
Modulo Node.js *read-only* che verifica cinque artefatti sintetici su cinque percorsi: cronologia firmata, attestazione alpha, attestazione beta, attestazione floor, keyring di sole chiavi pubbliche. Il chiamante è tenuto a fornire separatamente la floor minima e l'impronta SHA256 attesa del file keyring, originate da una fonte controllata fuori banda.

Difese nuove: limiti dimensionali per ruolo, rifiuto di file non regolari e symlink di file finale con O_NOFOLLOW, verifica UTF-8 reversibile, JSON canonico con newline singolo (respinge campi duplicati), schema e forma esatti, confronto del fingerprint keyring, rifiuto dei cinque artefatti collocati nella medesima directory risolta, due firme/attestazioni e floor con validazione v0.27. Non crea file, non riscrive alcuna ricevuta, non avanza la floor e non consegna dati di mercato.

CLI offline: restituisce soltanto JSON con status BLOCKED oppure REVIEWABLE_LAB_ONLY, sempre manualApprovalRequired=true e marketDeliveryPermitted=false. Exit code 0 significa **soltanto revisionabile**, exit code 3 significa bloccato. NON equivale a consenso, idoneità operativa, pubblicazione, ordine di trading o prova di un'ancora esterna aggiornata.

## Prove effettivamente eseguite
- 21/11/2026, container Linux locale, Node.js v22.16.0, moduli built-in Node e coppie Ed25519 effimere di prova, tutte generate localmente.
- Comando: cd research/contributors && node --test test_offline_source_audit_v028_lab.mjs test_offline_audit_cli_v028_lab.mjs
- Nuovi risultati **37/37 PASS**, 0 failed: 32 casi del verificatore files + 5 casi del comando.
- Casi comprendono prova sintetica valida, gen2, ABANDONED, floor assente/diversa, chiavi/fingerprint alterati, assenza alpha/beta, firma errata, due ricevute vecchie, JSON con chiave duplicata, UTF-8 scorretto, extra fields, symlink del file e alias delle directory, file oltre limite, cronologia incompleta, clock regressivo/invalid, sola lettura, mancata esposizione in stdout.
- NESSUNO dei precedenti 366 collaudi Experience, 40 verifiche Safari Mac, 28/33/40 test v0.25–v0.27 o Witness/Private Capture precedenti è stato ripetuto.

## Limiti NO-GO che non devono essere sopravvalutati
1. Cinque directory nello stesso host **non** sono cinque domini amministrativi o di backup indipendenti. Il codice può individuare alcune anomalie locali, non garantire custodia separata da Mac/Oracle/Cloudflare.
2. La floor minima e l'impronta delle chiavi possono essere fornite entrambe stale o falsificate se il chiamante non le verifica esternamente. L'audit non può dimostrare da solo che il pin sia più recente, e accetta un vecchio insieme firmato coerente come REVIEWABLE_LAB_ONLY (senza autorizzazione di mercato).
3. Non è provata resistenza a mutazioni concorrenti, symlink di directory superiori, un amministratore locale ostile, TOCTOU, compromissione chiavi o guasti fisici. L'open e il secondo stat sono solo controlli locali.
4. La CLI accetta la floor via argomenti; l'origine manuale su un altro dispositivo, l'indipendenza dei custodi e il confronto umano non vengono attestati dal software.
5. Nessun login, autorizzazione reale, rete, cloud, server, fingerprint derivato da chiave operativa, CAS distribuito o integrazione Home/Contributors.
6. L'ora dell'orologio locale è un ingresso potenzialmente non attendibile. Policy di età v0.27 non è prova anti-replay contro entità che controllano le ricevute.

## Runbook futuro a costo di servizi zero (SOLO proposta)
1. Custodia offline del riferimento all'ultima generazione e del fingerprint delle chiavi, con duplicazione fisica/amministrativa verificata e registro a prova di modifiche. La coppia Mac+iPhone è una soluzione da collaudare, NON già promossa ad autorità indipendente.
2. Disponibilità di cinque JSON canonici prodotti da un'applicazione *attestata*, non dalla cartella di test. No private key nel repo o in un comando in chat.
3. Sul Mac, in una copia locale autorizzata del progetto, il formato del comando è:
   node research/contributors/offline_audit_cli_v028_lab.mjs <file-catena> <file-alpha> <file-beta> <file-floor> <file-keyring> <impronta-keyring-sha256> <sequenza-floor-verificata> <digest-floor-verificato> <generazione>
   Segnaposto: non eseguirlo su dati reali ora. Nodo e file devono essere offline e approvati; output reviewable non permette alcuna pubblicazione.
4. Se mancano le prove o non concordano, non ripristinare automaticamente, non resettare generazioni, non mostrare numeri e non effettuare merge/deploy.

## Prossima roadmap
- Experience v0.29: protocollo *sperimentale* di consegna/ricezione manuale dei pin fra due custodie verificate con input separati; design di disaster rehearsal senza impiego di real keys.
- Contributors v0.57: audit di gap ACL in documento dedicato; priorità a correzione append-only dei propri livelli (non UPDATE in-place), limitazione server-side e preview personale, senza modificare v0.56 o attivare servizi.
- TradingView v0.8.181: holdout1 23–29/11/2026 UTC, replica 30/11–06/12 UTC; protocollo e soglie congelati, risultati non ancora osservati.
- Shark Science v0.4: distinzione fra proxy Delta/CVD e partecipazione istituzionale, baseline e falsi segnali; nessun edge dimostrato.
- Mac/Oracle: custody Witness 001–005, Safari Mac, APFS e Debian Private Capture preservati. Safari fisico iPhone da eseguire. Collector invariato; v1.65 NO-GO; Ampere Radar non modificato.
- Telegram: nessun invio, solo progetto di formattazione per livelli approvati.

## Costi/autorizzazioni
Nessun nuovo servizio o database Cloudflare, spesa, Secret reale, operazione Oracle, installazione, acquisizione live, merge, deploy o nuova CI hosted deliberatamente avviata. Questi 37 test hanno usato solo Node locale e file temporanei; quote Cloudflare/GitHub attuali **non misurate** e da verificare prima di un'eventuale attivazione.

**Checkpoint: Experience v0.28 LAB — verificatore offline completo e riproducibile, custodia realmente indipendente ancora non realizzata.**
