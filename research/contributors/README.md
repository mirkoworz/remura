# REMURA Contributors v0.1 LAB — 14/11/2026 23:20 CET
## Filone E — indipendente, DRAFT, NO MERGE / NO DEPLOY
Obiettivo: due collaboratori invitati possono inviare livelli volumetrici manuali senza accedere a impostazioni, dati privati, broker, infrastruttura o elaborazioni. Nessuna modifica ai filoni A/B/C/D.

### Roadmap
- [x] Registro in memoria SQLite, nessun file, HTTP, rete o segreto. Principal sintetico fornito da chiamante fidato; NON autenticazione. Allowlist subject e simboli completi del feed, prezzo decimale positivo, periodo DAY/WEEK/CURRENT_MONTH/PREVIOUS_MONTH, metodologia dichiarata, istante osservato UTC e istante ricezione separato. Request UUID idempotente per autore, cap sperimentale 20 invii/giorno UTC e 200 totali; invii UNREVIEWED, nessuna promozione o segnale.
- [x] Test sintetici di rifiuto accessi, campi extra, date future, prezzi invalidi, feed ambiguo, classificazione e duplicazione.
- [ ] UI prototipo mobile: dati fittizi, invio e conferma; data/ora e versione in alto. Eventuale livello da futures/non spot deve conservare simbolo, contratto e feed; nessuna conversione implicita. Se non autorizzata la redistribuzione dalla fonte, non raccogliere dati.
- [ ] Accesso Google vero: app/client ID e origine HTTPS autorizzata, solo identità (no Gmail/Drive), Google Identity Services; verificare firma, issuer, audience, scadenza e CSRF/nonce server-side con libreria ufficiale. Allowlist di identità stabili Google sub dopo invito e verifica owner; email solo per contatto/bootstrap controllato. Revoca sessioni e ruoli, cookie sicuri, rate limiting al perimetro, cap dimensione body, niente token nei log. Non creare credenziali ora.
- [ ] Separare endpoint di raccolta e superficie collaboratori da server privato owner: Google login da solo non autorizza attraversamento Tailscale; non aprire porte VPS, Funnel o accesso generale. Definire ingress autorizzato a costo zero verificato e segregazione effettiva prima di qualsiasi deploy; valutare risorse esistenti senza usare token provider in tale processo.
- [ ] Archivio persistente separato dal DB live, ruoli contributor (solo invio e propri ricevuti) e owner (revisione). Identità pseudonima, retention e cancellazione concordate, audit delle correzioni senza sovrascritture, dedup semantica e qualità, limiti per autore e globali; distinguere osservato da ricevuto, UTC; sanitizzare output HTML e non esporre note ad altri. Niente password, API key, screenshot o dati conto.
- [ ] Revisione manuale, provenienza e autorizzazione fonti. Solo livelli approvati come nuova fonte dichiarata manuale; non contare più amici che usano stessa fonte come prove indipendenti, non inferire identità istituzionali. Nessuna influenza retroattiva sui fold D o B congelati; eventuale nuovo protocollo prospettico separato.
- [ ] Raccordo a REMURA Volumetrica solo dopo coordinamento A/B/C/D, test reali, consenso deploy e check quote/costo; nessun ordine.

## Confronto livelli manuali e automatici — approvato 14/11/2026 23:20 CET
- [ ] Dopo revisione owner, confrontare i livelli manuali disponibili all'istante di valutazione con quelli automatici REMURA, distinguendo feed, eventuale contratto, periodo/anchor e timestamp di nascita. Nessuna equivalenza automatica fra spot e future.
- [ ] Mostrare distanza in tick/pip o ATR quando confrontabile; tolleranza da definire e congelare prima dello studio, nessun valore inventato. Classificare accordo, disaccordo e non confrontabile; preservare anche livelli isolati.
- [ ] Registrare fonte/metodo dichiarati e raggruppare contributi correlati (stessa fonte o indicatore): consenso umano non significa evidenze indipendenti né conferma istituzionale.
- [ ] Valutare prospetticamente l'informazione aggiuntiva rispetto al radar automatico senza alterare fold B/D, selezionare a posteriori o produrre segnali operativi. Nessuna promozione al motore prima della validazione.
- [ ] UI futura owner: livelli automatici, manuali approvati e sovrapposizioni distinguibili, stato N/D se dati non confrontabili. Nessun accesso dei collaboratori al dossier riservato.

### Limiti attuali
Il ledger vive solo nella memoria del processo e perde i record a chiusura. Non è multi-thread, non è un servizio né una barriera di sicurezza contro chiamanti Python ostili, non implementa autenticazione, sessioni o revoca, revisione o dedup fra request ID diversi. Il tempo di ricezione deve provenire da clock fidato del futuro server; non usare date storiche come prove causali. Limiti arbitrari prudenziali LAB da riesaminare. Nessuna spesa aggiuntiva o servizio cloud creato; futura gratuità non attestata.

Riferimenti: https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid e https://developers.google.com/identity/gsi/web/guides/verify-google-id-token.
Test: python3 -m unittest discover -s research/contributors -p 'test_*.py' -v
