# REMURA — checkpoint v0.59 Contributors LAB + v0.30 Experience DESIGN
**21/11/2026, 08:35 CET — ora italiana.**

## Continuità
- Base verificata: research/experience-handoff-contributors-amend-v029-20261121 @ 46c2d5e34a198513e8a23e768950094077c70c80.
- Branch esclusivo LAB: research/contributors-d1-amendment-v059-20261121. Nessun merge, PR, modifica a main o al ramo ufficiale Contributors v0.56.
- Schema D1 candidato originale preso in sola lettura da research/contributors-offline-20261114 @ 21338d4a405b0a3053e5a51322f8643c428ac757: research/contributors/d1_access_candidate.sql, blob 9ed38b6ed83755186af05f1bf28b4608cdc5f901.
- Nessun HTML/asset aggiornato: splash toro/orso, 9 frame, logo SMF, Home v0.22 e data/ora di intestazione sulle pagine rimangono intatti.
- TradingView research/tradingview-delta-peaks-20261111 @ bf24eab0e9f833b6a8b7b3b6d04d28a2927829c5 non modificato.

## Nuovi file v0.59 — blob verificati contro esecuzione locale
1. research/contributors/d1_amendment_v059_lab.sql — SHA Git blob 289cb54f0b3e33976b255ce976ca5e00bc43ab3c. Overlay SQL *additivo*, senza ALTER/DROP delle tabelle precedenti. Due nuovi registri per correzioni e decisioni, con trigger di immutabilità e controllo di ruolo, source, mapping, revoca, flag write/recovery, transizioni APPROVED/REJECTED/REVOKED e unica correzione APPROVED ancora attiva. Limite LAB di 100 correzioni totali e 10 per autore/giorno.
2. research/contributors/test_d1_amendment_v059_lab.py — SHA f9ff2c3d0dc1aea8ad2f6a3803aead3a18449e5d. Quaranta controlli offline su inserimento, autore originale, periodi, guard, dati non validi, revoca, univocità, owner, immutabilità, approvazione, validità FK, capacità.
3. research/contributors/d1_amendment_queries_v059_lab.mjs — SHA 3d25cb33e38a4820bb19412606bb4908523f96ce. SQL preparato separato per submit, ricevute personali, coda dell'OWNER, review e proiezione dei soli livelli approvati. Le query devono essere invocate esclusivamente da un adapter con soggetto + email_tag ricavati da Cloudflare Access verificato; nessuna query SQL può essere fornita direttamente dal browser.
4. research/contributors/test_d1_amendment_queries_v059_lab.py — SHA f9d95916f9d0523acd3be8bb132af94f625bd0f7. Venticinque controlli su isolamento soggetti, editor non proprietario, review OWNER, proiezione approvata, pending/rejected non visibili, revoche, catalogo disattivo, controllo lettura e minimizzazione dei campi (nessuna nota o subject nella proiezione).
5. research/contributors/EXPERIENCE-V030-CUSTODY-REAL-GATES-20261121.md — solo design del gate reale, non rilascio v0.30 né prova fisica Mac/iPhone.

## Test e verifiche NUOVI effettivamente eseguiti
- Container Linux locale, Python 3.13.5, sqlite3 standard, test offline. Comando:
  cd research/contributors && python -W error::ResourceWarning -m unittest -q test_d1_amendment_v059_lab.py test_d1_amendment_queries_v059_lab.py
- **65/65 PASS, zero errori**. Tempi circa 0.13 s.
- ATTENZIONE: il test è stato eseguito su una **surrogata ridotta** del vecchio schema con le stesse tabelle/colonne essenziali. Dentro il repository, i due test sono predisposti a caricare e verificare automaticamente il file ORIGINALE d1_access_candidate.sql presente accanto ai test; questa seconda esecuzione completa non è stata eseguita in questo ambiente e rimane un gate richiesto.
- Controllo separato in sola lettura sullo schema originale GitHub: tutti i nomi di tabella e campi necessari esistono; nessun ALTER/DROP dei registri preesistenti nell'overlay. Risultato STRUCTURAL_MATCH_ONLY, non prova transazionale completa.
- Impronte GitHub dei quattro file codice/test confrontate con git hash-object dei file locali utilizzati, tutte MATCH.
- Non ripetuti test v0.58 (33), v0.29 (25), v0.28 (37), v0.27 (40), v0.26 (33), vecchi 366 Experience, Mac Safari 40, witness 001–005, APFS, SQL Oracle, D1 fixture precedenti o PRIVATE CAPTURE.

## Condizioni operative non ancora superate (NO-GO)
- Le query SQL possono verificare ruoli e subject nella fixture, ma NON sono login, sessioni, IAM, reverse proxy, rate limit o HTTP deploy. Un amministratore D1 con privilegi SQL non è limitato dalle query del frontend. Il controllo reale richiede Worker con Cloudflare Access e boundary integrati.
- Non esiste l'endpoint di correzione; serve adapter a transazione e identità accertata, gestione di idempotency key e retry incerti. Lo schema limita request_id a 36 caratteri: il controllo UUID completo resta compito del validator applicativo prima del commit.
- SQL controlla il formato semplice di UTC/prezzo ma NON sostituisce il validator rigoroso d1_lab_adapter.mjs. Nessuna garanzia del clock fisico/attestato.
- La vista approvata non è feed COT o presenza istituzionale: è un **elenco sintetico di livelli manuali approvati**. Nessun edge o profitto dimostrato.
- Correzioni solo su un originale APPROVED: i draft precedenti alla prima approvazione restano immutabili; una policy di ritiro e riemissione richiederà specifica separata.
- Mancano integrazione reale contro schema candidato completo, transazioni parallele multi-connessione, D1 Cloudflare fixture, compatibilità frontend iPhone e misurazione quote Free.
- Nessun SQL eseguito sui database remura-contributors-lab o remura-contributors-fixture, nessun nuovo DB o binding.

## Experience v0.30
- Salvato solo il piano per dimostrare custodia indipendente di pin e firmatari su domini Mac/iPhone/ulteriore supporto offline, con esercitazione sintetica di rollback e perdita.
- Mac+iPhone con medesimo controllo dei backup NON sono automaticamente due autorità indipendenti. Verifica fisica e amministrativa ancora non svolta. Nessuna chiave privata reale creata o inviata.
- Il ramo v0.29 resta il checkpoint crittografico; v0.30 è **DESIGN**, non implementazione o release.

## Roadmap prioritizzata
1. Contributors v0.60 LAB: eseguire i 65 test **sullo schema originale completo**, aggiungere case concurrency/cross-process, poi adapter isolato che usi Access ctx affidabile. Se fallisce, correggere solo branch LAB e documentare la regressione.
2. Contributors Experience: sviluppare form di correzione e ricevute personali dopo certezza dei gate server; OWNER revisione separata. Accesso reale amici solo dopo permesso specifico, collaudi di sessione/ACL e verifica budget.
3. Experience v0.30: prima custodire su due domini realmente indipendenti un pin aggiornato e verificare tramite prova ripristino, poi riparlare di integrazione con Home. Safari iPhone fisico resta non verificato.
4. TradingView v0.8.181: holdout 1 dal **23/11/2026 al 29/11/2026 UTC**, holdout 2 **30/11–06/12 UTC**, criteri/preregistrazione invariati. Non pubblicare risultati prima dei dati effettivamente ricevuti.
5. Shark Science v0.4: baseline price-only, Delta/CVD proxy, disponibilità ex-ante, falso segnale, confronto a costi ipotetici; non dichiarare i trader istituzionali identificati.
6. Mac custody, Oracle collector, Private Capture v0.15, Ampere Radar: mantenere checkpoint; collector e v1.65 NO-GO installazione, hosted Private Capture STOP. Telegram amici solo design opt-in di livelli approvati, nessun invio.

## Risorse
Nessun provider cloud o database toccato, nessuna acquisizione dati reali, Secret, spesa, merge, deploy o runner Actions avviato per questi test locali. Verificare la cronologia di Actions per il nuovo branch prima di dichiarare 0 esecuzioni hosted. Contatori Free Cloudflare/Oracle/GitHub NON rimisurati: non dichiarare quote disponibili senza dati.

**Stato: v0.59 LAB funzionale sul surrogato, struttura del D1 base verificata; v0.30 solo disegno. NO-GO reale.**
