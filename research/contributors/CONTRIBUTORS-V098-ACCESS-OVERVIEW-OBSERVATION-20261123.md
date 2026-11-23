# REMURA Contributors v0.98 LAB — Evidenza manuale parziale Access (23/11/2026)

**Fonte**: screenshot iPhone dell'OWNER della panoramica Cloudflare One, visualizzata il 23 novembre 2026 alle **15:05 Europe/Rome**. Nessuna chiamata API, azione di provisioning o modifica Cloudflare.

## Solo aggregati osservati, nessun identificativo
- Cloudflare One / Overview, voce **Users**: **1 of 50 available** (interfaccia inglese).
- Capienza apparente ricavata: **49** posti in più rispetto al conteggio mostrato; numero **indicativo**, non attestazione contabile di Access seats attivi/assegnati.
- Active devices (7 days): **0**.
- Applications: **1** (app esistente non identificata: NON modificare).
- Targets: **0**; Active Tunnels: **0**.
- Connected users / top private applications / routes: grafici vuoti o **No data available**. Il vuoto NON significa zero consumo, e NON prova login, logout o identità Access.
- **Non registrati deliberatamente**: dominio team, nome team, account ID, screenshot integrali o altri identificativi.

## Stato del gate v0.97 (fail-closed)
- Capacity per 1 OWNER + 1–2 CONTRIBUTOR: **verifica visiva preliminare favorevole**, ma non segna il gate come completato.
- **Access plan=UNKNOWN** finché Billing/Subscriptions e la configurazione del piano non siano documentati per l'account.
- **ActiveSeatsUsed / SeatsAllocated**: UI suggerisce 1/50; conferma ancora richiesta da Team & Resources / Users o Billing prima di inserire valori nel gate formale.
- **Workers plan=UNKNOWN**, **D1 rows read/written=UNKNOWN**, **Billing=UNKNOWN**.
- Autenticazione reale, JWT Access, isolamento D1, login/logout/revoca su Safari: **NON TESTATI**.
- Nessuna promozione automatica a GO, nessun deployment/merge/utente creato, nessuna spesa autorizzata. PR #105 resta Draft.

## Controllo successivo più utile
Dalla dashboard dell'account, leggere **Billing / Subscriptions** o **Zero Trust plan details**, verificare Free e prezzo 0, e annotare solamente il nome del piano e l'assenza/presenza di addon a pagamento; non aprire percorsi di upgrade. Poi verificare le quote Workers e D1 del giorno UTC dalla dashboard in sola lettura. Non usare API o SQL console.
