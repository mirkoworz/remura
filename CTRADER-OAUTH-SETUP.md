# REMURA — attivazione cTrader OAuth privata (iPhone + Tailscale)

Questa procedura **non richiede acquisti né MetaApi**. Il codice e i test sono
preparati; l'accesso reale dipende dall'approvazione dell'app sul portale
Spotware e dal conto di un broker cTrader abilitato.

## Stato e prerequisiti

- Fino allo stato **Approved** sul portale https://openapi.ctrader.com/,
  non attivare il raccoglitore. "Submitted" non equivale a "Approved".
- Usa prima un conto **demo**, senza abilitare ordini.
- REMURA privata deve essere già in esecuzione sul server con
  `127.0.0.1:8765` e Tailscale **Serve** in HTTPS (non Funnel).
  Vedi [ORACLE-ALWAYS-FREE.md](ORACLE-ALWAYS-FREE.md).
- Occorre un **solo** hostname HTTPS Tailscale, per esempio
  `https://nome-server.nome-tailnet.ts.net`. Non inserire credenziali
  nel frontend, nella chat, nei commit o in GitHub Secrets.
- Il repo `mirkoworz/remura` è pubblico: Tailscale protegge soltanto il
  servizio personale, non la pubblicazione su GitHub Pages.

## 1 — Redirect URI ufficiale

Sul portale cTrader Open API, nell'app **approvata** aggiungi esattamente:

```text
https://NOME-SERVER.NOME-TAILNET.ts.net/private-api/ctrader/callback
```

Sostituisci il dominio con l'indirizzo reale mostrato dal comando
`sudo tailscale serve status`. Usa quel medesimo URL nella configurazione:
per OAuth deve corrispondere **esattamente**, compreso il percorso.

La connessione funziona esclusivamente con una callback HTTPS su dominio
`.ts.net`. Non aprire la porta 8765 verso Internet.

## 2 — Configurazione privata sul server

Nel file `/opt/remura/private/remura.env` gestito da systemd
(permessi 0600, utente `remura`), imposta **solo sul server**:

```ini
CTRADER_CLIENT_ID=IL_TUO_CLIENT_ID
CTRADER_CLIENT_SECRET=IL_TUO_CLIENT_SECRET
CTRADER_REDIRECT_URI=https://NOME-SERVER.NOME-TAILNET.ts.net/private-api/ctrader/callback
CTRADER_OAUTH_ENABLED=1
CTRADER_ENV=demo
REMURA_COLLECTOR_ENABLED=0
REMURA_SYMBOLS=EURUSD,XAUUSD
```

Non aggiungere `scope=trading`: REMURA richiede esclusivamente
`scope=accounts` (sola lettura). Il server mantiene
`REMURA_COLLECTOR_ENABLED=0` finché non è configurato anche l'ID conto.

Dopo aver installato i file aggiornati su Oracle, installa la dipendenza
ufficiale una volta sola:

```bash
sudo -u remura /opt/remura/.venv/bin/python -m pip install ctrader-open-api
sudo systemctl restart remura-private
```

L'aggiornamento su GitHub **non** installa automaticamente i file su Oracle.

## 3 — Autorizza dal tuo iPhone, senza copiare token

Con l'iPhone collegato alla **tua** rete Tailscale, apri in Safari:

```text
https://NOME-SERVER.NOME-TAILNET.ts.net/private-api/ctrader/start
```

REMURA genera un consenso temporaneo nel browser e ti reindirizza al
login ufficiale `id.ctrader.com`. Autorizza **solo** il conto demo e il
permesso di lettura. Il browser torna sul server privato, che riceve e scambia
il codice OAuth **prima che scada (circa 60 secondi)** e salva i token in
`/opt/remura/private/ctrader-tokens.json` con permessi 0600.

Non copiare il codice, il Client Secret o i token nel telefono, in screenshot
o in chat. Il consenso temporaneo usa un cookie Secure/HttpOnly/SameSite=Lax,
valido 5 minuti e utilizzabile una sola volta. Senza cookie o dopo la scadenza
non vengono accettati codici.

Il messaggio finale deve dire che i token sono salvati, senza mostrarli.
Conferma la presenza del token aprendo:

```text
https://NOME-SERVER.NOME-TAILNET.ts.net/private-api/health
```

Cerca `"ctraderTokenStored": true`. Questo verifica che il server abbia
memorizzato il token, **non** che il broker stia già inviando prezzi.

## 4 — Attiva la prima prova prezzi

Serve l'**ID Open API ctidTraderAccountId** del conto autorizzato,
che non è necessariamente il numero di login del terminale.
Si ottiene dalla risposta ufficiale `ProtoOAGetAccountListByAccessTokenReq`.
Non inventare l'ID e non scegliere automaticamente un conto live.

Configura nel file privato:

```ini
CTRADER_ACCOUNT_ID=ID_API_DEL_TUO_CONTO_DEMO
REMURA_COLLECTOR_ENABLED=1
REMURA_SYMBOLS=EURUSD,XAUUSD
```

Riavvia `sudo systemctl restart remura-private`. Dopo la raccolta, verifica
`/private-api/health` e gli endpoint:

```text
/private-api/prices/EURUSD
/private-api/prices/XAUUSD
```

Il sistema controlla quali simboli il broker espone realmente. Se l'oro
si chiama diversamente, inserisci il nome **verificato** soltanto nel file
`/opt/remura/private/ctrader-symbols.json`, ad esempio:

```json
{"XAUUSD":"NOME_ESATTO_DEL_BROKER"}
```

Se il feed non risponde o il conto non è autorizzato, REMURA mostra N/D,
senza inventare quotazioni e senza eseguire ordini. Solo dopo il test sui
due strumenti allargheremo `REMURA_SYMBOLS` agli altri mercati.

## Sicurezza e test

La callback è disponibile **solo nel server privato**. È una nuova rotta
dell'applicazione Python, **non** della versione pubblica su GitHub Pages.
Non usare Tailscale Funnel né aprire la porta 8765 verso Internet.
Conserva il file token fuori da Git e, se un dispositivo viene compromesso,
revoca l'autorizzazione dell'app dal cTID.

Verifica offline:

```bash
python -m unittest discover -s tests -p 'test_ctrader_oauth.py' -v
python -m unittest discover -s tests -p 'test_ctrader_tokens.py' -v
python -m unittest discover -s tests -p 'test_ctrader_feed.py' -v
```

Riferimenti ufficiali:
- https://help.ctrader.com/open-api/api-application/
- https://help.ctrader.com/open-api/account-authentication/
- https://github.com/spotware/OpenApiPy

**Stato della prima prova reale:** in attesa dell'approvazione Spotware,
della VM privata configurata e dell'autorizzazione cTrader.
