# REMURA v0.8.16 — Piano di autorizzazione WEBHOOK REALE (NON ATTIVO)
**Aggiornamento: 13/11/2026, ore 13:11 CET**
**PR #102: DRAFT · Worker runtime v0.8.5 · sorgente v0.8.6 in GitHub · monitor main v0.8.14.**

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
- Cloudflare Access può imporre login sul Worker; TradingView invia webhook POST e non dispone nel normale alert di un login browser o dei custom header Access Service Token. Se esiste un Access login sul percorso webhook, il POST **non funzionerebbe senza un'architettura di accesso diversa**. L'esito 403 resta quindi una **possibile** spiegazione, non un fatto accertato. NON disabilitare Access senza piano separato e consenso.
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
