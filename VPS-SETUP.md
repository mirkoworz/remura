# REMURA su VPS privato — guida Ubuntu 24.04

**Stato:** preparazione su PR #2, non ancora installato su un VPS. Nessun abbonamento, IP o server è stato acquistato/creato da ChatGPT. La versione pubblica GitHub Pages v0.9 resta separata: disattivarla prima di utilizzare dati personali. Repository `mirkoworz/remura` ancora pubblico alla data di preparazione: rendilo privato quando avrai completato la migrazione e verifica il collegamento GitHub di ChatGPT.

## Architettura

- VPS Linux x86-64 online 24/7, consigliato Ubuntu 24.04 LTS e almeno 2 vCPU / 4 GB RAM.
- Python `scripts/private_server.py` su **127.0.0.1:8765** come servizio `systemd`, account Linux dedicato senza shell `remura`.
- Tailscale Serve solo nella tua tailnet: HTTPS privato aperto da Safari su iPhone con Tailscale VPN attivata. **Non** usare Tailscale Funnel, Cloudflare Quick Tunnel o port forwarding.
- SQLite nel percorso `/opt/remura/private/remura-prices.sqlite3`, credenziali/tokens nella directory privata `/opt/remura/private/`, fuori dal repository.
- Dopo approvazione cTrader e OAuth `scope=accounts`, recupero M15 automatico ogni 15 minuti, raccolta Myfxbook ogni 20 minuti se abilitata; COT settimanale tramite fonte CFTC già presente nelle schede.
- La cartella `/opt/remura` contiene il codice proprietario amministrato da root: soltanto `/opt/remura/private` è scrivibile dal processo REMURA.

## 1. Creare il VPS (pannello provider)

Per iniziare si può scegliere [Hetzner Cloud](https://console.hetzner.cloud/) in Germania, server **CX23** (2 vCPU, 4 GB RAM, 40 GB) se disponibile; in caso di stock esaurito scegliere un server **x86-64** equivalente o superiore, non passare arbitrariamente a ARM. La tariffa CX23 in Europa dal 15 giugno 2026 è **€5,49/mese, IVA e IPv4 esclusi**, verificare il totale nel pannello prima del pagamento. Non è necessario comprare un dominio.

Nel pannello:
1. Crea un progetto `REMURA`, quindi **Servers → Add server**.
2. Seleziona regione Germania/Europa, **Ubuntu 24.04 LTS**, categoria Shared vCPU x86-64 e tipo CX23 (o equivalente con almeno 2 vCPU/4GB).
3. Dai nome `remura-vps`; se possibile configura una **chiave SSH pubblica** (mai inviare una chiave privata). Per semplicità iniziale usa IPv4 se necessario per la tua connessione SSH; il costo può essere aggiuntivo.
4. Configura la firewall cloud del provider: **nessuna porta HTTP 80/443 o 8765 pubblica**. Consenti SSH porta 22 solo dal tuo IP attuale, se lo conosci. Se utilizzi la console web del provider per il bootstrap, dopo aver verificato Tailscale puoi evitare ingressi SSH da Internet. Non chiudere SSH fino a quando non avrai verificato un altro accesso amministrativo al VPS.
5. Verifica il totale e conferma il server. La macchina sarà fatturata finché non la elimini, anche se spenta: consulta le condizioni del provider.

Documentazione: https://docs.hetzner.com/cloud/servers/getting-started/creating-a-server/

## 2. Preparare codice e avvio automatico

Dalla console Ubuntu del server o via SSH, scarica il ramo **di sviluppo** (non `main`!) e lancia lo script già incluso nel progetto. Se il repository è diventato privato usa una chiave di distribuzione GitHub **read-only** configurata direttamente sul VPS, mai token in chat/URL.

```bash
git clone --branch feature/private-price-engine-v10 --single-branch https://github.com/mirkoworz/remura.git
cd remura
sudo bash deploy/bootstrap-ubuntu.sh
curl --fail http://127.0.0.1:8765/private-api/health
```

Lo script prepara Ubuntu, un account `remura`, ambiente virtuale Python, SDK ufficiale Spotware, installa il servizio `systemd` con riavvio automatico e configurazione isolata. Non apre porte, non installa un broker terminale e lascia raccolta cTrader/Myfxbook **disattivata per impostazione predefinita**.

Verifica:

```bash
sudo systemctl status remura-private --no-pager
sudo journalctl -u remura-private -n 40 --no-pager
```

Non copiare mai credenziali nei messaggi, nel repository, nei log o nelle schermate.

## 3. Accedere su iPhone usando Tailscale Serve (solo rete privata)

- Crea un account [Tailscale Personal](https://tailscale.com/), utilizzando lo stesso login sul VPS e sull'iPhone. Il piano Personal è gratuito per uso personale, in base ai termini vigenti.
- Sul VPS installa Tailscale secondo la [guida Linux ufficiale](https://tailscale.com/docs/install/linux), poi esegui `sudo tailscale up --hostname=remura-vps` e conferma il login nel browser sul tuo dispositivo.
- Attiva le opzioni HTTPS richieste dalla tua tailnet, quindi esegui **sul VPS** `sudo tailscale serve --bg 8765` e `tailscale serve status`. Copia l'indirizzo HTTPS `https://remura-vps.<nome-tailnet>.ts.net` mostrato da Tailscale.
- Installa l'app ufficiale Tailscale sul tuo iPhone, accedi con **lo stesso account**, abilita la VPN, quindi apri l'indirizzo HTTPS in Safari. Il sito resta raggiungibile soltanto all'interno della tailnet (e da altri dispositivi che eventualmente autorizzerai).
- Imposta le regole di accesso della tailnet per consentire solo i tuoi dispositivi. **Serve** è privato; **Funnel** è pubblico.
- In Safari puoi usare **Condividi → Aggiungi alla schermata Home** per installare REMURA come web app.

Guide: https://tailscale.com/docs/features/tailscale-serve e https://tailscale.com/docs/reference/tailscale-cli/serve

## 4. Dopo l'approvazione Spotware: autorizzazione read-only e raccolta

Quando lo stato dell'app `REMURA Personal` diventa `Approved`, completa prima il flusso OAuth **`scope=accounts`** dalla tua connessione protetta. Non scegliere `scope=trading`.

Apri solo **sul VPS** il file `/opt/remura/private/remura.env` con un editor amministrativo, senza committarlo su Git. Riempi con gli identificativi e token generati dal tuo account (non trasmetterli in chat). Devi impostare:
- `REMURA_COLLECTOR_ENABLED=1`
- `CTRADER_CLIENT_ID`, `CTRADER_CLIENT_SECRET`, `CTRADER_REFRESH_TOKEN` e `CTRADER_ACCOUNT_ID` (quest'ultimo è l'ID API del conto autorizzato)
- `CTRADER_ENV=demo` o `live` in base al conto concesso
- `REMURA_SYMBOLS=EURUSD,XAUUSD,US500` per i primi controlli; dopo verifica passare a `all`.

Il collector salva i token rinnovati localmente, non permette ordini, recupera i simboli dal tuo broker e mette `N/D` quando non trova un mercato. Non inventiamo una corrispondenza fra futures CFTC e CFD del broker.

Per Myfxbook, sempre sul VPS, aggiungi `REMURA_RETAIL_ENABLED=1`, `MYFXBOOK_EMAIL` e `MYFXBOOK_PASSWORD`. Riavvia `sudo systemctl restart remura-private`.

Le API visibili **solo attraverso Tailscale**:
- `/private-api/health` — stato del collector.
- `/private-api/prices/EURUSD` — candele confermate per un mercato.
- `/private-api/retail/latest.json` — ultimo snapshot Myfxbook.
- `/private-api/retail/history/EURUSD.json` — storico retail del mercato.

**La raccolta non è ancora stata verificata contro un conto cTrader reale:** servono approvazione dell'app, token autorizzati, e il VPS operativo.

## 5. Mantenere la macchina sicura, aggiornare e fare backup

- Configura gli aggiornamenti di sicurezza Ubuntu e un firewall cloud: lascia chiuse tutte le porte web pubbliche. Tailscale si collega in uscita.
- Non disattivare l'accesso di gestione al server prima di aver verificato login alternativo via Tailscale oppure console cloud.
- Attiva backup o snapshot del VPS presso il provider: hanno un costo potenzialmente aggiuntivo. SQLite, storia retail e token di accesso sono dati privati; un backup deve essere protetto e conservato fuori dal server.
- Per aggiornare il codice, prima revisiona il ramo GitHub e poi usa `sudo bash deploy/update-ubuntu.sh` dalla cartella di checkout aggiornata; il comando preserva la cartella privata.
- Se il VPS si ferma, `systemd` tenta il riavvio del servizio; non garantisce da solo disponibilità di rete, feed del broker o assenza di manutenzione Spotware.

## Verifica finale e stato attuale

Lo script e il servizio sono stati predisposti come **codice testabile**, non c'è ancora alcun account VPS collegato. Finché non crei il server, non è tecnicamente possibile verificare il login da Safari né simulare l'approvazione cTrader. Non fare merge della PR #2 sul sito pubblico: la pagina GitHub Pages corrente è ancora pubblica e la versione privata usa percorsi backend che GitHub Pages non esegue.
