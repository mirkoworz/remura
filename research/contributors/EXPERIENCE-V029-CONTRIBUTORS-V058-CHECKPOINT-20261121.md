# REMURA Experience v0.29 LAB + Contributors Amendment v0.58 LAB
**Checkpoint: 21 novembre 2026, 08:22 CET (Europe/Rome)**

## Provenienza verificata
- Base Experience v0.28: `research/experience-offline-custody-audit-v028-20261121` @ `e4786a8f3ba00bfb8ace1919786c609f42fb250c`.
- Nuovo branch **isolato** `research/experience-handoff-contributors-amend-v029-20261121`; nessuna scrittura su main, branch Contributors ufficiale o TradingView.
- Contributors v0.56 LAB: `research/contributors-offline-20261114` @ `21338d4a405b0a3053e5a51322f8643c428ac757` invariato; nessuna migrazione su D1.
- Quattro nuovi file effettivamente pubblicati e verificati byte per byte contro `git hash-object` dei file locali eseguiti:
  - `research/contributors/amendment_v058_lab.py` — blob `23782436916891189f3fc8965ffa45b5451fbee4`, commit `176dcd456dbb4a1847566cc5a4aa817d130f156e`.
  - `research/contributors/test_amendment_v058_lab.py` — blob `9b64c1693ef4ad6345cf210cc0969b62ca99f56c`, commit `a590963873170ae4b84673d558a50782b6414767`.
  - `research/contributors/handoff_v029_lab.mjs` — blob `d080c9e2a7a4abec7ee411adadc817986f2f5904`, commit `b4fa58f624d23f2086841b551fe5d20490b2a99d`.
  - `research/contributors/test_handoff_v029_lab.mjs` — blob `f0623bf01f7c388853b826a6b75a29405f4c759c`, commit `256b7609e7182f86c524825859dfcf0836ebc84e`.

## Prototipo Contributors v0.58: correzioni personali append-only
Nuova fixture **SQLite in memoria**, separata completamente da D1, Cloudflare e Workers, con tre identità TEST: fixture-owner, fixture-a, fixture-b. Nessuna identità o chiave reale. Autorizzazione in-process: NON è autenticazione reale; l'argomento actor deve derivare esclusivamente da una sessione verificata lato server in un'eventuale futura implementazione.

- La correzione crea una **nuova entry** collegata a un originale esistente dello STESSO autore tramite base_id e digest del payload originario; originale e decisioni di review sono immutabili, con trigger UPDATE/DELETE.
- La correzione NON viene automaticamente approvata: rimane in attesa. Solo OWNER può approvare/rifiutare. Nessuna correzione approvata se l'originale non è prima APPROVED; al massimo una correzione approvata per originale; un autore revocato non può presentare nuove entry né ricevere approvazioni.
- Idempotenza della submission per coppia autore/request_id; stessa richiesta con payload o parent diverso è respinta. Nessuna operazione di retry automatico.
- Ruoli e ricevute personali verificati nella stessa transazione per le mutazioni; l'accesso alle ricevute usa filtro per soggetto, mai vista dei livelli altrui per Contributor.
- Campo price, UTC, prodotto/contratto, periodo, metodologia e note seguono una forma sintetica **ispirata** al contratto D1 LAB, non sono una migrazione compatibile certificata.
- La fixture usa una connessione SQLite singola in memoria. Non prova isolamento multi-processo, concorrente cross-host, durabilità fisica, Access JWT/Cloudflare, CAS distribuito o protezione da amministratore del database. Non espone API o pagina web.
- **Limite funzionale dichiarato**: un originale può avere una sola correzione APPROVED. Ulteriori rettifiche dopo tale correzione richiederanno politica esplicita di sostituzione/revoca e revisione audit, non sono implementate.
- **Nessun edit diretto del record originale**. La possibilità futura di una vista pubblicata di soli livelli APPROVED deve ricostruire la catena e rispettare gli esiti REVOCATION; oggi la fixture non distribuisce livelli a utenti finali.

## Experience v0.29: handoff Mac/iPhone SOLO SIMULATO
Nuovo modulo Node.js puro, basato sul verificatore Ed25519 v0.26 esistente:
- Un manifest firmato dall'emittente lega protocollo, generazione, sequenza, digest testa, nonce, dispositivo mittente e destinatario, data di emissione e scadenza (massimo 1 ora nel LAB).
- Una conferma del destinatario, firmata con una **seconda chiave Ed25519 differente**, lega digest del manifest, nonce e destinatario. Entrambe le chiavi pubbliche devono essere impostate fuori banda dal chiamante e non accettate dallo stesso documento come prova.
- Verifica la cronologia completa firmata v0.26 contro la testa dichiarata e un riferimento minimo manuale che deve coincidere con un elemento della cronologia.
- Output positivo esclusivamente `REVIEWABLE_LAB_ONLY`, `manualApprovalRequired=true`, `marketDeliveryPermitted=false`; output negativo `BLOCKED`. Nessuna scrittura, nessuna promozione dell'ancora, nessuna approvazione automatica o mercato.
- **I test generano tutte le chiavi sul medesimo host e non usano un vero iPhone né un secondo custode indipendente.** Due firme non significano separazione amministrativa o fisica.
- Un replay completo di manifest+conferma+floor vecchi ma coerenti può ancora essere revisionabile, mai pubblicabile. Non è attuata la persistenza monotona, un protocollo anti-replay fra sessioni, una chiave hardware o un canale sicuro.

## Test nuovi realmente eseguiti
- Ambiente locale Linux, Python 3.13.5 / sqlite3 standard e Node 22.16.0 / node:crypto Ed25519; nessun provider di mercato, Internet, runner hosted, secret o database esterno durante i test.
- `cd research/contributors && python -W error::ResourceWarning -m unittest -q test_amendment_v058_lab.py` → **33/33 PASS, 0 errori**.
- `cd research/contributors && node --test test_handoff_v029_lab.mjs` → **25/25 PASS, 0 fail**.
- **Totale 58 nuovi test PASS**. Suites ripetute dopo GitHub publish sulle identiche impronte dei 4 file; nessun test storico della roadmap è stato ricontato.
- Copertura: livelli propri vs altrui, append-only, no UPDATE/DELETE, idempotenza, approvazione esclusiva owner, revoche, note/prezzi/UTC, correttezza parent e anti-doppia approvazione; manifest e conferma firmati, chiavi alterate, nonce, destinatario, scadenza, rollback singolo, floor errata, firme mancanti e vecchie attestazioni congiunte.

## Roadmap coordinata e prossimi gate
1. **Contributors v0.59**: progettare **transizione SQL D1 append-only** (senza rompere trigger immutabili) e test di rollback/revoca concorrenza; successivamente adapter reale con Cloudflare Access verificato e preview autorizzata. Non usare direttamente lo schema sintetico SQLite.
2. **Experience v0.30**: proof-of-custody per il recupero manuale con registrazione realmente indipendente e monotona di pin/revoche. Valutare prima il caso gratuito con Mac+iPhone, tenendo presente che una copia iPhone o GitHub non prova monotonicità. NON generare chiavi vere o attivare custodi esterni senza nuovo consenso.
3. **Contributors accesso amici**: desiderio fisso OWNER amministratore, Contributor vista approvata + soli propri livelli; nessun ingresso reale fino a verifica identità, ACL server-side, sessioni, rate limit, difese CSRF, audit e costo Free.
4. **TradingView v0.8.181**: criteri e soglie congelati; holdout 1 23–29 novembre 2026 UTC, holdout 2 30 novembre–6 dicembre; non calcolare risultati prima della finestra e senza dati validati. Squalincome/Shark Science: proxy Delta/CVD non identificano direttamente istituzionali; nessun edge o profitto dimostrato.
5. **Custodia Mac e Experience**: witness 001–005, APFS, Debian Private Capture, Chrome/WKWebView e Safari Mac rimangono test precedenti acquisiti; Safari iPhone fisico ancora aperto. Splash toro/orso, 9 frame, pinna REMURA e ringraziamento SMF invariati.
6. **Oracle**: collector operativo secondo ultimo checkpoint, autoupdater inibito, v1.65 NO-GO; Ampere Radar invariato. Telegram Contributor formato bandierine: design backlog, nessun invio.

## Autorizzazioni, costi e limiti
Nessun deploy, merge, workflow hosted privato, Cloudflare D1 schema/binding, real market capture, nuova chiave personale, operazione Oracle, spesa o registrazione utente. Test completamente offline; nessun minuto Actions impiegato per **queste** suite locali. Le quote attuali Cloudflare, Oracle e GitHub non sono state rimisurate, quindi non attestare disponibilità dei limiti Free.

**Stato: v0.29 Experience LAB + v0.58 Contributors LAB; verifiche locali nuove completate, zero ammissione alla produzione.**
