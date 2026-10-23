# REMURA personale — automazione 24/7 (preparata, non ancora attivata)

Questa guida si riferisce al ramo `feature/private-price-engine-v10`, **non ancora pubblicato**. Il progetto è per uso personale; l'originale GitHub Pages è pubblico finché non viene disattivato separatamente.

## Cosa fa già il codice

Il servizio `scripts/private_server.py` è un unico processo locale. Avvia un piccolo server HTTP **solo su 127.0.0.1:8765** e, se abilitati, tre lavoratori automatici facoltativi:

- **cTrader** ogni quarto d'ora UTC, 90 secondi dopo la chiusura della candela M15. Il processo figlio `scripts/ctrader_feed.py` richiede soltanto prezzi storici M15 tramite Open API ufficiale, poi memorizza le candele in SQLite `private/remura-prices.sqlite3`, ricostruendo H1 e H4 senza dati fittizi. Primo avvio: massimo 30 giorni di storico; successivamente 2 giorni per recuperare eventuali disconnessioni. Storico locale massimo 45 giorni.
- **Myfxbook** ogni 20 minuti, riutilizzando `scripts/update_myfxbook.py` ma eseguendolo nella cartella privata `private/myfxbook/`. Salva l'archivio e le rilevazioni senza fare commit sul repository. Rispetta la stessa frequenza esistente: circa 72 richieste giornaliere (+ login/logout come previsto dall'API). Se il feed non è disponibile, non inventa rilevazioni.

- **IG Client Sentiment (facoltativo):** una lettura ogni ora dal servizio REST ufficiale autenticato. I soli aggregati percentuali vengono salvati nel file privato `private/ig/latest.json`; nessun commit automatico, nessuna chiave nel JavaScript. Mercati privi di dati IG verificati restano N/D.

Il COT CFTC continua a essere recuperato dalla fonte ufficiale all'apertura della scheda. La sua frequenza rimane settimanale, non M15.

La dashboard legge tutto dalla **stessa origine privata**, tramite `/private-api/prices/EURUSD`, `/private-api/retail/latest.json`, `/private-api/retail/history/EURUSD.json` e `/private-api/ig/latest.json`. Quando un dato non esiste, la pagina mostra N/D anziché inventarlo.

Nessun comando apre o chiude posizioni. Il servizio non legge saldi né operazioni personali. Prezzi e storico privati restano fuori dal repository grazie a `.gitignore`.

## Soluzione più semplice: PC o mini-PC acceso + Tailscale Serve

Per uso personale, consigliamo [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve). NON Tailscale Funnel, che rende il sito pubblico.

Vantaggi: nessun dominio obbligatorio, sito HTTPS accessibile solo ai dispositivi della tua rete Tailscale (*tailnet*), stesso indirizzo sul telefono, una sola app, nessuna password del broker nel browser.

1. Installa Tailscale sul computer/mini-PC che userai per REMURA, accedi con il **tuo** account. Installa Tailscale anche sull'iPhone, con lo stesso account e VPN attivata.
2. Installa Python 3.11+ su quel computer e scarica o clona il repository. Posizionati nel ramo `feature/private-price-engine-v10`.
3. Installa solo l'SDK richiesto dalla connessione cTrader: `python -m pip install ctrader-open-api`.
4. Per provare il sito PRIMA dell'approvazione cTrader, esegui `python scripts/private_server.py`. Vedrai il messaggio `127.0.0.1:8765`; apri sullo stesso PC `http://127.0.0.1:8765`. **È normale vedere prezzi N/D**.
5. Da un altro terminale sullo stesso PC, esegui `tailscale serve 8765`. Segui l'attivazione dell'HTTPS se richiesta e usa l'indirizzo `https://<nome-dispositivo>.<tailnet>.ts.net` che Tailscale ti mostra, dal Safari dell'iPhone con Tailscale connesso. Puoi rendere Serve persistente con `tailscale serve --bg 8765` dopo la prima prova.
6. Prima di usare i dati personali, limita l'accesso alla tailnet al tuo account e verifica che **Tailscale Serve**, non **Funnel**, sia attivo. Non aprire porte sul router e non cambiare l'indirizzo di ascolto del servizio: resta `127.0.0.1`.

**Importante:** il computer deve restare acceso connesso a Internet, anche quando l'iPhone è spento. Se vuoi il servizio acceso anche con il tuo computer spento, servirà un mini-PC a casa oppure una piccola VM/VPS sempre attiva. Non è stato noleggiato alcun server per conto tuo.

## Dopo l'approvazione Spotware: attivare la raccolta prezzi

Servono l'account cTrader autorizzato e i permessi OAuth **`scope=accounts`** (sola lettura, **mai** `scope=trading`). Le credenziali iniziali e il refresh token devono essere creati e inseriti **da te** direttamente nell'ambiente protetto del tuo server, mai nella chat, nel repository o nel JavaScript.

Variabili d'ambiente da configurare localmente sul server:

| Variabile | Scopo |
|---|---|
| `REMURA_COLLECTOR_ENABLED=1` | Abilita il lavoratore cTrader |
| `CTRADER_CLIENT_ID` | ID applicazione personale (non account prop) |
| `CTRADER_CLIENT_SECRET` | Segreto applicazione, da mantenere privato |
| `CTRADER_REFRESH_TOKEN` | Token ottenuto dopo OAuth in sola lettura |
| `CTRADER_ACCOUNT_ID` | ID API cTrader dell'account autorizzato, **non** il login del terminale |
| `CTRADER_ENV` | `demo` o `live` (deve corrispondere all'account) |
| `REMURA_SYMBOLS` | Opzionale, `all` per tutti i 35 o elenco separato da virgole per prove iniziali |

Puoi usare temporaneamente `CTRADER_ACCESS_TOKEN` al posto di `CTRADER_REFRESH_TOKEN`, ma il servizio non potrà rinnovarlo automaticamente alla scadenza. Con `CTRADER_REFRESH_TOKEN` il modulo `scripts/ctrader_tokens.py` rinnova in modo riservato il token tramite endpoint ufficiale Spotware, salva atomica­mente i nuovi access/refresh token in `private/ctrader-tokens.json` con permessi 0600 e li riutilizza. Il refresh token in ingresso viene consumato dal primo rinnovo: **non riutilizzare un vecchio token dopo che è stato ruotato**.

La cartella `private/` deve essere leggibile solo dall'utente di sistema che esegue REMURA (non da altri utenti o servizi web). I token non appaiono nei log del server. Se il token viene revocato o il broker non permette l'accesso Open API, servirà una nuova autorizzazione manuale: REMURA segnalerà feed assente.

Il primo storico può richiedere alcuni minuti. La copertura reale di Forex, metalli e indici dipende dal conto broker: un ticker mancante diventa N/D. Per simboli CFD particolari, crea **solo sul server** `private/ctrader-symbols.json`:

```json
{
  "XAUUSD": "NOME_ESATTO_ORO_DEL_TUO_BROKER",
  "US500": "NOME_ESATTO_INDICE_DEL_TUO_BROKER"
}
```

Non indovinare simboli o confondere CFD/futures differenti.

## Attivare Myfxbook nello stesso servizio privato

Imposta sul computer/server, non su GitHub:

- `REMURA_RETAIL_ENABLED=1`
- `MYFXBOOK_EMAIL` e `MYFXBOOK_PASSWORD` (le credenziali della tua integrazione Myfxbook)

Riavvia il server privato. Le rilevazioni rimangono nel percorso locale `private/myfxbook/` e non vengono salvate nella repository. Il raccoglitore prosegue circa ogni 20 minuti secondo disponibilità e rate limits del provider. Senza credenziali il pannello resta N/D.

Quando la versione privata sarà quella che utilizzi, si potrà disattivare il precedente workflow GitHub Actions Myfxbook che scrive `data/myfxbook/` nel repository. **Non disabilitarlo adesso**: REMURA v0.9 pubblica ancora lo usa.

## Attivare IG Client Sentiment privato (facoltativo)

Per una seconda fonte numerica indipendente da Myfxbook, serve un account IG con accesso API abilitato, autorizzato secondo i termini del provider. Non serve inviare credenziali in chat o inserirle su GitHub. Imposta **solo nel file d'ambiente privato della macchina**:

- `REMURA_IG_ENABLED=1` — avvia il lettore automatico orario;
- `IG_API_KEY` — chiave generata nel tuo account IG;
- `IG_IDENTIFIER` e `IG_PASSWORD` — login API personale;
- `IG_ENV=demo` oppure `IG_ENV=live` — ambiente coerente con l'account.

Il server effettua login verso la REST API, legge solo `/clientsentiment` e salva in privato percentuali long/short per i gruppi di mercato che IG restituisce effettivamente. **Non esegue ordini**. L'elenco di copertura reale dipende dal conto e dai permessi IG, non possiamo garantirlo per tutti i 35 strumenti prima della prova autentica. Il nome del marketId non è necessariamente quello del CFD e gli strumenti non trovati vengono esclusi.

Usa `/private-api/ig/latest.json` per verificare che il server esponga i soli aggregati consentiti (mai chiavi, password o token). In `/private-api/health` sono disponibili `igStatus` e `igLastSuccess`. Gli aggiornamenti sono su base oraria, non M5. Se IG non è configurata o il feed non risponde, il pannello mostra N/D o l'ultima lettura marcata come datata. Nessuna media arbitraria fra quote di lotti Myfxbook e percentuali di posizioni IG.

Per i test senza internet o credenziali: `python -m unittest discover -s tests -p 'test_ig_sentiment.py' -v` e `python -m unittest discover -s tests -p 'test_ig_private.py' -v`.

## Avvio automatico su server Linux (facoltativo)

Su una macchina Linux dedicata con utente non privilegiato `remura`, ambiente Python virtuale e codice in `/opt/remura`, prepara un file privato `/opt/remura/private/remura.env` leggibile soltanto da `remura`. Includi variabili sopra con valore reale senza usare Git. Installa come amministratore un servizio `/etc/systemd/system/remura-private.service`:

```ini
[Unit]
Description=REMURA Private (localhost + scheduled market readers)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=remura
WorkingDirectory=/opt/remura
EnvironmentFile=/opt/remura/private/remura.env
ExecStart=/opt/remura/.venv/bin/python /opt/remura/scripts/private_server.py
Restart=on-failure
RestartSec=15
UMask=0077
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/opt/remura/private
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Avvia/abilita con `sudo systemctl daemon-reload` e `sudo systemctl enable --now remura-private`, poi avvia Tailscale Serve sullo stesso server. Se sei su Windows, usa l'Utilità di pianificazione per avviare `python scripts/private_server.py` all'accesso e configura il riavvio automatico; lo script Python **non richiede il terminale MT5**, soltanto rete e OAuth cTrader.

## Stato, sicurezza e verifiche

- Apri solo all'interno della tailnet `https://<nome-dispositivo>.<tailnet>.ts.net/private-api/health` per lo stato dei raccoglitori. Non contiene token né dati di conto. `/private-api/prices/EURUSD` fornisce il documento prezzi per la dashboard e non è destinato alla consultazione pubblica.
- Il servizio HTTP ascolta esclusivamente su `127.0.0.1`, serve una **lista esplicita** di file statici e rifiuta `/private/`, `/scripts/`, `.env`, SQL e altri file. L'accesso remoto è protetto dalla tailnet/Tailscale Serve; HTTP locale non richiede un login per chi ha già accesso alla stessa macchina.
- Il Service Worker non conserva risposte `/private-api/*` nella cache.
- La raccolta non viene eseguita finché non imposti `REMURA_COLLECTOR_ENABLED=1` e le credenziali reali in modo locale. Non è ancora stata verificata una sessione cTrader live/della tua prop, perché l'approvazione Spotware è in attesa.
- **Niente port forwarding, Quick Tunnel, Funnel o repository pubblici con credenziali.**
- Backup: salva privatamente il database e i file token (con protezione equivalente). Se la macchina viene rubata/compromessa, revoca le autorizzazioni cTrader dal tuo account.

### Test automatici offline

```bash
python -m unittest discover -s tests -p 'test_private_server.py' -v
python -m unittest discover -s tests -p 'test_ctrader_tokens.py' -v
python -m unittest discover -s tests -p 'test_ctrader_feed.py' -v
node --test tests/price.test.js tests/insights.test.js
```

Questi test utilizzano dati sintetici **solo nelle fixture**, mai nel sito come mercato reale.

## Limiti da verificare quando attiviamo i dati reali

La frequenza programmata M15 non assicura la disponibilità di ogni quotazione esattamente al secondo di chiusura (mercati chiusi, manutenzione cTrader, assenza di tick, VPN/Internet, rate limit). Il pannello contrassegna le candele datate. L'analisi H4/H1/M15 resta indicativa e non backtestata, e COT rimane settimanale con giorno di pubblicazione diverso dalla data delle posizioni.


---
## REMURA v1.8: cTrader storico a gruppi, senza simulazioni

L'attivazione dei prezzi richiede il pacchetto Open API Spotware dentro il **venv dell'utente REMURA**. Il normale installer Ubuntu NON installa automaticamente dipendenze Python di terzi, quindi verificare separatamente l'SDK prima di abilitare cTrader.

La raccolta usa gruppi di massimo **5 strumenti ogni quarto d'ora**. Se uno strumento non ha ancora storico, chiede 21 giorni di M15, altrimenti recupera 2 giorni e unisce le sole candele chiuse. I 35 mercati ruotano in 7 cicli, fino a circa 105 minuti tra due tentativi per lo stesso strumento, evitando 35 × 30 richieste che superavano il timeout di 5 minuti. I ticker dipendono dal broker e si configurano, se necessario, in `/opt/remura/private/ctrader-symbols.json` senza caricare dati su GitHub.

Le Impostazioni mostrano lo stato sicuro `/private-api/health` con `ctraderPreflight.sdk`, `ctraderPreflight.configuration`, eventuale errore categorizzato e mercati presenti. **Nessun token, ID conto o password viene restituito dalla API.** Una connessione funzionante si conferma soltanto quando `instruments` contiene strumenti con candele reali.

Nota: modifiche a `scripts/` richiedono l'installazione controllata da Termius; il timer v1.7 non aggiorna automaticamente il backend sensibile.


---
## v1.9 · Diagnostica del protocollo cTrader senza credenziali

La risposta `no_data` della v1.8 non identifica la fase di errore. La v1.9 associa ogni richiesta Spotware a una fase enumerata (`application_auth`, `account_list`, `account_auth`, `symbols_list`, `symbol_details`, `trendbars`) e classifica le eccezioni con un elenco fisso di nomi tecnici. Non registra messaggi, contenuti JSON/protobuf, token, identificativi account, URL privati o testi di eccezioni non verificati. La diagnostica viene restituita nella voce `lastError` di `/private-api/health` e si legge in Impostazioni → Diagnostica cTrader. Questa versione non modifica né rigenera autorizzazioni OAuth.

Un `SDK installato / OAuth ready` indica solo che il programma trova i pacchetti e la configurazione; il successo dell'autorizzazione e della raccolta si verifica soltanto osservando nuove candele M15 con un timestamp recente. Essendo una modifica a `scripts/`, richiede un aggiornamento manuale approvato dalla VPS.
