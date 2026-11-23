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
- **Access plan=Teams Free Base osservato in Billing/Subscriptions** (schermata 16:31 CET); non è ancora attestata l'assenza di ogni servizio opzionale fatturabile.
- **ActiveSeatsUsed / SeatsAllocated**: UI suggerisce 1/50; conferma ancora richiesta da Team & Resources / Users o Billing prima di inserire valori nel gate formale.
- **Workers plan=Workers Free, Active, osservato in Billing/Subscriptions**. **D1 overview 23/11 visually verified below: 258 rows read / 928 rows written (Daily);** **Workers requests 23/11 = 486 / 100.000 osservate alle 20:18 CET; CPU = UNKNOWN**. **Billing importo totale del periodo e add-on fatturabili=UNKNOWN**: l'etichetta Free per questi due prodotti non certifica un addebito totale nullo.
- Autenticazione reale, JWT Access, isolamento D1, login/logout/revoca su Safari: **NON TESTATI**.
- Nessuna promozione automatica a GO, nessun deployment/merge/utente creato, nessuna spesa autorizzata. PR #105 resta Draft.

## Controllo successivo più utile
**Non ripetere** il controllo dei nomi dei piani Free già completato. **D1 overview completata**, non ripetere le stesse schermate. Workers & Pages → Usage (richieste giornaliere) completato, NON ripetere. Verificare solo CPU per invocazione nel dettaglio Metrics/Analytics di un Worker pertinente, se disponibile, senza modificarlo. In seguito usare Billing (Invoices/complete billable usage) soltanto in lettura per l'importo effettivo e possibili add-on. Non premere Upgrade, non usare API o SQL console.

## Aggiornamento osservazione Billing — 23/11/2026 ore 16:31 CET (Europe/Rome)
- Screenshot iPhone della scheda **Subscriptions → Subscribed**: **Workers Free — Active** (Compute) e **Teams Free Base — Renews on Dec 15, 2026** (Zero Trust).
- **Upgrade to Workers Paid** è un'offerta di upgrade a **$5/mese più utilizzo**, NON una sottoscrizione attiva: nessun clic su Upgrade.
- Scheda **Billable usage**, filtro Current Month, mostra **Argo traffic cumulative total this month: 0 B**; è **solo traffico Argo**, non D1 rows, Workers usage, fattura totale né prova di spesa generale $0.
- Sezione Billing presenta informazioni sul metodo di pagamento, ma **nessun dato di pagamento, identificativo account o immagine** viene riportato qui.
- Interpretazione per gate: due piani Free osservati e confermati da schermata; il pilot rimane **NO-GO** per metrica D1/Workers, fatturazione complessiva, JWT/role enforcement, Safari e revoca non attestati. Non valorizzare come true `extraPaidServicesConfirmedAbsent` o `planPriceZeroConfirmed` soltanto in base a questi due screenshot.

## Aggiornamento osservazione D1 — 23/11/2026 ore 20:17 CET (Europe/Rome)
- Fonte: screenshot iPhone del pannello **D1 Database → Daily**, intervallo mostrato **November 23 - November 23**. Nessuna query, SQL Console o API eseguita per questa osservazione.
- **Total databases: 4 / 10**; rimangono 6 slot nella capienza numerica del piano Free. Non creare altri DB senza nuovo consenso e prova dell'isolamento.
- **Rows read: 258 / 5.000.000** per giorno mostrato (0,00516% del limite); **Rows written: 928 / 100.000** (0,928% del limite).
- **Total storage: 7,61 MB / 5 GB** (circa 0,15% della capienza nominale dell'account); **Metered storage: 199,04 kB-mo**, misura diversa da una fattura o da un costo pagato.
- Nella tabella dei quattro DB compaiono, nell'ordine visualizzato, dimensioni **131,07 kB**, **131,07 kB**, **7,32 MB**, **28,67 kB**. Nessun nome, ID o configurazione dei DB è stato registrato; non identificare né riutilizzare uno di questi DB senza controllo di isolamento.
- Il database di circa 7,32 MB è molto sotto il massimo Free individuale documentato di 500 MB; anche gli altri risultano piccoli.
- Margine ingegneristico REMURA del 25%: le metriche osservate sono inferiori alle soglie conservative di 3.750.000 righe lette, 75.000 scritte e 3,75 GB storage, **ma il pilot forecast e le attestazioni di sicurezza restano sconosciuti**; non marcare il gate come superato.
- Evidenza sufficiente per descrivere il consumo mostrato per il giorno selezionato; non prova costi totali, uso Workers, orario UTC esatto del contatore o una misura prospettica dopo attivazione del nuovo wrapper POST v0.98.
- **Decisione: D1 capienza osservata favorevole; pilot reale resta NO-GO.** Nessuna modifica Cloudflare/Oracle/Workers/D1/Access, nessun utente, merge o deploy.

## Aggiornamento Workers & Pages — 23/11/2026 ore 20:18 CET (Europe/Rome)
- Fonte: screenshot iPhone dashboard Workers & Pages, filtro **Today**, sola lettura.
- **Requests today: 486 / 100.000** (0,486% del limite Workers Free indicato nella schermata, capienza nominale restante 99.514 al momento dell'osservazione).
- **Observability events today: 386 / 200.000** (0,193% del limite mostrato). È un contatore distinto dalle richieste Worker e da CPU.
- Riserva ingegneristica REMURA 25%: massimale cautelativo per richieste giornaliere 75.000; margine istantaneo teorico **74.514** prima delle previsioni del pilot e delle altre applicazioni. Non è una promessa di fatturazione zero.
- CPU invocazioni, forecast del nuovo wrapper POST v0.98 e variabilità del carico: **UNKNOWN**; non considerare attestato il limite CPU o l'intero gate v0.97.
- Il pannello elenca un Worker esistente riferito a Contributors con etichetta **No active routes**; non prova l'assenza di deploy, chiamate `workers.dev`, binding o autenticazione. NON aprire URL pubblici, modificare Worker, route o Access solo per collaudarlo.
- I nomi degli altri Worker e i loro URL NON vengono copiati in questo registro pubblico; nulla è stato toccato.
- La quota Free Workers risulta ampiamente libera all'ora mostrata, ma **Billing totale, CPU, autenticazione/revoca Safari, isolamento dello staging e consenso separato** restano non attestati: **pilot reale NO-GO**.
- Nessuna nuova autorizzazione implicita: niente utenti, modifiche Access/D1/Workers, query GraphQL, merge o deploy.
