# REMURA Experience v0.23 LAB — checkpoint e gate v0.24 — 20/11/2026 23:08 CET

## Provenienza e branch
- Base Experience v0.22: research/contributors-experience-20261120 @ 3971c0af7b6a802a9d3566c4345e804d1ffdefbe.
- Collaudi Mac separati: codex/mac-experience-checkpoint-20261120 @ 57b8612dc30015046f36936e7a9fbf8298f41c88, tre commit SOLO documentali. Chrome, WKWebView e Safari Mac già validati; Safari su iPhone fisico no.
- Nuovo branch isolato: research/experience-abandonment-v023-20261120. Nessun merge.
- Codice v0.23: commit 4be9180e27bfd772549f8a4cb0c463292443280e, blob 1b952955e9bc967bf774ffd5e1cb7b456b68bf4a.
- Test v0.23: commit e89622a95715a4b8436cae0b3fa51593d377d1c8, blob 5f119c85843563aad87f7097e2f4c254e66d17f8.
- Entrambi i blob remoti confrontati con git hash-object sui file locali effettivamente eseguiti: MATCH.
- Asset toro/orso, nove frame, ringraziamento SMF, HTML cinematografico v0.22 e Home v0.22 INVARIATI.

## V0.23 implementato: annullamento isolato
File: abandonment_v023_lab.py e test_abandonment_v023_lab.py.

Tre archivi SQLite sintetici distinti per percorso locale: (1) candidati, (2) journal, (3) intenti e disposizioni in autorità simulata. L'intento vincola generazione v0.23, sequenza, digest del candidato, scadenza e tag precedente dell'autorità. L'autorizzazione sintetica del proprietario vincola esplicitamente intento, digest, azione, ragione, proprietario e timestamp. Le disposizioni sono PUBLISHED o ABANDONED; il secondo stato richiede EXPIRED_PENDING e timestamp oltre scadenza. Approvazione esplicita, mai automatica in base al timer.

I record sono append-only a livello di trigger SQLite, con HMAC e verifica di catena in fase di lettura. In caso di sola scrittura nell'archivio, l'annullamento autorizzato completa la voce journal; se il journal esiste, ne verifica e conserva il tag. Un'interruzione lascia intatta l'evidenza. L'ultima testa ABANDONED o PENDING non fornisce payload al lettore, nemmeno retrocedendo l'orologio. Dopo un annullamento validato, una nuova candidatura sintetica può occupare SOLO la sequenza successiva; quella abbandonata rimane verificabile.

La verifica dell'autorità usa un CAS locale sul suo head. Il parametro opzionale external_pin permette a un testimone fornito dall'esterno di rifiutare una testa più vecchia. Il prototipo NON crea o custodisce autonomamente un pin esterno.

## Verifiche realmente eseguite
Ambiente: Python 3.13.5, Linux container locale, soli moduli standard sqlite3, hashlib, hmac, unittest; database in directory temporanee, nessuna rete, Secret o runner GitHub Actions.

Comando: cd research/contributors && python3 -W error::ResourceWarning -m unittest -v test_abandonment_v023_lab.py

21/21 TEST PASS: archivio-only scaduto, journal-ahead, confine della scadenza, autorizzazione esplicita, digest errato, owner errato, intento mancante o errato, generazione errata, interruzione, doppia ricevuta, blocco pubblicazione scaduta, revoca al punto CAS, immutabilità SQL, manomissione journal, rollback archivio+journal, rollback sola autorità, rollback triplo con/senza pin, sequenza successiva, duplicati e scadenza vista sintetica. Non sono prove di crash fisici, concorrenza distribuita, isolamento fra host o non-compromissione delle chiavi.

I precedenti 366 controlli Experience v0.7–v0.22, 40 verifiche Safari Mac e altri collaudi storici NON sono stati ripetuti né conteggiati come nuovi. Nessuna PR, deploy o CI hosted attivata nel nuovo branch.

## Limiti NO-GO operativo
1. Le quattro chiavi HMAC nel sorgente sono deliberatamente PUBBLICHE e SINTETICHE; non sono autenticazione reale. L'owner fittizio non rappresenta identità accertata.
2. I database sono nel medesimo host/dominio di ripristino. Un ripristino simultaneo integrale appare coerente se manca un'ancora più recente conservata fuori dal ripristino. Questa limitazione è stata riprodotta nei test.
3. CAS e revoca sono simulazioni locali. Mancano protocollo firmato indipendente, garanzie transazionali fra domini, serializzazione multi-processo, fsync/crash fisico e gestione sign-in/revoca reali.
4. I trigger di non modifica possono essere rimossi da un amministratore. Gli HMAC hanno significato solo con segreti non compromessi, qui fittizi.
5. Lo schema REMURA_V023_SYNTHETIC_ONLY NON è V2 e non deve essere consegnato a consumer_v021.mjs o alla Home. I vecchi binari non sono attestati fail-closed su una migrazione futura.
6. Nessuna migrazione a Contributors v0.56, COT reale o prova di vantaggio nel trading.

## V0.24 — nuovi gate da implementare e collaudare
- [ ] Fixture separata di envelope disposizione verificato lato servizio: generazione, catena, digest, scadenza, ruolo e identificativo intenzione; mai inferito dal client.
- [ ] Per ABANDONED e PENDING risposta non numerica e no-store; eliminazione immediata delle informazioni prima visibili dopo refresh, risposta tardiva, logout e clock regress.
- [ ] Test negativi per legacy V1/V2 sulla nuova generazione prima di modificare consumer_v021.mjs o Home v0.22.
- [ ] Controlli multi-processo, interruzioni fisiche e recupero su nuova fixture; STOP a qualunque falsa attestazione di CAS distribuito.
- [ ] Progetto indipendente di ultima ancora monotona e recupero dopo perdita dell'autorità stessa.
- [ ] Safari iPhone fisico non ancora eseguito; nessuna ripetizione Safari Mac. Tutte le pagine eventualmente aggiornate dovranno mostrare versione/data/ora italiane in alto.

## Coordinamento generale — sola lettura 20/11/2026
| Filone | HEAD verificato | Stato / gate |
| --- | --- | --- |
| Contributors v0.56 LAB | 21338d4a405b0a3053e5a51322f8643c428ac757 | LOCAL_MATCH_ONLY acquisito; deploy/binding non autorizzati |
| TradingView v0.8.181 LAB | bf24eab0e9f833b6a8b7b3b6d04d28a2927829c5 | Holdout 1 dal 23 al 29/11 UTC; soglie congelate |
| Shark Science v0.4 LAB | 05e731b26bccb167ba7e0859797de01136a5c933 | Edge e profitti non dimostrati |
| Ampere Radar v0.36 | 3cdd6b8ba6cd7601db29e3b8d6a092f96ce72e0a | Monitoraggio invariato |
| Collector main | a34a1767ed25eab57675b8be8de263c67f0cbc7c | Collector Oracle invariato; v1.65 NO-GO |
| Private Capture v0.15 LAB | 6808c6b9c1b1142333681247af1a115766823f92 | VM Debian locale PASS acquisito; STOP hosted |
| Mac custody | 7a23f61b2cb1e520bff623348366231ee093bb3f | Witness 001–005/APFS acquisiti; indipendenza definitiva aperta |
| Remura main | 907e6ca6fb32ce1f37ab7a7031e081c0fd17b376 | Invariato |

## Costi, risorse, autorizzazioni
Nessun nuovo servizio cloud, database D1, richiesta a provider di mercato, risorsa Oracle o spesa. Test locali offline: zero consumi di quota GitHub Actions per questi test. Quota Workers/D1/Actions non rimisurata: valori precedenti da considerare storici. Nessun merge, deploy, acquisizione reale, collegamento utenti, Secret, installazione v1.65, invio Telegram o modifica collector.

Checkpoint append-only LAB, NON rilascio. Prossima decisione: revisione v0.24 e autorità realmente esterna prima dell'eventuale integrazione Home.
