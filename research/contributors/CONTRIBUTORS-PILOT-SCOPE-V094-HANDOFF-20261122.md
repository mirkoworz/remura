# REMURA Contributors v0.94 LAB — contratto scope per pilot 1-2 amici
22 novembre 2026, Europe/Rome. Offline, NON autenticazione.

## Nuovo sviluppo rispetto a v0.93
v0.93 verifica le lacune di prove sul costo Free e rimane NO-GO. v0.94 aggiunge una matrice minima e deterministica delle autorizzazioni desiderate senza rifare i controlli ownership/revoca/hardcap gia' verdi.

- Codice: research/contributors/contributors_pilot_scope_v094_lab.py
- Test: research/contributors/test_contributors_pilot_scope_v094_lab.py (16 casi nuovi).
- Il compilatore ammette soltanto un owner fixture e 1-2 contributor fixture, nessun nome/email/UUID/token reale.
- Digest del manifest per rilevare mutazioni accidentali e rifiuto di utenti duplicati, scope extra, privilegi non elencati.
- Contributor: sola consultazione delle sezioni REMURA consentite, lettura e creazione/modifica dei propri livelli; niente owner queue/approvazione, livelli altrui, COT, Oracle, Secret o deploy.
- Owner: lettura, coda, audit, revisione e approvazione di altri; auto-approvazione negata, nessun accesso Secret o deploy.
- review_claimed_ui controlla soltanto i controlli previsti, non concede permessi.
- model_action e' una preview del piano su identita' fittizie autodichiarate, NON valida un JWT Access, un profilo D1 o sessione Safari. Il server Worker/D1 deve applicare sempre permessi e ownership reali.

## NO-GO pilot
Cloudflare D1 quota UNKNOWN_NO_GRAPHQL_DATA; Access seats, fatturazione, piano e margine GitHub Actions ancora non verificati completamente. Nessuna query aggiuntiva Cloudflare, nessuna nuova utenza, worker o deploy. Future prove richiedono consenso mirato, quote reali, due identita' in Safari iPhone, login/logout/revoca e isolamento D1. PR #105 resta DRAFT.

Nessun titolo di autorizzazione reale prodotto da questo LAB.