# REMURA Experience v0.26 LAB — checkpoint — 21/11/2026 07:35 CET

## Provenienza
- Branch isolato `research/experience-anchor-proof-v026-20261121`, creato esattamente da Experience v0.25 `7089335ea60c01f540f880235b5fd76ba6fb9370`. Nessun merge o modifica a `main`.
- Codice: `research/contributors/anchor_proof_v026_lab.mjs`; commit `648e55ae30cc54377784457a5654f226a4684e6c`; blob Git `5b705d74352c789bf8ac437923fc754ffe749c92`.
- Test: `research/contributors/test_anchor_proof_v026_lab.mjs`; commit `916927051df9a49dfa0c311a12ba16119247fc64`; blob Git `764833bfc2333fa5a937328f1e4f399bbd1835f1`.
- Gli hash dei due file pubblicati coincidono con `git hash-object` dei file locali realmente testati. Nessun file HTML o pagina aggiornata; versione/data/ora delle pagine approvate restano invariate.

## Funzione verificata
Verificatore offline di record sintetici con firme digitali **Ed25519 reali** e due chiavi pubbliche già fissate esternamente: owner e custodian. Le coppie private usate nei test sono generate al momento della prova e non vengono inserite nel repository. Il codice applicativo **non firma**, non genera chiavi di produzione, non salva registri e non avanza autonomamente il pin.

- Un record include versione del protocollo, generazione, sequenza, predecessore, intent ID, digest candidato, digest autorità, stato, istante osservato e scadenza.
- Entrambe le firme devono essere valide sulla stessa rappresentazione canonica; i due public key pin devono essere Ed25519 e distinti.
- Il verificatore autentica tutta la catena e richiede `externalPin` come parametro obbligatorio: coppia sequenza/digest identica all'ultima testa. Senza pin, niente accettazione; una catena più nuova del pin non viene automaticamente promossa.
- Una proposta di avanzamento valida può produrre un **pin proposto**, ma non persiste né approva il nuovo pin; serve conferma esterna esplicita e durevole.
- Stato `ABANDONED`, scadenza superata, orologio invalido o dati mancanti: nessuno stato `PUBLISHED` visibile al lettore. La funzione non consegna prezzi, COT o dati numerici di mercato.
- Firme, chiavi, intestazioni e digest ricevuti nello stesso record non sono considerati radici di fiducia. Nessuna sostituzione automatica di chiavi e nessuna migrazione delle generazioni vecchie.

## Test realmente eseguiti
Ambiente: container Linux locale, Node.js **v22.16.0**, API standard `node:crypto` (Ed25519) e `node:test`; nessun runner GitHub Actions, nessuna rete o credenziale reale impiegata nel test. Comando: `cd research/contributors && node --test test_anchor_proof_v026_lab.mjs`.

**33/33 PASS**, 0 failure. Verifica ripetuta dopo la pubblicazione degli stessi blob Git. Tra i nuovi casi: due firme corrette, chiavi pubbliche false/sostituite/uguali/RSA, manomissioni di digest, firme e payload, base64 malformata, generazione e sequenza sbagliate, predecessore errato, rollback di uno o più record rispetto al pin esterno, pin mancante, pin vecchio, proposta senza commit, scadenza, timestamp errato, ABANDONED e assenza di dati numerici da una risposta.

Non ripetuti: Experience v0.7–v0.25; Safari Mac 40 verifiche; Witness 001–005; APFS; VM Debian Private Capture; LOCAL_MATCH_ONLY Contributors; vecchie CI e migrazioni D1.

## Limiti e NO-GO
1. **La protezione contro rollback resta condizionata alla freschezza e autenticità del pin passato dall'esterno.** Il modulo non dimostra dove è conservato, chi può modificarlo o se sopravvive alla perdita/ripristino dei domini Mac, iPhone, Oracle e Cloudflare. Se un attaccante sostituisce **insieme** registro, chiavi pubbliche e pin, il modulo non può distinguerlo.
2. Il fatto che due firme siano valide **non prova** l'indipendenza operativa dei firmatari; entrambe le chiavi di test sono generate nella stessa sessione e nello stesso host. Segregazione reale dei custodi non collaudata.
3. Le chiavi pubbliche devono essere verificate con una radice di fiducia fuori banda; se il chiamante usa chiavi fornite dallo stesso record, la protezione è illusoria.
4. Il modulo non crea CAS distribuito, quorum remoto, storage non riscrivibile, gestione delle chiavi reali, rotazione/revoca sicura, transazioni tra domini o crash-test fisici.
5. Non è collegato alla v0.24 gateway, Home v0.22 o Contributors v0.56. Viene verificata l'ammissibilità di uno stato sintetico, non dati di mercato. Nessuna certificazione produttiva o prova scientifica di redditività.

## Coordinamento filoni e prossimi gate
- Experience v0.27: revisione modello di minaccia e procedura **gratuita** di custodia esterna che non condivida l'autorità di ripristino con il registro. Accertare con prove, non supposizioni, l'origine delle chiavi, la persistenza dell'ultima ancora e il comportamento fail-closed se manca. Simulare compromissione o perdita di uno dei custodi senza produrre pin alternativi non autorizzati.
- Contributors v0.56: congelato a `21338d4a405b0a3053e5a51322f8643c428ac757`, Mac `LOCAL_MATCH_ONLY` acquisito. Il progetto v0.57 documentale rimane separato: niente binding, preview reale, registrazioni, migrazioni o deploy.
- TradingView v0.8.181: periodo sviluppo 16–22/11 UTC; holdout 1 **23–29/11 UTC**, holdout 2 **30/11–06/12 UTC**. Protocollo prospettico e soglie inalterati. Non inventare pacchetti osservati o risultati.
- Shark Science v0.4: nessuna redditività dimostrata. COT settimanale e proxy Delta/CVD non identificano direttamente istituzionali.
- Mac custody `7a23f61b`, Experience Mac `57b8612d`, Witness 001–005, Safari Mac e APFS: risultati preservati. Safari iPhone fisico resta da eseguire.
- Private Capture v0.15: stop nuovi tentativi hosted. Oracle collector operativo, autoupdater inibito, v1.65 NO-GO. Ampere Radar invariato.
- Telegram: nessun invio reale; design dei soli livelli approvati in futuro.

## Costi e autorizzazioni
Test e codice eseguiti solo localmente, con strumenti già installati; non creati nuovi database, servizi, chiavi reali, hosting o spese. Nessun workflow privato avviato. Quote Cloudflare/GitHub **non misurate nuovamente**: valori storici non equivalgono a disponibilità attuale. Nessun merge, deploy, acquisizione di mercato, installazione o modifica Oracle.

**Stato: Experience v0.26 LAB — doppia firma verificata, indipendenza della custodia e anti-rollback completo NON attestati.**
