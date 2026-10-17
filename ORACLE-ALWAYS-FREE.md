# REMURA personale — installazione su Oracle Always Free

Questa guida si riferisce **solo** al ramo `fix/private-multisource-v11` (proposta PR #3), costruito sopra la v1.0 privata (PR #2). **Non fare merge su `main` e non pubblicare su GitHub Pages:** il sito pubblico e la VM sono ambienti diversi.

## 1. Crea l'account Oracle e la macchina gratuita

- Vai a https://www.oracle.com/cloud/free/ e seleziona l'account gratuito, **non Pay As You Go**. La verifica dell'identità può richiedere una carta. Controlla tutti gli addebiti/piani prima di confermare.
- Scegli attentamente la **home region**: le risorse Always Free vanno create lì. Una volta scelta, la regione principale non è liberamente trasferibile.
- Dalla console: **Compute → Instances → Create instance**.
- Nome: `remura-private`. Immagine: Ubuntu Server 24.04 **aarch64/ARM64** (o altra release Ubuntu ARM64 supportata).
- Shape: **VM.Standard.A1.Flex**, con etichetta **Always Free eligible**; inizialmente **1 OCPU, 6 GB RAM**. Il limite Always Free corrente complessivo è **2 OCPU e 12 GB RAM** (valido entro le ore e i GB-hour previsti dal piano), non una garanzia di capacità.
- Disco: dimensione predefinita che rientri nel piano Always Free. Verifica l'etichetta **Always Free** e il riepilogo costi **prima** di confermare.
- Rete: consenti solo ciò che serve a SSH, senza ingressi 80/443/8765 verso Internet. Si può usare un IP pubblico per bootstrap SSH, ma **REMURA non deve ascoltare pubblicamente**. Imposta chiavi SSH, preferibilmente proprie; custodisci in privato la chiave privata.
- Se compare `Out of host capacity`, prova un altro *availability domain* nella stessa home region; non passare automaticamente a una forma a pagamento.

Fonti: https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm e https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/connect-to-linux-instance.htm

**Attenzione:** Oracle può recuperare le istanze Always Free ritenute inattive. Non creare carichi fittizi per evitare questa politica: prevedi backup privati fuori dalla VM.

## 2. Collegati alla VM via SSH

Da terminale o OCI Cloud Shell, usando la tua chiave SSH (con Ubuntu la login predefinita è normalmente `ubuntu`):

```bash
ssh -i /percorso/chiave_privata ubuntu@INDIRIZZO_IP_DELLA_VM
```

**Non condividere** indirizzi di accesso personali, chiavi, password o token. La console Oracle Cloud Shell supporta anche collegamenti tramite rete privata VCN, ma il procedimento può cambiare rispetto a SSH pubblico. Vedi https://docs.oracle.com/en/learn/access-oci-linux-instance/

## 3. Installa REMURA in modo controllato

Esegui sulla VM (non su Cloud Shell locale):

```bash
git clone --single-branch --branch fix/private-multisource-v11 https://github.com/mirkoworz/remura.git
cd remura
sudo bash deploy/oracle/install.sh
sudo systemctl --no-pager status remura-private
curl -fsS http://127.0.0.1:8765/private-api/health
```

Il bootstrap crea un utente di sistema non privilegiato `remura`, copia il codice in `/opt/remura` **senza sincronizzare cartelle private o file di segreti**, crea l'ambiente Python e un servizio systemd che ascolta soltanto su `127.0.0.1:8765`. All'inizio tutti i raccoglitori sono **disabilitati**, così niente account o sorgenti esterne vengono usati di nascosto.

Il codice dell'applicazione non richiede dipendenze Python esterne per funzionare come server e per Myfxbook/IG; per cTrader occorre il pacchetto `ctrader-open-api` e l'autorizzazione OAuth in sola lettura. Questo non attiva operazioni automatiche.

## 4. Accesso privato HTTPS dall'iPhone — Tailscale Serve

Sulla VM:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
sudo tailscale serve --bg 8765
sudo tailscale serve status
```

Se preferisci, installa Tailscale tramite i pacchetti della distribuzione invece dello script. Quando `tailscale up` mostra un URL, autentica il **tuo** account. L'HTTPS su Serve deve essere abilitato per la tailnet. Installa Tailscale anche sull'iPhone, accedi allo stesso account, attiva la VPN e apri l'indirizzo `https://nome-vm.nome-tailnet.ts.net` mostrato da `tailscale serve status`.

**Usa Serve, non Funnel**. Serve è interno alla tailnet; Funnel renderebbe l'app raggiungibile pubblicamente. Non aprire la porta **8765** sul firewall OCI. Riduci le policy d'accesso della tailnet ai soli tuoi dispositivi.

Fonti: https://tailscale.com/docs/install/linux e https://tailscale.com/docs/reference/tailscale-cli/serve

## 5. Abilita i feed uno alla volta, solo con le tue credenziali locali

Dopo avere confermato che il server e l'iPhone si vedono, modifica il file privato:

```bash
sudo nano /opt/remura/private/remura.env
```

Esempio **senza valori segreti**:

```ini
REMURA_RETAIL_ENABLED=1
REMURA_IG_ENABLED=0
REMURA_COLLECTOR_ENABLED=0
IG_ENV=demo
```

Per Myfxbook aggiungi `MYFXBOOK_EMAIL` e `MYFXBOOK_PASSWORD` solo sul server; per IG servono inoltre `IG_API_KEY`, `IG_IDENTIFIER`, `IG_PASSWORD` ed `REMURA_IG_ENABLED=1` dopo aver verificato termini e permessi. Per cTrader rimanda a `PRIVATE-AUTOMATION.md`.

```bash
sudo chmod 600 /opt/remura/private/remura.env
sudo systemctl restart remura-private
sudo systemctl --no-pager status remura-private
```

Per i primi controlli visita gli endpoint privati `/private-api/health`, `/private-api/retail/latest.json` e `/private-api/ig/latest.json`. È **normale** vedere 503 sui feed non configurati: nessun dato fittizio.

## 6. Sicurezza, backup e aggiornamenti

- Non rendere `/opt/remura/private` disponibile come asset del web server o su GitHub, neppure in un repository privato; conserva le credenziali solo nella VM.
- La VM ha bisogno di accesso Internet in uscita. Per SSH usa chiavi e limita le regole di ingresso; una volta configurato Tailscale puoi restringere ulteriormente SSH secondo le tue necessità.
- Conserva un **backup cifrato esterno** del database `/opt/remura/private/remura-prices.sqlite3` e degli storici dei sentiment. Non conservare backup contenenti i token in chiaro.
- Per aggiornare il codice in sicurezza, scarica/controlla la nuova versione in un checkout separato, poi riesegui l'installer. **Non esegue merge di branch e non aggiorna automaticamente il software.**
- Verifica l'uso delle risorse nella console Oracle: la gratuità dipende da forma, storage, traffico e altre risorse.
