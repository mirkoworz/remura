# REMURA Experience v0.25 LAB — checkpoint verificabile — 21/11/2026 07:23 CET

## Branch, provenienza, versionamento
- Branch dedicato: `research/experience-monotonic-anchor-v025-20261121`, nato da Experience v0.24 @ `f8446f2c5f58bb850d8290d2036ec1fb21951d85`.
- Codice nuovo: `research/contributors/independent_anchor_v025_lab.py`, blob finale `72474e6a6c858d5b6342790498c30f678d5e306f`, commit di correzione `a28b2a02dd8de0f7eec976f933b387ee2d28d4e2` (prima stesura `8ac0ce6fd2ed37c810214b5ec01f12e47cf1759b`).
- Nuovi test: `research/contributors/test_independent_anchor_v025_lab.py`, blob finale `4ed8782d82de3d860b5b48e919f06a4e8012da45`, commit di correzione `a52801f7949d3c06d1e02ee6d1fe53784861f168` (prima stesura `86520eb8dc37165ae6defd26c1dbe90dd813dee9`).
- Impronte finali remote e locali coincidenti tramite `git hash-object` e GitHub. Nessun file HTML, grafica toro/orso, nove frame, logo SMF, consumer o Home modificati. Le pagine esistenti restano alla propria versione e data precedenti. Nessun merge.

## Cosa fa il laboratorio
Simula su un *solo host* due directory SQLite distinte, primaria e testimone, con:
1. Proposta immutabile di intenzione; nessun dato ammissibile quando è solo pending.
2. Conferma di sequenza strettamente crescente sul testimone con `BEGIN IMMEDIATE` e compare-and-swap rispetto alla testa attesa.
3. Ricevuta primaria separata dalla prova del testimone. Nessuna consegna della sola intenzione o del solo commit parziale.
4. HMAC e catena di digest **con chiavi pubbliche di fixture**, non autenticazione di produzione.
5. Trattamento terminale distinto `PUBLISHED` / `ABANDONED`. Una pubblicazione abbandonata non è leggibile come mercato.
6. `external_pin` opzionale: simula un riferimento più recente sopravvissuto a un ripristino congiunto. Non conserva davvero un pin su terzo dominio.
7. Aperture SQLite di lettura `mode=ro`, evitando di ricreare database mancanti. Nessuna autoriparazione.
8. `finalize` senza una generazione esistente rifiutato esplicitamente.

## Test nuovi, effettivamente eseguiti
- Ambiente: container locale Linux, Python **3.13.5**, moduli standard `sqlite3`, `hmac`, `hashlib`, `unittest`, nessuna connessione al cloud nel runtime di prova.
- Comando: `cd research/contributors && python -W error::ResourceWarning -m unittest -q test_independent_anchor_v025_lab.py`
- Esito finale dopo correzioni: **28/28 test PASS**, 0 errori, runtime inferiore a 2 secondi.
- Test su genesis, pubblicazione completa, pendenti non distribuibili, conferma prima del testimone respinta, acknowledgement idempotente, scadenze e confini, annullamento, seconda generazione, firme di prova errate, CAS con due thread (uno vince), manomissione SQL, rollback singolo primario, rollback singolo testimone, rollback congiunto, presenza/assenza dell'ancora esterna, perdita di DB senza ricreazione e rifiuto di ack senza generazione.
- La verifica ha **riprodotto** il limite: rollback congiunto di entrambi i DB appare coerente **senza** il pin esterno. Con pin esterno preesistente più recente, fallisce. Poiché il pin è un parametro in memoria, non è attestato alcun terzo dominio.
- Non sono stati ripetuti i 366 controlli storici Experience, Safari Mac 40 controlli, Witness 001–005, recupero APFS, LOCAL_MATCH_ONLY, VM Debian Private Capture, collaudi SQL o hosted già conclusi.

## NO-GO / limiti non risolti
- Due *path* non sono due domini di controllo indipendenti: se lo stesso soggetto può ripristinarli entrambi, il rollback congiunto passa senza pin.
- Le chiavi HMAC sono note pubblicamente e servono esclusivamente a individuare errori nella fixture, **non** a proteggere dal compromesso intenzionale; identità e timestamp simulati.
- `BEGIN IMMEDIATE` serializza due thread locali, non prova CAS o atomicità tra due server né garanzie di rete.
- Nessuna prova di `fsync`, crash fisico, perdita simultanea della root di fiducia, ripristino del testimone realmente indipendente o firma sicura. Nessun accesso dati reali.
- Il modulo restituisce uno stato sintetico, non dati COT/prezzi e non è collegato a `disposition_gateway_v024_lab.mjs` o alla Home.
- No validazione scientifica di edge, identificazione istituzionale o redditività. Oracle v1.65 resta NO-GO.

## Proposta tecnica v0.26, ancora NON eseguita
- Revisione dei domini di ripristino e controllo: identificare chi può cancellare/sovrascrivere i pin su Mac, iPhone, GitHub, Oracle, Cloudflare.
- Priorità **gratuita**: procedura manuale con ricevuta firmata dell'ultima testa registrata su un supporto del proprietario veramente fuori dal dominio che può ripristinare i registri. La disponibilità iPhone offline di Witness 005 è evidenza di copia recuperabile, **non** una prova di monotonicità. Non dare per scontato che un file su un altro dispositivo sia immutabile.
- Prima di qualsiasi sincronizzazione automatica H24 o deploy: minacce, identità del firmatario, fiducia iniziale e rotazione/revoca, prova di ripristino indipendente, comportamento fail-closed su indisponibilità. In assenza di queste prove: mantenere il gate chiuso.
- Contributors v0.56: mantenere `LOCAL_MATCH_ONLY`; preparare permessi per scrittura dei soli propri livelli, ma nessun binding/deploy/accesso reale autorizzato.
- TradingView v0.8.181: protocollo V2 immutato, sviluppo 16–22/11 UTC; holdout 1 **23–29/11**, holdout 2 **30/11–06/12**. Endpoint, esiti, soglie e campioni non presunti; niente ottimizzazione ex post.
- Shark Science v0.4: continuare a distinguere proxy, dati osservati, baseline, errori e campioni. Nessuna inferenza di redditività.
- Safari iPhone fisico: da programmare; Chrome/WebKit/Safari Mac restano test acquisiti senza ripetizioni.
- Private Capture v0.15: STOP ai nuovi tentativi hosted. Oracle collector invariato; v1.65 non installata.

## Costi e sicurezza
Nessun nuovo servizio, database Cloudflare, spesa, acquisizione reale, modifica Oracle, merge, deploy o workflow privato attivato. I nuovi test girano in locale; zero minuti GitHub Actions consumati da **questi** test. Le quote Cloudflare e GitHub attuali non sono state interrogate e non possono essere dichiarate ancora disponibili sulla sola base del checkpoint storico.

**Stato: v0.25 LAB, verifica funzionale simulata, autorità indipendente NON ANCORA REALIZZATA.**
