# REMURA Capital.com — modalità DEMO

STATO: codice e test offline predisposti. Nessuna richiesta autenticata eseguita.

API ufficiale: https://open-api.capital.com/
- SERVER UNICO: https://demo-api-capital.backend-capital.com
- POST /api/v1/session con X-CAP-API-KEY, identifier (email di login)
  e password PERSONALIZZATA DELLA CHIAVE, non la password del conto.
- La risposta contiene CST e X-SECURITY-TOKEN negli header.
- GET /api/v1/clientsentiment?marketIds=SILVER restituisce percentuali
  longPositionPercentage e shortPositionPercentage in clientSentiments.
- NON esistono nel raccoglitore funzioni per ordini o accesso al server LIVE.
- Le chiavi Capital.com hanno permessi di trading: usare solo account DEMO.

COPERTURA INIZIALE: XAGUSD = SILVER, ID confermato negli esempi ufficiali.
Per estendere a EURUSD, GOLD e altri mercati, verificare prima gli ID reali
nell'account demo. Configurazione facoltativa, MAI nel repo pubblico:
private/capital/markets.json, formato {"XAGUSD":"SILVER"}.
Non presumere che 35 mercati siano già supportati.

LIMITI RIGIDI IMPLEMENTATI:
- Massimo 36 richieste HTTP Capital.com per giorno UTC, inclusi errori.
- Minimo 2 ore tra tentativi, anche dopo un errore.
- Un ciclo normale = 2 richieste: login e sentiment multi-market.
- Nessun retry automatico. Timer locale e ledger persistente su disco Linux.
- Conteggio prima della richiesta. Stato danneggiato = blocco delle chiamate.
- Storico numerico vero per ogni simbolo, fino a 90 giorni/1100 osservazioni.
- Nessun inserimento di numeri fittizi o ricostruzioni retroattive.
- Nessun salvataggio di email, chiavi, password o token CST/XST.

FILE LOCALI:
private/capital/budget.json
private/capital/latest.json
private/capital/history/XAGUSD.json
Questa cartella è esclusa dal Git pubblico REMURA.

ATTIVAZIONE SOLO IN AMBIENTE PRIVATO:
- CAPITAL_API_KEY = chiave API Capital.com creata dall'utente
- CAPITAL_IDENTIFIER = email login
- CAPITAL_API_PASSWORD = password personalizzata della CHIAVE
- REMURA_CAPITAL_ENABLED = 1

NON condividere questi dati in chat, screenshot, GitHub o repository pubblico.
Mai usare Windows direttamente per questo script: fcntl è specifico Linux.
Lanciare una volta: python3 scripts/update_capital.py.
Il collettore e il server privato sono inattivi in assenza di opt-in.
Il pannello privato legge /private-api/capital/latest.json e
/private-api/capital/history/XAGUSD.json. Non è disponibile pubblicamente
su GitHub Pages, né si devono pubblicare gli aggregati senza verificare
le condizioni di utilizzo di Capital.com.

IMPORTANTE PER IL COSTO ZERO:
Un job GitHub Actions su runner effimero NON preserva budget.json o
lo storico: riavviarlo senza ripristinare lo stato annulla il limite.
Per cron continuativi occorre un repository separato PRIVATO che
ripristini e versioni lo stato in modo atomico, con concurrency e
nessuna duplicazione con altri raccoglitori. Verificare prima i minuti
Actions Free residui (condivisi con i progetti MIRKO), le impostazioni
di fatturazione e i permessi di memorizzazione dei dati.
Non abbiamo ancora creato o abilitato quel repository o i suoi cron.

TEST SENZA API:
python3 -m unittest discover -s tests -p 'test_capital*.py' -v
node --check sources.js
python3 -m py_compile scripts/update_capital.py scripts/private_server.py

La prima richiesta Capital.com vera richiede le credenziali custodite
in privato e resta da collaudare.
