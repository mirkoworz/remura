# REMURA Experience v0.25 — protocollo di custodia monotona indipendente — Design LAB
Data: 20/11/2026, 23:17 CET. SOLO DESIGN. Nessun host, testimone reale o firma attivati.

## Perché serve
Tre registri SQLite diversi, una firma valida o una ricevuta GitHub modificabile non dimostrano da soli che una generazione sia la PIÙ RECENTE. Un ripristino simultaneo di archivio, journal e autorità può presentare una catena vecchia ma crittograficamente valida. Occorre una prova separata e fresca dello stato massimo irrevocabilmente accettato, conservata fuori dai domini ripristinabili.

## Contratto candidato
Record canonico v0.25 con: schema_id, protocol_generation, sequence, previous_anchor_digest, intent_id, snapshot_digest, journal_head, authority_head, disposition, expiry_utc, actor_id, approval_digest, signer_key_id e status_digest. Nessun payload di mercato nell'ancora. La firma deve autenticare TUTTI questi campi e la generazione di formato. ABANDONED è stato terminale distinto da PUBLISHED e non può essere tradotto in snapshot valido.

Il trust store indipendente conserva LAST_ACCEPTED_SEQUENCE, LAST_ACCEPTED_ANCHOR_DIGEST e IDENTITÀ DEL FIRMATARIO già verificata. Ogni tentativo di avanzamento deve controllare sequenza strettamente successiva, predecessore uguale alla testa attuale, firma valida e approvazione specifica; usare una primitiva compare-and-swap su un dominio che non può essere ripristinato assieme a Oracle, Cloudflare e Mac. L'assenza della testa persistita o il dubbio sulla freschezza blocca PUBBLICAZIONE E LETTURA, senza fallback a una generazione precedente.

## Prova di indipendenza: condizioni necessarie
- Controllo del testimone da autorità distinta rispetto a quella che può ripristinare o cancellare il registro di produzione. La cartella separata sullo stesso Mac non soddisfa la condizione.
- Supporto e procedura di recupero del riferimento più recente non soggetti al medesimo backup/restoring di Mac, Oracle e Cloudflare.
- Recupero della testa massima dopo perdita temporanea del testimone; se non dimostrabile: NO-GO e riconciliazione manuale firmata, mai reset automatico.
- Trasparenza sul potere di chi gestisce le chiavi: firma autentica non implica freschezza; rollback di chiave o pin deve essere rilevabile.
- Nei test v0.23/v0.24 il pin è mock, non affermare la protezione risolta.

## Strategie gratuite da valutare, NON implementate
A. Approccio manuale: attestazione firmata dell'ultima ancora su supporto proprietario realmente offline, accompagnata da verifica periodica contro un secondo dominio amministrativo indipendente. Costo di servizi nullo, ma impedisce avanzamenti H24 automatici e ha rischi di perdita del supporto.
B. Due dispositivi propri, con conservazione differenziata e verificata (ad esempio Mac e iPhone): è una possibile ridondanza, NON un'autorità monotona indipendente senza dimostrare backup, ripristini, possibilità di modifica e gestione chiavi. L'originale iPhone Witness 005 prova disponibilità offline, non il punto di controllo monotono definitivo.
C. Servizio terzo con log pubblico append-only davvero non riscrivibile, verifica di inclusione e consistenza e conservazione degli ultimi checkpoint, solo dopo valutazione tecnica, legale, privacy e costi. Issue/commit GitHub modificabili, Drive e copie normali non bastano a qualificarsi.

## Matrice prove future — non eseguite
1. Rollback congiunto Oracle+Cloudflare+Mac a n-1 contro pin esterno n: rifiuto totale.
2. Pin esterno non raggiungibile: NO-GO, nessun numero distribuito.
3. Testimone più vecchio o sostituito: rifiuto; cambio firmatario senza procedura: rifiuto.
4. Pubblicazione interrotta prima/dopo la scrittura dell'ancora: recupero controllato senza doppio commit.
5. Doppia intenzione stessa sequenza / digest diverso: un solo vincitore CAS, altro rifiutato.
6. ABANDONED: revisione non riutilizzabile, evidenza candidata conservata immutata.
7. Spegnimento fisico e riavvio mentre scrive il testimone; verifica di durabilità dopo restore.
8. Revoca owner e compromissione simulata della chiave; blocco e rotazione esplicita.
9. Vecchio client Home V1/V2, risposta tardiva, re-login: mai mostrare valori di stato non approvato.
10. Perdita totale del dispositivo testimone e tentativo di ricostruzione: procedura documentata, senza affermare freschezza se la prova manca.

## Gate non superati
- Nessuna custodia indipendente concretamente attestata.
- Nessuna radice di fiducia anti-rollback definitiva, anche in assenza/perdita del firmatario.
- Nessun CAS distribuito né crashtest fisico.
- Nessun costo ricorrente o servizio attivato.
- v1.65 resta NO-GO, Private Capture hosted STOP, Contributors no binding/deploy.

Prossimo passo ammissibile: revisione del modello di minaccia e scelta verificabile di una sola modalità gratuita di custodia manuale prima di qualunque test real-world. Registrare il punto in roadmap senza sostituire le prove Witness 001–005.
