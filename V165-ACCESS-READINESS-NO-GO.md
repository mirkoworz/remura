# REMURA v1.65 — C4b(l), decisione di accesso privato: PREPARAZIONE SENZA ATTIVAZIONE

**Checkpoint: 8 novembre 2026. Stato: NO-GO per accesso nuovo, SSH, rilascio e raccolta C5.**
Questo file è una scheda operativa per il proprietario. Non contiene segreti, indirizzi privati, chiavi, OCID o comandi da eseguire sulla VPS. È soltanto nella PR #98 DRAFT; non installa alcuna GitHub Action.

## 1. Cosa sappiamo già, senza ripetere controlli

- I repository sono `mirkoworz/remura` (pubblico) e `mirkoworz/remura-collector` (privato, main; ID GitHub 1424422834). La PR #98 conserva il template sotto `deploy/oracle/templates/`, **non** in `.github/workflows/`. Il Filone B è PR #89 DRAFT; il Filone C è PR #97 DRAFT.
- Nel collector esiste il workflow manuale di diagnostica `remura-vps-diagnostic.yml`: Tailscale HTTPS/443, sole GET, nessun SSH né accesso diretto ai file. Questo conferma solo ciò che espongono gli endpoint, **non** l'identità indipendente dei 15 file installati.
- Il modello futuro fissa checkout e Tailscale Action a commit specifici, il checksum pubblico del tarball Tailscale 1.104.4 Linux amd64, l'identità del verificatore locale e la ricezione strettamente limitata. Il gate remoto forzato `v165_pinned_ssh_forced_gate_REVIEW_ONLY.py` è preparato ma **non installato**.
- Checkpoint CI verificato prima di questo documento: 344/344 test offline v1.65 in 12 suite, Price Engine #42516947113 e Insights #42516947089 SUCCESS. Nessun test attesta il server, l'utente SSH, le ACL o i prezzi reali del mercato.

## 2. Percorsi possibili, non equivalenti

**A — Restare su diagnostica HTTPS esistente (nessun nuovo accesso).** Non richiede cambiare porte, ACL o utente SSH. Può confermare metriche e versione dichiarate, quando l'operatore autorizzerà un run manuale già esistente. **NON** dimostra i 15 hash autonomamente: non consente quindi di sbloccare la v1.65 sulla base di quelle sole GET.

**B — Audit SSH protetto dei soli 15 file (prospettiva completa, non attivo).** Richiede modifica separata della configurazione Tailscale e della VPS. Quando e solo quando autorizzato, il runner effimero potrà trasmettere un verificatore immutabile via SSH all'utente dedicato non privilegiato. Sul server il forced-command deve essere root-owned e deve confrontare l'esatto Git blob **prima di eseguire** il codice ricevuto. Il client da solo non rende sicuro il servizio SSH.

## 3. Gate preliminari, controllabili da console senza usare Termius

| Gate | Evidenza richiesta | Stato adesso |
|---|---|---|
| GitHub piano/costi | Verificare piano reale, quote Actions private, consumo mensile e budget con blocco alla soglia; nessun acquisto | NON ATTESTATO |
| Tailscale piano/quote | Verificare fatturazione attuale, uso effimero, tag e compatibilità d'uso: il Personal gratuito è dichiarato per uso **non commerciale** | NON ATTESTATO |
| Tailscale policy globale | Controllare l'intera ACL/grants esistente, assenza di regole allow-all che vanificherebbero la nuova restrizione; non ampliare `tag:remura-ci-read` (HTTPS/443) | NON ATTESTATO |
| Federazione OIDC futura | Nuova identità e `tag:remura-ci-v165-audit`, vincoli GitHub repo/visibilità/branch/evento/workflow sul solo job manuale | NON CONFIGURATO |
| Accesso host | Solo VPS specifica TCP/22 sulla tailnet; nessuna apertura Internet; host key verificata fuori banda | NON ATTESTATO |
| SSH server | Utente specifico non-root senza sudo e senza accesso a SQLite/segreti; authorized_keys `restrict` + forced command esatto installato come root e verificato | NON INSTALLATO |
| Consenso workflow | Workflow manuale, owner/repo ID fissati, input booleano default OFF, variabile di abilitazione default OFF, no rerun: **solo preparati nel template** | NON INSTALLATO |
| Integrità produzione | Hash reali dei 15 file leggibili senza privilegi, versione della VPS e controllo autoupdater indipendente | NON MISURATO |
| Backup e ripristino | SQLite consistente con restore-test fuori host, rollback verificato prima del rilascio | NON ESEGUITO |
| Oracle | Classe account/Always Free, fatturazione, quote effettive, inode/spazio; niente nuove VM, policy o pagamenti | NON CERTIFICATO |

**Se un gate di accesso è incerto: STOP.** Non risolvere dando sudo/root, aggiungendo `0.0.0.0/0`, espandendo vecchi tag Tailscale, pubblicando il repo privato o aggirando policy. Mai inviare chiavi SSH, token, hostname privati, PE​M o OCID in chat o commit.

## 4. Scelta gratuita e limiti reali

- [GitHub Environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments): i **required reviewers** per repo privati non sono disponibili sui piani Free/Pro/Team. La via owner-only del template è una doppia conferma, **non** una revisione da un secondo soggetto. Non creare fittizi environment protetti.
- [GitHub Actions Billing](https://docs.github.com/en/actions/concepts/billing-and-usage): per repository privati valgono i limiti di calcolo/storage del piano. La quota reale residua non è consultabile in questo preflight; non inferire 0€ da run verdi. Controllare anche la [guida ai budget](https://docs.github.com/en/billing/managing-your-billing/using-budgets-control-spending).
- [Tailscale Pricing](https://tailscale.com/pricing): piano Personal gratuito per uso non commerciale; il listino pubblico riporta limiti sulle risorse effimere (1.000 minuti/mese al checkpoint), utenti e tag. Verificare **piano e uso reale** prima di aggiungere un runner. Eventuale futura monetizzazione di REMURA potrebbe richiedere una scelta diversa, non presumere idoneità del Personal.
- [Tailscale GitHub Action](https://tailscale.com/docs/integrations/github/github-action): un nuovo OIDC federato e tag devono essere creati prima di poter accedere. [Tailscale Grants](https://tailscale.com/docs/features/access-control/grants): nuove regole ristrette non eliminano automaticamente altri permessi già concessi.
- [OpenSSH authorized_keys](https://man.openbsd.org/sshd): `restrict` limita forwarding/PTY, il forced command riceve `SSH_ORIGINAL_COMMAND`; un semplice `command="python3 -"` sarebbe insufficiente senza controllo dei byte eseguiti. Non installare un key-gate non revisionato.

## 5. Ordine delle autorizzazioni future — SEMPRE SEPARATE

**Fase 0: consultazione da console, senza modifiche.** Il proprietario verifica piano/quote GitHub, piano/uso Tailscale, policy globale Tailscale e stato account OCI. Non condivide segreti. I run storici già verdi non si ripetono solo per ottenere un altro verde.

**Fase 1: consenso specifico alla configurazione di rete.** Soltanto dopo approvazione esplicita: nuova OIDC/tag con ACL minima solo su un host/porta 22. Non cambiare il tag HTTPS esistente, non accedere ancora alla VPS.

**Fase 2: consenso specifico alla preparazione del server.** Solo dopo audit costi e rischio, creare account non-root, forced-command root-owned e host key confermata. Backup e piano di rollback **prima** di qualsiasi modifica server. Nessuna scrittura o attivazione automatica in questa documentazione.

**Fase 3: consenso specifico a UN audit read-only dei 15 file.** Un solo workflow manuale controllato, nessuna diagnostica privata grezza nei log; il risultato prova soltanto la corrispondenza dei 15 file nello specifico istante. Non attesta updater/backup/Oracle.

**Fase 4: rilascio v1.65, separato dalla fase 3.** Soltanto dopo prova backup/restore SQLite, rollback, baseline attuale, quote e autorizzazione espressa. La release deve stampare numero versione e data/ora reali italiane su tutte le nove pagine. C5 resta un'altra autorizzazione, e i dati prospettici non vanno confusi con prove sintetiche.

**Decisione adesso:** preparazione completata, NO-GO SSH/VM/VPS/release/C5, nessuna credenziale o costo attivati. Il prossimo punto efficace è raccogliere le sole quattro evidenze di console della Fase 0 e valutare se il percorso gratuito sia davvero percorribile.

## 8 novembre 2026 — Evidenza visiva Tailscale ACL dell'operatore (sola lettura)

L'operatore ha mostrato la schermata reale **Policies → General access rules** di Tailscale con **due regole espanse**. Contenuti registrati senza hostname/IP private, credenziali o altri identificativi:

1. `src: ["autogroup:member"], dst: ["autogroup:self"], ip: ["*"]`. Secondo la documentazione ufficiale Tailscale, `self` significa **solo dispositivi posseduti dalla stessa persona**, non qualunque dispositivo dell'intera tailnet. La selezione `autogroup:self` **non si applica a dispositivi taggati**. L'asterisco concede tutte le porte soltanto entro quell'ambito di identita'.
2. `src: ["tag:remura-ci-read"], dst: ["singolo dispositivo della VPS"], ip: ["tcp:443"]`. E' coerente con la diagnostica CI HTTPS/443 esistente; **nessuna autorizzazione SSH/22** per il tag della CI e nessun tag `remura-ci-v165-audit` appare nelle due regole mostrate.

**Esito di questa specifica evidenza:** `TAILSCALE_VISIBLE_GRANTS=SCOPED_NOT_GLOBAL_ALLOW_ALL`. La vecchia ipotesi che `member → self → *` fosse un vero `* → * → *` e' stata esclusa per queste due regole. **Non** e' ancora un audit dell'intera policy (altre ACL/grants, SSH tab, tag ownership, OIDC e varianti policy possono aggiungere accessi) e non prova che l'host abbia SSH sicuro. Non modificare o eliminare regole esistenti. Tailscale `Access Controls` e `Tailscale SSH` restano oggetti di verifica distinti.

Fonti: [Tailscale selectors, autogroup:self](https://tailscale.com/docs/reference/targets-and-selectors), [Tailscale grant examples](https://tailscale.com/docs/reference/examples/grants) e [policy file reference](https://tailscale.com/docs/reference/syntax/policy-file). Nessuna modifica tailnet/collector/VPS, nessun accesso remoto o costo generato.

**Rimane da verificare prima di qualsiasi nuova connessione:** piano e uso Tailscale, tag ownership/autoapprovers, ACL complete e Tailscale SSH, OIDC claim mapping futuro; indipendentemente GitHub Actions quota/costi e Oracle Always Free; account SSH nonroot/forced gate/server key e, solo con via libera separato, hash LIVE/backup/rollback. `SSH_AUDIT=NO_GO`, `V165_RELEASE=NO_GO`, `C5=NO_GO`.

## 8 novembre 2026 — Evidenza Tailscale SSH check su self (sola lettura)

Nuove schermate dell'operatore da **Policies → Tailscale SSH** mostrano una regola SSH (senza secret o indirizzi):

```json
{ "action": "check", "src": ["autogroup:member"], "dst": ["autogroup:self"], "users": ["autogroup:nonroot", "root"] }
```

**Interpretazione verificata dalla documentazione Tailscale** ([Tailscale SSH](https://tailscale.com/docs/features/tailscale-ssh)): questa e' la **regola SSH predefinita**. La sorgente sono membri; la destinazione sono soltanto i **dispositivi posseduti dallo stesso utente**, non tutti gli host taggati. Sono ammessi come *possibili account di destinazione* `root` e altri utenti non-root che esistano sul dispositivo. `check` richiede re-autenticazione periodica dell'utente (tipicamente 12 ore); non e' un permesso automatico root per la CI. La regola, da sola, **non dimostra** che il servizio Tailscale SSH sia abilitato sulla VPS o che SSH esposto sia OpenSSH/Tailscale SSH.

**Separazione critica dei protocolli:** il modello futuro `v165-private-ssh-audit-REVIEW-ONLY.yml` usa un tradizionale client SSH con chiave e `UserKnownHostsFile` + forced command `authorized_keys` previsto sul server. Tailscale SSH e' un servizio *diverso* che, se abilitato sul nodo, prende la porta TCP/22 della tailnet e gestisce l'autenticazione senza rispettare l'`authorized_keys` di OpenSSH per le connessioni Tailscale SSH. **NON usare il nostro modello con Tailscale SSH abilitato sulla VPS** credendo che la chiave/forced-command lo contenga. L'eventuale via SSH autorizzata richiede verificare da console/stato nodo che il flusso sia **OpenSSH tradizionale sopra la rete Tailscale**, oppure riprogettare il sistema e rifare una revisione indipendente: non abilitarlo per sbloccare i test.

**Decisione:** la regola attuale e' `action:check` per `member→self`; **non** concedere automaticamente root alla CI e **non modificare** la policy Tailscale SSH in questa fase. Le due regole General access rules visibili in precedenza restano l'unica evidenza network: `member→self:*` e `tag:remura-ci-read→solo HTTPS/443` senza SSH. Nessuna prova di OIDC/ACL nuove, account dedicato, host-key, backup, quote o prova file LIVE. `SSH_AUDIT=NO_GO`, `V165_RELEASE=NO_GO`, `C5=NO_GO`.

**Prossimo controllo operativo innocuo:** pagina Machines della console Tailscale, cercare la VPS e verificare **soltanto lo stato di Tailscale SSH / owner/tag**. Se si condivide una schermata, oscurare nome dispositivo, IP/tailnet e dati identificativi; mai inviare chiavi, token o indirizzi. Non cambiare toggle. In alternativa continuare con la diagnostica HTTPS/443 già presente. Nessun comando o run remoto eseguito per questo checkpoint.

## 8 novembre 2026 — Evidenza Machines remura-server, stato online (sola lettura)

L'operatore ha condiviso quattro schermate della console Tailscale **Machines** e della pagina dettagli di `remura-server`. Evidenza visuale: **due dispositivi** elencati (iPhone personale e VPS REMURA); VPS **Connected**, gestita dall'account proprietario, con `node:os=linux`, Tailscale client `1.104.2` stable; `node:tsAutoUpdate=true`, `node:tsStateEncrypted=false`; chiave di macchina con scadenza riportata circa cinque mesi dopo la consultazione; certificato TLS mostrato valido con scadenza indicativa circa due mesi; nessuna subnet route pubblicizzata. Lo stato cifratura locale `node:tsStateEncrypted=false` **non e'** la proprieta' che indica Tailscale SSH; e' una distinta considerazione di sicurezza da verificare prima di future modifiche, senza conclusioni sulla esposizione del servizio. Non trascrivere in repository IP pubblici/privati, FQDN, nodekey o identificativi visibili nelle immagini.

**Quello che non e' ancora accertato:** SSH Tailscale abilitato/non abilitato sul nodo. La pagina Machine Details mostrata **non contiene un campo leggibile Tailscale SSH**. Per ottenere una prova **senza connessioni** la documentazione ufficiale Tailscale prescrive: Machines → Filters → Property → Tailscale SSH. Se `remura-server` compare nel risultato filtrato, il nodo pubblicizza la funzione; se non compare pur essendo online nella lista generale, non risulta configurato con Tailscale SSH nel censimento di quel momento. Non premere «SSH to machine», non eseguire connessioni e non modificare la configurazione. Fonti: [Tailscale device filter](https://tailscale.com/docs/features/access-control/device-management/how-to/filter), [Tailscale SSH](https://tailscale.com/docs/features/tailscale-ssh), [device posture attributes](https://tailscale.com/docs/features/device-posture/postures-and-attributes).

**La versione runner Tailscale 1.104.4 prevista nel template audit FUTURO non coincide con la versione 1.104.2 del client gia' installato sulla VPS:** sono **due macchine diverse**; la differenza non rappresenta da sola un problema, ne' autorizza aggiornamenti del server. Nessuna chiamata Oracle, SSH, tag o ACL modificati. `SSH_AUDIT=NO_GO`, `V165_RELEASE=NO_GO`, `C5=NO_GO`.

## 8 novembre 2026, ore 21:58 italiane — Filtro Tailscale SSH: zero macchine

**Evidenza diretta dall'operatore:** nella console amministrativa Tailscale la pagina Machines, con il solo filtro **Property: Tailscale SSH** (`property:tailscale-ssh`), restituisce **0 machines / No machines match your search**. Poco prima, senza filtro, `remura-server` risultava Connected nella stessa tailnet, con due dispositivi in elenco. Questa e' evidenza specifica dell'assenza di dispositivi **segnalati come Tailscale SSH abilitati** al momento della consultazione.

**Interpretazione confermata dalla documentazione ufficiale:** [Filter devices in the admin console](https://tailscale.com/docs/features/access-control/device-management/how-to/filter) dichiara esplicitamente che la proprieta' Tailscale SSH seleziona i dispositivi con tale servizio abilitato. Si puo' quindi considerare chiuso il dubbio operativo sulla funzione **Tailscale SSH attualmente pubblicizzata dalla VPS**: non risulta abilitata. Questa constatazione non dimostra che OpenSSH sia gia' installato, attivo, in ascolto sulla tailnet o configurato in modo sicuro; non certifica alcuna futura ACL, identita' OIDC o porta 22.

**Decisione tecnica:** il percorso di progetto da valutare resta **OpenSSH tradizionale sopra Tailscale**, con un account nuovo non-root/no-sudo, chiave host verificata, ACL dedicata e forced-command root-owned che controlli esattamente il verificatore ricevuto. Tailscale SSH **NON va attivato**, perche' intercetterebbe il traffico TCP/22 sulla tailnet e non farebbe rispettare i vincoli dell'authorized_keys previsti dal nostro modello. Nessun cambio regole, niente SSH o azioni LIVE; per attivare la rete e preparare server/accesso servono autorizzazioni distinte.

**Gate chiuso:** `TAILSCALE_SSH_ON_REMURA_SERVER=NOT_ENABLED_IN_CONSOLE_SNAPSHOT` (riscontro UI puntuale, non prova perpetua). **Gate tuttora aperti:** `OPENSSH_SERVER_ATTESTED=NO`, `TAILSCALE_NEW_OIDC_ACL_ATTESTED=NO`, `NONROOT_ACCOUNT_FORCED_COMMAND=NO`, `GITHUB_TAILSCALE_QUOTAS_BILLING=UNKNOWN`, `V164_15_FILES_LIVE_VERIFIED=NO`, `SQLITE_BACKUP_OFFHOST_RESTORE=NO`, `ORACLE_ALWAYS_FREE_BILLING=UNKNOWN`. Decisione complessiva `C4b(l)=NO_GO`, `V165_RELEASE=NO_GO`, `C5=NO_GO`.

## 8 novembre 2026, ore 22:06 italiane — conferma account Free Trial e topologia VNIC Oracle, firewall ancora NON verificato

**Evidenza diretta dall'operatore (sole schermate di console, nessuna nuova chiamata Oracle):** il banner Oracle Cloud indica **Account di livello gratuito, versione di prova gratuita attiva**; in assenza di upgrade, dopo la scadenza i servizi utilizzabili saranno quelli Sempre gratis. Questo chiude la precedente classificazione `ACCOUNT_CLASS=UNKNOWN`: **`ACCOUNT_CLASS=FREE_TIER_TRIAL_ACTIVE` alla data della schermata**. Non dimostra che ogni risorsa attuale rimanga Always Free alla scadenza, né fattura futura o assenza di costi/servizi non idonei. Non fare upgrade.

**Topologia rete acquisita:** la VM REMURA nella regione home Milano mostra una VNIC primaria collegata a una **subnet pubblica** nella VCN del progetto, un IPv4 pubblico e privato, route table predefinita e campo **Network Security Groups = —**. Il controllo effettivo dell'ingresso è quindi da ricercare nelle **Security Lists associate alla subnet**, oltre alle regole firewall Linux e al routing. **La presenza di IPv4 pubblico NON prova che TCP/22 sia raggiungibile da Internet.** Nessun IP, nome proprio, domicilio o identificativo di account delle schermate viene trascritto nei documenti.

**Prossima prova in sola lettura:** nella Oracle Console: Networking → Virtual Cloud Networks → VCN della REMURA → Security Lists (oppure entrare prima nella subnet e leggere le Security Lists ad essa associate) → aprire tutte le liste effettivamente associate alla subnet → **Ingress Rules**. Registrare solo `Source CIDR`, `IP Protocol` e `Destination Port Range` della riga TCP/22, oltre a qualsiasi altra regola ingress e NSG applicabile. Se `0.0.0.0/0 → TCP/22`, l'accesso internet sarebbe **consentito dalla security list** (resta da verificare firewall host/rete); si raccomandera' piano di mitigazione con approvazione separata, **non** eliminare/modificare la regola al buio. Se manca, non inventare conferma assoluta: controllare tutte le liste della subnet e NSG della VNIC.

Fonte Oracle: [Security Lists](https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/securitylists.htm) e [Addressing Basic Configuration Issues](https://docs.oracle.com/en-us/iaas/Content/Security/Reference/configuration_tasks.htm) — le regole applicate alla subnet si sommano; una singola regola di ingresso sufficiente puo' permettere il traffico. La console non certifica da sola la configurazione del demone SSH sul server.

**Decisione:** `ORACLE_FREE_TRIAL_ACTIVE=ATTESTED_BY_UI`, `ORACLE_EACH_RESOURCE_ALWAYS_FREE=UNKNOWN`, `VNIC_PUBLIC_SUBNET=YES`, `VNIC_NSG_SHOWN=NONE`, `OCI_TCP22_INGRESS_EXPOSURE=UNKNOWN`. Nessuna modifica a rete, VNIC, subnet, IAM, SSH o VPS; C4b(l), release v1.65 e C5 restano NO-GO. Non riavviare audit OCI storici già verdi.

## 8 novembre 2026, ore 22:57 italiane — Security List ingress: due ICMP, nessun TCP/22 visibile

**Evidenza puntuale da screenshot Oracle, senza chiamate nuove:** l'operatore ha aperto la `Default Security List` della VCN REMURA, scheda `Regole di sicurezza`; la tabella **Regole di entrata** mostra `pagina 1 di 1`, esattamente **due righe** con protocollo `ICMP`. Le sorgenti visibili sono `0.0.0.0/0` e `10.0.0.0/16`, con tipi/codici ICMP `3,4` e `3`. **Nessuna regola TCP, in particolare TCP/22, compare nella Security List esaminata.**

La tabella **Regole di uscita** mostra una regola verso `0.0.0.0/0` per tutti i protocolli. Una regola **egress** non apre da sola la porta SSH alle nuove connessioni Internet in ingresso; può permettere traffico di risposta a connessioni avviate dall'istanza, per esempio Tailscale.

**Limitazione da non oltrepassare:** una subnet Oracle può avere *più Security Lists associate*, e una regola in qualsiasi lista può autorizzare il traffico; la VNIC precedente non mostrava NSG. Fonte [Oracle Security Lists](https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/securitylists.htm). **Non risulta ancora dalla nuova schermata un elenco esplicito e completo delle liste associate alla subnet della VPS.** Perciò la formulazione corretta è `EXAMINED_DEFAULT_LIST_PUBLIC_TCP22=NO`, non `OCI_ALL_INGRESS_TCP22_CLOSED=YES`.

**Prossima verifica in sola lettura**: sulla pagina della **subnet effettiva** della VNIC REMURA aprire `Dettagli` e individuare `Security Lists / Liste di sicurezza` *associate alla subnet*. Se solo la Default Security List è collegata, l'audit delle ACL Oracle per la porta 22 può essere chiuso come nessuna regola d'ingresso pubblico **sulla base della configurazione del momento**, fermo restando il firewall host. Se sono elencate altre liste, esaminare tutte le loro regole d'ingresso. Nessuna modifica, disabilitazione, o aggiunta di regole, NSG, IP o SSH.

**Gate:** `DEFAULT_SECURITY_LIST_TCP22=NOT_ALLOWED_IN_SCREENSHOT`, `SUBNET_ALL_ASSOCIATED_SECURITY_LISTS=NOT_ATTESTED`, `OCI_PUBLIC_SSH_EXPOSURE=NO_GO_UNTIL_ASSOCIATIONS`, `SSH_AUDIT=NO_GO`, `V165_RELEASE=NO_GO`, `C5=NO_GO`. Immagini mostrano dati operativi, ma nessun IP o dato personale è riportato qui. Nessun costo, risorsa OCI o accesso VPS introdotto da questa nota.
