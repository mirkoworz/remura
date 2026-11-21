# REMURA Experience v0.27 LAB — checkpoint, minacce e roadmap
**Versione v0.27 LAB · 21/11/2026, 07:59 CET (Europa/Roma)**

## Provenienza e separazione dei branch
- Base esatta v0.26: research/experience-anchor-proof-v026-20261121 @ 4273befcd85a0becb0dd1ec9dac1449ff23cbbe8.
- Nuovo branch: research/experience-custody-recovery-v027-20261121.
- Modulo: research/contributors/custody_recovery_v027_lab.mjs; commit 3831d6c620a1053372c589239bc3482d99ea3d1c; Git blob 7d883094788ac840febd2fa9be2be2d1eecdcbba.
- Test: research/contributors/test_custody_recovery_v027_lab.mjs; commit 81ae291181783459092f2acdfc457e0ce2e971d2; Git blob 151146b661b4dbd64494a060a7b8eac2575aba04.
- Dipendenza immutata da v0.26: anchor_proof_v026_lab.mjs; Git blob 5b705d74352c789bf8ac437923fc754ffe749c92.
- SHA dei due nuovi file letti da GitHub coincidenti con git hash-object dei file locali effettivamente testati.
- Home v0.22, HTML cinematografico, 9 frame toro/orso, logo SMF e ringraziamento non modificati. Nessuna nuova pagina HTML: le intestazioni versione/data/ora delle pagine esistenti restano quelle già collaudate.
- Branch Mac Experience, Mac Custody, Contributors, TradingView e Shark Science non modificati. Main ha avanzato separatamente rispetto al checkpoint precedente e NON è stato toccato.

## Nuovo risultato tecnico: gate di recupero solo lettura
Il codice verifica una catena v0.26 firmata Ed25519 da OWNER e CUSTODIAN più due attestazioni v0.27 di custodia, firmate da chiavi Ed25519 diverse etichettate alpha e beta.

Sono richiesti tutti i seguenti ingressi dal chiamante: quattro chiavi pubbliche pre-fissate fuori banda, entrambe le attestazioni firmate, la cronologia completa, un riferimento minimo esterno di generazione/digest (trustedFloor) e un orologio affidabile. Il codice verifica formato stretto, sequenza, hash, firme, identità del custode, concordanza esatta delle due teste, conformità alla floor e ordine cronologico degli eventi, senza accettare intent duplicati.

Le ricevute oltre 24 ore sono respinte come policy **illustrativa LAB**. Un timestamp firmato non prova da solo che l'informazione sia la più recente.

Anche con prove coerenti, il risultato è REVIEWABLE_LAB_ONLY, manualApprovalRequired=true, marketDeliveryPermitted=false. Non esistono comandi di scrittura, avanzamento dell'ancora, pubblicazione, recupero automatico o trasporto HTTP. L'output BLOCKED è privo dei digest e di dati di mercato. Un'intenzione ABANDONED non è reinterpretata come mercato approvato.

## Collaudi nuovi realmente eseguiti
- Ambiente: container locale Linux, Node.js v22.16.0, node:crypto Ed25519, node:test, filesystem temporaneo.
- Comando: node --test research/contributors/test_custody_recovery_v027_lab.mjs
- Risultato finale: **40/40 PASS, zero FAIL** (ripetuto sulla stessa copia finale del codice dopo confronto con le impronte GitHub).
- Copertura: firme corrette, custode A/B assente, chiavi diverse e chiavi riutilizzate, falsificazione, conflitto fra teste firmate, timestamp futuri, vecchi o non validi, scadenza dimostrativa, errore di floor, rollback parziale e congiunto, generazione errata, manomissione della catena, evento ABANDONED, intent ID duplicato, cronologia inversa, controllo del tempo delle attestazioni e diniego non numerico.
- È stato riprodotto un limite fondamentale: con entrambe le attestazioni vecchie ancora valide e una floor altrettanto vecchia, il codice non può sapere se esista un record successivo. In tal caso produce esclusivamente REVIEWABLE_LAB_ONLY, senza permessi di pubblicazione.
- Durante la messa a punto di questa nuova suite si sono corretti un isolamento errato degli oggetti test (chiavi simulate condivise) e il caso limite della scadenza rispetto al timestamp dell'evento. Nessuno dei fallimenti intermedi è conteggiato come PASS.
- NON ripetuti: 366 verifiche Experience storiche; 40 Safari Mac; 33 casi v0.26; Witness 001–005; APFS; fixture D1; PRIVATE CAPTURE Debian.

## Limiti / gate ancora NO-GO
1. Tutto il LAB viene eseguito sullo stesso host. Quattro chiavi effimere diverse non dimostrano custodi o domini amministrativi/di ripristino indipendenti.
2. La funzione trustedFloor viene fornita dal chiamante; il codice non ne attesta origine, autenticità, disponibilità dopo guasti o conservazione monotona. Se tutte le ancore indipendenti vengono ripristinate o compromesse assieme, anche firme valide possono essere rigiocate.
3. Il vincolo di 24h è un limite di età dichiarata, non una garanzia di freschezza contro chi controlla i firmatari o può rigiocare attestazioni recenti.
4. Nessuna infrastruttura quorum reale, firma a hardware separato, log append-only non riscrivibile, protezione della root di fiducia, gestione della perdita/rotazione chiavi, CAS multi-host, spegnimento fisico o test della custodia iPhone/Oracle.
5. Nessuna integrazione col gateway v0.24, consumer V2, Home, Contributors, Cloudflare o collector. Queste funzioni restano solo prove sintetiche.
6. Nessuna evidenza nuova su COT reale, identificazione degli istituzionali, capacità predittiva o redditività.

## Roadmap operativa v0.28 (non implementata)
- Descrivere e verificare i domini di controllo realmente differenti (chi può riscrivere/disporre dei backup del Mac, iPhone, Oracle, GitHub, Cloudflare). Distinguere **disponibilità della copia** dalla **freschezza monotona**.
- Prima opzione da valutare: attestazione periodica manuale, firmata, su un supporto offline sotto controllo del proprietario, con seconda custodia fisica/amministrativa indipendente. Gratis come servizi cloud, ma NON H24 automatica e non garantita contro furto/perdita simultanea; richiede dimostrazioni reali e autorizzazioni dedicate.
- Preparare simulazione di perdita del testimone A o B: FAIL-CLOSED, nessun reset di generazione, nessuna accettazione di fallback o promozione automatica. La nuova suite verifica già la mancanza di A/B, non la perdita fisica.
- Verificare la root di fiducia e la rotazione dei firmatari con revisione esplicita, separando credenziali di test da quelle operative. Non generare o trasferire chiavi reali senza autorizzazione.
- Solo dopo un gate indipendente: test di integrazione negativa V2/Contributors e preproduzione, sempre in fixture locale.

## Coordinamento dei filoni
- Contributors v0.56: branch research/contributors-offline-20261114 @ 21338d4a405b0a3053e5a51322f8643c428ac757, LOCAL_MATCH_ONLY Mac acquisito. OWNER pieno controllo; CONTRIBUTOR solo vista approvata e propri livelli, con ACL server-side da implementare prima di accessi reali. Nessun binding, deploy, utente o migrazione autorizzati.
- TradingView v0.8.181: research/tradingview-delta-peaks-20261111 @ bf24eab0e9f833b6a8b7b3b6d04d28a2927829c5. Sviluppo 16–22/11/2026 UTC; holdout 1 23–29/11, holdout 2 30/11–06/12. Soglie, criteri e definizioni congelate; non dichiarare raccolti 6048 pacchetti senza verifica dei run.
- Shark Science v0.4: ricerca causale/prospettica, baseline e falsi segnali. Nessuna redditività dimostrata. COT settimanali e proxy Delta/CVD non identificano gli operatori istituzionali.
- Mac Experience @ 57b8612dc30015046f36936e7a9fbf8298f41c88 e Mac Custody @ 7a23f61b2cb1e520bff623348366231ee093bb3f: checkpoint preservati; Safari iPhone fisico resta non collaudato.
- Private Capture v0.15: STOP hosted, VM Debian locale PASS storico. Oracle collector operativo, autoupdater sospeso/inibito, v1.65 NO-GO. Ampere Radar operativo secondo ultimo checkpoint, nessuna modifica.
- Telegram Contributors: solo futuro design per livelli approvati; nessun invio effettuato.

## Costi e autorizzazioni
Nessun nuovo servizio cloud, costo, DB D1, run GitHub Actions, flusso di mercato, Secret reale, deploy, merge, modifica Oracle o installazione v1.65. Nuovi test locali con moduli standard di Node: consumo diretto di quota GitHub Actions pari a zero per questi test. Le quote Cloudflare e Actions effettive **non** sono state rimisurate; non inferire saldo attuale da valori storici.

**Esito: v0.27 LAB completato come gate di sola revisione; custodia indipendente reale e produzione restano NO-GO.**
