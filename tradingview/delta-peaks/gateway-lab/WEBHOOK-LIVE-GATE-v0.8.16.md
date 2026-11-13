# REMURA v0.8.18-doc — Piano di autorizzazione WEBHOOK REALE (NON ATTIVO)
**Aggiornamento: 13/11/2026, ore 13:58 CET — metadata API e Test Worker**
**PR #102: DRAFT · Worker runtime v0.8.5 · sorgente v0.8.6 in GitHub · monitor main v0.8.14.**

## Checkpoint Worker metadata GET — 13/11/2026 13:58 CET
- [Run #43428754941](https://github.com/mirkoworz/remura/actions/runs/43428754941): 11 test offline OK, API **GET autenticata** al Worker configurazione con token D1 Read esistente; esito `REMURA_WORKER_SETTINGS=INCONCLUSIVE_HTTP_403`. **Nessun permesso Worker Metadata confermato, nessuna risposta settings utilizzabile**. Il successo del workflow significa che il diniego è stato classificato correttamente; non equivale a verifica LIVE del Worker.
- Questo 403 riguarda **api.cloudflare.com** e non è la stessa sonda GET pubblica `workers.dev` già inconcludente: non attribuirlo al BIC di `workers.dev`. Presumibile carenza permessi Workers del token, ma non dimostrata in modo definitivo. **Non ripetere stesso test**.
- Preparato nuovo Worker di test **SOLO COME MANIFEST NON DEPLOYABILE**, `wrangler.webhook-test.EXAMPLE.json`: D1 `remura-tv-lab-test`, flag ingest OFF, UUID e limiter namespace placeholder, nessun segreto. Guard `predeploy_test_manifest_guard_v1.py` + test CI [#43429329813](https://github.com/mirkoworz/remura/actions/runs/43429329813) superati. Protegge contro target `remura-tv-lab` reale e flag ON.
- Prossima verifica dal proprietario, **solo quando indispensabile**: in Dashboard Worker Settings, mostrare **nomi e tipi dei binding e Variabili/Secrets senza aprire valori**. Non duplicare screenshot Domains & Routes già archiviato. I binding rate limiter potrebbero non apparire in dashboard (documentazione Cloudflare); per quelli servirà altro preflight prima di autorizzare distribuzione.
- Non creare token Workers Write né disabilitare Access; per un futuro permesso API, valutare esclusivamente Worker Metadata Read-Only su quel singolo Worker, se e solo se la UI non basta. Nessuna credenziale da inviare in chat.
- Tutto resta DRAFT, nessun deploy, nessuna scrittura D1, nessun alert TradingView.

## Nuovo checkpoint screenshot Cloudflare (13/11/2026 13:44 CET)
- `remura-tv-ingest-lab.mirkoworz.workers.dev` appare **Production** con `Anyone with this URL can visit` e `Enable Access`: **Access non abilitato nella vista specifica dell'URL Production**. Non è prova esaustiva su tutte le policy account-wide/hostname.
- `No custom domains` nella sezione Custom Domains and Routes; visibile un hostname Preview differente. Non serve acquistare dominio o aggiungere route per il laboratorio.
- Il vecchio `INCONCLUSIVE_EDGE_403` non va ripetuto: esito ancora inspiegato. Cloudflare documenta che Browser Integrity Check è applicato a `workers.dev` e che alcuni client automatizzati possono essere bloccati prima dell'esecuzione del Worker (anche senza Access). Questo è **un possibile meccanismo**, NON prova retrospettiva della causa del 403. Fonti: https://developers.cloudflare.com/workers/configuration/routing/workers-dev/ e https://developers.cloudflare.com/workers/configuration/cloudflare-access/.
- Nessun deploy, modifica alla configurazione Access, ai binding, agli alert TradingView o alle risorse Cloudflare da questa verifica. Prossimo controllo: lettura autentica metadata Worker e stato binding, minimizzando permessi; non chiedere un'altra foto delle stesse schermate.

## Stato dimostrato, non supposizioni
- Pine v0.8.1 compila, include `alert(payload, alert.freq_once_per_bar_close)` e opzioni telemetria/heartbeat impostate OFF. TradingView Premium/2FA: utente ha già confermato 2FA, non richiederla ancora.
- `remura-tv-ingest-lab` runtime v0.8.5 era raggiungibile da sessione utente con `accepting:false` e `disabled` nel checkpoint 12/11. La sonda runner GitHub ha dato **403/403 INCONCLUSIVE_EDGE_403**: NON dimostra che Access sia presente, attivo o non attivo, né che ingest sia oggi OFF.
- `remura-tv-lab` (principale, UE) e `remura-tv-lab-test` (TEST, UE) esistono. L'unica scrittura sintetica reale nota resta nel **TEST**; non cancellarla e non ripetere la prova.
- Budget Cloudflare D1 13/11: 2 DB / 57.344 byte; diario main v0.8.14 SUCCESS. Sono metadati veri, NON conferma tariffazione, piano effettivo né CPU per singolo POST.
- Run CI v0.8.16: Node con richiesta POST sintetica completa → FakeD1 → validazione e bridge Python, più lettore D1 `SELECT` simulato; NON è una consegna reale TradingView.
- Script `d1_preview_reader_v1.py` non ha entrypoint CLI, rifiuta senza `explicit_live_approval=True`, ed è escluso da ogni job con Secrets. Non accede al database principale in questa fase.

## Bloccanti *prima* di qualsiasi attivazione, da risolvere in ordine

### A. Configurazione autenticata del solo Worker (nuova strategia, NON sonda pubblica ripetuta)
- Leggere in sola lettura, con permessi minimi, **GET**
  `/accounts/{account_id}/workers/scripts/remura-tv-ingest-lab/settings` e la sua configurazione di accesso nel pannello Cloudflare. La documentazione API indica che è disponibile uno scope di tipo **Workers Metadata Read-Only/Workers Scripts Read** per la lettura; i GitHub Secrets oggi disponibili sono SOLO D1 Read e Account Analytics Read, **non presumere che autorizzino Workers Settings**.
- Verificare in modo autenticato: route/hostname e Cloudflare Access; `TELEMETRY_DB` associato a `remura-tv-lab`, eventuale `INGEST_ENABLED`, presenza di `WEBHOOK_TOKEN_SHA256` (solo nome, MAI valore), stato binding `INGEST_RATE_LIMITER`, versione Worker realmente distribuita. Alcuni dettagli non sono disponibili da un singolo endpoint: assenti → UNKNOWN.
- **Non esporre nei log** risposta integrale, script, binding secrets, token, URL segreto o corpo di richieste. Leggere, sanificare e pubblicare solo stati allowlisted.
- Nella schermata dell'utente, il collegamento `workers.dev` Production risulta **pubblico senza il pulsante di Access attivato**; non presumere login Access su quel collegamento. Una policy più ampia o regole di hostname richiederebbero comunque verifica specifica. Controllare separatamente BIC `workers.dev` e altre protezioni edge; non interpretare 403 come prova di una causa specifica e **non cambiare Access** per tentativi.
- Nessun token nuovo deve essere creato automaticamente o condiviso in chat. Prima valutare connettori Cloudflare autorizzati o la UI read-only già accessibile al proprietario; solo se davvero inevitabile scegliere il minimo permesso temporaneo.

### B. Contenimento Free prima del deploy
- Cloudflare Workers Free: **100.000 richieste/giorno account-wide**, CPU **10 ms/invocazione** documentati; un Worker pubblico anonimo può consumare richieste **prima** del controllo limiter eseguito nel codice.
- Workers Rate Limiting binding: namespace ID **stringa contenente intero positivo univoco**, `period=10|60`, limite per *Cloudflare location*, NON globale certo. Non inventare namespace e non assimilare Rate Limiting API a regole WAF del proprio dominio. Disponibilità nell'account e costo effettivo: **DA VERIFICARE** prima di attivarlo.
- `workers.dev` è adatto a prototipi/hobby, non lo diamo per equivalente ad un servizio production security-hardened.
- Ingestione deve rimanere `INGEST_ENABLED` OFF fino a test di configurazione, protezione edge e autorizzazione scritta. Non cambiare DB principale o Filoni A/B/C.

### C. Primo test HTTP reale strettamente isolato (richiede consenso specifico)
1. Decidere una destinazione **solo TEST**, con binding D1 TEST, secret separato se necessario, rate limiter e regole IP; nessun dato prospettico in `remura-tv-lab` nel primo tentativo.
2. Rilasciare una versione Worker fail-closed (ingest OFF), verificare bindings/config autenticati senza trasmettere segreti. Avere percorso di rollback testato. Nessun cambio al Worker principale v0.8.5 se non autorizzato separatamente.
3. **Solo dopo** consenso: permettere un POST originato davvero da TradingView verso endpoint test, usando messaggio JSON v0.8.1 (contenuto senza password), controllare registro TradingView e riga D1 TEST. Attenzione: runner GitHub NON è una IP TradingView autorizzata, e non può sostituire questa prova.
4. Registrare latenza effettiva (TradingView interrompe dopo 3s), status (accepted / duplicate / rejected), CPU/quote del Worker, ricevuta D1 e identità evento. Se fallisce o è incerto: NON abilitare il database principale.
5. Per una raccolta prospettica completa attivare successivamente anche heartbeat M5 solo se quota e piano di retention lo consentono. Consegne perse e missing devono restare osservabili.

### D. REMURA analizza, ma NON fa trading
- Preparato `d1_preview_reader_v1.py` `SELECT` limitato e ordinato, massimo 100 righe, intervallo ≤ 24 ore, rifiuto pagine incomplete. Necessita un'attivazione read-only deliberata per il DB principale, senza introdurre scritture o Secrets nei log.
- `remura_tv_bridge_preview_v1.py` può convertire in **osservazioni**, non ancora in segnali. Necessari campioni prospettici reali, collegamento B/C sotto coordinamento, baseline, test out-of-sample, falsi positivi e notifiche. Non creare percentuali di vittoria senza dati.
- Ogni milestone: versione+data/ora italiane, prova offline distinta da prova live e audit dei costi. **Nessun ordine autorizzato**.

## Fonti ufficiali verificate 13/11/2026
- TradingView webhook (IP, 2FA, POST JSON, 80/443, timeout 3s): https://it.tradingview.com/support/solutions/43000529348/
- Worker settings GET, Workers Metadata Read-Only: https://developers.cloudflare.com/api/resources/workers/subresources/scripts/subresources/script_and_version_settings/
- Cloudflare Access per Workers e ordine delle policy: https://developers.cloudflare.com/workers/configuration/cloudflare-access/
- Rate Limiting binding, semantica per località: https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/
- workers.dev e Access: https://developers.cloudflare.com/workers/configuration/routing/workers-dev/
- Workers Free pricing/limits: https://developers.cloudflare.com/workers/platform/pricing/

**Stato attuale: LIVE WEBHOOK BLOCCATO; nessun manuale richiesto finché non è pronta una procedura autenticata e strettamente necessaria.**
